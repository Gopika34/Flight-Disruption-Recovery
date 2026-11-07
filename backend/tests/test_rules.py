import json
import re
from app.core.config import BASE_DIR
from app.rules.rule_engine import evaluate

cases = json.loads((BASE_DIR / "data" / "test_cases.json").read_text(encoding="utf-8"))["cases"]


def base(clause):
    return re.sub(r"\(.*\)$", "", clause)          # "3.2.2(a)" -> "3.2.2"


passed = failed = skipped = 0
for case in cases:
    cid = case["case_id"]
    try:
        res = evaluate(case)
    except ValueError:
        print(f"SKIP {cid}  (not a rule-engine case)")
        skipped += 1
        continue

    problems = []
    if "expected_compensation" in case and res["compensation"] != case["expected_compensation"]:
        problems.append(f"compensation {res['compensation']} != {case['expected_compensation']}")
    for key, field in (("expected_meals", "meals"), ("expected_hotel", "hotel"),
                       ("expected_alt_or_refund", "alt_or_refund")):
        if key in case and res[field] != case[key]:
            problems.append(f"{field} {res[field]} != {case[key]}")
    if not set(case.get("expected_missing_facts", [])) <= set(res["missing_facts"]):
        problems.append(f"missing facts {res['missing_facts']}")
    expected = {base(c) for c in case.get("expected_clause_ids", [])}
    if not expected <= {base(c) for c in res["clauses"]}:
        problems.append(f"clauses {sorted(expected - {base(c) for c in res['clauses']})} not cited")

    tag = "  (boundary interpretation)" if case.get("boundary_interpretation") else ""
    if problems:
        failed += 1
        print(f"FAIL {cid}{tag}: " + "; ".join(problems))
    else:
        passed += 1
        print(f"PASS {cid}{tag}")

print(f"\nPassed {passed}/{passed + failed}  (skipped {skipped})")