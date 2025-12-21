from typing import List

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from mapa_ciencia_unc.auth import require_auth
from mapa_ciencia_unc.models.research_topic import ResearchTopic, ResearchTopicCreate


router = APIRouter(
    prefix="/api/research_topics",
    tags=["research_topics"],
    dependencies=[Depends(require_auth)],
)


@router.get("", status_code=status.HTTP_200_OK, response_model=List[ResearchTopic])
async def get_research_topics():
    research_topics = await ResearchTopic.find_all().to_list()
    return research_topics


@router.post("/bulk", status_code=status.HTTP_201_CREATED, response_model=dict)
async def create_research_topics_bulk(payload: List[ResearchTopicCreate]):
    created_research_topics = []
    failed_research_topics = []
    for research_topic_data in payload:
        try:
            existing = await ResearchTopic.find_one(
                ResearchTopic.name == research_topic_data.name
            )
            if existing:
                failed_research_topics.append(
                    {
                        "name": research_topic_data.name,
                        "error": "This research topic already exists.",
                    }
                )
                continue  # Skip existing research topics

            research_topic = ResearchTopic(**research_topic_data.model_dump())
            await research_topic.insert()
            created_research_topics.append(research_topic)
        except Exception as e:
            failed_research_topics.append(
                {
                    "name": research_topic_data.name,
                    "error": str(e),
                }
            )

    return {
        "created": created_research_topics,
        "failed": failed_research_topics,
    }
