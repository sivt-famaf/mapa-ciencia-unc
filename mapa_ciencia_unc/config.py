from dotenv import load_dotenv
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent   # mapa_ciencia_unc

ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)

PROFILE_SUMMARY_DIR = BASE_DIR / "prompts" / "profile_summary"
SYSTEMS_DIR = PROFILE_SUMMARY_DIR / "system"
USER_PROMPTS_DIR = PROFILE_SUMMARY_DIR / "user"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = os.getenv("GEMINI_API_URL")
INTERNAL_SWAGGER_KEY = os.getenv("INTERNAL_SWAGGER_KEY")