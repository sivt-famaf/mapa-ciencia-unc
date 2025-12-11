from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from mapa_ciencia_unc.controllers.graph import get_researcher_graph
from mapa_ciencia_unc.models.researcher import Researcher, ResearcherPublicView
from beanie import PydanticObjectId

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter(tags=["frontend"])


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})


@router.get("/graph", response_class=HTMLResponse)
async def graph_view(request: Request, tag: str | None = None):
    try:
        graph = get_researcher_graph(tag=tag)
    except ValueError as e:
        # No graphs available or specific tag not found
        error_message = str(e)
        if "No available graphs" in error_message:
            return templates.TemplateResponse(
                "404.html",
                {
                    "request": request,
                    "error_code": "404",
                    "title": "No hay gráficos disponibles",
                    "message": "Actualmente no hay gráficos de red disponibles. Los gráficos se generan a partir de embeddings de investigadores.",
                },
                status_code=404,
            )
        else:
            # Specific tag not found
            return templates.TemplateResponse(
                "404.html",
                {
                    "request": request,
                    "error_code": "404",
                    "title": "Gráfico no encontrado",
                    "message": f"El gráfico solicitado '{tag}' no existe.",
                    "additional_info": "Verificá que el identificador del gráfico sea correcto.",
                    "show_graph_link": True,
                },
                status_code=404,
            )
    return templates.TemplateResponse(
        "graph.html", {"request": request, "graph": graph.model_dump()}
    )


@router.get("/other", response_class=HTMLResponse)
async def other(request: Request):
    return templates.TemplateResponse("other.html", {"request": request})


@router.get("/researcher/{researcher_id}", response_class=HTMLResponse)
async def researcher_view(request: Request, researcher_id: str, tag: str | None = None):
    researcher_doc = await Researcher.find_one({"_id": PydanticObjectId(researcher_id)})

    if not researcher_doc:
        return HTMLResponse(content="Researcher not found", status_code=404)

    researcher_public_view = ResearcherPublicView.from_researcher(
        researcher_doc, tag=tag
    )

    return templates.TemplateResponse(
        "researcher.html",
        {"request": request, "researcher": researcher_public_view.model_dump()},
    )
