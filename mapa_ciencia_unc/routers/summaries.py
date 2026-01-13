import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from beanie import PydanticObjectId

from mapa_ciencia_unc.auth import require_auth
from mapa_ciencia_unc.llms.utils import (
    process_articles,
    process_project_intros,
    process_projects,
)
from mapa_ciencia_unc.models.summary import MultipleSummariesCreate, Summary
from mapa_ciencia_unc.models.researcher import Researcher
from mapa_ciencia_unc.models.article import Article
from mapa_ciencia_unc.models.project import Project, ProjectExtractedIntro

from mapa_ciencia_unc.models.summary import SummaryRequest
from mapa_ciencia_unc.llms.summary_generator import (
    SummaryGenerator,
)
from mapa_ciencia_unc.config import SYSTEMS_DIR, USER_PROMPTS_DIR

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/api/summaries", tags=["summaries"], dependencies=[Depends(require_auth)]
)


@router.post("/generate")
async def generate_summaries(req: SummaryRequest):
    """
    Generate and persist a summary for a researcher using LLM or template-based generation.

    Retrieves a researcher's profile, articles, and projects from the database,
    processes the data through the specified model, and stores the generated summary.
    The summary replaces any existing summary with the same tag.

    **Process:**
    1. Validates system instruction and prompt template files exist
    2. Fetches researcher by ID
    3. Retrieves all articles, projects, and project intros for the researcher (matched by CUIT)
    4. Processes articles, projects, and intros into context format (sorted by date, newest first)
    5. Applies optional limits on number of items and word counts
    6. Generates summary using specified model
    7. Removes any existing summary with the same tag
    8. Stores the new summary with the researcher

    **Supported Models:**
    - **Gemini models**: "gemini-2.5-flash", "gemini-2.5-pro", etc.
      - Requires both system_name and prompt_name
    - **Ollama models**: "gemma3:4b", "llama3.1", etc.
    - **Full-text**: "full-text": No LLM processing, renders Jinja template with
      researcher's raw data

    **Request Body:**
    - `researcher_id`: MongoDB ObjectId of the researcher (required)
    - `model`: Model identifier (e.g., "gemini-2.5-flash", "gemma3:4b", "full-text")
    - `tag`: Tag to assign to the summary (e.g., "user_academic_v1")
    - `prompt_name`: Name of the prompt template (e.g., "v2/user_academic")
    - `system_name`: Name of the system instruction template (optional for Ollama/full-text)
    - `max_articles`: Maximum number of articles to include (optional)
    - `max_articles_length`: Maximum number of words per article abstract (optional)
    - `max_projects`: Maximum number of projects to include (optional)
    - `max_projects_length`: Maximum number of words per project summary (optional)
    - `max_intros`: Maximum number of project intros to include (optional)
    - `max_intros_length`: Maximum number of words per project intro (optional)

    **Returns:**
    - `researcher_id`: ID of the researcher
    - `tag`: Tag assigned to the summary
    - `model`: Model used for generation
    - `summary`: Generated summary content (JSON string or text)

    **Raises:**
    - `404 Not Found`: Researcher not found
    - `FileNotFoundError`: Template file missing
    ```
    """
    # Optional system_name
    if req.system_name:
        system_path = SYSTEMS_DIR / f"{req.system_name}.jinja"
        if req.system_name and not system_path.exists():
            raise FileNotFoundError(f"System instruction missing: {system_path}")

    # Mandatory prompt
    prompt_path = USER_PROMPTS_DIR / f"{req.prompt_name}.jinja"
    if not prompt_path.exists():
        raise FileNotFoundError(f"User prompt template missing: {prompt_path}")

    # Search objects in db
    researcher = await Researcher.get(
        PydanticObjectId(req.researcher_id),
        fetch_links=False,
    )
    if not researcher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Researcher not found.",
        )

    articles = await Article.find(Article.cuit == researcher.cuit).to_list()
    projects = await Project.find(Project.cuit == researcher.cuit).to_list()
    projects_intro = await ProjectExtractedIntro.find(
        ProjectExtractedIntro.cuit == researcher.cuit
    ).to_list()
    context = {
        "researcher": {
            "research_area": researcher.research_area,
            "last_project_title": researcher.last_project_title,
        },
        "publications": process_articles(
            articles,
            max_length=req.max_articles_length,
            max_articles=req.max_articles
        ),
        "projects": process_projects(
            projects,
            max_length=req.max_projects_length,
            max_projects=req.max_projects
        ),
        "projects_intro": process_project_intros(
            projects_intro,
            max_length=req.max_intros_length,
            max_intros=req.max_intros
        ),
    }

    content = SummaryGenerator.generate_researcher_summary(
        context, system_path, prompt_path, model_name=req.model
    )
    if not isinstance(content, str):
        content = json.dumps(content)

    new_summary = Summary.from_content(
        model=req.model,
        tag=req.tag,
        content=content,
    )

    researcher.summaries = [s for s in researcher.summaries if s.tag != req.tag]
    researcher.summaries.append(new_summary)

    await researcher.save()

    return {
        "researcher_id": str(researcher.id),
        "tag": req.tag,
        "model": req.model,
        "summary": content,
    }


@router.post("/upload/bulk", response_model=dict)
async def upload_multiple_summaries(payload: MultipleSummariesCreate):
    """
    Upload multiple summaries to researchers in bulk.

    This endpoint accepts a mapping of researcher identifiers to summary content
    and creates or updates summaries for multiple researchers in a single request.

    - Tries to find researcher by `researcher_id` (MongoDB ObjectId) first
    - If not found or invalid ObjectId, tries to find by `cuit` (CUIT identifier)
    - This allows flexibility in how researchers are identified
    - With `overwrite=True`: Replaces existing summaries with the same tag
    - With `overwrite=False`: Skips researchers who already have a summary with the same tag

    **Request Body:**
    - `content_mapping`: Dictionary mapping researcher identifier (ID or CUIT) to summary JSON string
    - `tag`: Tag to assign to all summaries (e.g., "user_academic_v1")
    - `model`: Model name used to generate summaries (e.g., "gemini-2.5-flash")
    - `overwrite`: Whether to replace existing summaries with the same tag (default: False)

    **Returns:**
    - `created_summaries`: Count of successfully created summaries
    - `skipped_summaries`: Dictionary of researcher_id -> reason for skipping
    - `failed_summaries`: List of researcher identifiers that failed
    """
    created_summaries = 0
    skipped_summaries = {}
    failed_summaries = []

    for identifier, content in payload.content_mapping.items():
        try:
            researcher = None

            # Try to find by researcher_id (ObjectId) first
            try:
                researcher = await Researcher.get(
                    PydanticObjectId(identifier), fetch_links=False
                )
            except Exception:
                # Not a valid ObjectId, try finding by CUIT
                pass

            # If not found by ID, try finding by CUIT
            if not researcher:
                researcher = await Researcher.find_one(
                    Researcher.cuit == identifier, fetch_links=False
                )

            # If still not found, mark as failed
            if not researcher:
                failed_summaries.append(identifier)
                logger.warning(f"Researcher with identifier '{identifier}' not found")
                continue

            summary = Summary.from_content(
                model=payload.model,
                tag=payload.tag,
                content=content,
            )

            if not payload.overwrite:
                # Check if a summary with the same model and tag already exists
                existing_summary = next(
                    (
                        s
                        for s in researcher.summaries
                        if s.model == payload.model and s.tag == payload.tag
                    ),
                    None,
                )
                if existing_summary:
                    skipped_summaries[identifier] = "Summary with tag already exists"
                    continue  # Skip creating this summary

            if payload.overwrite:
                # Remove existing summaries with the same model and tag
                researcher.summaries = [
                    s
                    for s in researcher.summaries
                    if not (s.model == payload.model and s.tag == payload.tag)
                ]

            researcher.summaries.append(summary)

            await researcher.save()
            created_summaries += 1
        except Exception as e:
            failed_summaries.append(identifier)
            logger.error(f"Error processing researcher '{identifier}': {e}")

    return {
        "created_summaries": created_summaries,
        "skipped_summaries": skipped_summaries,
        "failed_summaries": failed_summaries,
    }


@router.delete("/tag/{tag}")
async def delete_summaries_by_tag(tag: str):
    """
    Delete all summaries with the specified tag across all researchers.

    Finds all researchers with summaries matching the given tag and removes them.
    Useful for cleanup or regenerating summaries with different parameters.

    Args:
        tag: Tag identifier for summaries to delete (e.g., "user_academic_v1", "test-summaries")

    Returns:
        - deleted_count: Number of summaries deleted
        - researchers_affected: Number of researchers that had summaries removed

    Example:
    ```
    DELETE /api/summaries/tag/user_academic_v1
    ```

    Returns:
    ```json
    {
        "deleted_count": 150,
        "researchers_affected": 150
    }
    ```
    """
    researchers = await Researcher.find({}).to_list()

    deleted_count = 0
    researchers_affected = 0

    for researcher in researchers:
        # Count summaries with this tag
        summaries_before = len(researcher.summaries)

        # Remove summaries with the specified tag
        researcher.summaries = [
            s for s in researcher.summaries if s.tag != tag
        ]

        summaries_after = len(researcher.summaries)
        summaries_removed = summaries_before - summaries_after

        # Save if summaries were removed
        if summaries_removed > 0:
            await researcher.save()
            deleted_count += summaries_removed
            researchers_affected += 1

    return {
        "deleted_count": deleted_count,
        "researchers_affected": researchers_affected,
    }
