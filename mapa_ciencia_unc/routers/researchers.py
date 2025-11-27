from typing import List

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from mapa_ciencia_unc.auth import require_auth
from mapa_ciencia_unc.models.researcher import Researcher, ResearcherCreate


router = APIRouter(
    prefix="/api/researchers",
    tags=["researchers"],
    dependencies=[Depends(require_auth)],
)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=Researcher)
async def create_researcher(payload: ResearcherCreate):
    existing = await Researcher.find_one(Researcher.cuit == payload.cuit)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Researcher with this CUIT already exists.",
        )

    researcher = Researcher(cuit=payload.cuit, embeddings=payload.embeddings or [])
    await researcher.insert()
    return researcher


@router.get("", response_model=List[Researcher])
async def list_researchers():
    researchers = await Researcher.find_all().to_list()
    return researchers


@router.get("/{researcher_id}", response_model=Researcher)
async def get_researcher(researcher_id: str):
    try:
        object_id = PydanticObjectId(researcher_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid researcher id.",
        )

    researcher = await Researcher.find_one({"_id": object_id})
    if not researcher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Researcher not found.",
        )
    return researcher
