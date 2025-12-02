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
    if await Article.find_one(Article.titulo == payload.titulo):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Article with this title already exists.",
        )
    article = Article(**payload.model_dump())
    await article.insert()
    return article


@router.post("/bulk", status_code=status.HTTP_201_CREATED, response_model=dict)
async def create_articles_bulk(payload: List[ArticleCreate]):
    created_articles = []
    failed_articles = []
    for article_data in payload:
        try:
            existing = await Article.find_one(article_data.model_dump())
            if existing:
                failed_articles.append(
                    {
                        "title": article_data.titulo,
                        "error": "This article already exists.",
                    }
                )
                continue  # Skip existing articles

            article = Article(**article_data.model_dump())
            await article.insert()
            created_articles.append(article)
        except Exception as e:
            failed_articles.append(
                {
                    "title": article_data.titulo,
                    "error": str(e),
                }
            )

    return {
        "created": created_articles,
        "failed": failed_articles,
    }


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
