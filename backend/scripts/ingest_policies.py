"""Ingest validated policy chunks into MongoDB Atlas (safe and repeatable).

Usage (from the backend folder):
    python -m scripts.ingest_policies --dry-run     # validate + embed, write nothing
    python -m scripts.ingest_policies               # full ingest
    python -m scripts.ingest_policies --skip-smoke  # skip the final search check

Running it twice is safe: chunks are upserted by chunk_id.
"""
import argparse
import json
import sys
import time

from pymongo import MongoClient, ReplaceOne
from pymongo.operations import SearchIndexModel

from app.core.config import (
    CHUNKS_PATH,
    EMBED_DIMS,
    MONGO_DB,
    MONGO_TIMEOUT_MS,
    MONGO_URI,
    PDF_PATH,
)
from app.rag.embeddings import embed_documents
from app.rag.validation import validate_chunks

INDEX_NAME = "policy_vector_index"
COLLECTION = "policy_chunks"
REQUIRED_KEYS = ("chunk_id", "clause_id", "section_title", "text", "content_hash")


def fail(message):
    print(f"\nERROR: {message}")
    sys.exit(1)


def load_chunks():
    """Step 1: load and validate the existing chunk file."""
    chunks = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))

    for chunk in chunks:
        missing = [key for key in REQUIRED_KEYS if not chunk.get(key)]
        if missing:
            fail(f"Chunk {chunk.get('chunk_id')} is missing fields: {missing}")

    ids = [c["chunk_id"] for c in chunks]
    if len(ids) != len(set(ids)):
        fail("Duplicate chunk_id values in policy_chunks.json")

    try:
        import pymupdf
        with pymupdf.open(PDF_PATH) as doc:
            total_pages = len(doc)
    except Exception:
        total_pages = max(c["page_end"] for c in chunks)

    errors = validate_chunks(chunks, total_pages)
    if errors:
        fail("Chunk validation failed:\n - " + "\n - ".join(errors))

    print(f"Loaded and validated {len(chunks)} chunks")
    return chunks


def embed_all(chunks):
    """Steps 2-4: batch embed, then verify count, order and dimensions."""
    # The label goes on the "folder": clause id and topic are embedded with the text.
    inputs = [f"Clause {c['clause_id']} - {c['section_title']}. {c['text']}" for c in chunks]
    print(f"Embedding {len(inputs)} clauses in batches...")
    vectors = embed_documents(inputs)

    if len(vectors) != len(chunks):
        fail(f"Got {len(vectors)} embeddings for {len(chunks)} chunks")
    bad = [i for i, v in enumerate(vectors) if len(v) != EMBED_DIMS]
    if bad:
        fail(f"Embeddings with wrong dimension at positions {bad}")

    print(f"Embeddings OK: {len(vectors)} x {EMBED_DIMS} dimensions")
    return vectors


def store(col, chunks, vectors):
    """Step 5: idempotent upsert by chunk_id."""
    ops = [
        ReplaceOne({"chunk_id": c["chunk_id"]}, {**c, "embedding": v}, upsert=True)
        for c, v in zip(chunks, vectors, strict=True)
    ]
    result = col.bulk_write(ops)
    print(f"Upserted: {result.upserted_count} new, {result.modified_count} updated")


def verify_store(col, chunks):
    """Steps 6-7: stored count, chunk ids, hashes and embedding sizes."""
    expected = {c["chunk_id"]: c["content_hash"] for c in chunks}
    stored = {
        d["chunk_id"]: d
        for d in col.find({"chunk_id": {"$in": list(expected)}},
                          {"chunk_id": 1, "content_hash": 1, "embedding": 1})
    }

    missing = sorted(set(expected) - set(stored))
    if missing:
        fail(f"{len(missing)} chunks were not stored: {missing[:5]}")

    wrong_hash = [i for i, h in expected.items() if stored[i].get("content_hash") != h]
    if wrong_hash:
        fail(f"Stored content_hash differs for: {wrong_hash[:5]}")

    wrong_dims = [i for i, d in stored.items() if len(d.get("embedding", [])) != EMBED_DIMS]
    if wrong_dims:
        fail(f"Stored embeddings with wrong size: {wrong_dims[:5]}")

    extra = col.count_documents({"chunk_id": {"$nin": list(expected)}})
    if extra:
        print(f"Note: {extra} stored documents are not in the chunk file (left untouched).")

    print(f"Verified {len(stored)} stored chunks (ids, hashes, dimensions)")


def ensure_index(col, timeout_s=300):
    """Steps 8-9: create or verify the Atlas vector index, wait until queryable."""
    existing = list(col.list_search_indexes(INDEX_NAME))

    if existing:
        fields = existing[0].get("latestDefinition", existing[0].get("definition", {})).get("fields", [])
        dims = [f.get("numDimensions") for f in fields if f.get("type") == "vector"]
        if dims and dims[0] != EMBED_DIMS:
            fail(f"Existing index has {dims[0]} dimensions but EMBED_DIMS is {EMBED_DIMS}. "
                 f"Drop and recreate the index in Atlas.")
        print("Vector index already exists")
    else:
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
        print("Vector index creation started")

    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        found = list(col.list_search_indexes(INDEX_NAME))
        if found and found[0].get("queryable"):
            print("Vector index is READY")
            return
        print("  waiting for index to become queryable...")
        time.sleep(10)

    fail(f"Index not queryable after {timeout_s}s. Check Atlas > Search Indexes.")


def smoke_test():
    """Step 10 (quick): one real search. Full evaluation: pytest -m integration."""
    from app.rag.retriever import search_policy

    hits = search_policy("airline cancelled my flight with a few hours notice", k=3)
    if not hits:
        fail("Smoke search returned no results. Is the index ready?")
    print("Smoke search OK, top clauses:", [h["clause_id"] for h in hits])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="validate and embed only; write nothing")
    parser.add_argument("--skip-index", action="store_true")
    parser.add_argument("--skip-smoke", action="store_true")
    args = parser.parse_args(argv)

    chunks = load_chunks()
    vectors = embed_all(chunks)

    if args.dry_run:
        print("\nDry run complete: nothing was written to MongoDB.")
        return

    if not MONGO_URI or not MONGO_DB:
        fail("MONGO_URI and MONGO_DB must be set.")

    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=MONGO_TIMEOUT_MS)
    try:
        col = client[MONGO_DB][COLLECTION]
        store(col, chunks, vectors)
        verify_store(col, chunks)
        if not args.skip_index:
            ensure_index(col)
            if not args.skip_smoke:
                smoke_test()
    finally:
        client.close()

    print("\nIngestion finished successfully.")


if __name__ == "__main__":
    main()
