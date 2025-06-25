import logging
import pdfplumber
import pdf2image
import easyocr
import numpy as np
from PIL import Image
from typing import List, Dict, Any, Optional
import pandas as pd
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self):
        self.poppler_path = self._setup_poppler()
        self.ocr_reader = None
        self._init_ocr()
        
    def _setup_poppler(self) -> Optional[str]:
        poppler_path = os.path.join(os.getcwd(), "poppler", "poppler-23.07.0", "Library", "bin")
        if os.path.exists(poppler_path):
            logger.info(f"✅ Poppler ready: {poppler_path}")
            return poppler_path
        else:
            logger.warning("⚠️ Poppler not found")
            return None
    
    def _init_ocr(self):
        try:
            self.ocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
            logger.info("✅ EasyOCR initialized")
        except Exception as e:
            logger.warning(f"⚠️ EasyOCR failed: {e}")
    
    def process_document(self, pdf_path: str) -> Dict[str, Any]:
        logger.info(f"🔍 Processing: {os.path.basename(pdf_path)}")
        
        doc_type = self._detect_document_type(pdf_path)
        logger.info(f"📋 Type: {doc_type}")
        
        if doc_type == "text_based":
            return self._process_text_based_pdf(pdf_path)
        elif doc_type == "scanned_image":
            return self._process_scanned_pdf(pdf_path)
        else:
            return self._process_mixed_pdf(pdf_path)
    
    def _detect_document_type(self, pdf_path: str) -> str:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                total_text = 0
                sample_pages = min(3, len(pdf.pages))
                
                for page in pdf.pages[:sample_pages]:
                    text = page.extract_text()
                    if text:
                        total_text += len(text.strip())
                
                avg_text = total_text / sample_pages if sample_pages > 0 else 0
                logger.info(f"📊 Text: {avg_text:.0f} chars/page")
                
                if avg_text > 500:
                    return "text_based"
                elif avg_text < 100:
                    return "scanned_image"
                else:
                    return "mixed"
                    
        except Exception as e:
            logger.error(f"❌ Detection failed: {e}")
            return "mixed"
    
    def _process_text_based_pdf(self, pdf_path: str) -> Dict[str, Any]:
        logger.info("⚡ Text-based processing...")
        
        from text_extractor import TextBasedExtractor
        extractor = TextBasedExtractor()
        
        return {
            'processing_method': 'text_extraction',
            'transactions': extractor.extract_transactions(pdf_path),
            'confidence': 'high',
            'processing_time': 'fast'
        }
    
    def _process_scanned_pdf(self, pdf_path: str) -> Dict[str, Any]:
        logger.info("🔍 OCR processing...")
        
        from ocr_extractor import OCRExtractor
        extractor = OCRExtractor(self.poppler_path, self.ocr_reader)
        
        return {
            'processing_method': 'ocr_extraction',
            'transactions': extractor.extract_transactions(pdf_path),
            'confidence': 'medium',
            'processing_time': 'slow'
        }
    
    def _process_mixed_pdf(self, pdf_path: str) -> Dict[str, Any]:
        logger.info("🔄 Hybrid processing...")
        
        all_transactions = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if text and len(text.strip()) > 200:
                        from text_extractor import TextBasedExtractor
                        extractor = TextBasedExtractor()
                        page_transactions = extractor.extract_transactions_from_text(text, page_num)
                    else:
                        if self.poppler_path:
                            images = pdf2image.convert_from_path(
                                pdf_path, 
                                first_page=page_num, 
                                last_page=page_num,
                                dpi=300,
                                poppler_path=self.poppler_path
                            )
                            if images:
                                from ocr_extractor import OCRExtractor
                                extractor = OCRExtractor(self.poppler_path, self.ocr_reader)
                                page_transactions = extractor.extract_transactions_from_image(images[0], page_num)
                            else:
                                page_transactions = []
                        else:
                            page_transactions = []
                    
                    all_transactions.extend(page_transactions)
        
        except Exception as e:
            logger.error(f"❌ Hybrid failed: {e}")
            return {
                'processing_method': 'hybrid_failed',
                'transactions': [],
                'confidence': 'low',
                'error': str(e)
            }
        
        return {
            'processing_method': 'hybrid_extraction',
            'transactions': all_transactions,
            'confidence': 'medium',
            'processing_time': 'medium'
        }
    
    def process_multiple_pdfs(self, pdf_paths: List[str]) -> pd.DataFrame:
        all_transactions = []
        
        for pdf_path in pdf_paths:
            try:
                result = self.process_document(pdf_path)
                transactions = result.get('transactions', [])
                
                for transaction in transactions:
                    transaction['source_file'] = os.path.basename(pdf_path)
                    transaction['processing_method'] = result.get('processing_method', 'unknown')
                    transaction['confidence_level'] = result.get('confidence', 'unknown')
                
                all_transactions.extend(transactions)
                
            except Exception as e:
                logger.error(f"❌ Failed: {pdf_path}: {e}")
                continue
        
        if not all_transactions:
            return pd.DataFrame()
        
        df = pd.DataFrame(all_transactions)
        
        required_columns = ['date', 'description', 'amount', 'source_file', 'processing_method']
        for col in required_columns:
            if col not in df.columns:
                if col in ['date', 'description', 'source_file', 'processing_method']:
                    df[col] = 'N/A'
                else:
                    df[col] = 0.0
        
        logger.info(f"✅ Processed {len(pdf_paths)} files, found {len(df)} transactions")
        return df


# Test the processor
if __name__ == "__main__":
    processor = DocumentProcessor()
    
    # Test with a sample PDF
    test_pdf = "statements/BMO Credit Card.pdf"
    if os.path.exists(test_pdf):
        result = processor.process_document(test_pdf)
        print(f"\n🎯 Processing Result:")
        print(f"Method: {result['processing_method']}")
        print(f"Transactions: {len(result['transactions'])}")
        print(f"Confidence: {result['confidence']}")
    else:
        print("❌ Test PDF not found") 