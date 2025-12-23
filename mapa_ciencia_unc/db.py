import os

from beanie import init_beanie
from pymongo import AsyncMongoClient
from mapa_ciencia_unc.models.researcher import Researcher
from mapa_ciencia_unc.models.article import Article
from mapa_ciencia_unc.models.project import Project, ProjectExtractedIntro
from mapa_ciencia_unc.models.agreement import Agreement


async def init_db():
    user = os.getenv("MONGO_INITDB_ROOT_USERNAME")
    password = os.getenv("MONGO_INITDB_ROOT_PASSWORD")
    host = os.getenv("MONGO_HOST", "mongo")
    port = os.getenv("MONGO_PORT", 27018)
    mongo_uri = f"mongodb://{user}:{password}@{host}:{port}"
    client = AsyncMongoClient(mongo_uri)
    db = client[os.getenv("MONGO_DB")]

    await init_beanie(
        database=db,
        document_models=[
            Researcher,
            Article,
            Project,
            ProjectExtractedIntro,
            Agreement,
        ],
    )
