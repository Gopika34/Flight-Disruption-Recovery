import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(override=True)

BASE_DIR = Path(__file__).resolve().parents[2]   # the backend folder
PDF_PATH = BASE_DIR / "data" / "policy" / "dgca_car.pdf"
CHUNKS_PATH = BASE_DIR / "data" / "policy_chunks.json"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MONGO_URI = os.getenv("MONGODB_URI")
MONGO_DB = os.getenv("MONGO_DB", "flight_engine")

EMBED_MODEL = "gemini-embedding-001"
EMBED_DIMS = 768