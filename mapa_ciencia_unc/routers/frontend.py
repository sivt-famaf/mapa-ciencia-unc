from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from mapa_ciencia_unc.controllers.graph import get_researcher_graph
from mapa_ciencia_unc.controllers.researchers import get_similar_researchers
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
async def graph_view(request: Request, graph_key: str | None = None):
    graph = get_researcher_graph(graph_key=graph_key)
    return templates.TemplateResponse(
        "graph.html", {"request": request, "graph": graph.model_dump()}
    )


@router.get("/other", response_class=HTMLResponse)
async def other(request: Request):
    return templates.TemplateResponse("other.html", {"request": request})


@router.get("/researcher/{researcher_id}", response_class=HTMLResponse)
async def researcher_view(
    request: Request,
    researcher_id: str,
    graph_key: str | None = None,
):
    researcher_doc = await Researcher.find_one({"_id": PydanticObjectId(researcher_id)})

    if not researcher_doc:
        return HTMLResponse(content="Researcher not found", status_code=404)

    model = graph_key.split("_")[-1] if graph_key else None
    tag = "_".join(graph_key.split("_")[:-1]) if graph_key else None

    researcher_public_view = ResearcherPublicView.from_researcher(
        researcher_doc, tag=tag, model=model
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
            "graph_key": graph_key,
        },
    )
