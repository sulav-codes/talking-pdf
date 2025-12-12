"""Utility functions for text extraction and processing"""
import re
import logging
from typing import List
from pathlib import Path

from PyPDF2 import PdfReader

logger = logging.getLogger(__name__)


def extract_text(file_path: str) -> str:
    """
    Extract text from a PDF file
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Extracted text from all pages
    """
    try:
        if not Path(file_path).exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        reader = PdfReader(file_path)
        
        if len(reader.pages) == 0:
            raise ValueError("PDF has no pages")
        
        logger.info(f"Extracting text from {len(reader.pages)} pages")
        
        text_parts = []
        for page_num, page in enumerate(reader.pages, 1):
            try:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            except Exception as e:
                logger.warning(f"Failed to extract text from page {page_num}: {e}")
                continue
        
        text = "\n".join(text_parts)
        
        # Clean up the text
        text = clean_text(text)
        
        logger.info(f"Extracted {len(text)} characters from PDF")
        
        return text
        
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
