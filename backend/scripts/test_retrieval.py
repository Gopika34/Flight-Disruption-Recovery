import json
import re
from app.core.config import BASE_DIR
from app.rag.retriever import search_policy, search_with_related

raw = json.loads((BASE_DIR / "data" / "rag_evaluation.json").read_text(encoding="utf-8"))
questions = raw if isinstance(raw, list) else (raw.get("questions") or raw.get("cases") or [])


def expected_ids(q):
    v = q.get("expected_clause_ids", q.get("verified_clause_id"))
    if not isinstance(v, list):
        return []
    return [re.sub(r"\(.*\)$", "", x) for x in v]


def run(search_fn, label):
    tested = any_hit = full_hit = found = total = 0
    for q in questions:
        exp = expected_ids(q)
        if not exp:
            continue
        got = {r["clause_id"] for r in search_fn(q["question"])}
        hit = set(exp) & got
        tested += 1
        any_hit += bool(hit)
        full_hit += set(exp) <= got
        found += len(hit)
        total += len(exp)
        missing = sorted(set(exp) - got)
        if missing:
            print(f"  [{label}] {q['question_id']} missing {missing}")
    print(f"{label}: any-hit {any_hit}/{tested} | all-clauses {full_hit}/{tested} | "
          f"clause recall {found}/{total} ({found / total:.0%})\n")


run(lambda q: search_policy(q, k=4), "vector only")
run(lambda q: search_with_related(q), "vector + related")