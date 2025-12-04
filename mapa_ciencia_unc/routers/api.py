from fastapi import APIRouter, Depends, HTTPException, status

from mapa_ciencia_unc.auth import require_auth
from mapa_ciencia_unc.controllers.graph import (
    get_researcher_graph,
    compute_graph,
    get_available_graphs,
)


router = APIRouter(prefix="/api", tags=["api"], dependencies=[Depends(require_auth)])
public_router = APIRouter(prefix="/api", tags=["api"])


@router.get("/graph")
async def get_graph_data():
    graph = get_researcher_graph()
    return graph.model_dump()


@public_router.get("/available_graph_tags")
async def get_available_graph_tags():
    graphs = get_available_graphs()
    return {"available_graph_tags": graphs}


@router.get("/compute_graph")
async def compute_graph_data(embeddings_tag: str, overwrite: bool = False):
    if not overwrite:
        exists = embeddings_tag in get_available_graphs()
        if exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Graph already exists. Use overwrite=true to overwrite it.",
            )

    try:
        graph = await compute_graph(embeddings_tag)
        return {
            "graph": graph.title,
            "nodes": len(graph.nodes),
            "edges": len(graph.edges),
        }
    except Exception as e:
        return {"error": str(e)}
