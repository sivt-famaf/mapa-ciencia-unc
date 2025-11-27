from fastapi import APIRouter, Depends

from mapa_ciencia_unc.auth import require_auth
from mapa_ciencia_unc.controllers.graph import get_researcher_graph


router = APIRouter(prefix="/api", tags=["api"], dependencies=[Depends(require_auth)])


@router.get("/graph")
async def get_graph_data():
    graph = get_researcher_graph()
    return graph.model_dump()
