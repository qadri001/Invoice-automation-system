"""OCR Engine wrapper supporting multiple backends."""
import os
import cv2
import numpy as np
from PIL import Image
from typing import List, Tuple, Dict, Any, Optional
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class BaseOCREngine(ABC):
    """Abstract base class for OCR engines."""

    @abstractmethod
    def extract_text(self, image_path: str) -> List[Dict[str, Any]]:
        """Extract text from image. Returns list of dicts with 'text', 'confidence', 'bbox'."""
        pass

    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Preprocess image for better OCR results."""
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Denoise
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)

        # Adaptive thresholding
        binary = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )

        return binary


class TesseractOCR(BaseOCREngine):
    """Tesseract OCR implementation."""

    def __init__(self, language: str = 'eng'):
        try:
            import pytesseract
            self.pytesseract = pytesseract
            self.language = language
        except ImportError:
            raise ImportError("pytesseract not installed. Run: pip install pytesseract")

    def extract_text(self, image_path: str) -> List[Dict[str, Any]]:
        """Extract text using Tesseract with bounding box data."""
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image: {image_path}")

        processed = self.preprocess_image(image)

        # Get detailed data including bounding boxes
        data = self.pytesseract.image_to_data(
            processed, 
            lang=self.language,
            output_type=self.pytesseract.Output.DICT
        )

        results = []
        n_boxes = len(data['text'])

        for i in range(n_boxes):
            if int(data['conf'][i]) > 0:  # Filter low confidence
                text = data['text'][i].strip()
                if text:
                    results.append({
                        'text': text,
                        'confidence': data['conf'][i] / 100.0,
                        'bbox': (
                            data['left'][i],
                            data['top'][i],
                            data['width'][i],
                            data['height'][i]
                        )
                    })

        return results


class PaddleOCREngine(BaseOCREngine):
    """PaddleOCR implementation - optimized for invoices."""

    def __init__(self, language: str = 'en', use_gpu: bool = False):
        try:
            from paddleocr import PaddleOCR
            self.ocr = PaddleOCR(
                use_angle_cls=True,
                lang=language,
                use_gpu=use_gpu,
                show_log=False
            )
            logger.info("PaddleOCR initialized successfully")
        except ImportError:
            raise ImportError("paddleocr not installed. Run: pip install paddleocr")

    def extract_text(self, image_path: str) -> List[Dict[str, Any]]:
        """Extract text using PaddleOCR."""
        result = self.ocr.ocr(image_path, cls=True)

        results = []
        if result and result[0]:
            for line in result[0]:
                if line:
                    bbox, (text, confidence) = line
                    results.append({
                        'text': text,
                        'confidence': confidence,
                        'bbox': [
                            int(bbox[0][0]), int(bbox[0][1]),
                            int(bbox[2][0] - bbox[0][0]),
                            int(bbox[2][1] - bbox[0][1])
                        ]
                    })

        return results


class HybridOCREngine(BaseOCREngine):
    """Combines multiple OCR engines for best results."""

    def __init__(self, primary: str = 'paddle', secondary: str = 'tesseract'):
        self.primary = self._create_engine(primary)
        self.secondary = self._create_engine(secondary)
        self.primary_name = primary
        self.secondary_name = secondary

    def _create_engine(self, engine_type: str) -> BaseOCREngine:
        if engine_type == 'paddle':
            return PaddleOCREngine()
        elif engine_type == 'tesseract':
            return TesseractOCR()
        else:
            raise ValueError(f"Unknown OCR engine: {engine_type}")

    def extract_text(self, image_path: str) -> List[Dict[str, Any]]:
        """Extract text using primary engine, fallback to secondary if needed."""
        try:
            results = self.primary.extract_text(image_path)
            avg_confidence = np.mean([r['confidence'] for r in results]) if results else 0

            # If primary confidence is low, try secondary
            if avg_confidence < 0.6:
                logger.info(f"Primary OCR confidence low ({avg_confidence:.2f}), trying secondary")
                secondary_results = self.secondary.extract_text(image_path)
                secondary_conf = np.mean([r['confidence'] for r in secondary_results]) if secondary_results else 0

                if secondary_conf > avg_confidence:
                    logger.info(f"Using secondary OCR (confidence: {secondary_conf:.2f})")
                    return secondary_results

            return results
        except Exception as e:
            logger.error(f"Primary OCR failed: {e}, trying secondary")
            return self.secondary.extract_text(image_path)


def create_ocr_engine(engine_type: str = 'paddle', **kwargs) -> BaseOCREngine:
    """Factory function to create OCR engine."""
    if engine_type == 'paddle':
        return PaddleOCREngine(**kwargs)
    elif engine_type == 'tesseract':
        return TesseractOCR(**kwargs)
    elif engine_type == 'hybrid':
        return HybridOCREngine(**kwargs)
    else:
        raise ValueError(f"Unknown OCR engine type: {engine_type}")
