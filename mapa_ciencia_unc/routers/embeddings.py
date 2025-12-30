from fastapi import APIRouter, Depends, HTTPException, status
from beanie import PydanticObjectId

from mapa_ciencia_unc.auth import require_auth
from mapa_ciencia_unc.models.researcher import Researcher
from mapa_ciencia_unc.models.embedding import (
    Embedding,
    EmbeddingCreate,
    EmbeddingRequest,
    MultipleEmbeddingsUpload,
)
from mapa_ciencia_unc.llms.embedding_generator import EmbeddingGenerator

router = APIRouter(
    prefix="/api/embeddings", tags=["embeddings"], dependencies=[Depends(require_auth)]
)


@router.post(
    "/researcher/{researcher_id}",
    status_code=status.HTTP_201_CREATED,
)
async def generate_researcher_embedding(
    researcher_id: str,
    req: EmbeddingRequest,
):
    """
    Generate and persist an embedding for a researcher based on an existing summary.

    Retrieves a researcher's summary, generates a dense vector embedding
    using the specified model, and stores it. The embedding replaces any existing
    embedding with the same tag

    **Process:**
    1. Fetches the researcher by ID
    2. Retrieves the summary with the specified tag
    3. Generates an embedding vector using the specified model and dimensions (if applicable)
    4. Removes any existing embedding with the same tag (if present)
    5. Stores the new embedding with the researcher

    **Request Body:**
    - `summary_tag`: Tag of the summary to use as input (e.g., "user_academic_v1")
    - `embedding_tag`: Tag to assign to the generated embedding (e.g., "v1_embeddings")
    - `model`: Embedding model to use (e.g., "gemini-embedding-001", "text-embedding-004")
    - `output_dim`: Dimensionality of the output vector (default: 768)

    **Supported Models:**
    - Gemini models: "gemini-embedding-001", "text-embedding-004"
    - Ollama models: Coming soon (will raise NotImplementedError)

    **Returns:**
    - `researcher_id`: ID of the researcher
    - `summary_tag`: Tag of the summary used as input
    - `embedding_tag`: Tag assigned to the embedding
    - `model`: Model used for generation
    - `dimensions`: Actual dimensionality of the generated vector

    **Raises:**
    - `404 Not Found`: If researcher or summary with tag not found
    - `500 Internal Server Error`: If embedding generation fails
    - `501 Not Implemented`: If using an Ollama model (not yet supported)
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

    # Generate embedding using the new EmbeddingGenerator class
    try:
        vector = EmbeddingGenerator.generate_embedding(
            text=summary.content,
            model_name=req.model,
            output_dim=req.output_dim,
        )
    except NotImplementedError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    if not vector:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate embedding.",
        )

    # Remove existing embeddings with the same tag
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
async def upload_multiple_embeddings(payload: MultipleEmbeddingsUpload):
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


@router.post("/researcher/{researcher_id}/upload", response_model=Researcher)
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


@router.delete("/tag/{tag}")
async def delete_embeddings_by_tag(tag: str):
    """
    Delete all embeddings with the specified tag across all researchers.

    Finds all researchers with embeddings matching the given tag and removes them.
    Useful for cleanup or regenerating embeddings with different parameters.

    Args:
        tag: Tag identifier for embeddings to delete (e.g., "embeddings-v1", "test-embeddings")

    Returns:
        - deleted_count: Number of embeddings deleted
        - researchers_affected: Number of researchers that had embeddings removed

    Example:
    ```
    DELETE /api/embeddings/tag/embeddings-v1
    ```

    Returns:
    ```json
    {
        "deleted_count": 150,
        "researchers_affected": 150
    }
    ```
    """
    researchers = await Researcher.find_all().to_list()

    deleted_count = 0
    researchers_affected = 0

    for researcher in researchers:
        # Count embeddings with this tag
        embeddings_before = len(researcher.embeddings)

        # Remove embeddings with the specified tag
        researcher.embeddings = [
            e for e in researcher.embeddings if e.tag != tag
        ]

        embeddings_after = len(researcher.embeddings)
        embeddings_removed = embeddings_before - embeddings_after

        # Save if embeddings were removed
        if embeddings_removed > 0:
            await researcher.save()
            deleted_count += embeddings_removed
            researchers_affected += 1

    return {
        "deleted_count": deleted_count,
        "researchers_affected": researchers_affected,
    }
