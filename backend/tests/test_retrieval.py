"""Retrieval quality against the REAL Atlas index.

Run with:  pytest -m integration -s
Needs MONGO_URI, MONGO_DB and GEMINI_API_KEY, and a ready vector index.
"""
import json
import os
import re

import pytest

from app.core.config import BASE_DIR, GEMINI_API_KEY, MONGO_DB, MONGO_URI

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not (MONGO_URI and MONGO_DB and GEMINI_API_KEY),
        reason="MongoDB / Gemini credentials not configured",
    ),
]

raw = json.loads((BASE_DIR / "data" / "rag_evaluation.json").read_text(encoding="utf-8"))
QUESTIONS = raw if isinstance(raw, list) else (raw.get("questions") or raw.get("cases") or [])

# Minimum overall clause recall. Set your own baseline after the first real run.
MIN_RECALL = float(os.getenv("RETRIEVAL_MIN_RECALL", "0.8"))


def expected_ids(q):
    v = q.get("expected_clause_ids", q.get("verified_clause_id"))
    if not isinstance(v, list):
        return []
    return [re.sub(r"\(.*\)$", "", x) for x in v]


CASES = [q for q in QUESTIONS if expected_ids(q)]


@pytest.fixture(scope="module", autouse=True)
def index_ready():
    from app.rag.retriever import vector_index_status
    status = vector_index_status()
    assert status == "ready", f"Vector index is {status}"


@pytest.mark.parametrize("q", CASES, ids=[str(q.get("question_id", i)) for i, q in enumerate(CASES)])
def test_any_expected_clause_retrieved(q):
    from app.rag.retriever import search_with_related
    got = {r["clause_id"] for r in search_with_related(q["question"])}
    assert set(expected_ids(q)) & got, f"none of {expected_ids(q)} in {sorted(got)}"


def test_overall_clause_recall():
    from app.rag.retriever import search_policy, search_with_related

    for label, fn in (("vector only", lambda s: search_policy(s, k=4)),
                      ("vector + related", search_with_related)):
        found = total = all_hit = 0
        for q in CASES:
            exp = set(expected_ids(q))
            got = {r["clause_id"] for r in fn(q["question"])}
            found += len(exp & got)
            total += len(exp)
            all_hit += exp <= got
        recall = found / total
        print(f"{label}: all-clauses {all_hit}/{len(CASES)} | recall {found}/{total} ({recall:.0%})")

    assert recall >= MIN_RECALL, f"recall {recall:.0%} below {MIN_RECALL:.0%}"
