import json
from pymongo import MongoClient, ReplaceOne
from pymongo.operations import SearchIndexModel
from app.core.config import MONGO_URI, MONGO_DB, CHUNKS_PATH, EMBED_DIMS
from app.rag.embeddings import embed_documents

INDEX_NAME = "policy_vector_index"

chunks = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))

# The label goes on the "folder": the clause id and topic are embedded with the text
inputs = [f"Clause {c['clause_id']} - {c['section_title']}. {c['text']}" for c in chunks]
print(f"Embedding {len(inputs)} clauses (this takes a minute)...")
vectors = embed_documents(inputs)

col = MongoClient(MONGO_URI)[MONGO_DB]["policy_chunks"]
ops = []
for c, v in zip(chunks, vectors):
    assert len(v) == EMBED_DIMS, f"Unexpected vector size: {len(v)}"
    ops.append(ReplaceOne({"chunk_id": c["chunk_id"]}, {**c, "embedding": v}, upsert=True))
col.bulk_write(ops)
print(f"Stored {len(ops)} clauses in Atlas")

try:
    col.create_search_index(model=SearchIndexModel(
        definition={"fields": [{
            "type": "vector",
            "path": "embedding",
            "numDimensions": EMBED_DIMS,
            "similarity": "cosine",
        }]},
        name=INDEX_NAME,
        type="vectorSearch",
    ))
    print("Vector index creation started (wait ~1 minute before searching)")
except Exception as e:
    print("Index step said:", e)
    print("If it is not 'already exists', create it in the Atlas UI (see below).")