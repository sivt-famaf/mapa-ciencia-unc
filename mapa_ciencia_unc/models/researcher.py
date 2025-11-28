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


class ResearcherBase(BaseModel):
    cuit: str = Field(
        ...,
        min_length=CUIT_LENGTH,
        max_length=CUIT_LENGTH,
    )
    email: str | None = None
    name: str | None = None
    last_name: str | None = None
    orcid_number: str | None = None
    gender: str | None = None
    academic_unit: str | None = None
    highest_position: str | None = None
    languages: str | None = None
    research_center: str | None = None
    research_area: str | None = None
    last_project_title: str | None = None
    ods: str | None = None
    maturity_level: str | None = None
    international_research_links: str | None = None
    embeddings: List[Embedding] = Field(
        ...,
        default_factory=list,
    )


class ResearcherCreate(ResearcherBase):
    pass


class Researcher(ResearcherBase, Document):
    created_at: datetime = Field(default_factory=datetime.now)
