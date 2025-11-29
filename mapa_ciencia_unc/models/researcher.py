from beanie import Document, Indexed, Link, PydanticObjectId
from pydantic import BaseModel, Field
from typing import List, Annotated
from datetime import datetime

from mapa_ciencia_unc.models.constants import CUIT_FIELD
from mapa_ciencia_unc.models.embedding import Embedding
from mapa_ciencia_unc.models.summary import Summary


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
    embeddings: List[Link[Embedding]] = Field(default_factory=list)
    summaries: List[Link[Summary]] = Field(default_factory=list)


class ResearcherResponse(Researcher):
    embeddings: List[PydanticObjectId]
