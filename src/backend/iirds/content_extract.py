from bs4 import BeautifulSoup
from io import BytesIO
from pypdf import PdfReader

def extract_text_from_xhtml(content: bytes) -> str:
    soup = BeautifulSoup(content, "lxml")
    # Keep human-visible text; drop nav/figcaptions if desired
    return soup.get_text(" ", strip=True)

def extract_text_from_pdf(content: bytes) -> str:
    reader = PdfReader(BytesIO(content))
    pages = [p.extract_text() or "" for p in reader.pages]
    return "\n".join(pages)
