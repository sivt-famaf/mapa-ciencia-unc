from beanie import Document
from pydantic import BaseModel, Field
from datetime import datetime


class ArticleBase(BaseModel):
    cuit: str = None
    autores: str | None = None
    titulo: str | None = None
    resumen: str | None = None
    lugar_de_trabajo: str | None = None


class ArticleCreate(ArticleBase):
    pass


class Article(ArticleBase, Document):
    created_at: datetime = Field(default_factory=datetime.now)
