"""
OCR and PDF processing utilities.
Handles text extraction and OCR with memory management.
"""

import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
import logging
import gc
import shutil
from typing import Dict, List, Any, Optional, Tuple
from app.core.config import settings

logger = logging.getLogger(__name__)

# Configure pytesseract
pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
logger.info(f'Tesseract configured at: {settings.TESSERACT_CMD}')


class PDFProcessor:
    """PDF processing with text extraction and OCR."""
    
    # Thresholds for OCR decision
    MIN_TEXT_LENGTH = 50  # Minimum characters to consider as "has text"
    
    def __init__(self, pdf_path: str):
        """
        Initialize PDF processor.
        
        Args:
            pdf_path: Path to PDF file
        """
        self.pdf_path = pdf_path
        self.document = None
        self.total_pages = 0
    
    def __enter__(self):
        """Context manager entry."""
        try:
            self.document = fitz.open(self.pdf_path)
            self.total_pages = len(self.document)
            logger.info(f"PDF opened: {self.pdf_path} ({self.total_pages} pages)")
            return self
        except Exception as e:
            logger.error(f"Failed to open PDF: {e}")
            raise
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup."""
        if self.document:
            self.document.close()
            logger.info("PDF closed and resources freed")
        # Force garbage collection to prevent memory leak
        gc.collect()
    
    def extract_text_from_page(self, page_num: int) -> str:
        """
        Extract text from PDF page using PyMuPDF.
        
        Args:
            page_num: Page number (0-indexed)
            
        Returns:
            Extracted text
        """
        try:
            page = self.document[page_num]
            text = page.get_text()
            return text.strip()
        except Exception as e:
            logger.error(f"Text extraction failed for page {page_num}: {e}")
            return ""
    
    def ocr_page(self, page_num: int) -> str:
        """
        Perform OCR on PDF page using Tesseract.
        
        Args:
            page_num: Page number (0-indexed)
            
        Returns:
            OCR'd text
        """
        try:
            page = self.document[page_num]
            
            # Render page to image (300 DPI for better OCR)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            img_data = pix.tobytes("ppm")
            
            # Convert to PIL Image
            img = Image.open(io.BytesIO(img_data))
            
            # Run Tesseract OCR
            text = pytesseract.image_to_string(
                img,
                lang=settings.OCR_LANGUAGE,
                config="--psm 1"  # Automatic page segmentation
            )
            
            # Free image memory
            del img
            del pix
            gc.collect()
            
            return text.strip()
        except Exception as e:
            logger.error(f"OCR failed for page {page_num}: {e}")
            return ""
    
    def process_page(self, page_num: int) -> Dict[str, Any]:
        """
        Process single page: extract text or OCR if needed.
        Smart decision: if text exists, skip OCR.
        
        Args:
            page_num: Page number (0-indexed)
            
        Returns:
            Dictionary with page data
        """
        page_data = {
            "page_number": page_num + 1,
            "text": "",
            "method": "none",  # "direct" or "ocr"
            "confidence": 0.0,
        }
        
        # Step 1: Try direct text extraction
        text = self.extract_text_from_page(page_num)
        
        if len(text) >= self.MIN_TEXT_LENGTH:
            # Page has sufficient text, no OCR needed
            page_data["text"] = text
            page_data["method"] = "direct"
            page_data["confidence"] = 1.0
            logger.debug(f"Page {page_num + 1}: Direct extraction ({len(text)} chars)")
        else:
            # Page is scanned/image-based, need OCR
            logger.debug(f"Page {page_num + 1}: Triggering OCR (only {len(text)} chars found)")
            ocr_text = self.ocr_page(page_num)
            page_data["text"] = ocr_text
            page_data["method"] = "ocr"
            page_data["confidence"] = 0.8  # OCR confidence (simplified)
        
        return page_data
    
    def process_all_pages(
        self,
        progress_callback=None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Process all pages in PDF.
        
        Args:
            progress_callback: Optional callback for progress updates
                              Receives (current_page, total_pages)
            
        Returns:
            Tuple of (pages_data, total_pages)
        """
        pages_data = []
        
        try:
            for page_num in range(self.total_pages):
                page_data = self.process_page(page_num)
                pages_data.append(page_data)
                
                # Call progress callback if provided
                if progress_callback:
                    progress_callback(page_num + 1, self.total_pages)
                
                # Periodic garbage collection to prevent memory leak
                if (page_num + 1) % 10 == 0:
                    gc.collect()
                    logger.debug(f"Garbage collection triggered after page {page_num + 1}")
            
            logger.info(f"PDF processing completed: {self.total_pages} pages")
            return pages_data, self.total_pages
        
        except Exception as e:
            logger.error(f"PDF processing failed: {e}")
            raise
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Extract PDF metadata.
        
        Returns:
            Dictionary with metadata
        """
        try:
            metadata = self.document.metadata
            return {
                "title": metadata.get("title", "Unknown"),
                "author": metadata.get("author", "Unknown"),
                "subject": metadata.get("subject", ""),
                "creator": metadata.get("creator", ""),
                "pages": self.total_pages,
            }
        except Exception as e:
            logger.error(f"Metadata extraction failed: {e}")
            return {"pages": self.total_pages}


def process_pdf_file(
    pdf_path: str,
    progress_callback=None
) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Main function to process PDF file.
    
    Args:
        pdf_path: Path to PDF file
        progress_callback: Optional callback for progress updates
        
    Returns:
        Tuple of (result_dict, error_message)
        result_dict contains: metadata, pages, summary
        error_message is None if successful
    """
    try:
        with PDFProcessor(pdf_path) as processor:
            # Get metadata
            metadata = processor.get_metadata()
            
            # Process all pages
            pages_data, total_pages = processor.process_all_pages(progress_callback)
            
            # Calculate statistics
            ocr_pages = sum(1 for p in pages_data if p["method"] == "ocr")
            direct_pages = sum(1 for p in pages_data if p["method"] == "direct")
            
            result = {
                "metadata": metadata,
                "pages": pages_data,
                "summary": {
                    "total_pages": total_pages,
                    "direct_extraction_pages": direct_pages,
                    "ocr_pages": ocr_pages,
                    "processing_method": "hybrid",
                }
            }
            
            logger.info(f"PDF processing successful: {direct_pages} direct, {ocr_pages} OCR")
            return result, None
    
    except Exception as e:
        error_msg = f"PDF processing failed: {str(e)}"
        logger.error(error_msg)
        return {}, error_msg
