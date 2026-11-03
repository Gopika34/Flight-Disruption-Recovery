from pymongo import MongoClient
from app.core.config import MONGO_URI, MONGO_DB
from app.rag.embeddings import embed_query

_col = MongoClient(MONGO_URI)[MONGO_DB]["policy_chunks"]
INDEX_NAME = "policy_vector_index"


def search_policy(query, k=4):
    pipeline = [
        {"$vectorSearch": {
            "index": INDEX_NAME,
            "path": "embedding",
            "queryVector": embed_query(query),
            "numCandidates": 50,
            "limit": k,
        }},
        {"$project": {
            "_id": 0, "clause_id": 1, "section_title": 1,
            "page_start": 1, "page_end": 1, "text": 1,
            "document_version": 1, "effective_date": 1,
            "score": {"$meta": "vectorSearchScore"},
        }},
    ]
    return list(_col.aggregate(pipeline))


def get_clause(clause_id):
    return _col.find_one({"clause_id": clause_id}, {"_id": 0, "embedding": 0})

# Clauses that legally travel together (taken from the CAR's own cross-references)
RELATED = {
    "3.2.2": ["3.2.1"],
    "3.3.1": ["3.3.2"],
    "3.3.2": ["3.3.1", "3.3.3", "3.3.4", "3.3.5"],
    "3.3.4": ["3.3.2", "3.3.5"],
    "3.4.1": ["3.4.4", "3.8.1"],
    "3.4.2": ["3.4.4"],
    "3.4.3": ["3.4.4", "3.8.1"],
}


def search_with_related(query, k=4, max_total=8):
    hits = search_policy(query, k)
    for h in hits:
        h["retrieved_by"] = "vector"

    have = [h["clause_id"] for h in hits]
    extra_ids = []
    for cid in have:
        for rid in RELATED.get(cid, []):
            if rid not in have and rid not in extra_ids:
                extra_ids.append(rid)

    for rid in extra_ids:
        if len(hits) >= max_total:
            break
        clause = get_clause(rid)
        if clause:
            clause["score"] = None
            clause["retrieved_by"] = "related"
            hits.append(clause)
    return hits
