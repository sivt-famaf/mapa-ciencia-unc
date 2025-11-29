from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Annotated
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


class Embedding(Document):
    created_at: datetime = Field(default_factory=datetime.now)
    model: str = Field(
        ..., examples=["embedding-model-v1"], description="Embedding model name"
    )
    vector: List[float] = Field(..., description="Embedding vector", min_items=1)
    dimensions: int
    tag: Annotated[str, Indexed(unique=True)] = Field(
        ..., description="tag for the embedding", examples=["test-run-1"]
    )
