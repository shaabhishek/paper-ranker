"""PDF parsing utilities using PyMuPDF."""

import hashlib
import logging
import re
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


class PDFParser:
  """PDF parser for extracting text and metadata from academic papers."""

  def __init__(self, chunk_size: int = 10000):
    """Initialize PDF parser with specified chunk size."""
    self.chunk_size = chunk_size

  def extract_text(self, pdf_path: str) -> str:
    """Extract full text from PDF file."""
    logger.info(f'Extracting text from {pdf_path}')

    try:
      doc = fitz.open(pdf_path)
      full_text = ''

      for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text()
        full_text += text + '\n'

      doc.close()

      # Clean up the text
      full_text = self._clean_text(full_text)
      logger.info(f'Extracted {len(full_text)} characters from {pdf_path}')

      return full_text

    except Exception as e:
      logger.error(f'Error extracting text from {pdf_path}: {e}')
      return ''

  def extract_metadata(self, pdf_path: str) -> Dict[str, Any]:
    """Extract metadata (title, authors, year) from PDF."""
    logger.info(f'Extracting metadata from {pdf_path}')

    try:
      doc = fitz.open(pdf_path)
      metadata = doc.metadata

      # Get first page text for title/author extraction
      first_page = doc.load_page(0).get_text()

      doc.close()

      # Extract information
      extracted_metadata = {
        'title': self._extract_title(metadata, first_page),
        'authors': self._extract_authors(metadata, first_page),
        'year': self._extract_year(metadata, first_page),
        'venue': self._extract_venue(first_page),
        'keywords': self._extract_keywords(first_page),
      }

      logger.info(f'Extracted metadata: {extracted_metadata}')
      return extracted_metadata

    except Exception as e:
      logger.error(f'Error extracting metadata from {pdf_path}: {e}')
      return {}

  def chunk_text(self, text: str) -> List[str]:
    """Split text into chunks of specified size."""
    logger.info(f'Chunking text into {self.chunk_size} character chunks')

    if not text:
      return []

    chunks = []
    words = text.split()
    current_chunk = ''

    for word in words:
      # Check if adding this word would exceed chunk size
      if len(current_chunk) + len(word) + 1 > self.chunk_size:
        if current_chunk:
          chunks.append(current_chunk.strip())
          current_chunk = word
        else:
          # Single word is longer than chunk size, add it anyway
          chunks.append(word)
          current_chunk = ''
      else:
        current_chunk += ' ' + word if current_chunk else word

    # Add the last chunk if it exists
    if current_chunk:
      chunks.append(current_chunk.strip())

    logger.info(f'Created {len(chunks)} chunks')
    return chunks

  def process_pdf(self, pdf_path: str) -> Dict[str, Any]:
    """Process PDF and return text chunks with metadata."""
    logger.info(f'Processing PDF: {pdf_path}')

    # Generate paper ID from file path
    paper_id = self._generate_paper_id(pdf_path)

    # Extract text and metadata
    text = self.extract_text(pdf_path)
    metadata = self.extract_metadata(pdf_path)

    # Chunk the text
    chunks = self.chunk_text(text)

    result = {
      'paper_id': paper_id,
      'text': text,
      'chunks': chunks,
      'metadata': metadata,
      'chunk_count': len(chunks),
      'text_length': len(text),
    }

    logger.info(
      f'Processed PDF: {paper_id} - {len(chunks)} chunks, {len(text)} chars'
    )
    return result

  def _clean_text(self, text: str) -> str:
    """Clean extracted text by removing extra whitespace and formatting."""
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)

    # Remove page numbers and headers/footers (simple heuristic)
    lines = text.split('\n')
    cleaned_lines = []

    for line in lines:
      line = line.strip()
      # Skip very short lines that might be page numbers or artifacts
      if len(line) > 3:
        cleaned_lines.append(line)

    return ' '.join(cleaned_lines)

  def _extract_title(self, metadata: Dict, first_page: str) -> str:
    """Extract title from metadata or first page."""
    # Try metadata first
    if metadata and metadata.get('title'):
      return metadata['title'].strip()

    # Try to extract from first page (first few lines, usually title)
    lines = first_page.split('\n')[:10]
    for line in lines:
      line = line.strip()
      # Title is usually one of the first substantial lines
      if len(line) > 10 and not line.isupper():
        return line

    return 'Unknown Title'

  def _extract_authors(self, metadata: Dict, first_page: str) -> List[str]:
    """Extract authors from metadata or first page."""
    # Try metadata first
    if metadata and metadata.get('author'):
      authors = metadata['author'].split(',')
      return [author.strip() for author in authors if author.strip()]

    # Try to extract from first page
    # Look for patterns like "Author1, Author2" or "Author1 and Author2"
    lines = first_page.split('\n')[:15]
    for line in lines:
      if re.search(r'\b(and|,)\b', line) and len(line.split()) < 10:
        # Likely an author line
        authors = re.split(r'\s+and\s+|,', line)
        return [author.strip() for author in authors if author.strip()]

    return []

  def _extract_year(self, metadata: Dict, first_page: str) -> Optional[int]:
    """Extract publication year."""
    # Try metadata first
    if metadata and metadata.get('creationDate'):
      try:
        # Extract year from creation date
        year_match = re.search(r'(\d{4})', str(metadata['creationDate']))
        if year_match:
          return int(year_match.group(1))
      except:
        pass

    # Try to find year in first page
    year_pattern = r'\b(19|20)\d{2}\b'
    matches = re.findall(year_pattern, first_page)
    if matches:
      return int(matches[0])

    return None

  def _extract_venue(self, first_page: str) -> Optional[str]:
    """Extract venue/conference information."""
    # Look for common conference/journal patterns
    venue_patterns = [
      r'Proceedings of[^.]*',
      r'Conference on[^.]*',
      r'International Conference[^.]*',
      r'Journal of[^.]*',
      r'IEEE[^.]*',
      r'ACM[^.]*',
    ]

    for pattern in venue_patterns:
      match = re.search(pattern, first_page, re.IGNORECASE)
      if match:
        return match.group(0).strip()

    return None

  def _extract_keywords(self, first_page: str) -> List[str]:
    """Extract keywords if available."""
    # Look for keywords section
    keywords_match = re.search(
      r'keywords?[:\-\s]+(.*?)(?:\n|$)', first_page, re.IGNORECASE | re.DOTALL
    )

    if keywords_match:
      keywords_text = keywords_match.group(1)
      # Split by common delimiters
      keywords = re.split(r'[,;·•]', keywords_text)
      return [kw.strip() for kw in keywords if kw.strip()]

    return []

  def _generate_paper_id(self, pdf_path: str) -> str:
    """Generate a unique paper ID from the file path."""
    # Use filename without extension as base
    filename = pdf_path.split('/')[-1].replace('.pdf', '')

    # Create a hash for uniqueness
    hash_obj = hashlib.md5(pdf_path.encode())
    hash_suffix = hash_obj.hexdigest()[:8]

    return f'{filename}_{hash_suffix}'
