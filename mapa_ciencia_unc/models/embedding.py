from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Annotated
from beanie import Document, Indexed, PydanticObjectId


class EmbeddingCreate(BaseModel):
    model: str = Field(
        ..., examples=["embedding-model-v1"], description="Embedding model name"
    )
    vector: List[float] = Field(..., description="Embedding vector", min_items=1)
    tag: str = Field(..., description="tag for the embedding", examples=["test-run-1"])


class MultipleEmbeddingsUpload(BaseModel):
    """
    Model for creating multiple embeddings in bulk.

    The vector_mapping keys can be either:
    - researcher_id (MongoDB ObjectId as string)
    - researcher_cuit (CUIT identifier as string)

    The endpoint will try researcher_id first, then fall back to CUIT lookup.
    """
    overwrite: bool = False
    model: str = Field(
        ..., examples=["embedding-model-v1"], description="Embedding model name"
    )
    tag: str = Field(..., description="tag for the embeddings", examples=["batch-1"])
    vector_mapping: dict[str, List[float]] = Field(
        ...,
        description="Mapping of researcher identifier (ID or CUIT) to embedding vectors",
        min_items=1,
    )


class Embedding(BaseModel):
    """Deprecated class. Use EmbeddingDocument instead."""
    created_at: datetime = Field(default_factory=datetime.now)
    model: str
    vector: List[float] = Field(..., min_items=1)
    dimensions: int
    tag: str


class EmbeddingRequest(BaseModel):
    summary_tag: str
    embedding_tag: str
    model: str = "gemini-embedding-001"
    output_dim: int = 768


class EmbeddingDocument(Document):
    """
    Separate collection for fast vector operations and FAISS indexing.

    This collection stores embeddings separately from researchers to enable:
    - Fast vector similarity search with FAISS
    - Efficient indexing on (tag, model) combinations
    - Quick filtering without loading full researcher documents
    """
    researcher_id: Annotated[PydanticObjectId, Indexed()] = Field(
        ..., description="Reference to the researcher"
    )
    vector: List[float] = Field(..., min_items=1, description="Embedding vector")
    tag: str = Field(..., description="Tag identifier for this embedding batch")
    model: str = Field(..., description="Model used to generate this embedding")
    dimensions: int = Field(..., description="Vector dimensionality")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")

    class Settings:
        name = "embeddings"
        indexes = [
            # Fast lookup by researcher and embedding type
            [
                ("researcher_id", 1),
                ("tag", 1),
                ("model", 1),
            ],
            # Fast filtering by embedding type and recency
            [
                ("tag", 1),
                ("model", 1),
                ("created_at", -1),
            ],
        ]