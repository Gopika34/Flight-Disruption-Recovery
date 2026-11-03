from fastapi import FastAPI
from app.rag.retriever import search_policy

app = FastAPI(title="Flight Disruption Recovery Engine")

@app.get("/")
def health():
    return {"status": "running"}

@app.get("/search")
def search(q: str, k: int = 4):
    return {"query": q, "results": search_policy(q, k)}