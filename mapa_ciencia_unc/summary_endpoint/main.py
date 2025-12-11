from fastapi import FastAPI
from .routers.summaries_router import router as summaries_router

app = FastAPI(title="Mapa Ciencia UNC - Summary API")

app.include_router(summaries_router, prefix="/summaries", tags=["Summaries"])