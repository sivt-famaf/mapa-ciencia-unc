import json
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
    created_summaries = 0
    skipped_summaries = {}
    failed_summaries = []
    for researcher_id, content in payload.content_mapping.items():
        try:
            researcher = await Researcher.get(
                PydanticObjectId(researcher_id), fetch_links=False
            )
            if not researcher:
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
                    skipped_summaries[researcher_id] = "Summary with tag already exists"
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
        except Exception:
            failed_summaries.append(researcher_id)

    return {
        "created_summaries": created_summaries,
        "skipped_summaries": skipped_summaries,
        "failed_summaries": failed_summaries,
    }
