from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from mapa_ciencia_unc.controllers.graph import get_researcher_graph
from mapa_ciencia_unc.models.researcher import Researcher, ResearcherPublicView
from mapa_ciencia_unc.models.project import ProjectExtractedIntro
from beanie import PydanticObjectId

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter(tags=["frontend"])


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})


@router.get("/graph", response_class=HTMLResponse)
async def graph_view(request: Request, tag: str | None = None):
    graph = get_researcher_graph(tag=tag)
    return templates.TemplateResponse(
        "graph.html", {"request": request, "graph": graph.model_dump()}
    )


@router.get("/other", response_class=HTMLResponse)
async def other(request: Request):
    return templates.TemplateResponse("other.html", {"request": request})


import numpy as np


async def get_similar_researchers(cuit: str, tag: str, model: str, n: int = 3):
    # 1. Get the target researcher and their specific vector
    target_researcher = await Researcher.find_one({"cuit": cuit})
    if not target_researcher:
        return []

    try:
        target_emb_obj = next(
            e for e in target_researcher.embeddings if e.tag == tag and e.model == model
        )
        target_vector = np.array(target_emb_obj.vector)
    except StopIteration:
        return []  # Or raise an error: specific embedding not found

    # 2. Fetch all candidates who have the matching tag/model
    # We fetch only the fields we need to keep memory usage low
    cursor = Researcher.find(
        {
            "cuit": {"$ne": cuit},
            "embeddings": {"$elemMatch": {"tag": tag, "model": model}},
        }
    )

    similarities = []

    async for researcher in cursor:
        # Find the specific embedding within the candidate's list
        candidate_emb = next(
            e for e in researcher.embeddings if e.tag == tag and e.model == model
        )
        candidate_vector = np.array(candidate_emb.vector)

        # 3. Compute Cosine Similarity using NumPy
        # Formula: (A dot B) / (norm(A) * norm(B))
        dot_product = np.dot(target_vector, candidate_vector)
        norm_target = np.linalg.norm(target_vector)
        norm_candidate = np.linalg.norm(candidate_vector)

        similarity = dot_product / (norm_target * norm_candidate)

        similarities.append({"researcher": researcher, "similarity": float(similarity)})

    # 4. Sort by similarity descending and return top N
    similarities.sort(key=lambda x: x["similarity"], reverse=True)

    return [
        {
            "name": r["researcher"].name,
            "last_name": r["researcher"].last_name,
            "research_center": r["researcher"].research_center,
            "researcher_id": str(r["researcher"].id),
        }
        for r in similarities[:n]
    ]


@router.get("/researcher/{researcher_id}", response_class=HTMLResponse)
async def researcher_view(request: Request, researcher_id: str, tag: str | None = None):
    researcher_doc = await Researcher.find_one({"_id": PydanticObjectId(researcher_id)})

    if not researcher_doc:
        return HTMLResponse(content="Researcher not found", status_code=404)

    researcher_public_view = ResearcherPublicView.from_researcher(
        researcher_doc, tag=tag
    )

    project_files = await ProjectExtractedIntro.find(
        {"cuit": researcher_doc.cuit}
    ).to_list()

    projects = [
        {
            "codigo_tramite": project.codigo_tramite,
            "intro": project.extracted_intro,
            "download_url": f"/api/projects/download_project_file/?reseacher_id={researcher_id}&codigo_tramite={project.codigo_tramite}",
        }
        for project in project_files
    ]

    model = "gemini"
    similar_researchers = await get_similar_researchers(
        cuit=researcher_doc.cuit, tag=tag, model=model, n=3
    )

    return templates.TemplateResponse(
        "researcher.html",
        {
            "request": request,
            "researcher": researcher_public_view.model_dump(),
            "projects": projects,
            "similar_researchers": similar_researchers,
            "tag": tag,
        },
    )
