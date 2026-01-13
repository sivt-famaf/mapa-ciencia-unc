import logging
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from mapa_ciencia_unc.auth import login
from fastapi.security import OAuth2PasswordRequestForm

from mapa_ciencia_unc.db import init_db
from mapa_ciencia_unc.services.embedding_index import get_embedding_index_manager
from mapa_ciencia_unc.routers import (
    agreements,
    articles,
    embeddings,
    frontend,
    graphs,
    projects,
    research_topics,
    researchers,
    summaries,
)

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Researcher API", version="0.0.1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static",
)


@app.on_event("startup")
async def app_startup() -> None:
    """
    Initialize database connections and load embedding indexes.

    This function:
    1. Initializes the database connection
    2. Creates the embedding index manager
    3. Loads all available indexes into memory (Option A: Eager Loading)
       - First tries to load from disk cache (./faiss_indexes/)
       - Falls back to building from MongoDB if cache miss
       - Saves newly built indexes to disk for faster next startup

    Alternative: For lazy loading (Option B), comment out the load_all_indexes() call.
    Indexes will be loaded on-demand when first requested.
    """
    await init_db()

    # Initialize embedding index manager and store in app state
    app.state.embedding_index = get_embedding_index_manager()

    # Option A: Eager Loading - Load all indexes at startup
    # This provides best performance but increases startup time
    try:
        await app.state.embedding_index.load_all_indexes(
            use_disk_cache=True,
            cache_dir="./faiss_indexes"
        )

        # Log loaded indexes
        loaded = app.state.embedding_index.get_loaded_indexes()
        if loaded:
            logger.info(f"Successfully loaded {len(loaded)} embedding indexes")
        else:
            logger.info("No embedding indexes found to load")

    except Exception as e:
        # Log error but don't fail startup - indexes can be loaded on-demand
        logger.error(f"Warning: Failed to load embedding indexes on startup: {e}")
        logger.info("Indexes will be loaded on-demand when first requested")

    # Option B: Lazy Loading (commented out by default)
    # If you prefer lazy loading, comment out the load_all_indexes() call above
    # and uncomment this message:
    # print("Embedding indexes will be loaded on-demand (lazy loading)")


@app.on_event("shutdown")
async def app_shutdown() -> None:
    """Clean up resources on shutdown."""
    if hasattr(app.state, "embedding_index"):
        app.state.embedding_index.clear_all_indexes()
        print("Cleared all embedding indexes from memory")


@app.get("/health")
async def health_check():
    return {"status": "ok"}


# login route
@app.post("/login")
def login_route(form: OAuth2PasswordRequestForm = Depends()):
    return login(form)


app.include_router(frontend.router)
app.include_router(graphs.router)
app.include_router(researchers.router)
app.include_router(projects.router)
app.include_router(articles.router)
app.include_router(research_topics.router)
app.include_router(agreements.router)
app.include_router(summaries.router)
app.include_router(embeddings.router)
