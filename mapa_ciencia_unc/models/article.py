from beanie import Document
from pydantic import BaseModel, Field
from datetime import datetime


class ArticleBase(BaseModel):
    autores: str
    titulo: str
    resumen: str
    cuit: str
    lugar_de_trabajo: str


class ArticleCreate(ArticleBase):
    pass


class Article(ArticleBase, Document):
    created_at: datetime = Field(default_factory=datetime.now)
