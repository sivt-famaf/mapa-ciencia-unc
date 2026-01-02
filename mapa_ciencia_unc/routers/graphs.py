from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from beanie import PydanticObjectId

from mapa_ciencia_unc.auth import require_auth
from mapa_ciencia_unc.models.graph import (
    ResearcherGraphCreate,
    ResearcherGraph,
    ResearcherGraphListItem,
)
from mapa_ciencia_unc.controllers.graph import (
    compute_graph,
)


router = APIRouter(
    prefix="/api/graphs", tags=["graphs"], dependencies=[Depends(require_auth)]
)


@router.get("", response_model=List[ResearcherGraphListItem])
async def get_available_graphs():
    graphs = await ResearcherGraph.find_all(
        projection_model=ResearcherGraphListItem
    ).to_list()
    return graphs


@router.get("/{graph_id}", response_model=ResearcherGraph)
async def get_graph(graph_id: str):
    try:
        # Convert string ID to PydanticObjectId
        object_id = PydanticObjectId(graph_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid graph ID format: '{graph_id}'",
        )

    graph = await ResearcherGraph.get(object_id)
    if not graph:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Graph with id '{graph_id}' not found.",
        )
    return graph


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def compute_graph_data(request: ResearcherGraphCreate):
    """
    Compute and save a 2D graph visualization of researchers based on embeddings.

    This endpoint retrieves researcher embeddings matching the specified tag and model,
    projects them to 2D space using the chosen dimensionality reduction strategy,
    and saves the resulting graph to disk for visualization.

    **Process:**
    1. Validates that the tag/model combination has associated embeddings
    2. Checks if a graph already exists (returns error unless overwrite=true)
    3. Retrieves all researchers with matching embeddings (uses most recent per researcher)
    4. Projects high-dimensional embeddings to 2D using the specified strategy
    5. Creates nodes with positions, colors by academic unit, and metadata
    6. Saves the graph to database`

    **Dimensionality Reduction Strategies:**
    1. **PCA (Principal Component Analysis)**
       - Direct linear projection from original dimensions to 2D
       - Time complexity: O(n * d²) where n=samples, d=dimensions

    2. **UMAP (Uniform Manifold Approximation and Projection)**
       - Two-step non-linear projection for better cluster preservation
       - Step 1: PCA reduces from original dimensions to 150D (removes noise)
       - Step 2: UMAP reduces from 150D to 2D (preserves local structure)
       - Time complexity: O(n^1.14) approximately

    3. **t-SNE (t-Distributed Stochastic Neighbor Embedding)**
       - Two-step non-linear projection emphasizing local structure
       - Step 1: PCA reduces from original dimensions to 50D (removes noise)
       - Step 2: t-SNE reduces from 50D to 2D (preserves local neighborhoods)
       - Parameters: perplexity=30, learning_rate=200, n_iter=1000, init='pca'
       - Time complexity: O(n²) worst case, optimized in practice

    **Request Body:**
    - `embedding`: dictionary with:
        - `tag`: Tag identifier for the embeddings (e.g., "v1_embeddings", "embeddings_v1_avg")
        - `model`: Model used to generate embeddings (e.g., "gemini-embedding-001")
    - `summary`: dictionary with:
        - `tag`: Tag identifier for the summaries used to generate embeddings
        - `model`: Model used to generate summaries
    - `strategy`: Dimensionality reduction strategy (default: "pca")
      - "pca": Fast linear projection, preserves global variance
      - "umap": Non-linear projection, preserves local clusters (balanced)
      - "tsne": Non-linear projection, emphasizes tight local clusters
    - `overwrite`: Whether to overwrite existing graph (default: false)

    **Returns:**
    - `title`: Graph title with metadata
    - `summary`: Summary model/tag used
    - `embedding`: Embedding model/tag used
    - `strategy`: Dimensionality reduction strategy used
    - `nodes`: Number of researcher nodes created
    - `edges`: Number of edges (currently always 0, reserved for future use)
    - `_id`: Unique identifier for the graph

    **Example Requests:**

    PCA projection (fast):
    ```json
    {
    "summary": {
        "model": "gemini-2.5",
        "tag": "summaries_v1"
    },
    "embedding": {
        "model": "gemini-embedding-001",
        "tag": "embeddings_v1_avg"
    },
    "strategy": "pca",
    "overwrite": false
    }
    ```

    UMAP projection (balanced clustering):
    ```json
    {
    "summary": {
        "model": "gemini-2.5",
        "tag": "summaries_v1"
    },
    "embedding": {
        "model": "gemini-embedding-001",
        "tag": "embeddings_v1_avg"
    },
    "strategy": "umap",
    "overwrite": false
    }
    ```

    t-SNE projection (tight clusters):
    ```json
    {
    "summary": {
        "model": "gemini-2.5",
        "tag": "summaries_v1"
    },
    "embedding": {
        "model": "gemini-embedding-001",
        "tag": "embeddings_v1_avg"
    },
    "strategy": "tsne",
    "overwrite": false
    }
    ```

    **Raises:**
    - `400 Bad Request`: If graph already exists and overwrite=false
    - `404 Not Found`: If no researchers have embeddings with the given tag/model
    - `501 Not Implemented`: If an unsupported strategy is specified (not 'pca', 'umap', or 'tsne')
    - `500 Internal Server Error`: If computation fails unexpectedly

    **Additional Notes:**
    - The graph file can be retrieved later using GET /api/graph?graph_id={_id}
    - Only the most recent embedding per researcher is used
    """
    existing_graphs = await ResearcherGraph.find(
        {
            "summary.tag": request.summary.tag,
            "summary.model": request.summary.model,
            "embedding.tag": request.embedding.tag,
            "embedding.model": request.embedding.model,
            "strategy": request.strategy,
        }
    ).to_list()

    if existing_graphs and not request.overwrite:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Graph with summary ({request.summary.tag}, {request.summary.model}) "
                f"and embedding ({request.embedding.tag}, {request.embedding.model}) "
                f"using strategy '{request.strategy}' already exists. "
                "Use overwrite=true to overwrite it."
            ),
        )
    else:
        for graph in existing_graphs:
            await graph.delete()

    try:
        graph = await compute_graph(
            embedding_tag=request.embedding.tag,
            embedding_model=request.embedding.model,
            summary_tag=request.summary.tag,
            summary_model=request.summary.model,
            strategy=request.strategy,
        )
        return {
            "_id": str(graph.id),
            "graph": graph.title,
            "summary": graph.summary,
            "embedding": graph.embedding,
            "strategy": graph.strategy,
            "nodes": len(graph.nodes),
            "edges": len(graph.edges),
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
