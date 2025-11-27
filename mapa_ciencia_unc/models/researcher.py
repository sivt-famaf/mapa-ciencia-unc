from beanie import Document
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

CUIT_LENGTH = 11


class Embedding(BaseModel):
    model: str = Field(
        ..., examples=["embedding-model-v1"], description="Embedding model name"
    )
    created_at: datetime = Field(default_factory=datetime.now)
    vector: List[float] = Field(..., description="Embedding vector", min_items=1)
    tag: Optional[str] = Field(
        None, description="Optional tag for the embedding", examples=["test-run-1"]
    )


class Researcher(Document):
    cuit: str = Field(
        ...,
        examples=["20123456789"],
        description="Unique CUIT identifier",
        min_length=CUIT_LENGTH,
        max_length=CUIT_LENGTH,
    )
    embeddings: List[Embedding] = Field(
        ...,
        description="List of embeddings associated with the researcher",
        default_factory=list,
    )


class ResearcherCreate(BaseModel):
    cuit: str = Field(
        ...,
        examples=["20123456789"],
        description="Unique CUIT identifier",
        min_length=CUIT_LENGTH,
        max_length=CUIT_LENGTH,
    )
    embeddings: Optional[List[Embedding]] = Field(
        None,
        description="Initial list of embeddings for the researcher",
    )


class ResearcherUpdateEmbedding(BaseModel):
    embedding: List[float] = Field(
        ...,
        description="New embedding vector to add",
        min_items=1,
    )
