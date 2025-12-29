from fastapi import APIRouter, Depends, HTTPException, status
from beanie import PydanticObjectId

from mapa_ciencia_unc.auth import require_auth
from mapa_ciencia_unc.models.researcher import Researcher
from mapa_ciencia_unc.models.embedding import (
    Embedding,
    EmbeddingRequest,
    MultipleEmbeddingsCreate,
)
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


@router.post("/upload/bulk", response_model=dict)
async def upload_multiple_embeddings(payload: MultipleEmbeddingsCreate):
    """
    Upload multiple embeddings to researchers in bulk.

    This endpoint accepts a mapping of researcher identifiers to embedding vectors
    and creates or updates embeddings for multiple researchers in a single request.

    **Researcher Identification:**
    - Tries to find researcher by `researcher_id` (MongoDB ObjectId) first
    - If not found or invalid ObjectId, tries to find by `cuit` (CUIT identifier)
    - This allows flexibility in how researchers are identified

    **Request Body:**
    - `vector_mapping`: Dictionary mapping researcher identifier (ID or CUIT)
        to embedding vector
    - `tag`: Tag to assign to all embeddings (e.g., "batch-1", "v1-embeddings")
    - `model`: Model name used to generate embeddings (e.g., "gemini-embedding-001")
    - `overwrite`: Whether to replace existing embeddings with the same tag (default: False)

    **Behavior:**
    - With `overwrite=True`: Replaces existing embeddings with the same tag
    - With `overwrite=False`: Skips researchers who already have an embedding with the same tag

    **Returns:**
    - `created_embeddings`: Count of successfully created embeddings
    - `skipped_embeddings`: Dictionary of researcher_id -> reason for skipping
    - `failed_embeddings`: List of researcher identifiers that failed

    **Example Request:**
    ```json
    {
        "vector_mapping": {
            "507f1f77bcf86cd799439011": [0.1, 0.2, 0.3, ...],
            "27273268885": [0.4, 0.5, 0.6, ...]
        },
        "tag": "v1-embeddings",
        "model": "gemini-embedding-001",
        "overwrite": false
    }
    ```

    **Notes:**
    - The first key uses researcher_id (MongoDB ObjectId)
    - The second key uses CUIT (will be looked up automatically)
    - All vectors in a batch must have the same dimensions
    """
    created_embeddings = 0
    failed_embeddings = []
    skipped_embeddings = {}

    for identifier, vector in payload.vector_mapping.items():
        try:
            researcher = None

            # Try to find by researcher_id (ObjectId) first
            try:
                researcher = await Researcher.get(
                    PydanticObjectId(identifier), fetch_links=False
                )
            except Exception:
                # Not a valid ObjectId, try finding by CUIT
                pass

            # If not found by ID, try finding by CUIT
            if not researcher:
                researcher = await Researcher.find_one(
                    Researcher.cuit == identifier, fetch_links=False
                )

            # If still not found, mark as failed
            if not researcher:
                failed_embeddings.append(identifier)
                continue

            embedding = Embedding(
                model=payload.model,
                vector=vector,
                dimensions=len(vector),
                tag=payload.tag,
            )

            if not payload.overwrite:
                # Check if an embedding with the same model and tag already exists
                existing_embedding = next(
                    (
                        e
                        for e in researcher.embeddings
                        if e.model == payload.model and e.tag == payload.tag
                    ),
                    None,
                )
                if existing_embedding:
                    skipped_embeddings[identifier] = "Embedding with tag already exists"
                    continue  # Skip creating this embedding
            if payload.overwrite:
                # Remove existing embeddings with the same model and tag
                researcher.embeddings = [
                    e
                    for e in researcher.embeddings
                    if not (e.model == payload.model and e.tag == payload.tag)
                ]

            researcher.embeddings.append(embedding)

            await researcher.save()
            created_embeddings += 1
        except Exception:
            failed_embeddings.append(identifier)

    return {
        "uploaded_embeddings": created_embeddings,
        "failed_embeddings": failed_embeddings,
        "skipped_embeddings": skipped_embeddings,
    }
