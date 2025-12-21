from fastapi import APIRouter, Depends, HTTPException, status
from beanie import PydanticObjectId
from pathlib import Path

from mapa_ciencia_unc.auth import require_auth
from mapa_ciencia_unc.models.summary import Summary
from mapa_ciencia_unc.models.researcher import Researcher
from mapa_ciencia_unc.models.article import Article
from mapa_ciencia_unc.models.project import Project

from mapa_ciencia_unc.models.summary import SummaryRequest
from mapa_ciencia_unc.llms.summary_generator import (
    generate_researcher_summary, 
    build_researcher_llm_inputs
)
from mapa_ciencia_unc.config import SYSTEMS_DIR, USER_PROMPTS_DIR


router = APIRouter(
    prefix="/api/summaries",
    tags=["summaries"],
    dependencies=[Depends(require_auth)])

@router.post(
    "/generate-summaries",
)

async def generate_summaries(req: SummaryRequest):
    """
    Generate a summary for a single researcher using data stored in MongoDB.
    """

    researcher = await Researcher.get(
        PydanticObjectId(req.researcher_id),
        fetch_links=False,
    )

    if not researcher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Researcher not found.",
        )

    articles = await Article.find(
        Article.researcher_id == researcher.id
    ).to_list()

    projects = await Project.find(
        Project.cuit == researcher.cuit
    ).to_list()

    context = build_researcher_llm_inputs(
        articles=articles,
        projects=projects,
    )

    system_path = SYSTEMS_DIR / f"{req.system_name}.jinja"
    prompt_path = USER_PROMPTS_DIR / f"{req.prompt_name}.jinja"

    content = generate_researcher_summary(
        info_completa_investigador=context,
        system_instruction_path=system_path,
        prompt_path=prompt_path,
    )

    new_summary = Summary(
        model=req.model,
        tag=req.tag,
        content=content,
    )

    researcher.summaries = [
        s for s in researcher.summaries if s.tag != req.tag
    ]
    researcher.summaries.append(new_summary)

    await researcher.save()

    return {
        "researcher_id": str(researcher.id),
        "tag": req.tag,
        "model": req.model,
        "summary": content,
    }
