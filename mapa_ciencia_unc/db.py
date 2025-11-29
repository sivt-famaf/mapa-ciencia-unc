from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
import os
from mapa_ciencia_unc.models.researcher import Researcher
from mapa_ciencia_unc.models.article import Article
from mapa_ciencia_unc.models.project import Project
from mapa_ciencia_unc.models.embedding import Embedding
from mapa_ciencia_unc.models.summary import Summary


async def init_db():
    user = os.getenv("MONGO_INITDB_ROOT_USERNAME")
    password = os.getenv("MONGO_INITDB_ROOT_PASSWORD")
    mongo_uri = f"mongodb://{user}:{password}@mongo:27017"
    client = AsyncIOMotorClient(mongo_uri)
    db = client[os.getenv("MONGO_DB")]

    await init_beanie(
        database=db,
        document_models=[Researcher, Article, Project, Embedding, Summary],
    )
