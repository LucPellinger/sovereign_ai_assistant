'''Extract text content from various document formats.'''

from bs4 import BeautifulSoup
from io import BytesIO
from pypdf import PdfReader

def extract_text_from_xhtml(content: bytes) -> str:
    '''
    Extract human-visible text from XHTML content.
    
    Args:
        content (bytes): The XHTML content as bytes.
        
    Returns:
        str: The extracted text.
    '''
    soup = BeautifulSoup(content, "lxml")
    # Keep human-visible text; drop nav/figcaptions if desired
    return soup.get_text(" ", strip=True)

def extract_text_from_pdf(content: bytes) -> str:
    '''
    Extract text from PDF content.
    
    Args:
        content (bytes): The PDF content as bytes.
        
    Returns:
        str: The extracted text.
    '''
    reader = PdfReader(BytesIO(content))
    pages = [p.extract_text() or "" for p in reader.pages]
    return "\n".join(pages)
