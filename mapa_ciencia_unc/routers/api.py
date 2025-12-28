from fastapi import APIRouter, Depends, HTTPException, status

from mapa_ciencia_unc.auth import require_auth
from mapa_ciencia_unc.models.graph import ComputeGraphRequest
from mapa_ciencia_unc.controllers.graph import (
    get_researcher_graph,
    compute_graph,
    get_available_graphs,
    generate_graph_key,
)


router = APIRouter(prefix="/api", tags=["api"], dependencies=[Depends(require_auth)])


@router.get("/graph")
async def get_graph_data():
    graph = get_researcher_graph()
    return graph.model_dump()


@router.get("/available_graph_tags")
async def get_available_graph_tags():
    graphs = get_available_graphs()
    return {"available_graph_tags": graphs}


@router.post("/compute_graph", response_model=dict)
async def compute_graph_data(request: ComputeGraphRequest):
    """
    Compute and save a 2D graph visualization of researchers based on embeddings.

    This endpoint retrieves researcher embeddings matching the specified tag and model,
    projects them to 2D space using the chosen dimensionality reduction strategy,
    and saves the resulting graph to disk.

    **Process:**
    1. Validates that the tag/model combination has associated embeddings
    2. Checks if a graph already exists (returns error unless overwrite=true)
    3. Retrieves all researchers with matching embeddings (uses most recent per researcher)
    4. Projects high-dimensional embeddings to 2D using the specified strategy
    5. Creates nodes with positions, colors by academic unit, and metadata
    6. Saves the graph to `GRAPHS_DIR/{tag}_{model}.json`

    **Request Body:**
    - `tag`: Tag identifier for the embeddings (e.g., "v1_embeddings")
    - `model`: Model used to generate embeddings (e.g., "gemini-embedding-001")
    - `strategy`: Dimensionality reduction strategy (default: "pca")
      - Currently supported: "pca" (Principal Component Analysis)
    - `overwrite`: Whether to overwrite existing graph (default: false)

    **Returns:**
    - `graph`: Graph title
    - `nodes`: Number of researcher nodes created
    - `edges`: Number of edges (currently always 0)
    - `graph_key`: Unique identifier for the graph file

    **Raises:**
    - `400 Bad Request`: If graph already exists and overwrite=false
    - `404 Not Found`: If no researchers have embeddings with the given tag/model
    - `501 Not Implemented`: If an unsupported strategy is specified

    **Notes:**
    - The graph file can be retrieved later using GET /api/graph with the graph_key
    - Computation time depends on number of researchers and embedding dimensions
    - Only the most recent embedding per researcher is used
    """
    graph_key = generate_graph_key(request.tag, request.model)
    exists = graph_key in get_available_graphs()

    if exists and not request.overwrite:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Graph '{graph_key}' already exists. Use overwrite=true to overwrite it.",
        )

    try:
        graph = await compute_graph(
            request.tag, request.model, strategy=request.strategy
        )
        return {
            "graph": graph.title,
            "nodes": len(graph.nodes),
            "edges": len(graph.edges),
            "graph_key": graph_key,
        }
    except NotImplementedError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error computing graph: {str(e)}",
        )
