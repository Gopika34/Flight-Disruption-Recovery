import json
import sys
from app.core.config import PDF_PATH, CHUNKS_PATH
from app.loaders.pdf_loader import load_pdf_pages
from app.rag.chunking import build_clause_chunks
from app.rag.validation import validate_chunks


def main():
    print("Loading DGCA policy PDF...")

    pages = load_pdf_pages(PDF_PATH)
    print(f"Loaded {len(pages)} pages")

    print("\nExtracting policy clauses...")

    chunks = build_clause_chunks(pages)
    print(f"Built {len(chunks)} chunks")

    print("\nRunning validation...")

    errors = validate_chunks(chunks, len(pages))

    if errors:
        print("\nVALIDATION FAILED")

        for error in errors:
            print(f" - {error}")

        print("\nExisting JSON was not modified.")
        sys.exit(1)

    print("\nVALIDATION PASSED")

    for chunk in chunks:
        print(
            f"{chunk['clause_id']:<8} "
            f"p{chunk['page_start']}-{chunk['page_end']} "
            f"{chunk['section_title']}"
        )

    temp_path = CHUNKS_PATH.with_suffix(".tmp")

    temp_path.write_text(
        json.dumps(chunks, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    temp_path.replace(CHUNKS_PATH)

    print(f"\nSaved {len(chunks)} validated chunks.")
    print(f"Output: {CHUNKS_PATH}")


if __name__ == "__main__":
    main()