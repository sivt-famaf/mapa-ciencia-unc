from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Annotated
from beanie import Document, Indexed


class EmbeddingCreate(BaseModel):
    model: str = Field(
        ..., examples=["embedding-model-v1"], description="Embedding model name"
    )
    vector: List[float] = Field(..., description="Embedding vector", min_items=1)
    tag: str = Field(..., description="tag for the embedding", examples=["test-run-1"])


class MultipleEmbeddingsCreate(BaseModel):
    model: str = Field(
        ..., examples=["embedding-model-v1"], description="Embedding model name"
    )
    tag: str = Field(..., description="tag for the embeddings", examples=["batch-1"])
    vector_mapping: dict[str, List[float]] = Field(
        ...,
        description="Mapping of researcher IDs to embedding vectors",
        min_items=1,
    )


class Embedding(BaseModel):
    created_at: datetime = Field(default_factory=datetime.now)
    model: str
    vector: List[float] = Field(..., min_items=1)
    dimensions: int
    tag: str
