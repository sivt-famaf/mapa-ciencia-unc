from typing import List

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from mapa_ciencia_unc.auth import require_auth
from mapa_ciencia_unc.models.researcher import (
    Researcher,
    ResearcherCreate,
)
from mapa_ciencia_unc.models.embedding import (
    Embedding,
    EmbeddingCreate,
    MultipleEmbeddingsCreate,
)
from mapa_ciencia_unc.models.summary import Summary, MultipleSummariesCreate


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
async def list_researchers():
    researchers = await Researcher.find_all(fetch_links=False).to_list()
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


@router.post("/embeddings/bulk", response_model=dict)
async def create_multiple_embeddings(payload: MultipleEmbeddingsCreate):
    created_embeddings = 0
    failed_embeddings = []
    for researcher_id, vector in payload.vector_mapping.items():
        try:
            researcher = await Researcher.get(
                PydanticObjectId(researcher_id), fetch_links=False
            )
            if not researcher:
                continue

            embedding = Embedding(
                model=payload.model,
                vector=vector,
                dimensions=len(vector),
                tag=payload.tag,
            )

            researcher.embeddings.append(embedding)

            await researcher.save()
            created_embeddings += 1
        except Exception:
            failed_embeddings.append(researcher_id)

    return {
        "created_embeddings": created_embeddings,
        "failed_embeddings": failed_embeddings,
    }


@router.post("/{researcher_id}/summaries", response_model=Researcher)
async def create_researcher_summary(researcher_id: str, payload: Summary):
    researcher = await Researcher.get(
        PydanticObjectId(researcher_id), fetch_links=False
    )
    if not researcher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Researcher not found.",
        )

    summary = Summary(
        **payload.model_dump(),
    )

    researcher.summaries.append(summary)

    await researcher.save()
    return researcher


@router.post("/summaries/bulk", response_model=dict)
async def create_multiple_summaries(payload: MultipleSummariesCreate):
    created_summaries = {}
    for researcher_id, content in payload.content_mapping.items():
        researcher = await Researcher.get(
            PydanticObjectId(researcher_id), fetch_links=False
        )
        if not researcher:
            continue

        summary = Summary(
            model=payload.model,
            prompt_id=payload.prompt_id,
            content=content,
        )

        researcher.summaries.append(summary)

        await researcher.save()
        created_summaries[researcher_id] = str(summary.id)

    return {"created_summaries": created_summaries}
