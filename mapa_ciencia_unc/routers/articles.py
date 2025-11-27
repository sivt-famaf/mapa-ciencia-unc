from typing import List

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from mapa_ciencia_unc.auth import require_auth
from mapa_ciencia_unc.models.article import Article, ArticleCreate


router = APIRouter(
    prefix="/api/articles",
    tags=["articles"],
    dependencies=[Depends(require_auth)],
)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=Article)
async def create_article(payload: ArticleCreate):
    article = Article(**payload.model_dump())
    await article.insert()
    return article


@router.get("", response_model=List[Article])
async def list_articles():
    articles = await Article.find_all().to_list()
    return articles


@router.get("/{article_id}", response_model=Article)
async def get_article(article_id: str):
    try:
        object_id = PydanticObjectId(article_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid article id.",
        )

    article = await Article.find_one({"_id": object_id})
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found.",
        )

    return article
