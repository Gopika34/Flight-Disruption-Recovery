
import hashlib
from collections import Counter


EXPECTED_CLAUSES = (
    [f"1.{i}" for i in range(1, 8)]
    + [f"2.{i}" for i in range(1, 11)]
    + [
        "3.1.1", "3.1.2", "3.1.3",
        "3.2.1", "3.2.2", "3.2.3",
    ]
    + [f"3.3.{i}" for i in range(1, 6)]
    + [f"3.4.{i}" for i in range(1, 6)]
    + [
        "3.5.1", "3.6.1", "3.7.1",
        "3.8.1", "3.8.2",
        "3.9.1", "3.9.2", "3.9.3",
    ]
    + [f"3.10.{i}" for i in range(1, 7)]
)


REQUIRED_FIELDS = {
    "chunk_id",
    "clause_id",
    "section_title",
    "page_start",
    "page_end",
    "text",
    "content_hash",
    "document_id",
    "document_title",
    "document_version",
    "effective_date",
}


def validate_chunks(chunks, total_pages):
    """
    Validate extracted policy chunks before saving or ingestion.

    Returns:
        list[str]: Validation errors.
        An empty list means all structural checks passed.
    """

    errors = []

    if not isinstance(chunks, list):
        return ["Chunks must be a list."]

    if not chunks:
        return ["No chunks were generated."]

    clause_ids = [
        chunk.get("clause_id")
        for chunk in chunks
        if isinstance(chunk, dict)
    ]

    # 1. Validate missing and unexpected clauses.
    found = set(clause_ids)

    missing = sorted(set(EXPECTED_CLAUSES) - found)
    unexpected = sorted(found - set(EXPECTED_CLAUSES))

    if missing:
        errors.append(f"Missing clauses: {missing}")

    if unexpected:
        errors.append(f"Unexpected clauses: {unexpected}")

    # 2. Validate duplicate clause IDs.
    counts = Counter(clause_ids)

    duplicates = sorted(
        clause_id
        for clause_id, count in counts.items()
        if clause_id is not None and count > 1
    )

    if duplicates:
        errors.append(f"Duplicate clause IDs: {duplicates}")

    # 3. Validate each chunk.
    for index, chunk in enumerate(chunks):

        if not isinstance(chunk, dict):
            errors.append(f"Chunk at index {index} is not a dictionary.")
            continue

        clause_id = chunk.get("clause_id", f"INDEX_{index}")

        # Required metadata.
        missing_fields = REQUIRED_FIELDS - set(chunk.keys())

        if missing_fields:
            errors.append(
                f"{clause_id}: Missing fields {sorted(missing_fields)}"
            )
            continue

        # Chunk ID consistency.
        expected_chunk_id = f"{chunk['document_id']}_{clause_id}"

        if chunk["chunk_id"] != expected_chunk_id:
            errors.append(f"{clause_id}: Invalid chunk_id")

        # Text validation.
        text = chunk.get("text")

        if not isinstance(text, str) or not text.strip():
            errors.append(f"{clause_id}: Empty or invalid text")
            continue

        # Page validation.
        start = chunk.get("page_start")
        end = chunk.get("page_end")

        if (
            not isinstance(start, int)
            or isinstance(start, bool)
            or not isinstance(end, int)
            or isinstance(end, bool)
        ):
            errors.append(f"{clause_id}: Page numbers must be integers")

        elif start < 1 or end > total_pages or start > end:
            errors.append(
                f"{clause_id}: Invalid page range {start}-{end}"
            )

        # Hash validation.
        actual_hash = hashlib.sha256(
            text.encode("utf-8")
        ).hexdigest()

        if chunk.get("content_hash") != actual_hash:
            errors.append(f"{clause_id}: Content hash mismatch")

    return errors
