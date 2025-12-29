from __future__ import annotations

from datetime import datetime
from typing import Annotated, List

from beanie import Document, Indexed
from pydantic import BaseModel, Field

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


class ResearcherPublicView(BaseModel):
    name: str
    last_name: str
    research_center: str
    research_area: str | None = "N/A"
    last_project_title: str | None = "N/A"
    tag: str | None = None
    model: str | None = None
    summary: str | None = None

    @classmethod
    def from_researcher(
        cls,
        researcher: "Researcher",
        summary_tag: str | None = None,
        summary_model: str | None = None,
    ) -> "ResearcherPublicView":
        summary_content = None
        if summary_tag and summary_model:
            summary = next(
                (
                    s
                    for s in researcher.summaries
                    if s.tag == summary_tag and s.model == summary_model
                ),
                None,
            )
            if summary:
                summary_content = summary.content

        return cls(
            name=researcher.name,
            last_name=researcher.last_name,
            research_center=researcher.research_center,
            research_area=researcher.research_area or "N/A",
            last_project_title=researcher.last_project_title or "N/A",
            tag=summary_tag,
            model=summary_model,
            summary=summary_content,
        )


class Researcher(ResearcherBase, Document):
    cuit: Annotated[str, Indexed(unique=True)] = CUIT_FIELD
    created_at: datetime = Field(default_factory=datetime.now)
    embeddings: List[Embedding] = Field(default_factory=list)
    summaries: List[Summary] = Field(default_factory=list)
