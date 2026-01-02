from datetime import datetime
from typing import List

from beanie import Document
from pydantic import BaseModel, Field

from mapa_ciencia_unc.models.embedding import Embedding, EmbeddingCreate


class ResearchTopicBase(BaseModel):
    name: str
    description: str | None = None
    embedding: Embedding
    keywords: List[str] = Field(default_factory=list)
    researcher_cuits: List[str] = Field(
        default_factory=list,
        description="List of researcher CUITs that belong to this research topic"
    )
    tag: str | None = None
    summary_tag: str | None = None
    summary_model: str | None = None
    embedding_tag: str | None = None
    embedding_model: str | None = None


class ResearchTopicCreate(ResearchTopicBase):
    embedding: EmbeddingCreate


class ResearchTopic(ResearchTopicBase, Document):
    created_at: datetime = Field(default_factory=datetime.now)


class BulkTopicItem(BaseModel):
    """Individual topic for bulk upload."""

    topic_id: int | None = None  # unused
    keywords: List[str] = Field(default_factory=list)
    researchers: List[str] = Field(
        default_factory=list,
        description="List of researcher CUITs that belong to this topic"
    )
    size: int | None = None
    name: str
    description: str | None = None
    embedding: List[float]


class BulkResearchTopicsUpload(BaseModel):
    """Model for bulk uploading research topics with shared metadata."""

    summary_tag: str
    summary_model: str
    embedding_tag: str
    embedding_model: str
    tag: str
    topics: List[BulkTopicItem]
    overwrite: bool = False
