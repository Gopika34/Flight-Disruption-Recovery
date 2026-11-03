import hashlib
import re

DOC_ID = "DGCA_CAR_M_IV_R4"
DOC_META = {
    "document_id": DOC_ID,
    "document_title": "Civil Aviation Requirements, Section 3, Series M, Part IV",
    "issuing_authority": "DGCA",
    "document_version": "Revision 4",
    "publication_date": "2023-01-25",
    "effective_date": "2023-02-15",
}

# Lines that repeat on every page and are not policy text
NOISE_PATTERNS = [
    re.compile(r"^CIVIL AVIATION REQUIREMENTS$"),
    re.compile(r"^SERIES.*PART IV$"),
    re.compile(r"^SECTION 3$"),
    re.compile(r"^6?\s*TH AUGUST, 2010$"),
    re.compile(r"^\(Arun Kumar\).*$"),
    re.compile(r"^Director General of Civil Aviation$"),
    re.compile(r"^Rev\. 4, dated.*$"),
    re.compile(r"^\d{1,2}$"),            # lone page numbers
]

CLAUSE_START = re.compile(r"^(\d+(?:\.\d+)+)\s+(?=[A-Z])")   # "3.3.2 Passengers..."
SECTION_HEADING = re.compile(r"^\d+\.\s+[A-Z][A-Z ]+$")      # "1. INTRODUCTION"
SUBSECTION_ID = re.compile(r"^3\.\d+$")                      # 3.1, 3.2 ... are titles

LONE_NUMBER = re.compile(r"^\d+(?:\.\d+)+$")

def _clean_lines(page_text):
    lines = [l.strip() for l in page_text.splitlines()]
    lines = [l for l in lines if l and not any(p.match(l) for p in NOISE_PATTERNS)]
    merged, i = [], 0
    while i < len(lines):
        if LONE_NUMBER.match(lines[i]) and i + 1 < len(lines):
            merged.append(lines[i] + " " + lines[i + 1])   # "3.8.2" + "Airlines shall..."
            i += 2
        else:
            merged.append(lines[i])
            i += 1
    return merged


def build_clause_chunks(pages):
    chunks, seen = [], set()
    current = None
    section_title = ""

    def flush():
        nonlocal current
        if current:
            text = " ".join(current["lines"]).replace("\uf0b7", "-")
            text = re.sub(r"(?<=[a-z])-\s+(?=[a-z])", "-", text)   # "non- scheduled" -> "non-scheduled"
            text = re.sub(r"\s+", " ", text).strip()
            chunks.append({
                "chunk_id": f"{DOC_ID}_{current['clause_id']}",
                "clause_id": current["clause_id"],
                "section_title": current["section_title"],
                "page_start": current["page_start"],
                "page_end": current["page_end"],
                "text": text,
                "content_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "verified": False,
                **DOC_META,
            })
        current = None

    for page in pages:
        for line in _clean_lines(page["text"]):

            if SECTION_HEADING.match(line):
                flush()
                section_title = line.split(".", 1)[1].strip().title()
                continue

            m = CLAUSE_START.match(line)
            if m and m.group(1) not in seen:
                clause_id = m.group(1)
                rest = line[m.end():]
                flush()
                seen.add(clause_id)
                if SUBSECTION_ID.match(clause_id):      # a title, not a clause
                    section_title = rest.strip()
                    continue
                current = {
                    "clause_id": clause_id,
                    "section_title": section_title,
                    "page_start": page["page_number"],
                    "page_end": page["page_number"],
                    "lines": [rest],
                }
            elif current:
                current["lines"].append(line)
                current["page_end"] = page["page_number"]

    flush()
    return chunks