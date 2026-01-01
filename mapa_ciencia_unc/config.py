from dotenv import load_dotenv
from pathlib import Path
import os

BASE_DIR = Path(".")  # mapa_ciencia_unc

load_dotenv(".env")

PROFILE_SUMMARY_DIR = BASE_DIR / "mapa_ciencia_unc" / "prompts" / "profile_summary"
SYSTEMS_DIR = PROFILE_SUMMARY_DIR / "system"
USER_PROMPTS_DIR = PROFILE_SUMMARY_DIR / "user"


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = os.getenv("GEMINI_API_URL")
INTERNAL_SWAGGER_KEY = os.getenv("INTERNAL_SWAGGER_KEY")

# Ollama Configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY")

# Local Embedding Server Configuration
LOCAL_EMBEDDING_HOST = os.getenv("LOCAL_EMBEDDING_HOST")
