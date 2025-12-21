from datetime import datetime
from typing import Annotated, List

from beanie import Document, Indexed
from pydantic import BaseModel, Field

from mapa_ciencia_unc.models.embedding import Embedding, EmbeddingCreate


class ResearchTopicBase(BaseModel):
    name: str
    description: str | None = None
    embedding: Embedding


class ResearchTopicCreate(ResearchTopicBase):
    embedding: EmbeddingCreate


class ResearchTopic(ResearchTopicBase, Document):
    created_at: datetime = Field(default_factory=datetime.now)
