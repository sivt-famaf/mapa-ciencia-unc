from beanie import Document, Indexed
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Annotated

from mapa_ciencia_unc.models.constants import CUIT_FIELD


class ArticleBase(BaseModel):
    cuit: str = CUIT_FIELD
    autores: List[str] = Field(..., min_items=1)
    titulo: str
    lugar_de_trabajo: str
    resumen: str | None = None
    issn: str | None = None
    eissn: str | None = None


class ArticleCreate(ArticleBase):
    pass


class Article(ArticleBase, Document):
    created_at: datetime = Field(default_factory=datetime.now)
    titulo: Annotated[str, Indexed()] = ArticleBase.model_fields["titulo"]
