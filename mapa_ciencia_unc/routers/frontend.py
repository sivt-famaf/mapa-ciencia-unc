from pathlib import Path

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates

from mapa_ciencia_unc.controllers.researchers import get_similar_researchers
from mapa_ciencia_unc.models.researcher import Researcher, ResearcherPublicView
from mapa_ciencia_unc.models.project import ProjectExtractedIntro
from mapa_ciencia_unc.models.article import Article
from mapa_ciencia_unc.models.graph import ResearcherGraph, ResearcherGraphListItem
from beanie import PydanticObjectId
from mapa_ciencia_unc.auth import verify_jwt_token


BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _extract_bearer_token(request: Request) -> str | None:
    """Return bearer token from Authorization header or cookie."""
    auth_header = request.headers.get("Authorization")
    if auth_header:
        scheme, _, credentials = auth_header.partition(" ")
        if scheme.lower() == "bearer" and credentials:
            return credentials.strip()

    cookie_token = request.cookies.get("token")
    if cookie_token:
        return cookie_token

    return None


def _token_is_valid(request: Request) -> bool:
    token = _extract_bearer_token(request)
    if not token:
        return False

    try:
        verify_jwt_token(token)
        return True
    except HTTPException:
        return False


REDIRECT_TO_LOGIN = RedirectResponse(url="/login", status_code=303)
router = APIRouter(tags=["frontend"])


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if not _token_is_valid(request):
        return REDIRECT_TO_LOGIN
    return templates.TemplateResponse("home.html", {"request": request})


@router.get("/graph", response_class=HTMLResponse)
async def graph_view(request: Request, graph_id: str | None = None):
    if not _token_is_valid(request):
        return REDIRECT_TO_LOGIN
    if graph_id:
        graph = await ResearcherGraph.find_one({"_id": PydanticObjectId(graph_id)})
        if not graph:
            raise HTTPException(status_code=404, detail="Graph not found")
    else:
        graph = await ResearcherGraph.find_one({})
        if not graph:
            raise HTTPException(
                status_code=404,
                detail=f"No graph found in database. Create a graph first.",
            )

    graph_json = graph.model_dump()
    graph_json["id"] = str(graph_json.get("id", None))

    return templates.TemplateResponse(
        "graph.html",
        {
            "request": request,
            "graph": graph_json,
        },
    )


@router.get("/other", response_class=HTMLResponse)
async def other(request: Request):
    if not _token_is_valid(request):
        return REDIRECT_TO_LOGIN
    return templates.TemplateResponse("other.html", {"request": request})


@router.get("/researcher/{researcher_id}", response_class=HTMLResponse)
async def researcher_view(
    request: Request,
    researcher_id: str,
    graph_id: str | None = None,
):
    if not _token_is_valid(request):
        return REDIRECT_TO_LOGIN
    researcher_doc = await Researcher.find_one({"_id": PydanticObjectId(researcher_id)})

    if not researcher_doc:
        return HTMLResponse(content="Researcher not found", status_code=404)

    graph = (
        await ResearcherGraph.find_one(
            {"_id": PydanticObjectId(graph_id)},
            projection_model=ResearcherGraphListItem,
        )
        if graph_id
        else None
    )

    if not graph:
        return HTMLResponse(content="Graph id not found", status_code=404)

    researcher_public_view = ResearcherPublicView.from_researcher(
        researcher_doc, summary_tag=graph.summary.tag, summary_model=graph.summary.model
    )

    project_files = await ProjectExtractedIntro.find(
        {"cuit": researcher_doc.cuit}
    ).to_list()

    articles = await Article.find(
        {"cuit": researcher_doc.cuit},
    ).to_list()

    articles_list = [
        {
            "titulo": article.titulo,
            "resumen": article.resumen,
            "issn": article.issn,
            "eissn": article.eissn,
            "year": article.year,
            "editorial": article.editorial,
        }
        for article in articles
    ]

    projects = [
        {
            "codigo_tramite": project.codigo_tramite,
            "intro": project.extracted_intro,
            "download_url": f"/download_project_file/?researcher_id={researcher_id}&codigo_tramite={project.codigo_tramite}",
        }
        for project in project_files
    ]

    similar_researchers = await get_similar_researchers(
        cuit=researcher_doc.cuit,
        tag=graph.embedding.tag,
        model=graph.embedding.model,
        n=3,
    )

    return templates.TemplateResponse(
        "researcher.html",
        {
            "request": request,
            "researcher": researcher_public_view.model_dump(),
            "projects": projects,
            "articles": articles_list,
            "similar_researchers": similar_researchers,
            "graph_id": graph_id,
        },
    )


@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


PROJECT_FILE_DIRECTORY = Path("./project_files").resolve()


@router.get("/download_project_file/")
async def download_file(request: Request, researcher_id: str, codigo_tramite: str):
    if not _token_is_valid(request):
        return REDIRECT_TO_LOGIN
    # get researcher cuit
    researcher = await Researcher.find_one({"_id": PydanticObjectId(researcher_id)})
    if not researcher:
        raise HTTPException(status_code=404, detail="Researcher not found")

    cuit = researcher.cuit

    # find file name from ProjectExtractedIntro
    intro_entry = await ProjectExtractedIntro.find_one(
        {
            "cuit": cuit,
            "codigo_tramite": codigo_tramite,
        }
    )
    if not intro_entry:
        raise HTTPException(status_code=404, detail="File not found")

    filename = intro_entry.file_name
    file_path = PROJECT_FILE_DIRECTORY / filename

    # Security Check: Prevent Directory Traversal attacks
    if not str(file_path).startswith(str(PROJECT_FILE_DIRECTORY)):
        raise HTTPException(status_code=403, detail="Access denied")

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return_filename = f"{codigo_tramite}.{file_path.suffix.lstrip('.')}"

    # Return the file as a response
    return FileResponse(
        path=file_path,
        filename=return_filename,
        media_type="application/octet-stream",
    )
