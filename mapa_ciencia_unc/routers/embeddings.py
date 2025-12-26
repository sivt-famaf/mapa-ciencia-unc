from fastapi import APIRouter, Depends, HTTPException, status
from beanie import PydanticObjectId

from mapa_ciencia_unc.auth import require_auth
from mapa_ciencia_unc.models.researcher import Researcher
from mapa_ciencia_unc.models.embedding import Embedding, EmbeddingRequest
from mapa_ciencia_unc.llms.embedding_generator import generate_gemini_embedding

router = APIRouter(
    prefix="/api/embeddings", tags=["embeddings"], dependencies=[Depends(require_auth)]
)


@router.post(
    "/researchers/{researcher_id}/embeddings",
    status_code=status.HTTP_201_CREATED,
)
async def generate_researcher_embedding(
    researcher_id: str,
    req: EmbeddingRequest,
):
    """
    Generate and persist an embedding for a researcher based on an existing summary.
    """

    researcher = await Researcher.get(
        PydanticObjectId(researcher_id),
        fetch_links=False,
    )

    if not researcher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Researcher not found.",
        )

    summary = next(
        (s for s in researcher.summaries if s.tag == req.summary_tag),
        None,
    )

    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Summary with tag '{req.summary_tag}' not found.",
        )

    vector = generate_gemini_embedding(
        profile_summary=summary.content,
        output_dim=req.output_dim,
    )

    if not vector:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate embedding.",
        )

    researcher.embeddings = [
        e for e in researcher.embeddings if e.tag != req.embedding_tag
    ]

    embedding = Embedding(
        model=req.model,
        vector=vector,
        dimensions=len(vector),
        tag=req.embedding_tag,
    )

    researcher.embeddings.append(embedding)

    await researcher.save()

    return {
        "researcher_id": str(researcher.id),
        "summary_tag": req.summary_tag,
        "embedding_tag": req.embedding_tag,
        "model": req.model,
        "dimensions": embedding.dimensions,
    }
