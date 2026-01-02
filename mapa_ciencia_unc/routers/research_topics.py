from typing import List

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, status

from mapa_ciencia_unc.auth import require_auth
from mapa_ciencia_unc.models.research_topic import (
    ResearchTopic,
    BulkResearchTopicsUpload,
)
from mapa_ciencia_unc.models.embedding import Embedding


router = APIRouter(
    prefix="/api/research_topics",
    tags=["research_topics"],
    dependencies=[Depends(require_auth)],
)


@router.get("", status_code=status.HTTP_200_OK, response_model=List[ResearchTopic])
async def get_research_topics():
    research_topics = await ResearchTopic.find_all().to_list()
    return research_topics


@router.post("/upload/bulk", status_code=status.HTTP_201_CREATED, response_model=dict)
async def create_research_topics_bulk(payload: BulkResearchTopicsUpload):
    """
    Bulk upload research topics with shared metadata.

    Creates multiple research topics with common summary and embedding metadata.
    Each topic includes an embedding vector, keywords, and associated researchers.

    **Request Body:**
    - `summary_tag`: Tag for summaries (e.g., "user_academic_temp05")
    - `summary_model`: Model used for summaries (e.g., "gemini-2.5-pro")
    - `embedding_tag`: Tag for embeddings (e.g., "embeddings_v1_avg")
    - `embedding_model`: Model used for embeddings (e.g., "gemini-embedding-001")
    - `tag`: General tag for the topics (e.g., "bertopic-sample15")
    - `topics`: List of topic objects with topic_id, keywords, researchers (CUITs),
      size, name, description, and embedding vector

    **Returns:**
    - `created`: Number of topics created
    - `failed`: List of failed topics with error messages
    """
    created_research_topics = []
    failed_research_topics = []

    for topic_data in payload.topics:
        try:
            existing = await ResearchTopic.find_one(
                ResearchTopic.name == topic_data.name
            )
            if existing and not payload.overwrite:
                failed_research_topics.append(
                    {
                        "name": topic_data.name,
                        "topic_id": topic_data.topic_id,
                        "error": "This research topic already exists.",
                    }
                )
                continue  # Skip existing research topics

            # Create embedding object
            embedding = Embedding(
                model=payload.embedding_model,
                vector=topic_data.embedding,
                dimensions=len(topic_data.embedding),
                tag=payload.embedding_tag,
            )

            if existing and payload.overwrite:
                # Update existing topic
                existing.description = topic_data.description
                existing.embedding = embedding
                existing.keywords = topic_data.keywords
                existing.researcher_cuits = topic_data.researchers
                existing.tag = payload.tag
                existing.summary_tag = payload.summary_tag
                existing.summary_model = payload.summary_model
                existing.embedding_tag = payload.embedding_tag
                existing.embedding_model = payload.embedding_model
                await existing.save()
                created_research_topics.append(existing)
            else:
                # Create new research topic
                research_topic = ResearchTopic(
                    name=topic_data.name,
                    description=topic_data.description,
                    embedding=embedding,
                    keywords=topic_data.keywords,
                    researcher_cuits=topic_data.researchers,
                    tag=payload.tag,
                    summary_tag=payload.summary_tag,
                    summary_model=payload.summary_model,
                    embedding_tag=payload.embedding_tag,
                    embedding_model=payload.embedding_model,
                )
                await research_topic.insert()
                created_research_topics.append(research_topic)
        except Exception as e:
            failed_research_topics.append(
                {
                    "name": topic_data.name,
                    "topic_id": topic_data.topic_id,
                    "error": str(e),
                }
            )

    return {
        "created": len(created_research_topics),
        "failed": failed_research_topics,
    }
