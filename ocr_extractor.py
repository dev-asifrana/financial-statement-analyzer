import logging
import pdf2image
import easyocr
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from typing import List, Dict, Any, Optional
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OCRExtractor:
    def __init__(self, poppler_path: Optional[str], ocr_reader):
        self.poppler_path = poppler_path
        self.ocr_reader = ocr_reader
        
        self.date_patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            r'\d{4}[/-]\d{1,2}[/-]\d{1,2}',
            r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}',
        ]
        
        self.amount_patterns = [
            r'\$\d{1,3}(?:,\d{3})*\.\d{2}',
            r'\$\d+\.\d{2}',
            r'\(\$\d+\.\d{2}\)',
        ]
    
    def extract_transactions(self, pdf_path: str) -> List[Dict[str, Any]]:
        logger.info(f"🔍 OCR extraction: {pdf_path}")
        
        if not self.poppler_path:
            logger.error("❌ Poppler not available for OCR")
            return []
        
        all_transactions = []
        
        try:
            # Convert PDF to images
            images = pdf2image.convert_from_path(
                pdf_path,
                dpi=300,
                poppler_path=self.poppler_path,
                fmt='RGB'
            )
            
            for page_num, image in enumerate(images, 1):
                page_transactions = self.extract_transactions_from_image(image, page_num)
                all_transactions.extend(page_transactions)
            
            logger.info(f"✅ OCR found {len(all_transactions)} transactions")
            return all_transactions
            
        except Exception as e:
            logger.error(f"❌ OCR failed: {e}")
            return []
    
    def extract_transactions_from_image(self, image: Image.Image, page_num: int) -> List[Dict[str, Any]]:
        if not self.ocr_reader:
            return []
        
        try:
            # Preprocess image for better OCR
            processed_image = self._preprocess_image(image)
            
            # Extract text with OCR
            image_np = np.array(processed_image)
            ocr_results = self.ocr_reader.readtext(image_np)
            
            # Process OCR results
            transactions = []
            for (bbox, text, confidence) in ocr_results:
                if confidence > 0.7 and len(text.strip()) > 3:
                    # Check if text looks like a transaction
                    if self._is_transaction_text(text):
                        transaction = self._parse_ocr_text(text, page_num, confidence)
                        if transaction:
                            transactions.append(transaction)
            
            return transactions
            
        except Exception as e:
            logger.error(f"❌ OCR processing failed: {e}")
            return []
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """Preprocess image for better OCR accuracy"""
        try:
            # Convert to grayscale
            if image.mode != 'L':
                image = image.convert('L')
            
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.5)
            
            # Enhance sharpness
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.2)
            
            # Apply slight blur to reduce noise
            image = image.filter(ImageFilter.MedianFilter(size=3))
            
            return image
            
        except Exception as e:
            logger.warning(f"⚠️ Image preprocessing failed: {e}")
            return image
    
    def _is_transaction_text(self, text: str) -> bool:
        """Check if OCR text looks like transaction data"""
        has_date = any(re.search(pattern, text, re.IGNORECASE) for pattern in self.date_patterns)
        has_amount = any(re.search(pattern, text) for pattern in self.amount_patterns)
        
        return has_date or has_amount
    
    def _parse_ocr_text(self, text: str, page_num: int, ocr_confidence: float) -> Dict[str, Any]:
        """Parse OCR text into transaction data"""
        date = self._extract_date(text)
        amount = self._extract_amount(text)
        
        # Need at least date or amount
        if not date and amount is None:
            return None
        
        # Generate missing data
        if not date:
            date = "Unknown"
        if amount is None:
            amount = 0.0
        
        description = self._extract_description(text, date, amount)
        
        return {
            'date': date,
            'description': description,
            'amount': amount,
            'page': page_num,
            'confidence': ocr_confidence * 0.8,  # Lower confidence for OCR
            'extraction_method': 'ocr'
        }
    
    def _extract_date(self, text: str) -> str:
        for pattern in self.date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group()
        return None
    
    def _extract_amount(self, text: str) -> float:
        for pattern in self.amount_patterns:
            match = re.search(pattern, text)
            if match:
                amount_str = match.group()
                amount_str = amount_str.replace('$', '').replace(',', '').replace('(', '').replace(')', '')
                try:
                    amount = float(amount_str)
                    if '(' in match.group():
                        amount = -amount
                    return amount
                except ValueError:
                    continue
        return None
    
    def _extract_description(self, text: str, date: str, amount: float) -> str:
        description = text
        
        if date and date != "Unknown":
            description = description.replace(date, '')
        
        for pattern in self.amount_patterns:
            description = re.sub(pattern, '', description)
        
        description = ' '.join(description.split()).strip()
        
        if len(description) < 5:
            description = "OCR Transaction"
        
        return description 