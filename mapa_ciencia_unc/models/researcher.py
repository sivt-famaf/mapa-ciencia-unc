from beanie import Document, Indexed
from pydantic import BaseModel, Field
from typing import List, Optional, Annotated
from datetime import datetime

from mapa_ciencia_unc.models.constants import CUIT_FIELD


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
    cuit: str = CUIT_FIELD
    email: str
    name: str
    last_name: str
    orcid_number: str | None = None
    gender: str
    academic_units: List[str] = []
    highest_position: str
    languages: List[str] = []
    research_center: str
    research_area: str | None = None
    last_project_title: str | None = None
    ods: List[str] = []
    maturity_level: str
    international_research_links: bool


class ResearcherCreate(ResearcherBase):
    pass


class Researcher(ResearcherBase, Document):
    cuit: Annotated[str, Indexed(unique=True)] = ResearcherBase.model_fields["cuit"]

    created_at: datetime = Field(default_factory=datetime.now)
