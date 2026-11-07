import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()   # no override=True: real env vars (Render/Railway) must win over a local .env


def _list(name: str, default: str = "") -> list[str]:
    value = os.getenv(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


# "production" turns on strict startup checks and hides /docs by default.
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").strip().lower()
IS_PRODUCTION = ENVIRONMENT == "production"

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")
MONGO_TIMEOUT_MS = int(os.getenv("MONGO_TIMEOUT_MS", "5000"))
SESSION_TTL_DAYS = int(os.getenv("SESSION_TTL_DAYS", "30"))
if SESSION_TTL_DAYS < 1:
    raise ValueError("SESSION_TTL_DAYS must be at least 1")


EMBED_MODEL = os.getenv("EMBED_MODEL", "gemini-embedding-001")
EMBED_DIMS = int(os.getenv("EMBED_DIMS", "768"))
EMBED_BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", "20"))
EMBED_RETRIES = int(os.getenv("EMBED_RETRIES", "4"))

BASE_DIR = Path(__file__).resolve().parents[2]   # the backend folder
DATA_DIR = BASE_DIR / "data"
PDF_PATH = DATA_DIR / "policy" / "dgca_car.pdf"
CHUNKS_PATH = DATA_DIR / "policy_chunks.json"


PROMPT_DIR = (
    Path(__file__).resolve().parents[1]
    / "llm"
    / "prompts"
)


# Text generation providers
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")


# Models are configurable without changing Python code.
GEMINI_MODELS = _list("GEMINI_MODELS", "gemini-3.1-flash-lite,gemini-3-flash-preview")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-small-latest")


# Live flight schedules/status (AirLabs free developer tier)
AIRLABS_API_KEY = os.getenv("AIRLABS_API_KEY")
FLIGHT_API_TIMEOUT_S = float(os.getenv("FLIGHT_API_TIMEOUT_S", "8"))
FLIGHT_API_CACHE_TTL_S = int(os.getenv("FLIGHT_API_CACHE_TTL_S", "60"))


# Provider priority
LLM_ORDER = _list("LLM_ORDER", "gemini,groq,mistral")

# Reliability settings
LLM_TIMEOUT_S = float(os.getenv("LLM_TIMEOUT_S", "20"))
LLM_RETRIES = int(os.getenv("LLM_RETRIES", "2"))
LLM_RETRY_BASE_S = float(os.getenv("LLM_RETRY_BASE_S", "1"))
LLM_COOLDOWN_S = int(os.getenv("LLM_COOLDOWN_S", "60"))

# CORS: never a wildcard. Development defaults to the local Vite frontend only;
# production must set CORS_ORIGINS to the real frontend URL(s).
CORS_ORIGINS = _list(
    "CORS_ORIGINS",
    "" if IS_PRODUCTION else "http://localhost:5173,http://127.0.0.1:5173",
)

# Public API protection (per client IP, per minute, per worker process).
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "20"))

# Swagger/OpenAPI docs: on in development, off in production unless enabled.
ENABLE_DOCS = _bool("ENABLE_DOCS", not IS_PRODUCTION)


def config_problems() -> list[str]:
    """Return human-readable configuration problems (empty list = fine)."""
    problems = []

    if not MONGO_URI:
        problems.append("MONGO_URI is not set")
    if not MONGO_DB:
        problems.append("MONGO_DB is not set")
    if not GEMINI_API_KEY:
        problems.append("GEMINI_API_KEY is not set (needed for policy search embeddings)")
    if "*" in CORS_ORIGINS:
        problems.append("CORS_ORIGINS must not contain '*'")
    if not CORS_ORIGINS:
        problems.append("CORS_ORIGINS is empty: set it to your frontend URL")

    return problems


def validate_production_config() -> None:
    """Fail fast at startup in production if the configuration is unsafe."""
    if not IS_PRODUCTION:
        return
    problems = config_problems()
    if problems:
        raise RuntimeError(
            "Invalid production configuration: " + "; ".join(problems)
        )