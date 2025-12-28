from typing import List

from beanie import PydanticObjectId
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query, status

from mapa_ciencia_unc.auth import require_auth
from mapa_ciencia_unc.models.researcher import (
    Researcher,
    ResearcherCreate,
)
from mapa_ciencia_unc.models.embedding import (
    Embedding,
    EmbeddingCreate,
)


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

    researcher = Researcher(**payload.model_dump())
    await researcher.insert()
    return researcher


@router.post("/bulk", status_code=status.HTTP_201_CREATED, response_model=dict)
async def create_researchers_bulk(payload: List[ResearcherCreate]):
    created_researchers = []
    failed_researchers = []
    for researcher_data in payload:
        try:
            existing = await Researcher.find_one(
                Researcher.cuit == researcher_data.cuit
            )
            if existing:
                continue  # Skip existing researchers

            researcher = Researcher(**researcher_data.model_dump())
            await researcher.insert()
            created_researchers.append(researcher)
        except Exception as e:
            failed_researchers.append(
                {
                    "cuit": researcher_data.cuit,
                    "error": str(e),
                }
            )

    return {
        "created": created_researchers,
        "failed": failed_researchers,
    }


@router.get("", response_model=List[Researcher])
async def list_researchers(
    skip: int = Query(0, ge=0, description="Number of researchers to skip"),
    limit: int = Query(
        10, ge=1, le=1000, description="Maximum number of researchers to return"
    ),
):
    """
    List researchers with pagination.

    Parameters:
    - skip: Number of researchers to skip (default: 0)
    - limit: Maximum number of researchers to return (default: 10, max: 1000)

    To retrieve all researchers:
    - Set limit to 1000 and make multiple requests with increasing skip values
    - Example: skip=0&limit=1000, then skip=1000&limit=1000, etc.
    - Continue until the response returns fewer items than the limit

    Returns:
    - List of Researcher objects
    """
    researchers = (
        await Researcher.find_all(fetch_links=False).skip(skip).limit(limit).to_list()
    )
    return researchers


class EmbeddingModelTagResponse(BaseModel):
    model: str
    tag: str
    dimensions: int
    count: int


@router.get("/list_embeddings", response_model=List[EmbeddingModelTagResponse])
async def list_embeddings():
    """
    List all embedding versions by:
    - model
    - tag
    - dimensions
    - count (How many researchers have this embedding)
    """
    pipeline = [
        # Flatten the embeddings array
        {"$unwind": "$embeddings"},
        # Group by unique pair
        {
            "$group": {
                "_id": {"model": "$embeddings.model", "tag": "$embeddings.tag"},
                # Take dimensions from the first document found in this group
                "dimensions": {"$first": "$embeddings.dimensions"},
                # Still counting occurrences
                "count": {"$sum": 1},
            }
        },
        # Reshape for output
        {
            "$project": {
                "_id": 0,
                "model": "$_id.model",
                "tag": "$_id.tag",
                "dimensions": 1,
                "count": 1,
            }
        },
        # Sort by model name and then tag
        {"$sort": {"model": 1, "tag": 1}},
    ]

    # 1. Prepare the query (No I/O happens here)
    query = await Researcher.aggregate(pipeline).to_list()

    return query


@router.get("/{researcher_id}", response_model=Researcher)
async def get_researcher(researcher_id: str):
    try:
        object_id = PydanticObjectId(researcher_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid researcher id.",
        )

    researcher = await Researcher.get(object_id)

    if not researcher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Researcher not found.",
        )
    return researcher


@router.post("/{researcher_id}/embeddings", response_model=Researcher)
async def create_researcher_embedding(researcher_id: str, payload: EmbeddingCreate):
    researcher = await Researcher.get(
        PydanticObjectId(researcher_id), fetch_links=False
    )
    if not researcher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Researcher not found.",
        )

    embedding = Embedding(
        **payload.model_dump(),
        dimensions=len(payload.vector),
    )

    researcher.embeddings.append(embedding)

    await researcher.save()
    return researcher
