import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(override=False)

BASE_DIR = Path(__file__).resolve().parents[2]   # the backend folder
DATA_DIR = BASE_DIR / "data"
PDF_PATH = DATA_DIR / "policy" / "dgca_car.pdf"
CHUNKS_PATH = DATA_DIR / "policy_chunks.json"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MONGO_URI = os.getenv("MONGODB_URI")
MONGO_DB = os.getenv("MONGO_DB", "flight_AgenticRAG")

EMBED_MODEL = "gemini-embedding-001"
EMBED_DIMS = 768

GEN_MODEL = os.getenv("GEN_MODEL", "gemini-3.8-flash")       # model that writes the answer
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")