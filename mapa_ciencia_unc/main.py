from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from mapa_ciencia_unc.auth import login
from fastapi.security import OAuth2PasswordRequestForm

from mapa_ciencia_unc.db import init_db
from mapa_ciencia_unc.routers import (
    api,
    frontend,
    researchers,
    projects,
    articles,
    research_topics,
    agreements,
)


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
    """Initialize database connections."""
    await init_db()


@app.get("/health")
async def health_check():
    return {"status": "ok"}


# login route
@app.post("/login")
def login_route(form: OAuth2PasswordRequestForm = Depends()):
    payload = login(form)
    response = JSONResponse(payload)
    access_token = payload.get("access_token")
    if access_token:
        response.set_cookie(
            "token",
            access_token,
            httponly=True,
            samesite="lax",
            max_age=60 * 60,
            path="/",
        )
    return response


app.include_router(frontend.router)
app.include_router(api.router)
app.include_router(researchers.router)
app.include_router(projects.router)
app.include_router(articles.router)
app.include_router(research_topics.router)
app.include_router(agreements.router)
