from dotenv import load_dotenv
from pathlib import Path
import os

BASE_DIR = Path(".")  # mapa_ciencia_unc

load_dotenv(".env")

PROFILE_SUMMARY_DIR = BASE_DIR / "mapa_ciencia_unc" / "prompts" / "profile_summary"
SYSTEMS_DIR = PROFILE_SUMMARY_DIR / "system"
USER_PROMPTS_DIR = PROFILE_SUMMARY_DIR / "user"


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
INTERNAL_SWAGGER_KEY = os.getenv("INTERNAL_SWAGGER_KEY")

# Ollama Configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY")

# Local Embedding Server Configuration
LOCAL_EMBEDDING_HOST = os.getenv("LOCAL_EMBEDDING_HOST")

# Default visualization tags and models
DEFAULT_EMBEDDING_TAG = os.getenv("DEFAULT_EMBEDDING_TAG", "embeddings_v1")
DEFAULT_EMBEDDING_MODEL = os.getenv("DEFAULT_EMBEDDING_MODEL", "gemini-embedding-001")
DEFAULT_SUMMARY_TAG = os.getenv("DEFAULT_SUMMARY_TAG", "complete")
DEFAULT_SUMMARY_MODEL = os.getenv("DEFAULT_SUMMARY_MODEL", "gemini-2.5-pro")
DEFAULT_GRAPH_TAG = os.getenv("DEFAULT_GRAPH_TAG", "graph_v1")
