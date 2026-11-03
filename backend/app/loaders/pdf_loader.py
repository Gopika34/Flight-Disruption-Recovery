import pymupdf

def load_pdf_pages(pdf_path):
    pages = []
    with pymupdf.open(pdf_path) as doc:
        for i, page in enumerate(doc, start=1):
            pages.append({"page_number": i, "text": page.get_text()})
    return pages