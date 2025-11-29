from fastapi import APIRouter, Depends

from mapa_ciencia_unc.auth import require_auth
from mapa_ciencia_unc.controllers.graph import get_researcher_graph, compute_graph


router = APIRouter(prefix="/api", tags=["api"], dependencies=[Depends(require_auth)])


@router.get("/graph")
async def get_graph_data():
    graph = get_researcher_graph()
    return graph.model_dump()


@router.get("/compute_graph")
async def compute_graph_data(embeddings_tag: str):
    try:
        graph = await compute_graph(embeddings_tag)
        return {
            "graph": graph.title,
            "nodes": len(graph.nodes),
            "edges": len(graph.edges),
        }

    except Exception as e:
        return {"error": str(e)}
