import logging
import pdfplumber
import pandas as pd
import re
import os
from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TextBasedExtractor:
    """
    Intelligent text-based transaction extractor using table detection
    and pattern recognition for text-based PDFs
    """
    
    def __init__(self):
        self.date_patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            r'\d{4}[/-]\d{1,2}[/-]\d{1,2}',
            r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s*\d{1,2},?\s*\d{4}',
            r'\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)',
            r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.\d{1,2},\d{4}',  # BMO format: Dec.5,2021
            r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.\d{1,2}\b',  # BMO transaction format: Nov.9
        ]
        
        self.amount_patterns = [
            r'\$\d{1,3}(?:,\d{3})*\.\d{2}',
            r'\$\d+\.\d{2}',
            r'\(\$\d+\.\d{2}\)',
            r'\+\$?\d{1,3}(?:,\d{3})*\.\d{2}',  # Positive amounts with +
            r'-\$?\d{1,3}(?:,\d{3})*\.\d{2}',  # Negative amounts with -
            r'\b\d{1,3}(?:,\d{3})*\.\d{2}\b',  # Plain decimal amounts (BMO format)
            r'\b\d+\.\d{2}\b',  # Simple decimal amounts
        ]
        
        # Keywords that indicate non-transaction content
        self.exclusion_keywords = [
            'opening balance', 'closing balance', 'total', 'subtotal',
            'previous statement', 'terms and conditions', 'privacy policy',
            'prior to april', 'member of', 'deposit insurance'
        ]
    
    def extract_transactions(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extract transactions from text-based PDF
        """
        logger.info(f"📄 Text extraction: {pdf_path}")
        
        all_transactions = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if text:
                        page_transactions = self.extract_transactions_from_text(text, page_num)
                        all_transactions.extend(page_transactions)
            
            logger.info(f"✅ Found {len(all_transactions)} transactions")
            return all_transactions
            
        except Exception as e:
            logger.error(f"❌ Failed: {e}")
            return []
    
    def extract_transactions_from_text(self, text: str, page_num: int) -> List[Dict[str, Any]]:
        """
        Extract transactions from page text using intelligent pattern detection
        """
        transactions = []
        
        # Preprocess text to handle concatenated formats like BMO
        cleaned_text = self._preprocess_text(text)
        
        # Step 1: Detect tabular structures
        table_regions = self._detect_table_regions(cleaned_text)
        
        # Step 2: Score and filter transaction tables
        transaction_tables = self._identify_transaction_tables(table_regions)
        
        # Step 3: Extract transactions from identified tables
        for table in transaction_tables:
            table_transactions = self._extract_from_table_region(table, page_num)
            transactions.extend(table_transactions)
        
        # Step 4: Fallback - look for transaction patterns in remaining text
        if not transactions:
            fallback_transactions = self._extract_transaction_patterns(cleaned_text, page_num)
            transactions.extend(fallback_transactions)
        
        return transactions
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text to handle concatenated formats and improve parsing"""
        # Add spaces around common patterns to separate concatenated text
        
        # Add space before dates
        text = re.sub(r'([a-zA-Z])(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', r'\1 \2', text)
        text = re.sub(r'([a-zA-Z])(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', r'\1 \2', text, flags=re.IGNORECASE)
        
        # Add space before dollar amounts
        text = re.sub(r'([a-zA-Z])(\$\d)', r'\1 \2', text)
        text = re.sub(r'([a-zA-Z])(\+\$?\d)', r'\1 \2', text)
        text = re.sub(r'([a-zA-Z])(-\$?\d)', r'\1 \2', text)
        
        # Add space after commas in dates
        text = re.sub(r'(\d),(\d{4})', r'\1, \2', text)
        
        # Add space around transaction keywords
        keywords = ['PreviousBalance', 'NewBalance', 'PaymentDue', 'CreditLimit', 'MinimumPayment']
        for keyword in keywords:
            text = re.sub(f'([a-zA-Z]){keyword}', f'\\1 {keyword}', text, flags=re.IGNORECASE)
            text = re.sub(f'{keyword}([a-zA-Z])', f'{keyword} \\1', text, flags=re.IGNORECASE)
        
        return text
    
    def _detect_table_regions(self, text: str) -> List[Dict[str, Any]]:
        """
        Detect potential table regions in text
        """
        lines = text.split('\n')
        table_regions = []
        current_region = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                if current_region:
                    # End of potential table region
                    table_regions.append({
                        'lines': current_region,
                        'start_line': i - len(current_region),
                        'end_line': i,
                        'text': '\n'.join(current_region)
                    })
                    current_region = []
                continue
            
            # Check if line looks like table data
            if self._is_table_like_line(line):
                current_region.append(line)
            else:
                if current_region and len(current_region) >= 2:
                    # Save accumulated region
                    table_regions.append({
                        'lines': current_region,
                        'start_line': i - len(current_region),
                        'end_line': i,
                        'text': '\n'.join(current_region)
                    })
                current_region = []
        
        # Handle last region
        if current_region and len(current_region) >= 2:
            table_regions.append({
                'lines': current_region,
                'start_line': len(lines) - len(current_region),
                'end_line': len(lines),
                'text': '\n'.join(current_region)
            })
        
        return table_regions
    
    def _is_table_like_line(self, line: str) -> bool:
        """
        Check if a line looks like it could be part of a table
        """
        # Must have both date and amount patterns
        has_date = any(re.search(pattern, line, re.IGNORECASE) for pattern in self.date_patterns)
        has_amount = any(re.search(pattern, line) for pattern in self.amount_patterns)
        
        # Or have multiple numeric/structured elements
        numeric_elements = len(re.findall(r'\d+', line))
        
        return (has_date and has_amount) or numeric_elements >= 3
    
    def _identify_transaction_tables(self, table_regions: List[Dict]) -> List[Dict]:
        """
        Score and identify which table regions contain transactions
        """
        transaction_tables = []
        
        for region in table_regions:
            score = self._score_transaction_table(region)
            if score >= 5:  # Threshold for transaction tables
                region['transaction_score'] = score
                transaction_tables.append(region)
        
        # Sort by score (highest first)
        return sorted(transaction_tables, key=lambda x: x['transaction_score'], reverse=True)
    
    def _score_transaction_table(self, region: Dict) -> int:
        """
        Score a table region for likelihood of containing transactions
        """
        score = 0
        text = region['text'].lower()
        lines = region['lines']
        
        # Check for transaction indicators
        transaction_keywords = ['date', 'transaction', 'description', 'amount', 'debit', 'credit']
        for keyword in transaction_keywords:
            if keyword in text:
                score += 2
        
        # Check for date patterns
        date_count = sum(1 for line in lines if any(re.search(p, line, re.IGNORECASE) for p in self.date_patterns))
        score += min(date_count, 5)  # Max 5 points for dates
        
        # Check for amount patterns
        amount_count = sum(1 for line in lines if any(re.search(p, line) for p in self.amount_patterns))
        score += min(amount_count, 5)  # Max 5 points for amounts
        
        # Penalty for exclusion keywords
        for keyword in self.exclusion_keywords:
            if keyword in text:
                score -= 3
        
        # Bonus for consistent structure
        if len(lines) >= 3:
            score += 2
        
        return max(0, score)
    
    def _extract_from_table_region(self, table_region: Dict, page_num: int) -> List[Dict[str, Any]]:
        """
        Extract individual transactions from a table region
        """
        transactions = []
        lines = table_region['lines']
        
        for line in lines:
            # Skip header-like lines
            if self._is_header_line(line):
                continue
            
            # Skip summary lines
            if self._is_summary_line(line):
                continue
            
            # Try to extract transaction from line
            transaction = self._parse_transaction_line(line, page_num)
            if transaction:
                transactions.append(transaction)
        
        return transactions
    
    def _is_header_line(self, line: str) -> bool:
        """Check if line is a table header"""
        line_lower = line.lower()
        header_indicators = ['date', 'transaction', 'description', 'amount', 'debit', 'credit', 'balance']
        
        # If line contains multiple header keywords but no actual data
        header_count = sum(1 for keyword in header_indicators if keyword in line_lower)
        has_date = any(re.search(pattern, line, re.IGNORECASE) for pattern in self.date_patterns)
        has_amount = any(re.search(pattern, line) for pattern in self.amount_patterns)
        
        return header_count >= 2 and not (has_date and has_amount)
    
    def _is_summary_line(self, line: str) -> bool:
        """Check if line is a summary/total line"""
        line_lower = line.lower()
        summary_keywords = ['total', 'subtotal', 'balance', 'opening', 'closing', 'previous', 'carried forward']
        
        return any(keyword in line_lower for keyword in summary_keywords)
    
    def _parse_transaction_line(self, line: str, page_num: int) -> Dict[str, Any]:
        """
        Parse a single transaction line
        """
        # Extract date
        date = self._extract_date(line)
        if not date:
            return None
        
        # Extract amount
        amount = self._extract_amount(line)
        if amount is None:
            return None
        
        # Extract description (everything else)
        description = self._extract_description(line, date, amount)
        
        return {
            'date': date,
            'description': description,
            'amount': amount,
            'page': page_num,
            'confidence': 0.85,  # High confidence for text-based extraction
            'extraction_method': 'text_pattern'
        }
    
    def _extract_date(self, line: str) -> str:
        """Extract date from line"""
        for pattern in self.date_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                return match.group()
        return None
    
    def _extract_amount(self, line: str) -> float:
        """Extract amount from line"""
        for pattern in self.amount_patterns:
            match = re.search(pattern, line)
            if match:
                amount_str = match.group()
                # Check for negative indicators
                is_negative = '(' in amount_str or amount_str.startswith('-')
                is_positive = amount_str.startswith('+')
                
                # Clean and convert to float
                amount_str = re.sub(r'[^\d.]', '', amount_str)
                try:
                    amount = float(amount_str)
                    # Handle negative amounts
                    if is_negative:
                        amount = -amount
                    return amount
                except ValueError:
                    continue
        return None
    
    def _extract_description(self, line: str, date: str, amount: float) -> str:
        """Extract description by removing date and amount"""
        description = line
        
        # Remove date
        if date:
            description = description.replace(date, '')
        
        # Remove amount patterns
        for pattern in self.amount_patterns:
            description = re.sub(pattern, '', description)
        
        # Clean up
        description = ' '.join(description.split()).strip()
        
        # If description is too short, generate a meaningful one
        if len(description) < 5:
            description = "Transaction"
        
        return description
    
    def _extract_transaction_patterns(self, text: str, page_num: int) -> List[Dict[str, Any]]:
        """
        Fallback method to extract transactions using pattern matching
        """
        transactions = []
        lines = text.split('\n')
        
        # First pass: Look for lines with both date and amount (single-line transactions)
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip obvious non-transaction lines
            if any(keyword in line.lower() for keyword in self.exclusion_keywords):
                continue
            
            # Look for lines with both date and amount
            has_date = any(re.search(pattern, line, re.IGNORECASE) for pattern in self.date_patterns)
            has_amount = any(re.search(pattern, line) for pattern in self.amount_patterns)
            
            if has_date and has_amount:
                transaction = self._parse_transaction_line(line, page_num)
                if transaction:
                    transaction['confidence'] = 0.7  # Lower confidence for fallback
                    transactions.append(transaction)
        
        # Second pass: Look for multi-line transactions (Tangerine format)
        if len(transactions) < 5:  # Only if we didn't find many transactions
            transactions.extend(self._extract_multiline_transactions(lines, page_num))
        
        return transactions
    
    def _extract_multiline_transactions(self, lines: List[str], page_num: int) -> List[Dict[str, Any]]:
        """
        Extract transactions that span multiple lines (like Tangerine format)
        """
        transactions = []
        used_lines = set()  # Track which lines we've already processed
        
        for i, line in enumerate(lines):
            if i in used_lines:
                continue
                
            line = line.strip()
            if not line:
                continue
            
            # Skip header lines and non-transaction content
            if any(keyword in line.lower() for keyword in ['transaction date', 'account balance', 'interest rate', 'opening balance']):
                continue
            
            # Look for date patterns
            date_match = None
            for pattern in self.date_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    date_match = match.group()
                    break
            
            if date_match:
                # Found a date, now look for amount in current line or next few lines
                description_parts = []
                amount = None
                
                # First check if amount is on the same line
                current_amount = self._extract_amount(line)
                if current_amount is not None:
                    amount = current_amount
                    # Extract description (remove date and amount)
                    current_desc = line
                    current_desc = current_desc.replace(date_match, '').strip()
                    for pattern in self.amount_patterns:
                        current_desc = re.sub(pattern, '', current_desc)
                    current_desc = current_desc.strip()
                    if current_desc:
                        description_parts.append(current_desc)
                    used_lines.add(i)
                else:
                    # Extract description from current line (remove date)
                    current_desc = line.replace(date_match, '').strip()
                    if current_desc:
                        description_parts.append(current_desc)
                    used_lines.add(i)
                    
                    # Look in next 2 lines for amount and more description
                    for j in range(1, 3):
                        if i + j < len(lines):
                            next_line = lines[i + j].strip()
                            if not next_line:
                                break
                            
                            # Check if this line has an amount
                            line_amount = self._extract_amount(next_line)
                            if line_amount is not None and amount is None:
                                amount = line_amount
                                used_lines.add(i + j)
                                
                                # Add any remaining text as description
                                remaining_text = next_line
                                for pattern in self.amount_patterns:
                                    remaining_text = re.sub(pattern, '', remaining_text)
                                remaining_text = remaining_text.strip()
                                if remaining_text and len(remaining_text) > 2:
                                    description_parts.append(remaining_text)
                                break
                            else:
                                # Add as description if it's substantial and not a header
                                if (len(next_line) > 5 and 
                                    not any(keyword in next_line.lower() for keyword in self.exclusion_keywords) and
                                    not any(keyword in next_line.lower() for keyword in ['transaction date', 'balance', 'account'])):
                                    description_parts.append(next_line)
                                    used_lines.add(i + j)
                
                # Create transaction if we found both date and amount
                if amount is not None and amount > 0:  # Only positive amounts for now
                    description = ' '.join(description_parts).strip()
                    if not description or len(description) < 3:
                        description = "Transaction"
                    
                    # Clean up description
                    description = re.sub(r'\s+', ' ', description)  # Normalize whitespace
                    description = description[:100]  # Limit length
                    
                    transaction = {
                        'date': date_match,
                        'description': description,
                        'amount': amount,
                        'page': page_num,
                        'confidence': 0.6,  # Lower confidence for multi-line
                        'extraction_method': 'multiline_pattern'
                    }
                    transactions.append(transaction)
        
        return transactions


# Test the extractor
if __name__ == "__main__":
    extractor = TextBasedExtractor()
    
    # Test with a sample PDF
    test_pdf = "statements/BMO Credit Card.pdf"
    if os.path.exists(test_pdf):
        transactions = extractor.extract_transactions(test_pdf)
        print(f"\n🎯 Text Extraction Results: {len(transactions)} transactions\n")
        
        for i, transaction in enumerate(transactions[:5], 1):
            print(f"{i}. {transaction['date']} - {transaction['description']} - ${transaction['amount']}")
    else:
        print("❌ Test PDF not found") 