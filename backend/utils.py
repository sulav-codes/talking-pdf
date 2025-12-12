"""Utility functions for text extraction and processing"""
import re
import logging
from typing import List
from pathlib import Path

from PyPDF2 import PdfReader

logger = logging.getLogger(__name__)


def extract_text(file_path: str) -> tuple:
    """
    Extract text from a PDF file with page numbers
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Tuple of (full_text, page_map) where page_map is list of (page_num, text) tuples
    """
    try:
        if not Path(file_path).exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        reader = PdfReader(file_path)
        
        if len(reader.pages) == 0:
            raise ValueError("PDF has no pages")
        
        logger.info(f"Extracting text from {len(reader.pages)} pages")
        
        text_parts = []
        page_map = []  # Track which text came from which page
        
        for page_num, page in enumerate(reader.pages, 1):
            try:
                page_text = page.extract_text()
                if page_text:
                    cleaned_page_text = clean_text(page_text)
                    text_parts.append(cleaned_page_text)
                    page_map.append((page_num, cleaned_page_text))
            except Exception as e:
                logger.warning(f"Failed to extract text from page {page_num}: {e}")
                continue
        
        full_text = "\n\n".join(text_parts)
        
        logger.info(f"Extracted {len(full_text)} characters from {len(page_map)} pages")
        
        return full_text, page_map
        
    except Exception as e:
        logger.error(f"Text extraction failed for {file_path}: {e}")
        raise


def clean_text(text: str) -> str:
    """
    Clean and normalize extracted text
    
    Args:
        text: Raw text to clean
        
    Returns:
        Cleaned text
    """
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove excessive newlines
    text = re.sub(r'\n\s*\n', '\n\n', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text


def chunk_text_with_pages(text: str, page_map: List[tuple], chunk_size: int = 1000, chunk_overlap: int = 200) -> List[tuple]:
    """
    Chunk text while preserving page number information
    
    Args:
        text: Full text to chunk
        page_map: List of (page_num, page_text) tuples
        chunk_size: Target size for each chunk
        chunk_overlap: Overlap between chunks
        
    Returns:
        List of (chunk_text, page_numbers) tuples
    """
    chunks_with_pages = []
    
    # Build position map for page numbers
    position = 0
    page_positions = []  # (start_pos, end_pos, page_num)
    
    for page_num, page_text in page_map:
        start = position
        end = position + len(page_text)
        page_positions.append((start, end, page_num))
        position = end + 2  # Account for \n\n separator
    
    # Chunk the text
    chunks = chunk_text(text, chunk_size, chunk_overlap)
    
    # Map chunks to page numbers
    current_pos = 0
    for chunk in chunks:
        chunk_start = text.find(chunk, current_pos)
        if chunk_start == -1:
            chunk_start = current_pos
        chunk_end = chunk_start + len(chunk)
        
        # Find which pages this chunk overlaps with
        chunk_pages = set()
        for start, end, page_num in page_positions:
            # Check if chunk overlaps with this page
            if not (chunk_end < start or chunk_start > end):
                chunk_pages.add(page_num)
        
        chunks_with_pages.append((chunk, sorted(list(chunk_pages))))
        current_pos = chunk_start + 1
    
    return chunks_with_pages


def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
    """
    Split text into overlapping chunks for better context preservation
    
    Args:
        text: Text to chunk
        chunk_size: Maximum size of each chunk
        chunk_overlap: Number of characters to overlap between chunks
        
    Returns:
        List of text chunks
    """
    if not text:
        return []
    
    if chunk_size <= chunk_overlap:
        raise ValueError("chunk_size must be greater than chunk_overlap")
    
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = start + chunk_size
        
        # If not the last chunk, try to find a good break point
        if end < text_length:
            # Look for sentence end or paragraph break
            chunk_text = text[start:end]
            
            # Try to break at sentence boundaries
            last_period = chunk_text.rfind('. ')
            last_newline = chunk_text.rfind('\n')
            last_question = chunk_text.rfind('? ')
            last_exclamation = chunk_text.rfind('! ')
            
            break_point = max(last_period, last_newline, last_question, last_exclamation)
            
            if break_point > chunk_size * 0.7:  # Only use break point if it's not too early
                end = start + break_point + 1
        
        chunk = text[start:end].strip()
        
        if chunk:
            chunks.append(chunk)
        
        # Move start position with overlap
        start = end - chunk_overlap if end < text_length else text_length
    
    logger.info(f"Created {len(chunks)} chunks from text of length {text_length}")
    
    return chunks
