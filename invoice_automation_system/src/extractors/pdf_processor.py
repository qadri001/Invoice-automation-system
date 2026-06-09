"""PDF processing utilities for invoice extraction."""
import os
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class PDFProcessor:
    """Handles PDF to image conversion and text extraction."""

    def __init__(self, dpi: int = 300):
        self.dpi = dpi
        self.temp_dir = "temp_images"
        os.makedirs(self.temp_dir, exist_ok=True)

    def pdf_to_images(self, pdf_path: str) -> List[str]:
        """Convert PDF pages to images."""
        try:
            from pdf2image import convert_from_path

            logger.info(f"Converting PDF: {pdf_path}")
            images = convert_from_path(pdf_path, dpi=self.dpi)

            image_paths = []
            base_name = Path(pdf_path).stem

            for i, image in enumerate(images):
                image_path = os.path.join(self.temp_dir, f"{base_name}_page_{i+1}.png")
                image.save(image_path, 'PNG')
                image_paths.append(image_path)

            logger.info(f"Converted {len(images)} pages")
            return image_paths

        except Exception as e:
            logger.error(f"PDF conversion failed: {e}")
            raise

    def extract_text_from_pdf(self, pdf_path: str) -> Optional[str]:
        """Try to extract text directly from PDF without OCR."""
        try:
            import fitz  # PyMuPDF

            text = ""
            with fitz.open(pdf_path) as doc:
                for page in doc:
                    text += page.get_text()

            # If we got substantial text, return it
            if len(text.strip()) > 100:
                return text
            return None

        except Exception as e:
            logger.warning(f"Direct PDF text extraction failed: {e}")
            return None

    def is_pdf(self, file_path: str) -> bool:
        """Check if file is a PDF."""
        return file_path.lower().endswith('.pdf')

    def cleanup(self, image_paths: List[str]):
        """Clean up temporary image files."""
        for path in image_paths:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception as e:
                logger.warning(f"Failed to remove temp file {path}: {e}")
