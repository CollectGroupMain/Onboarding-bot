import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

# Always load .env from project root (works even if cwd is elsewhere, e.g. IDE).
load_dotenv(ROOT / ".env")

ROOT = Path(__file__).resolve().parent.parent

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
SURVEY_PATH = Path(os.environ.get("SURVEY_PATH", ROOT / "data" / "survey.json"))
SUBMISSIONS_PATH = Path(
    os.environ.get("SUBMISSIONS_PATH", ROOT / "data" / "submissions.jsonl")
)

# Web admin (FastAPI)
ADMIN_WEB_PASSWORD = os.environ.get("ADMIN_WEB_PASSWORD", "").strip()
ADMIN_WEB_HOST = os.environ.get("ADMIN_WEB_HOST", "127.0.0.1").strip()
ADMIN_WEB_PORT = int(os.environ.get("ADMIN_WEB_PORT", "8080"))
ADMIN_SESSION_SECRET = os.environ.get("ADMIN_SESSION_SECRET", "").strip() or secrets.token_hex(
    32
)
