import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from beanie import PydanticObjectId

from mapa_ciencia_unc.auth import require_auth
from mapa_ciencia_unc.llms.utils import build_researcher_llm_inputs
from mapa_ciencia_unc.models.summary import MultipleSummariesCreate, Summary
from mapa_ciencia_unc.models.researcher import Researcher
from mapa_ciencia_unc.models.article import Article
from mapa_ciencia_unc.models.project import Project

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
    Generate a summary for a single researcher using data stored in MongoDB.

    For Ollama models, system_name can be None or omitted since the combined prompt
    template includes both system instruction and user prompt.
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
    context = build_researcher_llm_inputs(
        articles=articles,
        projects=projects,
    )

    content = SummaryGenerator.generate_researcher_summary(
        context, system_path, prompt_path, model_name=req.model
    )
    if not isinstance(content, str):
        content = json.dumps(content)

    new_summary = Summary(
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


@router.post("/bulk", response_model=dict)
async def create_multiple_summaries(payload: MultipleSummariesCreate):
    """
    Upload multiple summaries to researchers in bulk.

    This endpoint accepts a mapping of researcher identifiers to summary content
    and creates or updates summaries for multiple researchers in a single request.

    **Researcher Identification:**
    - Tries to find researcher by `researcher_id` (MongoDB ObjectId) first
    - If not found or invalid ObjectId, tries to find by `cuit` (CUIT identifier)
    - This allows flexibility in how researchers are identified

    **Request Body:**
    - `content_mapping`: Dictionary mapping researcher identifier (ID or CUIT) to summary JSON string
    - `tag`: Tag to assign to all summaries (e.g., "user_academic_v1")
    - `model`: Model name used to generate summaries (e.g., "gemini-2.5-flash")
    - `overwrite`: Whether to replace existing summaries with the same tag (default: False)

    **Behavior:**
    - With `overwrite=True`: Replaces existing summaries with the same tag
    - With `overwrite=False`: Skips researchers who already have a summary with the same tag

    **Returns:**
    - `created_summaries`: Count of successfully created summaries
    - `skipped_summaries`: Dictionary of researcher_id -> reason for skipping
    - `failed_summaries`: List of researcher identifiers that failed

    **Example Request:**
    ```json
    {
        "content_mapping": {
            "507f1f77bcf86cd799439011": "{\"brief\": \"...\", \"profile\": \"...\", \"areas\": [...]}",
            "27273268885": "{\"brief\": \"...\", \"profile\": \"...\", \"areas\": [...]}"
        },
        "tag": "user_academic_v1",
        "model": "gemini-2.5-flash",
        "overwrite": false
    }
    ```

    **Notes:**
    - The first key uses researcher_id (MongoDB ObjectId)
    - The second key uses CUIT (will be looked up automatically)
    - Summary content should be a JSON string (will be stored as-is)
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

            summary = Summary(
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
