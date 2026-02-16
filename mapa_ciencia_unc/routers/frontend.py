from pathlib import Path
from typing import List

from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from mapa_ciencia_unc.controllers.researchers import get_similar_researchers
from mapa_ciencia_unc.controllers.portfolio import get_portfolio_context
from mapa_ciencia_unc.llms.portfolio_generator import PortfolioGeneratorOllama
from mapa_ciencia_unc.models.researcher import Researcher, ResearcherPublicView
from mapa_ciencia_unc.models.project import ProjectExtractedIntro
from mapa_ciencia_unc.models.article import Article
from mapa_ciencia_unc.models.graph import ResearcherGraph
from beanie import PydanticObjectId
from mapa_ciencia_unc.auth import verify_jwt_token
from mapa_ciencia_unc.services.embedding_index import get_embedding_index_manager
from mapa_ciencia_unc.llms.embedding_generator import EmbeddingGenerator
from mapa_ciencia_unc.config import (
    DEFAULT_EMBEDDING_TAG,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_SUMMARY_TAG,
    DEFAULT_SUMMARY_MODEL,
    DEFAULT_GRAPH_TAG,
)


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


class ResearcherSearchResult(BaseModel):
    """Search result for a single researcher."""
    researcher_id: str = Field(description="Researcher's unique identifier")
    name: str = Field(description="Researcher's first name")
    last_name: str = Field(description="Researcher's last name")
    research_center: str = Field(description="Research center affiliation")
    research_area: str | None = Field(description="Research area")
    summary_brief: str | None = Field(description="Brief summary of researcher")
    summary_content: str | None = Field(description="Full summary content of researcher")
    distance: float = Field(description="Distance from query (lower is more similar)")
    similarity_score: float = Field(description="Similarity score (0-1, higher is more similar)")


class SemanticSearchResponse(BaseModel):
    """Response from semantic search."""
    query: str = Field(description="The original query text")
    model: str = Field(description="Embedding model used")
    tag: str = Field(description="Embedding tag used")
    results: List[ResearcherSearchResult] = Field(description="Top matching researchers")
    total_results: int = Field(description="Number of results returned")


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
    summary_tag: str = Query(DEFAULT_SUMMARY_TAG, description="Summary tag to retrieve"),
    summary_model: str = Query(DEFAULT_SUMMARY_MODEL, description="Summary model to retrieve"),
    embedding_tag: str = Query(DEFAULT_EMBEDDING_TAG, description="Embedding tag for similar researchers"),
    embedding_model: str = Query(DEFAULT_EMBEDDING_MODEL, description="Embedding model for similar researchers"),
):
    if not _token_is_valid(request):
        return REDIRECT_TO_LOGIN
    researcher_doc = await Researcher.find_one({"_id": PydanticObjectId(researcher_id)})

    if not researcher_doc:
        return HTMLResponse(content="Researcher not found", status_code=404)

    researcher_public_view = ResearcherPublicView.from_researcher(
        researcher_doc, summary_tag=summary_tag, summary_model=summary_model
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
        tag=embedding_tag,
        model=embedding_model,
        n=3,
        summary_tag=summary_tag,
        summary_model=summary_model,
    )

    return templates.TemplateResponse(
        "researcher.html",
        {
            "request": request,
            "researcher": researcher_public_view.model_dump(),
            "projects": projects,
            "articles": articles_list,
            "similar_researchers": similar_researchers,
            "summary_tag": summary_tag,
            "summary_model": summary_model,
            "embedding_tag": embedding_tag,
            "embedding_model": embedding_model,
        },
    )


@router.get("/search", response_class=HTMLResponse)
async def search_page(request: Request):
    """Page for searching researchers by profile characteristics."""
    if not _token_is_valid(request):
        return REDIRECT_TO_LOGIN
    return templates.TemplateResponse("search.html", {
        "request": request,
        "default_embedding_tag": DEFAULT_EMBEDDING_TAG,
        "default_embedding_model": DEFAULT_EMBEDDING_MODEL,
        "default_summary_tag": DEFAULT_SUMMARY_TAG,
        "default_summary_model": DEFAULT_SUMMARY_MODEL,
        "default_graph_tag": DEFAULT_GRAPH_TAG,
    })


@router.get("/api/search/by-name", response_model=SemanticSearchResponse)
async def search_by_name(
    request: Request,
    name: str = Query(..., description="Name or last name to search", min_length=1),
    n: int = Query(10, ge=1, le=100, description="Number of results to return (1-100)"),
    summary_tag: str = Query("complete", description="Summary tag to retrieve"),
    summary_model: str = Query("gemini-2.5-pro", description="Summary model to retrieve"),
):
    """
    Search researchers by name or last name.

    This endpoint searches for researchers whose name or last name contains the search term.
    Results are sorted alphabetically by last name, then by name.

    **Query Parameters:**
    - `name`: Text to search in researcher names (case-insensitive)
    - `n`: How many results to return (default: 10, max: 100)
    - `summary_tag`: Which summary tag to retrieve
    - `summary_model`: Which summary model to retrieve

    **Returns:**
    Similar format to semantic search, but with distance and similarity_score set to 0.
    """
    # Search for researchers by name (case-insensitive)
    # Use regex for case-insensitive search
    search_pattern = {"$regex": name, "$options": "i"}

    researchers = await Researcher.find(
        {
            "$or": [
                {"name": search_pattern},
                {"last_name": search_pattern},
            ]
        },
        fetch_links=False
    ).sort([("last_name", 1), ("name", 1)]).limit(n).to_list()

    # Build response
    results = []
    for researcher in researchers:
        # Extract summary brief and content if available
        summary_brief_text = None
        summary_content_text = None
        summary_obj = next(
            (
                s
                for s in researcher.summaries
                if s.tag == summary_tag and s.model == summary_model
            ),
            None,
        )
        if summary_obj:
            summary_brief_text = summary_obj.brief
            summary_content_text = summary_obj.content

        results.append(
            ResearcherSearchResult(
                researcher_id=str(researcher.id),
                name=researcher.name,
                last_name=researcher.last_name,
                research_center=researcher.research_center,
                research_area=researcher.research_area,
                summary_brief=summary_brief_text,
                summary_content=summary_content_text,
                distance=0.0,  # Not applicable for name search
                similarity_score=1.0,  # Not applicable for name search
            )
        )

    return SemanticSearchResponse(
        query=name,
        model="N/A",  # Not applicable for name search
        tag="N/A",  # Not applicable for name search
        results=results,
        total_results=len(results),
    )


@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/api/search/semantic", response_model=SemanticSearchResponse)
async def semantic_search(
    request: Request,
    query: str = Query(..., description="Search query text", min_length=1),
    model: str = Query(DEFAULT_EMBEDDING_MODEL, description="Embedding model name"),
    tag: str = Query(DEFAULT_EMBEDDING_TAG, description="Embedding tag to search in"),
    n: int = Query(10, ge=1, le=100, description="Number of results to return (1-100)"),
    output_dim: int = Query(512, ge=128, le=2048, description="Embedding dimensionality"),
    summary_tag: str = Query(DEFAULT_SUMMARY_TAG, description="Summary tag to retrieve"),
    summary_model: str = Query(DEFAULT_SUMMARY_MODEL, description="Summary model to retrieve"),
):
    """
    Perform semantic search to find researchers similar to a text query.

    This endpoint:
    1. Generates an embedding vector for the query text using the specified model
    2. Searches the FAISS index for the top N most similar researchers
    3. Returns researcher details with similarity scores

    **Use Cases:**
    - Find researchers working on specific topics
    - Discover experts based on research descriptions
    - Match researchers to project requirements

    **Example:**
    ```
    GET /api/search/semantic?query=machine+learning+healthcare&model=gemini-embedding-001&tag=v1_embeddings&n=5
    ```

    **Query Parameters:**
    - `query`: Text describing what you're looking for (e.g., "machine learning in healthcare")
    - `model`: Embedding model to use (must match the model used for the tag)
    - `tag`: Which embedding set to search in
    - `n`: How many results to return (default: 10, max: 100)
    - `output_dim`: Vector dimensions (default: 768, must match model output)

    **Returns:**
    ```json
    {
        "query": "machine learning healthcare",
        "model": "gemini-embedding-001",
        "tag": "v1_embeddings",
        "results": [
            {
                "researcher_id": "507f1f77bcf86cd799439011",
                "name": "Juan",
                "last_name": "Pérez",
                "research_center": "CIEM",
                "research_area": "Inteligencia Artificial",
                "distance": 0.234,
                "similarity_score": 0.945
            }
        ],
        "total_results": 5
    }
    ```

    **Notes:**
    - Authentication required (use token in Authorization header or cookie)
    - Distance is L2 distance (lower is more similar)
    - Similarity score is normalized (0-1, higher is more similar)
    - FAISS index must be loaded for the specified tag/model
    """
    # Step 1: Generate embedding for the query using EmbeddingGenerator
    query_vector = EmbeddingGenerator.generate_embedding(
        text=query,
        model_name=model,
        output_dim=output_dim,
    )

    if not query_vector:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate embedding for query"
        )

    # Step 2: Search for similar researchers using FAISS
    index_manager = get_embedding_index_manager()

    try:
        similar_results = await index_manager.search_similar(
            query_vector=query_vector,
            tag=tag,
            model=model,
            k=n,
            include_distances=True,
        )
    except ValueError as e:
        # Index not found or not loaded
        raise HTTPException(
            status_code=404,
            detail=f"No index found for tag='{tag}' and model='{model}'. {str(e)}"
        )

    # Step 3: Fetch researcher details from database
    researcher_ids = [PydanticObjectId(rid) for rid, _ in similar_results]

    researchers = await Researcher.find(
        {"_id": {"$in": researcher_ids}},
        fetch_links=False
    ).to_list()

    # Create a mapping for quick lookup
    researcher_map = {str(r.id): r for r in researchers}

    # Step 4: Build response with similarity scores
    results = []
    for researcher_id, distance in similar_results:
        if researcher_id in researcher_map:
            researcher = researcher_map[researcher_id]

            # Convert L2 distance to similarity score (0-1 scale)
            # Using inverse distance: similarity = 1 / (1 + distance)
            similarity_score = 1.0 / (1.0 + distance)

            # Extract summary brief and content if available
            summary_brief_text = None
            summary_content_text = None
            summary_obj = next(
                (
                    s
                    for s in researcher.summaries
                    if s.tag == summary_tag and s.model == summary_model
                ),
                None,
            )
            if summary_obj:
                summary_brief_text = summary_obj.brief
                summary_content_text = summary_obj.content

            results.append(
                ResearcherSearchResult(
                    researcher_id=researcher_id,
                    name=researcher.name,
                    last_name=researcher.last_name,
                    research_center=researcher.research_center,
                    research_area=researcher.research_area,
                    summary_brief=summary_brief_text,
                    summary_content=summary_content_text,
                    distance=float(distance),
                    similarity_score=float(similarity_score),
                )
            )

    return SemanticSearchResponse(
        query=query,
        model=model,
        tag=tag,
        results=results,
        total_results=len(results),
    )


class PortfolioGenerateRequest(BaseModel):
    """Request body for portfolio generation."""
    prompt: str = Field(description="Instructions for portfolio generation", min_length=1)
    researcher_ids: List[str] = Field(description="List of researcher IDs to include", min_items=1)


class PortfolioGenerateResponse(BaseModel):
    """Response from portfolio generation."""
    portfolio_text: str = Field(description="The generated portfolio text")
    researcher_count: int = Field(description="Number of researchers included")
    prompt: str = Field(description="The original prompt used")


@router.post("/api/portfolio/generate", response_model=PortfolioGenerateResponse)
async def generate_portfolio(
    request: Request,
    body: PortfolioGenerateRequest,
):
    """
    Generate a portfolio based on a prompt and list of researcher IDs.

    This endpoint will generate a customized portfolio document for the selected researchers
    based on the provided instructions.

    **Request Body:**
    ```json
    {
        "prompt": "Generate a portfolio highlighting recent publications and research areas...",
        "researcher_ids": ["507f1f77bcf86cd799439011", "507f1f77bcf86cd799439012"]
    }
    ```

    **Returns:**
    ```json
    {
        "portfolio_text": "Generated portfolio content...",
        "researcher_count": 2,
        "prompt": "Generate a portfolio highlighting..."
    }
    ```

    **Notes:**
    - Authentication required
    - Uses Ollama to generate the portfolio text
    """
    if not _token_is_valid(request):
        raise HTTPException(status_code=401, detail="Authentication required")

    # Validate researcher ID formats
    for rid in body.researcher_ids:
        try:
            PydanticObjectId(rid)
        except Exception:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid researcher ID format: {rid}"
            )

    # Build per-researcher context texts (preserves input order)
    contexts = await get_portfolio_context(body.researcher_ids)

    # All contexts empty means none of the researchers were found or had summaries
    if all(ctx == "" for ctx in contexts):
        raise HTTPException(
            status_code=404,
            detail="No valid researcher data found for the provided IDs"
        )

    # Filter out empty contexts (missing researchers / missing summaries)
    valid_contexts = [ctx for ctx in contexts if ctx]

    # Call Ollama
    prompt_path = BASE_DIR / "prompts" / "portfolio" / "prompt.jinja"
    portfolio_text = PortfolioGeneratorOllama.generate_portfolio(
        user_prompt=body.prompt,
        researcher_contexts=valid_contexts,
        prompt_path=prompt_path,
    )

    return PortfolioGenerateResponse(
        portfolio_text=portfolio_text,
        researcher_count=len(valid_contexts),
        prompt=body.prompt,
    )


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
