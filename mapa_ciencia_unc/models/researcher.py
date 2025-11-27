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
    email: str
    name: str
    last_name: str
    orcid_number: str
    gender: str
    academic_unit: str
    highest_position: str
    languages: str
    research_center: str
    research_area: str
    last_project_title: str
    ods: str
    maturity_level: str
    international_research_links: str
    embeddings: List[Embedding] = Field(
        ...,
        default_factory=list,
    )


class ResearcherCreate(ResearcherBase):
    pass


class Researcher(ResearcherBase, Document):
    created_at: datetime = Field(default_factory=datetime.now)
