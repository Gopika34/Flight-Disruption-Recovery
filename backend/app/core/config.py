# backend/app/core/config.py

import os
import secrets
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()   # no override=True: real env vars (Render/Railway) must win over a local .env


def _list(name: str, default: str = "") -> list[str]:
    """
    Helper to read a comma‑separated env var into a list of stripped strings.
    """
    value = os.getenv(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


def _bool(name: str, default: bool) -> bool:
    """
    Helper to read a boolean env var. Accepts common truthy strings.
    """
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


# ---------------------------------------------------------------------------
# General environment
# ---------------------------------------------------------------------------
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").strip().lower()
if ENVIRONMENT not in {"development", "dev", "test", "staging", "production"}:
    raise ValueError(
        "ENVIRONMENT must be development, dev, test, staging, or production"
    )
IS_PRODUCTION = ENVIRONMENT == "production"


# ---------------------------------------------------------------------------
# MongoDB
# ---------------------------------------------------------------------------
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")
MONGO_TIMEOUT_MS = int(os.getenv("MONGO_TIMEOUT_MS", "5000"))


# ---------------------------------------------------------------------------
# Authentication (Clerk for registered users, guest JWT for anonymous)
# ---------------------------------------------------------------------------
CLERK_ISSUER_URL = os.getenv("CLERK_ISSUER_URL", "").strip().rstrip("/")
CLERK_JWKS_URL = os.getenv("CLERK_JWKS_URL", "").strip()
AUTHORIZED_PARTIES = _list("AUTHORIZED_PARTIES", "")

# Guest token secret is generated on‑the‑fly in non‑production for convenience.
GUEST_TOKEN_SECRET = (
    os.getenv("GUEST_TOKEN_SECRET", "")
    or (secrets.token_urlsafe(48) if not IS_PRODUCTION else "")
)
GUEST_TOKEN_ISSUER = os.getenv("GUEST_TOKEN_ISSUER", "flightguard-api")
GUEST_TOKEN_TTL_HOURS = int(os.getenv("GUEST_TOKEN_TTL_HOURS", "168"))
SESSION_TTL_DAYS = int(os.getenv("SESSION_TTL_DAYS", "30"))
if SESSION_TTL_DAYS < 1:
    raise ValueError("SESSION_TTL_DAYS must be at least 1")


# ---------------------------------------------------------------------------
# Embedding / RAG configuration
# ---------------------------------------------------------------------------
EMBED_MODEL = os.getenv("EMBED_MODEL", "gemini-embedding-001")
EMBED_DIMS = int(os.getenv("EMBED_DIMS", "768"))
EMBED_BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", "20"))
EMBED_RETRIES = int(os.getenv("EMBED_RETRIES", "4"))

BASE_DIR = Path(__file__).resolve().parents[2]   # the backend folder
DATA_DIR = BASE_DIR / "data"
PDF_PATH = DATA_DIR / "policy" / "dgca_car.pdf"
CHUNKS_PATH = DATA_DIR / "policy_chunks.json"

PROMPT_DIR = (
    Path(__file__).resolve().parents[1] / "llm" / "prompts"
)


# ---------------------------------------------------------------------------
# LLM provider API keys
# ---------------------------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")


# ---------------------------------------------------------------------------
# Model selection
# ---------------------------------------------------------------------------
GEMINI_MODELS = _list(
    "GEMINI_MODELS",
    "gemini-3.1-flash-lite,gemini-3-flash-preview",
)
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-small-latest")


# ---------------------------------------------------------------------------
# AirLabs flight status API
# ---------------------------------------------------------------------------
AIRLABS_API_KEY = os.getenv("AIRLABS_API_KEY")
FLIGHT_API_TIMEOUT_S = float(os.getenv("FLIGHT_API_TIMEOUT_S", "8"))
FLIGHT_API_CACHE_TTL_S = int(os.getenv("FLIGHT_API_CACHE_TTL_S", "60"))


# ---------------------------------------------------------------------------
# Provider priority order
# ---------------------------------------------------------------------------
LLM_ORDER = _list("LLM_ORDER", "gemini,groq,mistral")


# ---------------------------------------------------------------------------
# LLM reliability settings
# ---------------------------------------------------------------------------
LLM_TIMEOUT_S = float(os.getenv("LLM_TIMEOUT_S", "20"))
LLM_RETRIES = int(os.getenv("LLM_RETRIES", "2"))
LLM_RETRY_BASE_S = float(os.getenv("LLM_RETRY_BASE_S", "1"))
LLM_COOLDOWN_S = int(os.getenv("LLM_COOLDOWN_S", "60"))


# ---------------------------------------------------------------------------
# CORS configuration (never a wildcard)
# ---------------------------------------------------------------------------
CORS_ORIGINS = _list(
    "CORS_ORIGINS",
    "" if IS_PRODUCTION else "http://localhost:5173,http://127.0.0.1:5173",
)


# ---------------------------------------------------------------------------
# Public API rate limiting
# ---------------------------------------------------------------------------
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "20"))


# ---------------------------------------------------------------------------
# Reverse‑proxy handling (how many X‑Forwarded‑For hops are trusted)
# ---------------------------------------------------------------------------
TRUSTED_PROXY_COUNT = int(os.getenv("TRUSTED_PROXY_COUNT", "0"))


# ---------------------------------------------------------------------------
# Swagger / OpenAPI docs visibility
# ---------------------------------------------------------------------------
ENABLE_DOCS = _bool("ENABLE_DOCS", not IS_PRODUCTION)


# ---------------------------------------------------------------------------
# GitHub App connector + local MCP server
# ---------------------------------------------------------------------------
GITHUB_MCP_ENABLED = _bool("GITHUB_MCP_ENABLED", True)
ALLOW_GITHUB_PAT_IMPORT = _bool("ALLOW_GITHUB_PAT_IMPORT", True)
# Fernet key used to encrypt user and refresh tokens at rest.
GITHUB_TOKEN_ENCRYPTION_KEY = os.getenv("GITHUB_TOKEN_ENCRYPTION_KEY", "")
GITHUB_OAUTH_CLIENT_ID = os.getenv("GITHUB_OAUTH_CLIENT_ID", "").strip()
GITHUB_OAUTH_CLIENT_SECRET = os.getenv("GITHUB_OAUTH_CLIENT_SECRET", "").strip()
GITHUB_OAUTH_REDIRECT_URI = os.getenv("GITHUB_OAUTH_REDIRECT_URI", "").strip()
GITHUB_OAUTH_SCOPES = os.getenv("GITHUB_OAUTH_SCOPES", "offline_access").strip()
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").strip()
ADMIN_USER_IDS = _list("ADMIN_USER_IDS", "")
USER_RATE_LIMIT_PER_MINUTE = int(os.getenv("USER_RATE_LIMIT_PER_MINUTE", str(RATE_LIMIT_PER_MINUTE)))
ENABLE_GUEST_MODE = _bool("ENABLE_GUEST_MODE", True)


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------
def config_problems() -> list[str]:
    """
    Returns a list of human‑readable configuration problems.
    An empty list means the configuration is healthy.
    """
    problems = []

    if GUEST_TOKEN_TTL_HOURS < 1 or GUEST_TOKEN_TTL_HOURS > 168:
        problems.append(
            "GUEST_TOKEN_TTL_HOURS must be between 1 and 168"
        )
    if IS_PRODUCTION and (
        not GUEST_TOKEN_SECRET or len(GUEST_TOKEN_SECRET) < 32
    ):
        problems.append(
            "GUEST_TOKEN_SECRET must be at least 32 characters in production"
        )
    if IS_PRODUCTION and (not CLERK_ISSUER_URL or not CLERK_JWKS_URL):
        problems.append(
            "CLERK_ISSUER_URL and CLERK_JWKS_URL are required in production"
        )
    if IS_PRODUCTION and not AUTHORIZED_PARTIES:
        problems.append(
            "AUTHORIZED_PARTIES must contain your trusted frontend origins in production"
        )
    if not MONGO_URI:
        problems.append("MONGO_URI is not set")
    if not MONGO_DB:
        problems.append("MONGO_DB is not set")
    if not GEMINI_API_KEY:
        problems.append(
            "GEMINI_API_KEY is not set (needed for policy search embeddings)"
        )
    if "*" in CORS_ORIGINS:
        problems.append("CORS_ORIGINS must not contain '*'")
    if not CORS_ORIGINS:
        problems.append("CORS_ORIGINS is empty: set it to your frontend URL")
    if IS_PRODUCTION and (not FRONTEND_URL.startswith("https://") or not GITHUB_OAUTH_REDIRECT_URI.startswith("https://")):
        problems.append("FRONTEND_URL and GITHUB_OAUTH_REDIRECT_URI must use HTTPS in production")
    if MONGO_TIMEOUT_MS <= 0:
        problems.append("MONGO_TIMEOUT_MS must be positive")
    if SESSION_TTL_DAYS < 1:
        problems.append("SESSION_TTL_DAYS must be at least 1")
    if EMBED_DIMS <= 0 or EMBED_BATCH_SIZE <= 0 or EMBED_RETRIES < 1:
        problems.append(
            "Embedding dimensions/batch size must be positive and retries at least 1"
        )
    if LLM_TIMEOUT_S <= 0 or LLM_RETRIES < 1 or LLM_RETRY_BASE_S < 0 or LLM_COOLDOWN_S < 0:
        problems.append(
            "LLM timeout/retry/cooldown settings are invalid"
        )
    if FLIGHT_API_TIMEOUT_S <= 0 or FLIGHT_API_CACHE_TTL_S < 0:
        problems.append(
            "Flight API timeout/cache settings are invalid"
        )
    if RATE_LIMIT_PER_MINUTE < 0:
        problems.append(
            "RATE_LIMIT_PER_MINUTE cannot be negative"
        )
    allowed_providers = {"gemini", "groq", "mistral"}
    if not LLM_ORDER:
        problems.append(
            "LLM_ORDER must include at least one configured provider"
        )
    if (
        "gemini" in [p.lower() for p in LLM_ORDER]
        and not GEMINI_MODELS
    ):
        problems.append(
            "GEMINI_MODELS must contain at least one model when Gemini is enabled"
        )
    unknown = [
        provider
        for provider in LLM_ORDER
        if provider.lower() not in allowed_providers
    ]
    if unknown:
        problems.append(
            "LLM_ORDER contains unsupported provider(s): "
            + ", ".join(unknown)
        )
    # GitHub MCP specific checks
    if USER_RATE_LIMIT_PER_MINUTE < 0:
        problems.append("USER_RATE_LIMIT_PER_MINUTE cannot be negative")
    oauth_values = (GITHUB_OAUTH_CLIENT_ID, GITHUB_OAUTH_CLIENT_SECRET, GITHUB_OAUTH_REDIRECT_URI)
    if any(oauth_values) and not all(oauth_values):
        problems.append("Set all GitHub OAuth client ID, secret and redirect URI values together")
    if GITHUB_MCP_ENABLED:
        if not GITHUB_TOKEN_ENCRYPTION_KEY:
            problems.append(
                "GITHUB_TOKEN_ENCRYPTION_KEY must be set for GitHub connector encryption"
            )

    return problems


def validate_production_config() -> None:
    """
    Fail fast at startup in production if the configuration is unsafe.
    """
    if not IS_PRODUCTION:
        return
    problems = config_problems()
    if problems:
        raise RuntimeError(
            "Invalid production configuration: " + "; ".join(problems)
        )