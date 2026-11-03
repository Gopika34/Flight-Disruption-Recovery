import json
from app.core.config import PDF_PATH, CHUNKS_PATH
from app.loaders.pdf_loader import load_pdf_pages
from app.rag.chunking import build_clause_chunks

pages = load_pdf_pages(PDF_PATH)
print(f"Loaded {len(pages)} pages")

chunks = build_clause_chunks(pages)
print(f"Built {len(chunks)} clause chunks\n")

for c in chunks:
    print(f"{c['clause_id']:<8} p{c['page_start']}-{c['page_end']}  "
          f"{c['section_title'][:22]:<22} {c['text'][:60]}")

EXPECTED = (
    [f"1.{i}" for i in range(1, 8)] + [f"2.{i}" for i in range(1, 11)]
    + ["3.1.1", "3.1.2", "3.1.3", "3.2.1", "3.2.2", "3.2.3"]
    + [f"3.3.{i}" for i in range(1, 6)] + [f"3.4.{i}" for i in range(1, 6)]
    + ["3.5.1", "3.6.1", "3.7.1", "3.8.1", "3.8.2", "3.9.1", "3.9.2", "3.9.3"]
    + [f"3.10.{i}" for i in range(1, 7)]
)

found = [c["clause_id"] for c in chunks]
print("\nMissing:   ", [e for e in EXPECTED if e not in found] or "none")
print("Unexpected:", [f for f in found if f not in EXPECTED] or "none")

CHUNKS_PATH.write_text(json.dumps(chunks, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Saved to {CHUNKS_PATH}")