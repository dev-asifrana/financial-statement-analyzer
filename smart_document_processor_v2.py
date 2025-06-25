# -*- coding: utf-8 -*-
import logging
import pdfplumber
import re
import pandas as pd
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from abc import ABC, abstractmethod

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BankProcessor(ABC):
    """Abstract base class for bank-specific processors"""
    
    def __init__(self, bank_name: str):
        self.bank_name = bank_name
        self.transactions = []
    
    @abstractmethod
    def can_process(self, text: str, filename: str) -> bool:
        """Check if this processor can handle the given document"""
        pass
    
    @abstractmethod
    def extract_transactions(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Extract transactions from the PDF"""
        pass
    
    def clean_amount(self, amount_str: str) -> float:
        """Clean and convert amount string to float"""
        if not amount_str:
            return 0.0
        
        # Handle negative amounts first (before cleaning)
        is_negative = '(' in str(amount_str) or str(amount_str).startswith('-')
        
        # Remove currency symbols and whitespace, keep digits, period, comma, parentheses, dash
        cleaned = re.sub(r'[^\d.,()\-]', '', str(amount_str))
        
        # Remove commas and convert
        try:
            final_cleaned = cleaned.replace(',', '').replace('(', '').replace(')', '')
            
            # If we already have a negative sign in the cleaned string, use it as-is
            if final_cleaned.startswith('-'):
                return float(final_cleaned)
            
            # Otherwise apply the detected negative sign
            amount = float(final_cleaned)
            return -amount if is_negative else amount
        except ValueError:
            logger.warning(f"Could not parse amount: {amount_str}")
            return 0.0
    
    def clean_date(self, date_str: str) -> str:
        """Clean and standardize date string to MM-DD format (no year)"""
        if not date_str:
            return "01-01"
        
        # Convert to MM-DD format (no year needed)
        try:
            from datetime import datetime
            
            # Try various date formats
            formats = [
                '%b %d %Y',     # Sep 28 2024
                '%b.%d %Y',     # Sep.28 2024  
                '%b-%d %Y',     # Sep-28 2024
                '%b %d',        # Sep 28 (no year)
                '%b.%d',        # Sep.28 (no year)
                '%m/%d/%Y',     # 09/28/2024
                '%d/%m/%Y',     # 28/09/2024
                '%m/%d',        # 09/28 (no year)
            ]
            
            for fmt in formats:
                try:
                    date_obj = datetime.strptime(date_str.strip(), fmt)
                    return date_obj.strftime('%m-%d')  # MM-DD format
                except ValueError:
                    continue
            
            # Handle special formats manually if strptime fails
            # BMO: Nov.3 -> 11-03
            month_map = {
                'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
                'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
                'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
            }
            
            # Try pattern: Month.Day or Month Day
            month_day_pattern = r'([A-Za-z]{3})\.?(\d{1,2})'
            match = re.search(month_day_pattern, date_str.lower())
            if match:
                month_str = match.group(1)[:3].lower()
                day_str = match.group(2).zfill(2)
                if month_str in month_map:
                    return f"{month_map[month_str]}-{day_str}"
                    
            # If no format matches, return as-is but truncate to avoid long strings
            return date_str.strip()[:5]
            
        except Exception:
            return date_str.strip()[:5]

class BMOProcessor(BankProcessor):
    """BMO Credit Card processor - handles concatenated text format"""
    
    def __init__(self):
        super().__init__("BMO")
    
    def can_process(self, text: str, filename: str) -> bool:
        indicators = ["BMO", "MasterCard", "CardNumber", "CustomerName"]
        return any(indicator in text for indicator in indicators)
    
    def extract_transactions(self, pdf_path: str) -> List[Dict[str, Any]]:
        logger.info(f"🏦 Processing BMO statement: {pdf_path}")
        transactions = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if not text:
                        continue
                    
                    lines = text.split('\n')
                    
                    for line in lines:
                        line = line.strip()
                        
                        # Look for BMO transaction pattern
                        if self._is_bmo_transaction(line):
                            transaction = self._parse_bmo_transaction(line, page_num)
                            if transaction:
                                transactions.append(transaction)
            
            logger.info(f"✅ BMO: Found {len(transactions)} transactions")
            return transactions
            
        except Exception as e:
            logger.error(f"❌ BMO processing failed: {e}")
            return []
    
    def _is_bmo_transaction(self, line: str) -> bool:
        """Check if line is a BMO transaction"""
        # BMO pattern: Month.Day Month.Day DESCRIPTION ... AMOUNT
        # Must start with month abbreviation followed by day
        pattern = r'^[A-Za-z]{3}\.\d{1,2}\s+[A-Za-z]{3}\.\d{1,2}'
        return bool(re.match(pattern, line))
    
    def _parse_bmo_transaction(self, line: str, page_num: int) -> Optional[Dict[str, Any]]:
        """Parse BMO transaction line"""
        # Improved pattern: Match date patterns and extract amount from end
        # Pattern: Nov.3 Nov.8 DESCRIPTION ... AMOUNT
        
        # First extract the two dates from the beginning
        date_pattern = r'^([A-Za-z]{3}\.\d{1,2})\s+([A-Za-z]{3}\.\d{1,2})\s+(.*)'
        match = re.match(date_pattern, line)
        
        if not match:
            return None
        
        trans_date = self.clean_date(match.group(1))
        post_date = self.clean_date(match.group(2))
        remaining_text = match.group(3).strip()
        
        # Extract amount from the end (last space-separated number with decimal)
        amount_pattern = r'([\d,]+\.\d{2})\s*$'
        amount_match = re.search(amount_pattern, remaining_text)
        
        if not amount_match:
            return None
        
        amount = self.clean_amount(amount_match.group(1))
        
        # Extract description (everything except the amount)
        description_end = amount_match.start()
        description = remaining_text[:description_end].strip()
        
        # Extract reference number (usually the last set of digits before amount)
        ref_pattern = r'(\d{10,})\s*[\d,]+\.\d{2}\s*$'
        ref_match = re.search(ref_pattern, remaining_text)
        reference = ref_match.group(1) if ref_match else ""
        
        # Clean description by removing reference if found
        if reference:
            description = description.replace(reference, '').strip()
        
        # Skip summary lines
        skip_keywords = ['total', 'interest', 'fee', 'balance', 'payment', 'credit limit']
        if any(keyword in description.lower() for keyword in skip_keywords):
            return None
        
        return {
            'date': trans_date,
            'posting_date': post_date,
            'description': description,
            'reference': reference,
            'amount': amount,
            'page': page_num,
            'bank': self.bank_name,
            'confidence': 0.9
        }

class EQBankProcessor(BankProcessor):
    """EQ Bank processor - handles clean transaction format"""
    
    def __init__(self):
        super().__init__("EQ Bank")
    
    def can_process(self, text: str, filename: str) -> bool:
        indicators = ["EQ Bank", "Cash Card", "Equitable Bank"]
        return any(indicator in text for indicator in indicators)
    
    def extract_transactions(self, pdf_path: str) -> List[Dict[str, Any]]:
        logger.info(f"🏦 Processing EQ Bank statement: {pdf_path}")
        transactions = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if not text:
                        continue
                    
                    lines = text.split('\n')
                    for line in lines:
                        line = line.strip()
                        
                        # EQ Bank format: "Sep 28 PRESTO ETIK/HSR****2590, TORON -$5.60"
                        if self._is_eq_transaction(line):
                            transaction = self._parse_eq_transaction(line, page_num)
                            if transaction:
                                transactions.append(transaction)
            
            logger.info(f"✅ EQ Bank: Found {len(transactions)} transactions")
            return transactions
            
        except Exception as e:
            logger.error(f"❌ EQ Bank processing failed: {e}")
            return []
    
    def _is_eq_transaction(self, line: str) -> bool:
        """Check if line is an EQ Bank transaction"""
        # Must have date pattern (Month Day) and amount pattern (-$X.XX or $X.XX)
        date_pattern = r'^[A-Za-z]{3}\s+\d{1,2}'
        amount_pattern = r'-?\$[\d,]+\.?\d{2}'
        
        return bool(re.search(date_pattern, line) and re.search(amount_pattern, line))
    
    def _parse_eq_transaction(self, line: str, page_num: int) -> Optional[Dict[str, Any]]:
        """Parse EQ Bank transaction"""
        # Pattern: "Sep 28 DESCRIPTION -$5.60"
        match = re.match(r'^([A-Za-z]{3}\s+\d{1,2})\s+(.*?)\s+(-?\$[\d,]+\.?\d{2})$', line)
        
        if match:
            from datetime import datetime
            current_year = datetime.now().year
            # For bank statements, use previous year if current month is early in year
            if datetime.now().month <= 3:  # Jan-Mar, assume statements are from previous year
                statement_year = current_year - 1
            else:
                statement_year = current_year
            date_str = match.group(1) + f" {statement_year}"  # Add appropriate year for EQ Bank
            date = self.clean_date(date_str)
            description = match.group(2).strip()
            amount = self.clean_amount(match.group(3))
            
            # Skip header lines
            if 'withdrawals' in description.lower() or 'deposits' in description.lower():
                return None
            
            return {
                'date': date,
                'description': description,
                'amount': amount,
                'page': page_num,
                'bank': self.bank_name,
                'confidence': 0.95
            }
        
        return None

class TDProcessor(BankProcessor):
    """TD Bank processor - handles section-based format"""
    
    def __init__(self):
        super().__init__("TD Bank")
    
    def can_process(self, text: str, filename: str) -> bool:
        indicators = ["STATEMENT OF ACCOUNT", "TD Personal", "Primary Account"]
        return any(indicator in text for indicator in indicators)
    
    def extract_transactions(self, pdf_path: str) -> List[Dict[str, Any]]:
        logger.info(f"🏦 Processing TD Bank statement: {pdf_path}")
        transactions = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if not text:
                        continue
                    
                    lines = text.split('\n')
                    current_section = None
                    
                    for line in lines:
                        line = line.strip()
                        
                        # Identify sections
                        if line.strip() == "Credits":
                            current_section = "credits"
                            continue
                        elif line.strip() == "Debits":
                            current_section = "debits"
                            continue
                        elif "DAILY ACCOUNT ACTIVITY" in line:
                            current_section = "credits"  # Start with credits section
                            continue
                        
                        # Parse transactions based on current section
                        if current_section and self._is_td_transaction(line):
                            transaction = self._parse_td_transaction(line, page_num, current_section)
                            if transaction:
                                transactions.append(transaction)
            
            logger.info(f"✅ TD Bank: Found {len(transactions)} transactions")
            return transactions
            
        except Exception as e:
            logger.error(f"❌ TD Bank processing failed: {e}")
            return []
    
    def _is_td_transaction(self, line: str) -> bool:
        """Check if line is a TD transaction"""
        # TD format: "07/02 CHECK D, 59 CONTRACTORS 3,750.00"
        pattern = r'^\d{2}/\d{2}'
        return bool(re.match(pattern, line))
    
    def _parse_td_transaction(self, line: str, page_num: int, section: str) -> Optional[Dict[str, Any]]:
        """Parse TD transaction line with section-based classification"""
        # Pattern: "07/02 DESCRIPTION AMOUNT"
        match = re.match(r'^(\d{2}/\d{2})\s+(.*?)\s+([\d,]+\.?\d{2})$', line)
        
        if match:
            date = self.clean_date(match.group(1))
            description = match.group(2).strip()
            amount = self.clean_amount(match.group(3))
            
            # Classify based on SECTION, not description keywords
            # TD Bank clearly separates Credits (money IN) and Debits (money OUT)
            if section == "credits":
                transaction_type = "credit"
                is_spending = False
            elif section == "debits":
                transaction_type = "debit"
                is_spending = True
            else:
                # Fallback: assume credit if no section identified
                transaction_type = "credit"
                is_spending = False
            
            return {
                'date': date,
                'description': description,
                'amount': amount,
                'page': page_num,
                'bank': self.bank_name,
                'confidence': 0.9,
                'transaction_type': transaction_type,
                'is_spending': is_spending,
                'abs_amount': abs(amount),
                'processing_method': 'td_bank_processor',
                'confidence_level': 'high'
            }
        
        return None

class TangerineProcessor(BankProcessor):
    """Tangerine processor - handles simple table format"""
    
    def __init__(self):
        super().__init__("Tangerine")
    
    def can_process(self, text: str, filename: str) -> bool:
        indicators = ["www.tangerine.ca", "Orange Key", "Tangerine Savings"]
        return any(indicator in text for indicator in indicators)
    
    def extract_transactions(self, pdf_path: str) -> List[Dict[str, Any]]:
        logger.info(f"🏦 Processing Tangerine statement: {pdf_path}")
        transactions = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if not text:
                        continue
                    
                    lines = text.split('\n')
                    in_transaction_section = False
                    
                    i = 0
                    while i < len(lines):
                        line = lines[i].strip()
                        
                        # Look for transaction section headers
                        if ("Transaction Date" in line and "Transaction Description" in line) or \
                           ("Transaction Date" in line and "Amount" in line):
                            in_transaction_section = True
                            i += 1
                            continue
                        
                        # Reset section when we hit account details again
                        if "Current Interest Rate" in line or "The Details -" in line:
                            in_transaction_section = False
                            i += 1
                            continue
                        
                        # Process multi-line transactions within the section
                        if in_transaction_section and self._is_tangerine_transaction(line):
                            # Handle multi-line transactions
                            transaction, lines_consumed = self._parse_tangerine_multiline_transaction(lines, i, page_num)
                            if transaction:
                                transactions.append(transaction)
                            i += lines_consumed
                        else:
                            i += 1
            
            logger.info(f"✅ Tangerine: Found {len(transactions)} transactions")
            return transactions
            
        except Exception as e:
            logger.error(f"❌ Tangerine processing failed: {e}")
            return []
    
    def _is_tangerine_transaction(self, line: str) -> bool:
        """Check if line is a Tangerine transaction"""
        # Tangerine format: "01 Oct 2021 Opening Balance 0.00 664.54"
        pattern = r'^\d{2}\s[A-Za-z]{3}\s\d{4}'
        return bool(re.match(pattern, line))
    
    def _parse_tangerine_multiline_transaction(self, lines: List[str], start_idx: int, page_num: int) -> tuple[Optional[Dict[str, Any]], int]:
        """Parse Tangerine multi-line transaction format"""
        try:
            current_line = lines[start_idx].strip()
            
            # Check if it's a single-line transaction (like Interest Paid)
            if self._is_complete_tangerine_transaction(current_line):
                transaction = self._parse_tangerine_transaction(current_line, page_num)
                return transaction, 1
            
            # Handle multi-line transactions
            date_str = None
            description = None
            amount = None
            balance = None
            lines_consumed = 1
            
            # First line should contain date
            if re.match(r'^\d{2}\s[A-Za-z]{3}\s\d{4}', current_line):
                parts = current_line.split()
                if len(parts) >= 3:
                    date_str = f"{parts[0]} {parts[1]} {parts[2]}"
                    # Check if description is on same line
                    if len(parts) > 3:
                        remaining_parts = parts[3:]
                        # Check if it contains amounts
                        amounts_in_line = [p for p in remaining_parts if re.match(r'^[\d,]+\.?\d{2}$', p)]
                        if len(amounts_in_line) >= 2:
                            # Single line with everything
                            desc_parts = [p for p in remaining_parts if not re.match(r'^[\d,]+\.?\d{2}$', p)]
                            description = ' '.join(desc_parts)
                            amount = self.clean_amount(amounts_in_line[0])
                            balance = self.clean_amount(amounts_in_line[1])
                        else:
                            description = ' '.join(remaining_parts)
            
            # Look ahead for description and amounts in next lines
            idx = start_idx + 1
            while idx < len(lines) and lines_consumed < 5:  # Max 5 lines per transaction
                next_line = lines[idx].strip()
                if not next_line:
                    idx += 1
                    lines_consumed += 1
                    continue
                
                # Stop if we hit another date line
                if re.match(r'^\d{2}\s[A-Za-z]{3}\s\d{4}', next_line):
                    break
                
                # Look for amounts in this line
                amounts_in_line = re.findall(r'[\d,]+\.\d{2}', next_line)
                if len(amounts_in_line) >= 2 and amount is None:
                    amount = self.clean_amount(amounts_in_line[0])
                    balance = self.clean_amount(amounts_in_line[1])
                    lines_consumed += 1
                    break
                elif not description and not any(c.isdigit() for c in next_line):
                    # This line likely contains description
                    if description:
                        description += " " + next_line
                    else:
                        description = next_line
                
                idx += 1
                lines_consumed += 1
            
            # Also check previous line for description (case where description comes before date)
            if not description and start_idx > 0:
                prev_line = lines[start_idx - 1].strip()
                if prev_line and not re.match(r'^\d{2}\s[A-Za-z]{3}\s\d{4}', prev_line):
                    description = prev_line
            
            if date_str and description and amount is not None and balance is not None:
                date = self._parse_tangerine_date(date_str)
                
                # Skip balance entries
                if any(skip in description.lower() for skip in ['opening balance', 'closing balance']) and amount == 0:
                    return None, lines_consumed
                
                # Classify transaction
                description_lower = description.lower()
                if any(keyword in description_lower for keyword in [
                    'interest paid', 'deposit', 'transfer in', 'e-transfer from', 'interac e-transfer from'
                ]):
                    transaction_type = "credit"
                    is_spending = False
                elif any(keyword in description_lower for keyword in [
                    'withdrawal', 'transfer to', 'internet withdrawal', 'fee', 'charge'
                ]):
                    transaction_type = "debit"
                    is_spending = True
                else:
                    transaction_type = "credit" if amount > 0 else "debit"
                    is_spending = amount <= 0
                
                return {
                    'date': date,
                    'description': description,
                    'amount': amount,
                    'balance': balance,
                    'page': page_num,
                    'bank': self.bank_name,
                    'confidence': 0.85,
                    'transaction_type': transaction_type,
                    'is_spending': is_spending,
                    'abs_amount': abs(amount),
                    'processing_method': 'tangerine_processor',
                    'confidence_level': 'medium'
                }, lines_consumed
            
        except Exception as e:
            pass
        
        return None, 1
    
    def _is_complete_tangerine_transaction(self, line: str) -> bool:
        """Check if line contains a complete transaction with date, description and amounts"""
        parts = line.split()
        if len(parts) < 6:  # Date (3) + desc + 2 amounts minimum
            return False
        
        # Check for date pattern
        if not re.match(r'^\d{2}\s[A-Za-z]{3}\s\d{4}', line):
            return False
        
        # Check for at least 2 amounts
        amounts = [p for p in parts if re.match(r'^[\d,]+\.?\d{2}$', p)]
        return len(amounts) >= 2
    
    def _parse_tangerine_transaction(self, line: str, page_num: int) -> Optional[Dict[str, Any]]:
        """Parse Tangerine transaction line with proper classification"""
        # Pattern: "01 Oct 2021 DESCRIPTION AMOUNT BALANCE"
        parts = line.split()
        if len(parts) < 4:
            return None
        
        # Extract date (first 3 parts) and convert to MM-DD format
        try:
            date_str = f"{parts[0]} {parts[1]} {parts[2]}"
            date = self._parse_tangerine_date(date_str)
        except:
            return None
        
        # Find amounts (last two numbers)
        amounts = []
        description_parts = []
        
        for part in parts[3:]:
            if re.match(r'[\d,]+\.?\d{2}$', part):
                amounts.append(part)
            else:
                description_parts.append(part)
        
        if len(amounts) < 2:
            return None
        
        description = ' '.join(description_parts)
        amount = self.clean_amount(amounts[0])
        balance = self.clean_amount(amounts[1])
        
        # Skip balance entries that don't represent actual transactions
        if any(skip in description.lower() for skip in ['opening balance', 'closing balance']) and amount == 0:
            return None
        
        # Classify transaction based on description for Tangerine savings account
        description_lower = description.lower()
        
        # Credits (money coming IN)
        if any(keyword in description_lower for keyword in [
            'interest paid', 'deposit', 'transfer in', 'e-transfer from', 'interac e-transfer from'
        ]):
            transaction_type = "credit"
            is_spending = False
        # Debits (money going OUT)
        elif any(keyword in description_lower for keyword in [
            'withdrawal', 'transfer to', 'internet withdrawal', 'fee', 'charge'
        ]):
            transaction_type = "debit"
            is_spending = True
        else:
            # Default for savings account: if amount > 0, likely credit
            if amount > 0:
                transaction_type = "credit"
                is_spending = False
            else:
                transaction_type = "debit"
                is_spending = True
        
        return {
            'date': date,
            'description': description,
            'amount': amount,
            'balance': balance,
            'page': page_num,
            'bank': self.bank_name,
            'confidence': 0.85,
            'transaction_type': transaction_type,
            'is_spending': is_spending,
            'abs_amount': abs(amount),
            'processing_method': 'tangerine_processor',
            'confidence_level': 'medium'
        }
    
    def _parse_tangerine_date(self, date_str: str) -> str:
        """Parse Tangerine date format '01 Oct 2021' to MM-DD"""
        try:
            month_map = {
                'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
                'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
                'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
            }
            
            # Handle "01 Oct 2021" format
            parts = date_str.split()
            if len(parts) >= 3:
                day = parts[0].zfill(2)  # Pad with zero if needed
                month_abbr = parts[1].lower()
                
                if month_abbr in month_map:
                    month_num = month_map[month_abbr]
                    return f"{month_num}-{day}"
        except:
            pass
        return "Unknown"

class RBCBankProcessor(BankProcessor):
    """RBC Bank Statement processor - handles table format with Date, Description, Withdrawals, Deposits, Balance"""
    
    def __init__(self):
        super().__init__("RBC Bank")
    
    def can_process(self, text: str, filename: str) -> bool:
        indicators = ["Royal Bank of Canada", "RBC Day to Day Banking", "account statement"]
        return any(indicator in text for indicator in indicators) and "visa" not in filename.lower()
    
    def extract_transactions(self, pdf_path: str) -> List[Dict[str, Any]]:
        logger.info(f"🏦 Processing RBC Bank statement: {pdf_path}")
        transactions = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if not text:
                        continue
                    
                    if "Details of your account activity" in text:
                        lines = text.split('\n')
                        
                        # Process lines with improved date carry-forward logic
                        current_date = None
                        
                        for line in lines:
                            line = line.strip()
                            if not line:
                                continue
                            
                            # Skip clearly non-transaction lines
                            if any(skip in line.lower() for skip in ['date', 'description', 'withdrawals', 'deposits', 'balance']):
                                continue
                            
                            # Look for VALID date patterns - month names only
                            valid_months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 
                                           'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
                            
                            found_date = False
                            # Pattern: "3 Mar", "10 Mar" etc. - but only with real month names
                            date_match = re.search(r'(\d{1,2}\s+([A-Za-z]{3}))', line)
                            if date_match:
                                month_part = date_match.group(2).lower()
                                if month_part in valid_months:
                                    # Valid date found - update current date
                                    current_date = self._parse_rbc_date(date_match.group(1))
                                    # Process line without the date
                                    clean_line = line.replace(date_match.group(1), '').strip()
                                    if clean_line:
                                        transaction = self._parse_rbc_transaction_line(current_date, clean_line, page_num)
                                        if transaction:
                                            transactions.append(transaction)
                                    found_date = True
                            
                            if found_date:
                                continue
                            
                            # Line without date - use current_date (carry forward)
                            if current_date:
                                transaction = self._parse_rbc_transaction_line(current_date, line, page_num)
                                if transaction:
                                    transactions.append(transaction)
                            # Skip lines without valid dates to maintain data quality
            
            logger.info(f"✅ RBC Bank: Found {len(transactions)} transactions")
            return transactions
            
        except Exception as e:
            logger.error(f"❌ RBC Bank processing failed: {e}")
            return []
    
    def _parse_rbc_date(self, date_str: str) -> str:
        """Parse RBC date format like '3 Mar' to MM-DD"""
        try:
            month_map = {
                'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
                'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
                'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
            }
            
            # Handle "3 Mar" format
            match = re.match(r'(\d{1,2})\s+([a-zA-Z]{3})', date_str.lower())
            if match:
                day = match.group(1).zfill(2)  # Pad with zero if needed
                month_abbr = match.group(2)
                
                if month_abbr in month_map:
                    return f"{month_map[month_abbr]}-{day}"
            
            return "Unknown"
        except:
            return "Unknown"
    
    def _parse_rbc_transaction_line(self, date: str, line: str, page_num: int) -> Optional[Dict[str, Any]]:
        """Parse RBC transaction line - simplified and more accurate"""
        if not line or len(line.strip()) < 5:
            return None
        
        # Skip headers and non-transaction lines
        skip_patterns = [
            'date', 'description', 'withdrawals', 'deposits', 'balance',
            'details of your account', 'continued', 'opening balance', 'closing balance',
            'total deposits', 'total withdrawals', 'summary', 'from.*to.*', 'rbc',
            'fee electronic', 'multiproduct rebate', 'monthly fee'
        ]
        
        line_lower = line.lower()
        if any(pattern in line_lower for pattern in skip_patterns):
            return None
        
        # Extract amounts
        amounts = re.findall(r'[\d,]+\.\d{2}', line)
        if not amounts:
            return None
        
        # Use first amount as transaction amount
        amount = self.clean_amount(amounts[0])
        if amount <= 0:
            return None
        
        # Extract description more carefully - use only the first amount
        amount_match = amounts[0]
        desc_end = line.find(amount_match)
        description = line[:desc_end].strip()
        
        # Clean description  
        description = re.sub(r'^\W+|\W+$', '', description)
        description = ' '.join(description.split())
        
        if len(description) < 3:
            return None
        
        # Simplified transaction classification for RBC Bank
        # Based on your feedback and PDF analysis:
        
        # DEFINITE CREDITS (money coming IN to account) 
        credit_patterns = [
            'e-transfer', 'autodeposit', 'deposit', 'rebate', 'refund'
        ]
        
        # DEFINITE DEBITS (money going OUT of account)
        debit_patterns = [
            'interac purchase', 'contactless interac purchase', 'online banking payment',
            'loan payment', 'atm withdrawal', 'fee', 'charge', 'misc payment'
        ]
        
        # Classify transaction
        if any(pattern in line_lower for pattern in credit_patterns):
            transaction_type = 'credit'
            is_spending = False
        elif any(pattern in line_lower for pattern in debit_patterns):
            transaction_type = 'debit'
            is_spending = True
        else:
            # Default for unclear cases: if it has a merchant name, probably spending
            merchants = ['subway', 'tim hortons', 'wal-mart', 'esso', 'phoenix', 'costco', 
                        'staples', 'nike', 'shoppers', 'fortinos', 'afrocan']
            if any(merchant in line_lower for merchant in merchants):
                transaction_type = 'debit'
                is_spending = True
            else:
                # Default to debit for bank accounts (most transactions are spending)
                transaction_type = 'debit'
                is_spending = True
        
        # Only return transactions with valid dates
        if not date or date == "Unknown":
            return None
            
        return {
            'date': date,
            'description': description,
            'amount': amount,
            'page': page_num,
            'bank': self.bank_name,
            'confidence': 0.85,
            'transaction_type': transaction_type,
            'is_spending': is_spending,
            'abs_amount': abs(amount),
            'processing_method': 'rbc_bank_processor',
            'confidence_level': 'medium'
        }

class RBCVisaProcessor(BankProcessor):
    """RBC Visa processor - handles dual-date format"""
    
    def __init__(self):
        super().__init__("RBC Visa")
    
    def can_process(self, text: str, filename: str) -> bool:
        indicators = ["RBC Visa", "Visa Infinite", "Avion"]
        return any(indicator in text for indicator in indicators) and "visa" in filename.lower()
    
    def extract_transactions(self, pdf_path: str) -> List[Dict[str, Any]]:
        logger.info(f"🏦 Processing RBC Visa statement: {pdf_path}")
        transactions = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if not text:
                        continue
                    
                    lines = text.split('\n')
                    for line in lines:
                        line = line.strip()
                        
                        # RBC Visa format: "DEC22 DEC29 PARSFOODINCNORTHYORKON $12.00"
                        if self._is_rbc_visa_transaction(line):
                            transaction = self._parse_rbc_visa_transaction(line, page_num)
                            if transaction:
                                transactions.append(transaction)
            
            logger.info(f"✅ RBC Visa: Found {len(transactions)} transactions")
            return transactions
            
        except Exception as e:
            logger.error(f"❌ RBC Visa processing failed: {e}")
            return []
    
    def _is_rbc_visa_transaction(self, line: str) -> bool:
        """Check if line is an RBC Visa transaction"""
        # Pattern: MONTH+DAY MONTH+DAY DESCRIPTION $AMOUNT
        pattern = r'^[A-Z]{3}\d{2}\s+[A-Z]{3}\d{2}'
        return bool(re.match(pattern, line))
    
    def _parse_rbc_visa_transaction(self, line: str, page_num: int) -> Optional[Dict[str, Any]]:
        """Parse RBC Visa transaction"""
        # Pattern: "DEC22 DEC29 DESCRIPTION $12.00"
        match = re.match(r'^([A-Z]{3}\d{2})\s+([A-Z]{3}\d{2})\s+(.*?)\s+\$?([\d,]+\.?\d{2})$', line)
        
        if match:
            trans_date = self.clean_date(match.group(1))
            post_date = self.clean_date(match.group(2))
            description = match.group(3).strip()
            amount = self.clean_amount(match.group(4))
            
            return {
                'date': trans_date,
                'posting_date': post_date,
                'description': description,
                'amount': amount,
                'page': page_num,
                'bank': self.bank_name,
                'confidence': 0.9
            }
        
        return None

class CIBCProcessor(BankProcessor):
    """CIBC Bank processor - handles page 2 table format"""
    
    def __init__(self):
        super().__init__("CIBC")
    
    def can_process(self, text: str, filename: str) -> bool:
        indicators = ["CIBC Account Statement", "CIBC", "Branch transit number"]
        return any(indicator in text for indicator in indicators)
    
    def extract_transactions(self, pdf_path: str) -> List[Dict[str, Any]]:
        logger.info(f"🏦 Processing CIBC statement: {pdf_path}")
        transactions = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                # CIBC transactions are typically on page 2+
                for page_num in range(1, len(pdf.pages)):
                    page = pdf.pages[page_num]
                    text = page.extract_text()
                    
                    if "Transaction details" in text:
                        lines = text.split('\n')
                        
                        # Process lines with date carry-forward logic (like RBC)
                        current_date = None
                        
                        for line in lines:
                            line = line.strip()
                            if not line:
                                continue
                            
                            # Skip headers
                            if any(skip in line.lower() for skip in ['date', 'description', 'withdrawals', 'deposits', 'balance']):
                                continue
                            
                            # Look for VALID date patterns - month names only
                            valid_months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 
                                           'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
                            
                            found_date = False
                            # Pattern: "May 1", "May 4" etc. - but only with real month names
                            date_match = re.search(r'([A-Za-z]{3})\s+(\d{1,2})', line)
                            if date_match:
                                month_part = date_match.group(1).lower()
                                if month_part in valid_months:
                                    # Valid date found - update current date
                                    current_date = self._parse_cibc_date(date_match.group(0))
                                    # Process line without the date
                                    clean_line = line.replace(date_match.group(0), '').strip()
                                    if clean_line:
                                        transaction = self._parse_cibc_transaction_line(current_date, clean_line, page_num + 1)
                                        if transaction:
                                            transactions.append(transaction)
                                    found_date = True
                            
                            if found_date:
                                continue
                            
                            # Line without date - use current_date (carry forward)
                            if current_date:
                                transaction = self._parse_cibc_transaction_line(current_date, line, page_num + 1)
                                if transaction:
                                    transactions.append(transaction)
            
            logger.info(f"✅ CIBC: Found {len(transactions)} transactions")
            return transactions
            
        except Exception as e:
            logger.error(f"❌ CIBC processing failed: {e}")
            return []
    
    def _parse_cibc_date(self, date_str: str) -> str:
        """Parse CIBC date format to MM-DD"""
        try:
            # Handle "May 1", "May 4" format
            if re.match(r'^[A-Za-z]{3}\s+\d{1,2}$', date_str):
                parts = date_str.strip().split()
                month = parts[0].lower()
                day = int(parts[1])
                
                month_map = {
                    'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
                    'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
                    'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
                }
                
                month_num = month_map.get(month[:3], '00')
                return f"{month_num}-{day:02d}"
        except:
            pass
        return "Unknown"
    
    def _parse_cibc_transaction_line(self, date: str, line: str, page_num: int) -> Optional[Dict[str, Any]]:
        """Parse CIBC transaction line with proper classification"""
        if not line or len(line.strip()) < 5:
            return None
        
        # Skip headers and non-transaction lines
        skip_patterns = [
            'opening balance', 'closing balance', 'balance forward',
            'total', 'summary', 'continued', 'transaction details'
        ]
        
        line_lower = line.lower()
        if any(pattern in line_lower for pattern in skip_patterns):
            return None
        
        # Extract amounts - CIBC format has amount and balance
        amounts = re.findall(r'[\d,]+\.\d{2}', line)
        if not amounts:
            return None
        
        # Use first amount as transaction amount
        amount = self.clean_amount(amounts[0])
        if amount <= 0:
            return None
        
        # Extract description by removing the amount
        amount_match = amounts[0]
        desc_end = line.find(amount_match)
        description = line[:desc_end].strip()
        
        # Clean description  
        description = re.sub(r'^\W+|\W+$', '', description)
        description = ' '.join(description.split())
        
        if len(description) < 3:
            return None
        
        # CIBC is a bank account - classify transactions properly
        description_lower = description.lower()
        
        # Credits (money coming IN)
        credit_patterns = [
            'deposit', 'e-transfer', 'transfer in', 'interest', 'refund', 'rebate'
        ]
        
        # Debits (money going OUT) 
        debit_patterns = [
            'retail purchase', 'purchase', 'withdrawal', 'teller withdrawal',
            'instant teller', 'atm', 'fee', 'charge', 'payment'
        ]
        
        # Classify transaction
        if any(pattern in description_lower for pattern in credit_patterns):
            transaction_type = 'credit'
            is_spending = False
        elif any(pattern in description_lower for pattern in debit_patterns):
            transaction_type = 'debit'
            is_spending = True
        else:
            # Default for bank accounts: most transactions are spending
            transaction_type = 'debit'
            is_spending = True
        
        # Only return transactions with valid dates
        if not date or date == "Unknown":
            return None
            
        return {
            'date': date,
            'description': description,
            'amount': amount,
            'balance': self.clean_amount(amounts[1]) if len(amounts) > 1 else None,
            'page': page_num,
            'bank': self.bank_name,
            'confidence': 0.85,
            'transaction_type': transaction_type,
            'is_spending': is_spending,
            'abs_amount': abs(amount),
            'processing_method': 'cibc_processor',
            'confidence_level': 'medium'
        }

class SimpliiProcessor(BankProcessor):
    """Simplii Credit Card processor - handles dual-date table format"""
    
    def __init__(self):
        super().__init__("Simplii")
    
    def can_process(self, text: str, filename: str) -> bool:
        indicators = ["Simplii Financial", "Cash Back Visa", "simplii.com"]
        return any(indicator in text for indicator in indicators)
    
    def extract_transactions(self, pdf_path: str) -> List[Dict[str, Any]]:
        logger.info(f"🏦 Processing Simplii statement: {pdf_path}")
        transactions = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if not text:
                        continue
                    
                    lines = text.split('\n')
                    in_transaction_section = False
                    
                    for line in lines:
                        line = line.strip()
                        
                        # Look for transaction section headers
                        if ("Trans" in line and "Post" in line and "date" in line) or \
                           ("Card number" in line and "XXXX" in line):
                            in_transaction_section = True
                            continue
                        
                        # Stop at totals or other sections
                        if any(stop in line.lower() for stop in ["total for", "total payments", "page", "information about"]):
                            in_transaction_section = False
                            continue
                        
                        if in_transaction_section and self._is_simplii_transaction(line):
                            transaction = self._parse_simplii_transaction(line, page_num)
                            if transaction:
                                transactions.append(transaction)
            
            logger.info(f"✅ Simplii: Found {len(transactions)} transactions")
            return transactions
            
        except Exception as e:
            logger.error(f"❌ Simplii processing failed: {e}")
            return []
    
    def _is_simplii_transaction(self, line: str) -> bool:
        """Check if line is a Simplii transaction"""
        # Simplii format: "Jul 27 Jul 28 PAYMENT THANK YOU/PAIEMENT MERCI 50.00"
        # Also handle: "Jul 14 Jul 18 PLAYNOW.COM 8777066789 8777066789 BC Hotel, Entertainment and Recreation 25.00"
        
        # Skip non-transaction lines
        skip_phrases = [
            'card number', 'total for', 'total payments', 'your payments', 'spend categories',
            'description', 'amount($)', 'identifies cash back'
        ]
        if any(phrase in line.lower() for phrase in skip_phrases):
            return False
        
        # Must start with month abbreviation + day, followed by another month + day
        pattern = r'^[A-Za-z]{3}\s+\d{1,2}\s+[A-Za-z]{3}\s+\d{1,2}\s+'
        has_date_pattern = bool(re.match(pattern, line))
        
        # Must have an amount at the end
        has_amount = bool(re.search(r'\d{1,3}(?:,\d{3})*\.\d{2}$', line))
        
        return has_date_pattern and has_amount and len(line) > 20
    
    def _parse_simplii_transaction(self, line: str, page_num: int) -> Optional[Dict[str, Any]]:
        """Parse Simplii transaction with proper credit card classification"""
        # Handle the complex Simplii format with categories
        # Pattern: "Jul 27 Jul 28 PAYMENT THANK YOU/PAIEMENT MERCI 50.00"
        # Or: "Jul 14 Jul 18 PLAYNOW.COM 8777066789 8777066789 BC Hotel, Entertainment and Recreation 25.00"
        
        # Extract dates (first two date groups)
        date_matches = re.findall(r'([A-Za-z]{3})\s+(\d{1,2})', line)
        if len(date_matches) < 2:
            return None
        
        trans_date = f"{date_matches[0][0]} {date_matches[0][1]}"
        post_date = f"{date_matches[1][0]} {date_matches[1][1]}"
        
        # Extract amount (last number in format XX.XX)
        amount_match = re.search(r'(\d{1,3}(?:,\d{3})*\.\d{2})$', line)
        if not amount_match:
            return None
        
        amount = self.clean_amount(amount_match.group(1))
        
        # Extract description (everything between dates and amount)
        # Remove the dates from beginning
        desc_start = line.find(post_date) + len(post_date)
        desc_end = amount_match.start()
        description = line[desc_start:desc_end].strip()
        
        # Clean up description - remove category info if present
        if any(category in description for category in ['Hotel, Entertainment', 'Personal and Household', 'Home and Office']):
            # Split and take first meaningful part
            parts = description.split()
            # Take everything before category keywords
            clean_parts = []
            for part in parts:
                if part in ['Hotel,', 'Personal', 'Home', 'Entertainment', 'Household', 'Office', 'BC', 'ON']:
                    break
                clean_parts.append(part)
            description = ' '.join(clean_parts) if clean_parts else description
        
        # Convert dates to MM-DD format
        parsed_trans_date = self._parse_simplii_date(trans_date)
        
        # For credit cards: positive amounts are spending (debits)
        transaction_type = "debit" if amount > 0 else "credit"
        is_spending = amount > 0
        
        return {
            'date': parsed_trans_date,
            'posting_date': self._parse_simplii_date(post_date),
            'description': description,
            'amount': amount,
            'page': page_num,
            'bank': self.bank_name,
            'confidence': 0.9,
            'transaction_type': transaction_type,
            'is_spending': is_spending,
            'abs_amount': abs(amount),
            'processing_method': 'simplii_processor',
            'confidence_level': 'high'
        }
    
    def _parse_simplii_date(self, date_str: str) -> str:
        """Parse Simplii date format 'Jul 27' to MM-DD"""
        try:
            month_map = {
                'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
                'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
                'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
            }
            
            parts = date_str.split()
            if len(parts) >= 2:
                month_abbr = parts[0].lower()
                day = parts[1].zfill(2)
                
                if month_abbr in month_map:
                    return f"{month_map[month_abbr]}-{day}"
        except:
            pass
        return "Unknown"

class RBCVisaProcessor(BankProcessor):
    """RBC Visa processor - handles dual-date format"""
    
    def __init__(self):
        super().__init__("RBC Visa")
    
    def can_process(self, text: str, filename: str) -> bool:
        indicators = ["RBC Visa", "Visa Infinite", "Avion"]
        return any(indicator in text for indicator in indicators) and "visa" in filename.lower()
    
    def extract_transactions(self, pdf_path: str) -> List[Dict[str, Any]]:
        logger.info(f"🏦 Processing RBC Visa statement: {pdf_path}")
        transactions = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if not text:
                        continue
                    
                    lines = text.split('\n')
                    for line in lines:
                        line = line.strip()
                        
                        # RBC Visa format: "DEC22 DEC29 PARSFOODINCNORTHYORKON $12.00"
                        if self._is_rbc_visa_transaction(line):
                            transaction = self._parse_rbc_visa_transaction(line, page_num)
                            if transaction:
                                transactions.append(transaction)
            
            logger.info(f"✅ RBC Visa: Found {len(transactions)} transactions")
            return transactions
            
        except Exception as e:
            logger.error(f"❌ RBC Visa processing failed: {e}")
            return []
    
    def _is_rbc_visa_transaction(self, line: str) -> bool:
        """Check if line is an RBC Visa transaction"""
        # Pattern: MONTH+DAY MONTH+DAY DESCRIPTION $AMOUNT
        pattern = r'^[A-Z]{3}\d{2}\s+[A-Z]{3}\d{2}'
        return bool(re.match(pattern, line))
    
    def _parse_rbc_visa_transaction(self, line: str, page_num: int) -> Optional[Dict[str, Any]]:
        """Parse RBC Visa transaction"""
        # Pattern: "DEC22 DEC29 DESCRIPTION $12.00"
        match = re.match(r'^([A-Z]{3}\d{2})\s+([A-Z]{3}\d{2})\s+(.*?)\s+\$?([\d,]+\.?\d{2})$', line)
        
        if match:
            trans_date = self.clean_date(match.group(1))
            post_date = self.clean_date(match.group(2))
            description = match.group(3).strip()
            amount = self.clean_amount(match.group(4))
            
            return {
                'date': trans_date,
                'posting_date': post_date,
                'description': description,
                'amount': amount,
                'page': page_num,
                'bank': self.bank_name,
                'confidence': 0.9
            }
        
        return None

class AmexProcessor(BankProcessor):
    """Amex Credit Card processor - handles concatenated format"""
    
    def __init__(self):
        super().__init__("Amex")
    
    def can_process(self, text: str, filename: str) -> bool:
        indicators = ["AmericanExpress", "Amex Bank of Canada", "Statement of Account"]
        return any(indicator in text for indicator in indicators) and "amex" in filename.lower()
    
    def extract_transactions(self, pdf_path: str) -> List[Dict[str, Any]]:
        logger.info(f"🏦 Processing Amex statement: {pdf_path}")
        transactions = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if not text:
                        continue
                    
                    lines = text.split('\n')
                    for line in lines:
                        line = line.strip()
                        
                        # Amex format: "December16 AMZNMKTPCA*NE4ZR9AWWW.AMAZON.CA 16.99"
                        if self._is_amex_transaction(line):
                            transaction = self._parse_amex_transaction(line, page_num)
                            if transaction:
                                transactions.append(transaction)
            
            logger.info(f"✅ Amex: Found {len(transactions)} transactions")
            return transactions
            
        except Exception as e:
            logger.error(f"❌ Amex processing failed: {e}")
            return []
    
    def _is_amex_transaction(self, line: str) -> bool:
        """Check if line is an Amex transaction"""
        # Amex format: MonthDay DESCRIPTION AMOUNT
        pattern = r'^[A-Za-z]{3,9}\d{1,2}\s+[A-Z]'
        return bool(re.match(pattern, line))
    
    def _parse_amex_transaction(self, line: str, page_num: int) -> Optional[Dict[str, Any]]:
        """Parse Amex transaction"""
        # Pattern: "December16 DESCRIPTION AMOUNT"
        match = re.match(r'^([A-Za-z]{3,9}\d{1,2})\s+(.*?)\s+([\d,]+\.?\d{2})$', line)
        
        if match:
            # Custom Amex date parsing for "December16" format
            raw_date = match.group(1)
            date = self._parse_amex_date(raw_date)
            description = match.group(2).strip()
            amount = self.clean_amount(match.group(3))
            
            # Skip summary lines
            if any(word in description.lower() for word in ['total', 'balance', 'payment']):
                return None
            
            return {
                'date': date,
                'description': description,
                'amount': amount,
                'page': page_num,
                'bank': self.bank_name,
                'confidence': 0.85
            }
        
        return None
    
    def _parse_amex_date(self, date_str: str) -> str:
        """Parse Amex-specific date format like 'December16' to MM-DD"""
        month_map = {
            'january': '01', 'february': '02', 'march': '03', 'april': '04',
            'may': '05', 'june': '06', 'july': '07', 'august': '08',
            'september': '09', 'october': '10', 'november': '11', 'december': '12'
        }
        
        # Extract month and day from "December16" format
        match = re.match(r'([A-Za-z]{3,9})(\d{1,2})', date_str)
        if match:
            month_name = match.group(1).lower()
            day = match.group(2).zfill(2)
            
            # Find matching month
            for full_month, month_num in month_map.items():
                if full_month.startswith(month_name.lower()):
                    return f"{month_num}-{day}"
        
        return "01-01"  # Fallback

class ScotiaBankProcessor(BankProcessor):
    """Scotiabank Bank Account processor"""
    
    def __init__(self):
        super().__init__("Scotiabank")
    
    def can_process(self, text: str, filename: str) -> bool:
        # Check filename first
        if 'scotia' in filename.lower() and 'bank' in filename.lower():
            return True
        
        # Check for bank-specific indicators (not credit card)
        if any(indicator in text.lower() for indicator in ["scotiabank", "scotia"]):
            # Must have bank account indicators, not credit card indicators
            has_bank_indicators = any(term in text.lower() for term in [
                'deposits', 'withdrawals', 'mb-billpayment', 'service charge', 
                'mb-transfer', 'chequing', 'savings', 'balance brought forward'
            ])
            has_credit_indicators = any(term in text.lower() for term in [
                'scene', 'credit card', 'minimum payment', 'credit limit'
            ])
            return has_bank_indicators and not has_credit_indicators
        
        return False

    def extract_transactions(self, pdf_path: str) -> List[Dict[str, Any]]:
        logger.info(f"🏦 Processing Scotiabank statement: {pdf_path}")
        transactions = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if not text:
                        continue
                    
                    lines = text.split('\n')
                    current_date = None
                    
                    for line in lines:
                        line = line.strip()
                        
                        # Look for date headers (date carry-forward like RBC)
                        date_match = re.search(r'(Dec|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov)(\d{1,2})', line)
                        if date_match:
                            month_abbr = date_match.group(1)
                            day = date_match.group(2).zfill(2)
                            current_date = self._parse_scotia_bank_date(f"{month_abbr}{day}")
                        
                        # Parse transaction lines
                        if self._is_scotia_bank_transaction(line):
                            transaction = self._parse_scotia_bank_transaction(line, current_date, page_num)
                            if transaction:
                                transactions.append(transaction)
            
            logger.info(f"✅ Scotiabank: Found {len(transactions)} transactions")
            return transactions
            
        except Exception as e:
            logger.error(f"❌ Scotiabank processing failed: {e}")
            return []
    
    def _is_scotia_bank_transaction(self, line: str) -> bool:
        """Check if line is a Scotiabank bank transaction"""
        # Skip summary/balance lines
        skip_phrases = [
            'opening balance', 'closing balance', 'minus total withdrawals', 
            'plus total deposits', 'plustotal deposits', 'minustotal withdrawals',
            'balance brought forward', 'your basic banking account summary'
        ]
        if any(phrase in line.lower() for phrase in skip_phrases):
            return False
        
        # Look for bank transaction patterns
        bank_patterns = [
            'mb-billpayment', 'mb-transfer', 'withdrawal', 'deposit', 
            'fees/dues', 'servicecharge', 'point of salepurchase', 
            'debit memo', 'mutual funds', 'error correction', 'ei canada'
        ]
        
        has_bank_pattern = any(pattern in line.lower() for pattern in bank_patterns)
        has_amount = bool(re.search(r'\$?[\d,]+\.\d{2}', line))
        
        return has_bank_pattern and has_amount and len(line) > 10
    
    def _parse_scotia_bank_transaction(self, line: str, current_date: str, page_num: int) -> Optional[Dict[str, Any]]:
        """Parse Scotiabank bank transaction"""
        # Extract amount
        amount_match = re.search(r'\$?([\d,]+\.\d{2})', line)
        if not amount_match:
            return None
        
        amount = self.clean_amount(amount_match.group(1))
        
        # Extract description (everything before amount)
        amount_start = amount_match.start()
        description = line[:amount_start].strip()
        
        # Use current date or try to extract from line
        date = current_date if current_date else "Unknown"
        
        # Clean description
        description = re.sub(r'^(Dec|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov)\d{1,2}\s*', '', description).strip()
        
        if len(description) < 3:
            return None
        
        # Classify transactions for bank account
        description_lower = description.lower()
        
        # Credits (money coming IN)
        if any(keyword in description_lower for keyword in [
            'deposit', 'transfer from', 'interest', 'credit', 'refund'
        ]):
            transaction_type = "credit"
            is_spending = False
        # Debits (money going OUT)
        else:
            transaction_type = "debit"
            is_spending = True
        
        return {
            'date': date,
            'description': description,
            'amount': amount,
            'page': page_num,
            'bank': self.bank_name,
            'confidence': 0.85,
            'transaction_type': transaction_type,
            'is_spending': is_spending,
            'abs_amount': abs(amount),
            'processing_method': 'scotiabank_processor',
            'confidence_level': 'medium'
        }
    
    def _parse_scotia_bank_date(self, date_str: str) -> str:
        """Parse Scotiabank date format like 'Dec18' to MM-DD"""
        try:
            month_map = {
                'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
                'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
                'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
            }
            
            # Handle "Dec18" format
            match = re.match(r'([a-zA-Z]{3})(\d{1,2})', date_str.lower())
            if match:
                month_abbr = match.group(1)
                day = match.group(2).zfill(2)
                
                if month_abbr in month_map:
                    return f"{month_map[month_abbr]}-{day}"
            
            return "Unknown"
        except:
            return "Unknown"

class ScotiaProcessor(BankProcessor):
    """Scotia Credit Card processor"""
    
    def __init__(self):
        super().__init__("Scotia Credit Card")
    
    def can_process(self, text: str, filename: str) -> bool:
        # Check for credit card specific indicators
        if any(indicator in text.lower() for indicator in ["scotia", "scotiabank"]):
            # Must have credit card indicators
            has_credit_indicators = any(term in text.lower() for term in [
                'scene', 'credit card', 'minimum payment', 'credit limit'
            ])
            return has_credit_indicators
        return False
    
    def extract_transactions(self, pdf_path: str) -> List[Dict[str, Any]]:
        logger.info(f"🏦 Processing Scotia statement: {pdf_path}")
        transactions = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if not text:
                        continue
                    
                    lines = text.split('\n')
                    for line in lines:
                        line = line.strip()
                        if self._is_scotia_transaction(line):
                            transaction = self._parse_scotia_transaction(line, page_num)
                            if transaction:
                                transactions.append(transaction)
            
            logger.info(f"✅ Scotia: Found {len(transactions)} transactions")
            return transactions
            
        except Exception as e:
            logger.error(f"❌ Scotia processing failed: {e}")
            return []
    
    def _is_scotia_transaction(self, line: str) -> bool:
        """Check if line is a Scotia transaction"""
        # Skip header/summary rows with broader patterns
        skip_phrases = [
            'beginning points', 'points earned', 'total', 'balance', 
            'statement', 'account', 'summary', 'payment due',
            'payments/credits', 'purchases/charges', 'based on your',
            'rewards points', 'eligible purchases', 'credit limit'
        ]
        if any(phrase in line.lower() for phrase in skip_phrases):
            return False
        
        # Must have both amount AND date (more strict)
        has_amount = bool(re.search(r'\$?[\d,]+\.\d{2}', line))
        has_date = bool(re.search(r'\w{3}[-\s]\d{1,2}', line))  # Apr-1, etc.
        
        # Only transactions with clear date patterns
        return has_amount and has_date and len(line) > 15
    
    def _parse_scotia_transaction(self, line: str, page_num: int) -> Optional[Dict[str, Any]]:
        """Parse Scotia transaction"""
        # Try to extract date, description, and amount
        amount_match = re.search(r'\$?([\d,]+\.\d{2})', line)
        if not amount_match:
            return None
        
        amount = self.clean_amount(amount_match.group(1))
        
        # Extract description (everything before amount)
        amount_start = amount_match.start()
        description = line[:amount_start].strip()
        
        # Try to extract date from description - Scotia uses "Apr-1" format
        date_match = re.search(r'(\w{3}[-\s]\d{1,2})', description)
        if date_match:
            date = self._parse_scotia_date(date_match.group(1))
            # Remove date from description
            description = description.replace(date_match.group(1), '').strip()
        else:
            date = "Unknown"
        
        # Clean up description - remove transaction numbers
        description = re.sub(r'\b\d{3}\b\s*', '', description).strip()
        
        # Skip if description is too short or looks like a summary
        if len(description) < 3:
            return None
        
        return {
            'date': date,
            'description': description,
            'amount': amount,
            'page': page_num,
            'bank': self.bank_name,
            'confidence': 0.8
        }
    
    def _parse_scotia_date(self, date_str: str) -> str:
        """Parse Scotia date format like 'Apr-1' to MM-DD"""
        try:
            # Scotia uses format like "Apr-1"
            month_map = {
                'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
                'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
                'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
            }
            
            # Handle "Apr-1" or "Apr 1" format
            match = re.match(r'([a-zA-Z]{3})[-\s](\d{1,2})', date_str.lower())
            if match:
                month_abbr = match.group(1)
                day = match.group(2).zfill(2)  # Pad with zero if needed
                
                if month_abbr in month_map:
                    return f"{month_map[month_abbr]}-{day}"
            
            return "Unknown"
        except:
            return "Unknown"

class WiseProcessor(BankProcessor):
    """Wise Credit Card processor - handles summary-style statements"""
    
    def __init__(self):
        super().__init__("Wise")
    
    def can_process(self, text: str, filename: str) -> bool:
        # Filename first
        if 'wise' in filename.lower():
            return True
        
        # Content indicators for Wise
        wise_indicators = ["Wise", "wise.com", "Credit Card Statement", "xxxx-xxxx-xxxx"]
        return any(indicator in text for indicator in wise_indicators)
    
    def extract_transactions(self, pdf_path: str) -> List[Dict[str, Any]]:
        logger.info(f"🏦 Processing Wise statement: {pdf_path}")
        transactions = []
        statement_period = None
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if not text:
                        continue
                    
                    lines = text.split('\n')
                    
                    # Extract statement period for date context
                    for line in lines:
                        if "Date:" in line and "to" in line:
                            statement_period = self._extract_statement_period(line)
                            break
                    
                    # Process transaction lines
                    for line in lines:
                        line = line.strip()
                        if self._is_wise_transaction(line):
                            transaction = self._parse_wise_transaction(line, page_num, statement_period)
                            if transaction:
                                transactions.append(transaction)
            
            logger.info(f"✅ Wise: Found {len(transactions)} transactions")
            return transactions
            
        except Exception as e:
            logger.error(f"❌ Wise processing failed: {e}")
            return []
    
    def _extract_statement_period(self, line: str) -> str:
        """Extract statement period for date context"""
        # Example: "Date: Mar 1, 2021 to Mar 23, 2021"
        match = re.search(r'Date:\s*(\w+\s+\d+,\s+\d+)\s+to\s+(\w+\s+\d+,\s+\d+)', line)
        if match:
            start_date = match.group(1)
            end_date = match.group(2)
            # Use end date as transaction date context
            try:
                from datetime import datetime
                date_obj = datetime.strptime(end_date, "%b %d, %Y")
                return date_obj.strftime("%m-%d")
            except:
                return "03-23"  # Default from example
        return None
    
    def _is_wise_transaction(self, line: str) -> bool:
        """Check if line is a Wise category summary"""
        # Must have amount and be a meaningful category
        has_amount = bool(re.search(r'\$[\d,]+\.\d{2}', line))
        if not has_amount:
            return False
        
        # Skip balance/summary lines
        skip_terms = ['total balance', 'statement', 'xxxx-xxxx', 'as of']
        if any(term in line.lower() for term in skip_terms):
            return False
        
        # Valid category patterns
        valid_categories = ['card payments', 'moneysent', 'top up', 'topup', 'atm withdrawals', 
                          'exchange in', 'exchange out', 'revolut fees', 'payment', 'withdrawal']
        return any(cat in line.lower() for cat in valid_categories)
    
    def _parse_wise_transaction(self, line: str, page_num: int, statement_period: str) -> Optional[Dict[str, Any]]:
        """Parse Wise category summary as transaction"""
        # Format: "Category Description $Amount"
        match = re.match(r'(.*?)\s+\$?([\d,]+\.\d{2})$', line)
        if not match:
            return None
        
        description = match.group(1).strip()
        amount = self.clean_amount(match.group(2))
        
        # Filter out zero amounts (meaningless summaries)
        if amount == 0.0:
            return None
        
        # Use statement period for date, or default
        date = statement_period if statement_period else "03-23"
        
        return {
            'date': date,
            'description': description,
            'amount': amount,
            'page': page_num,
            'bank': self.bank_name,
            'confidence': 0.8,  # Higher confidence for clean category data
            'note': 'category_summary'  # Flag this as summary data
        }

class TangerineCreditCardProcessor(BankProcessor):
    """Tangerine Money-Back Credit Card processor - handles table format with dual dates"""
    
    def __init__(self):
        super().__init__("Tangerine Credit Card")
    
    def can_process(self, text: str, filename: str) -> bool:
        # Check for Tangerine Credit Card specific indicators
        tangerine_credit_indicators = [
            "Tangerine Money-Back Credit Card", "Money-Back Credit Card", 
            "Here's your latest statement for your Tangerine"
        ]
        
        # Must have Tangerine credit card indicators AND be a credit card (not bank statement)
        has_tangerine_credit = any(indicator in text for indicator in tangerine_credit_indicators)
        
        # Additional credit card features (not bank account features)
        has_credit_card_features = any(term in text for term in [
            "Credit limit", "Cash advance limit", "Money-Back Rewards",
            "Transaction Posted Description Category Amount Reward"
        ])
        
        # Ensure it's NOT the existing Tangerine bank account format
        has_bank_features = any(term in text for term in [
            "Transaction Date", "Transaction Description", "Orange Key",
            "Interest Paid", "Opening Balance", "Closing Balance"
        ])
        
        return has_tangerine_credit and has_credit_card_features and not has_bank_features
    
    def extract_transactions(self, pdf_path: str) -> List[Dict[str, Any]]:
        logger.info(f"🏦 Processing Tangerine Credit Card statement: {pdf_path}")
        transactions = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if not text:
                        continue
                    
                    lines = text.split('\n')
                    in_transaction_section = False
                    
                    for line in lines:
                        line = line.strip()
                        
                        # Look for transaction table headers
                        if "Transaction Posted Description Category Amount Reward" in line:
                            in_transaction_section = True
                            continue
                        
                        # Stop processing only when we hit terminal sections (not informational sections)
                        if any(keyword in line for keyword in [
                            "Tangerine.ca:", "Minimum Payment:", "Transaction/Posting Date",
                            "Interest and Grace Period", "Foreign Currency Transactions"
                        ]):
                            in_transaction_section = False
                            continue
                        
                        # Parse transactions - continue processing regardless of informational sections
                        if self._is_tangerine_credit_transaction(line):
                            transaction = self._parse_tangerine_credit_transaction(line, page_num)
                            if transaction:
                                transactions.append(transaction)
            
            logger.info(f"✅ Tangerine Credit Card: Found {len(transactions)} transactions")
            return transactions
            
        except Exception as e:
            logger.error(f"❌ Tangerine Credit Card processing failed: {e}")
            return []
    
    def _is_tangerine_credit_transaction(self, line: str) -> bool:
        """Check if line is a Tangerine Credit Card transaction"""
        # Skip header lines and summaries
        skip_patterns = [
            'transaction posted', 'description', 'category', 'amount', 'reward',
            'previous balance', 'your chosen', 'currently earning', 'money-back',
            'purchases', 'cash advances', 'quebec'
        ]
        
        if any(pattern in line.lower() for pattern in skip_patterns):
            return False
        
        # Tangerine Credit Card format: "15-Feb-2025 17-Feb-2025 DESCRIPTION $8.57 $0.04"
        # Also handle negative amounts: "23-Jan-2025 23-Jan-2025 PAYMENT - THANK YOU – -$2,292.91 –"
        has_dual_date = bool(re.search(r'\d{2}-[A-Z][a-z]{2}-\d{4}\s+\d{2}-[A-Z][a-z]{2}-\d{4}', line))
        has_amount = bool(re.search(r'-?\$[\d,]+\.\d{2}', line))  # Now handles negative amounts
        
        return has_dual_date and has_amount and len(line) > 25
    
    def _parse_tangerine_credit_transaction(self, line: str, page_num: int) -> Optional[Dict[str, Any]]:
        """Parse Tangerine Credit Card transaction line"""
        # Pattern: "15-Feb-2025 17-Feb-2025 AGENCE DE MOBILITE DUR $8.57 $0.04"
        # Also handles: "23-Jan-2025 23-Jan-2025 PAYMENT - THANK YOU – -$2,292.91 –"
        # Extract: Transaction Date | Posted Date | Description | Amount | Reward Amount
        pattern = r'(\d{2}-[A-Z][a-z]{2}-\d{4})\s+(\d{2}-[A-Z][a-z]{2}-\d{4})\s+(.*?)\s+(-?\$?[\d,]+\.\d{2})(?:\s+\$?([\d,]+\.\d{2}|–))?'
        match = re.search(pattern, line)
        
        if not match:
            return None
        
        trans_date = match.group(1)  # "15-Feb-2025"
        post_date = match.group(2)   # "17-Feb-2025"
        description = match.group(3).strip()  # "AGENCE DE MOBILITE DUR"
        amount = self.clean_amount(match.group(4))  # "8.57" or "-2292.91"
        reward = match.group(5) if match.group(5) and match.group(5) != "–" else "0.00"
        
        # Convert dates to MM-DD format
        parsed_trans_date = self._parse_tangerine_credit_date(trans_date)
        parsed_post_date = self._parse_tangerine_credit_date(post_date)
        
        # Skip if we can't parse the date properly
        if parsed_trans_date == "Unknown":
            return None
        
        # Clean description - remove extra location info that might be in separate lines
        description = re.sub(r'\s+(QC|ON|BC|AB|MB|SK|NB|NS|PE|NL)(\s|$)', '', description)
        description = ' '.join(description.split())  # Clean multiple spaces
        
        # For credit cards: positive amounts are spending (debits), negative would be credits/payments
        transaction_type = "debit" if amount > 0 else "credit"
        is_spending = amount > 0
        
        return {
            'date': parsed_trans_date,
            'posting_date': parsed_post_date,
            'description': description,
            'amount': amount,
            'reward_earned': self.clean_amount(reward) if reward != "0.00" else 0.0,
            'page': page_num,
            'bank': self.bank_name,
            'confidence': 0.9,
            'transaction_type': transaction_type,
            'is_spending': is_spending,
            'abs_amount': abs(amount),
            'processing_method': 'tangerine_credit_card_processor',
            'confidence_level': 'high'
        }
    
    def _parse_tangerine_credit_date(self, date_str: str) -> str:
        """Parse Tangerine Credit Card date format '15-Feb-2025' to MM-DD"""
        try:
            month_map = {
                'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
                'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
                'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
            }
            
            # Handle "15-Feb-2025" format
            parts = date_str.split('-')
            if len(parts) >= 3:
                day = parts[0].zfill(2)
                month_abbr = parts[1].lower()
                
                if month_abbr in month_map:
                    return f"{month_map[month_abbr]}-{day}"
            
            return "Unknown"
        except:
            return "Unknown"

class CIBCVisaProcessor(BankProcessor):
    """CIBC Visa Credit Card processor - handles U.S. Dollar card with dual dates and exchange rates"""
    
    def __init__(self):
        super().__init__("CIBC Visa")
    
    def can_process(self, text: str, filename: str) -> bool:
        # Check for CIBC Visa Credit Card specific indicators
        cibc_visa_indicators = [
            "CIBC U.S. Dollar Aventura", "Aventura Gold Visa Card", 
            "CIBC Visa", "U.S. Dollar Aventura"
        ]
        
        # Must have CIBC visa indicators AND be a credit card (not bank account)
        has_cibc_visa = any(indicator in text for indicator in cibc_visa_indicators)
        
        # Additional credit card features (not bank account features)
        has_credit_card_features = any(term in text for term in [
            "Amount Due", "Minimum Payment", "Credit Card", "Aventura Points",
            "Trans Post", "date date Description Amount"
        ])
        
        # Ensure it's NOT the existing CIBC bank account format
        has_bank_features = any(term in text for term in [
            "Opening Balance", "Closing Balance", "Direct Deposit", 
            "Account Balance Summary", "DAILY BALANCE"
        ])
        
        return has_cibc_visa and has_credit_card_features and not has_bank_features
    
    def extract_transactions(self, pdf_path: str) -> List[Dict[str, Any]]:
        logger.info(f"🏦 Processing CIBC Visa statement: {pdf_path}")
        transactions = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if not text:
                        continue
                    
                    lines = text.split('\n')
                    in_transaction_section = False
                    i = 0
                    
                    while i < len(lines):
                        line = lines[i].strip()
                        
                        # Look for transaction table headers
                        if "Trans Post" in line and i + 1 < len(lines) and "date date Description" in lines[i + 1]:
                            in_transaction_section = True
                            i += 2  # Skip header lines
                            continue
                        
                        # Stop processing when we hit other sections
                        if any(keyword in line for keyword in [
                            "Information about your CIBC", "Payment options", 
                            "Interest charges", "Foreign currency"
                        ]):
                            in_transaction_section = False
                        
                        # Parse transactions if we're in the transaction section
                        if in_transaction_section and self._is_cibc_visa_transaction(line):
                            # Handle multi-line transactions (main line + exchange rate line)
                            transaction, next_i = self._parse_cibc_visa_multiline_transaction(lines, i, page_num)
                            if transaction:
                                transactions.append(transaction)
                            i = next_i
                        else:
                            i += 1
            
            logger.info(f"✅ CIBC Visa: Found {len(transactions)} transactions")
            return transactions
            
        except Exception as e:
            logger.error(f"❌ CIBC Visa processing failed: {e}")
            return []
    
    def _is_cibc_visa_transaction(self, line: str) -> bool:
        """Check if line is a CIBC Visa transaction"""
        # Skip header lines and summaries
        skip_patterns = [
            'trans post', 'date date', 'description', 'amount', 'card number',
            'prepared for', 'account number', 'information about'
        ]
        
        if any(pattern in line.lower() for pattern in skip_patterns):
            return False
        
        # CIBC Visa format: "DEC 28 DEC 29 WWW.ALIEXPRESS.COM LONDON 13.63"
        # Must have dual date pattern (MMM DD) and amount
        has_dual_date = bool(re.search(r'^[A-Z]{3}\s+\d{1,2}\s+[A-Z]{3}\s+\d{1,2}', line))
        has_amount = bool(re.search(r'[\d,]+\.\d{2}$', line))  # Amount at end of line
        
        return has_dual_date and has_amount and len(line) > 20
    
    def _parse_cibc_visa_multiline_transaction(self, lines: List[str], start_idx: int, page_num: int) -> tuple[Optional[Dict[str, Any]], int]:
        """Parse CIBC Visa multi-line transaction (main line + exchange rate line)"""
        line = lines[start_idx].strip()
        
        # Pattern: "DEC 28 DEC 29 WWW.ALIEXPRESS.COM LONDON 13.63"
        # Extract: Trans Date | Post Date | Description | Location | Amount
        pattern = r'^([A-Z]{3}\s+\d{1,2})\s+([A-Z]{3}\s+\d{1,2})\s+(.*?)\s+([\d,]+\.\d{2})$'
        match = re.search(pattern, line)
        
        if not match:
            return None, start_idx + 1
        
        trans_date = match.group(1)  # "DEC 28"
        post_date = match.group(2)   # "DEC 29"
        description_and_location = match.group(3).strip()  # "WWW.ALIEXPRESS.COM LONDON"
        amount = self.clean_amount(match.group(4))  # "13.63"
        
        # Split description and location (location is usually the last word)
        desc_parts = description_and_location.split()
        if len(desc_parts) > 1 and desc_parts[-1].isupper() and len(desc_parts[-1]) > 2:
            # Last part looks like a location (all caps)
            description = ' '.join(desc_parts[:-1])
            location = desc_parts[-1]
        else:
            description = description_and_location
            location = ""
        
        # Convert dates to MM-DD format
        parsed_trans_date = self._parse_cibc_visa_date(trans_date)
        parsed_post_date = self._parse_cibc_visa_date(post_date)
        
        # Skip if we can't parse the date properly
        if parsed_trans_date == "Unknown":
            return None, start_idx + 1
        
        # Check for exchange rate line (next line might contain CAD conversion)
        exchange_rate_info = ""
        cad_amount = None
        next_idx = start_idx + 1
        
        if next_idx < len(lines):
            next_line = lines[next_idx].strip()
            # Look for exchange rate pattern: "18.53 CAD @ 0.735563950**"
            exchange_match = re.search(r'^([\d,]+\.\d{2})\s+CAD\s+@\s+([\d.]+)', next_line)
            if exchange_match:
                cad_amount = self.clean_amount(exchange_match.group(1))
                exchange_rate = exchange_match.group(2)
                exchange_rate_info = f"CAD ${cad_amount} @ {exchange_rate}"
                next_idx += 1  # Skip the exchange rate line
        
        # For credit cards: positive amounts are spending (debits)
        transaction_type = "debit" if amount > 0 else "credit"
        is_spending = amount > 0
        
        transaction = {
            'date': parsed_trans_date,
            'posting_date': parsed_post_date,
            'description': description,
            'location': location,
            'amount': amount,
            'currency': 'USD',
            'cad_amount': cad_amount,
            'exchange_rate_info': exchange_rate_info,
            'page': page_num,
            'bank': self.bank_name,
            'confidence': 0.9,
            'transaction_type': transaction_type,
            'is_spending': is_spending,
            'abs_amount': abs(amount),
            'processing_method': 'cibc_visa_processor',
            'confidence_level': 'high'
        }
        
        return transaction, next_idx
    
    def _parse_cibc_visa_date(self, date_str: str) -> str:
        """Parse CIBC Visa date format 'DEC 28' to MM-DD"""
        try:
            month_map = {
                'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
                'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
                'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
            }
            
            # Handle "DEC 28" format
            parts = date_str.strip().split()
            if len(parts) >= 2:
                month_abbr = parts[0].lower()
                day = parts[1].zfill(2)
                
                if month_abbr in month_map:
                    return f"{month_map[month_abbr]}-{day}"
            
            return "Unknown"
        except:
            return "Unknown"

class BMOAccountProcessor(BankProcessor):
    """BMO Account processor - handles Everyday Banking account statements"""
    
    def __init__(self):
        super().__init__("BMO Account")
    
    def can_process(self, text: str, filename: str) -> bool:
        # Check for BMO Account specific indicators
        bmo_account_indicators = [
            "Your Everyday Banking statement", "Everyday Banking", 
            "Primary Chequing Account", "BMO Bank of Montreal"
        ]
        
        # Must have BMO account indicators
        has_bmo_account = any(indicator in text for indicator in bmo_account_indicators)
        
        # Additional bank account features (adjusted for actual text patterns)
        has_account_features = any(term in text for term in [
            "deducted($)", "added($)", "Opening", "Closing totals", 
            "Primary Chequing", "INTERAC e-Transfer", "Direct Deposit"
        ])
        
        # Ensure it's NOT the existing BMO credit card format (be more specific)
        has_credit_card_features = any(term in text for term in [
            "Previous Balance", "Credit Limit", "Minimum Payment",
            "Payment Due Date", "Interest Rate", "Cash Advance"
        ])
        
        return has_bmo_account and has_account_features and not has_credit_card_features
    
    def extract_transactions(self, pdf_path: str) -> List[Dict[str, Any]]:
        logger.info(f"🏦 Processing BMO Account statement: {pdf_path}")
        transactions = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if not text:
                        continue
                    
                    lines = text.split('\n')
                    in_transaction_section = False
                    
                    for line in lines:
                        line = line.strip()
                        
                        # Look for transaction table headers (can be on separate lines)
                        if ("Date Description" in line) or ("Amountsdeducted" in line):
                            in_transaction_section = True
                            continue
                        
                        # Stop processing when we hit other sections
                        if any(keyword in line for keyword in [
                            "Please report any errors", "Trade-marks", "Important information",
                            "Alternatively, you can bring", "GST-", "QST-"
                        ]):
                            in_transaction_section = False
                            continue
                        
                        # Parse transactions if we're in the transaction section
                        if in_transaction_section and self._is_bmo_account_transaction(line):
                            transaction = self._parse_bmo_account_transaction(line, page_num)
                            if transaction:
                                transactions.append(transaction)
            
            logger.info(f"✅ BMO Account: Found {len(transactions)} transactions")
            return transactions
            
        except Exception as e:
            logger.error(f"❌ BMO Account processing failed: {e}")
            return []
    
    def _is_bmo_account_transaction(self, line: str) -> bool:
        """Check if line is a BMO Account transaction"""
        # Skip header lines and summaries
        skip_patterns = [
            'date description', 'amounts deducted', 'amounts added', 'balance',
            'primary chequing account', 'continued', 'opening balance', 'closing totals'
        ]
        
        if any(pattern in line.lower() for pattern in skip_patterns):
            return False
        
        # BMO Account format: "Nov28 DirectDeposit,RA-GENPAYMENTMSP/DIV 300.62 309.91"
        # Must have date pattern (MMM+DD) and either amounts or balance
        has_date = bool(re.search(r'^[A-Z][a-z]{2}\d{1,2}', line))
        has_amount = bool(re.search(r'[\d,]+\.\d{2}', line))
        
        return has_date and has_amount and len(line) > 10
    
    def _parse_bmo_account_transaction(self, line: str, page_num: int) -> Optional[Dict[str, Any]]:
        """Parse BMO Account transaction line"""
        # Pattern handles formats like:
        # "Nov27 INTERACe-TransferReceived 30.00 9.29"
        # "Nov28 DirectDeposit,RA-GENPAYMENTMSP/DIV 300.62 309.91"
        # "Nov28 INTERACe-TransferSent 205.00 104.91"
        
        # Try to extract date at start
        date_match = re.match(r'^([A-Z][a-z]{2}\d{1,2})', line)
        if not date_match:
            return None
        
        date_str = date_match.group(1)
        rest_of_line = line[len(date_str):].strip()
        
        # Parse the rest: Description and amounts
        # Look for numbers at the end of the line
        amounts = re.findall(r'[\d,]+\.\d{2}', rest_of_line)
        
        if not amounts:
            return None
        
        # Extract description (everything before the amounts)
        desc_part = rest_of_line
        for amount in amounts:
            desc_part = desc_part.replace(amount, '', 1).strip()
        
        # Clean description
        description = desc_part.strip().rstrip(',').strip()
        
        # Determine transaction type and amount based on BMO account format
        # The amounts in BMO account statements can be:
        # - Single amount (either deducted or added)
        # - Two amounts (deducted amount, balance) or (added amount, balance)
        # - Three amounts (deducted, added, balance)
        
        deducted_amount = 0.0
        added_amount = 0.0
        balance = None
        
        if len(amounts) == 1:
            # Single amount - need to determine if it's deducted or added based on context
            amount_val = self.clean_amount(amounts[0])
            balance = amount_val
        elif len(amounts) == 2:
            # Two amounts - usually [transaction_amount, balance]
            transaction_amount = self.clean_amount(amounts[0])
            balance = self.clean_amount(amounts[1])
            
            # Determine if it's deducted or added based on transaction type
            if any(keyword in description.lower() for keyword in [
                'transfersent', 'transfer sent', 'debitcardpurchase', 'debit card purchase', 
                'fee', 'charge', 'returned item', 'overdraft'
            ]):
                deducted_amount = transaction_amount
            else:
                added_amount = transaction_amount
        elif len(amounts) >= 3:
            # Three amounts - [deducted, added, balance] or [transaction, transaction, balance]
            deducted_amount = self.clean_amount(amounts[0])
            added_amount = self.clean_amount(amounts[1])
            balance = self.clean_amount(amounts[2])
        
        # Convert date to MM-DD format
        parsed_date = self._parse_bmo_account_date(date_str)
        
        # Skip if we can't parse the date properly
        if parsed_date == "Unknown":
            return None
        
        # Determine net amount and transaction type
        net_amount = added_amount - deducted_amount
        
        # For bank accounts: negative net = spending (debit), positive net = deposit (credit)
        transaction_type = "debit" if net_amount < 0 else "credit"
        is_spending = net_amount < 0
        
        return {
            'date': parsed_date,
            'description': description,
            'amount': net_amount,
            'deducted_amount': deducted_amount,
            'added_amount': added_amount,
            'balance': balance,
            'page': page_num,
            'bank': self.bank_name,
            'confidence': 0.9,
            'transaction_type': transaction_type,
            'is_spending': is_spending,
            'abs_amount': abs(net_amount),
            'processing_method': 'bmo_account_processor',
            'confidence_level': 'high'
        }
    
    def _parse_bmo_account_date(self, date_str: str) -> str:
        """Parse BMO Account date format 'Nov28' to MM-DD"""
        try:
            month_map = {
                'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
                'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
                'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
            }
            
            # Handle "Nov28" format (month+day without space)
            match = re.match(r'^([A-Z][a-z]{2})(\d{1,2})$', date_str)
            if match:
                month_abbr = match.group(1).lower()
                day = match.group(2).zfill(2)
                
                if month_abbr in month_map:
                    return f"{month_map[month_abbr]}-{day}"
            
            return "Unknown"
        except:
            return "Unknown"

class SmartDocumentProcessor:
    """Intelligent document processor that routes to appropriate bank processor"""
    
    def __init__(self):
        self.processors = [
            BMOAccountProcessor(),  # NEW: BMO Account processor - BEFORE BMOProcessor 
            BMOProcessor(),
            EQBankProcessor(),
            TDProcessor(),
            TDCreditCardProcessor(),  # NEW: TD Credit Card processor
            TangerineProcessor(),
            TangerineCreditCardProcessor(),  # NEW: Tangerine Credit Card processor
            RBCBankProcessor(),
            RBCVisaProcessor(),
            SimpliiProcessor(),  # Put BEFORE CIBC to fix identification issue
            CIBCVisaProcessor(),  # NEW: CIBC Visa Credit Card processor - BEFORE CIBCProcessor
            CIBCProcessor(),
            AmexProcessor(),
            ScotiaBankProcessor(),  # Put BEFORE ScotiaProcessor to prioritize bank over credit card
            ScotiaProcessor(),
            WiseProcessor(),
        ]
    
    def identify_bank(self, pdf_path: str) -> Optional[BankProcessor]:
        """Identify which bank processor should handle this document"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                # Get text from first few pages
                sample_text = ""
                for page in pdf.pages[:3]:
                    text = page.extract_text()
                    if text:
                        sample_text += text + "\n"
                
                filename = os.path.basename(pdf_path)
                
                # Test each processor
                for processor in self.processors:
                    if processor.can_process(sample_text, filename):
                        logger.info(f"🎯 Identified: {processor.bank_name} for {filename}")
                        return processor
                
                logger.warning(f"⚠️ No processor found for: {filename}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Bank identification failed: {e}")
            return None
    
    def process_document(self, pdf_path: str) -> Dict[str, Any]:
        """Process document with appropriate bank processor"""
        processor = self.identify_bank(pdf_path)
        
        if not processor:
            return {
                'processing_method': 'unidentified',
                'transactions': [],
                'confidence': 'low',
                'error': 'No suitable processor found'
            }
        
        try:
            transactions = processor.extract_transactions(pdf_path)
            
            # 🚨 FIXED: Proper bank-specific transaction classification
            for tx in transactions:
                bank_name = tx['bank']
                amount = tx['amount']
                
                # Use processor's classification if already set, otherwise apply default rules
                if 'transaction_type' not in tx or 'is_spending' not in tx:
                    # CORRECTED LOGIC: Bank-specific classification rules
                    if self._is_credit_card_bank(bank_name):
                        # Credit Cards: Positive amounts = spending (debit), Negative = payments (credit)
                        tx['transaction_type'] = 'debit' if amount > 0 else 'credit'
                        tx['is_spending'] = amount > 0
                    else:
                        # Bank Accounts: Negative amounts = spending (debit), Positive = deposits (credit)  
                        tx['transaction_type'] = 'debit' if amount < 0 else 'credit'
                        tx['is_spending'] = amount < 0
                
                # Add standardized fields
                tx['abs_amount'] = abs(amount)
                
                # Add processing metadata
                tx['processing_method'] = f"{bank_name.lower().replace(' ', '_')}_processor"
                tx['confidence_level'] = 'high' if tx.get('confidence', 0) >= 0.9 else 'medium'
            
            # Add enhanced summary counts
            debit_count = sum(1 for tx in transactions if tx['transaction_type'] == 'debit')
            credit_count = sum(1 for tx in transactions if tx['transaction_type'] == 'credit')
            
            return {
                'processing_method': f'{processor.bank_name}_processor',
                'transactions': transactions,
                'confidence': 'high',
                'bank': processor.bank_name,
                'transaction_count': len(transactions),
                'debit_count': debit_count,
                'credit_count': credit_count,
                'spending_transactions': [tx for tx in transactions if tx['is_spending']]
            }
            
        except Exception as e:
            logger.error(f"❌ Processing failed with {processor.bank_name}: {e}")
            return {
                'processing_method': f'{processor.bank_name}_failed',
                'transactions': [],
                'confidence': 'low',
                'error': str(e)
            }
    
    def _is_credit_card_bank(self, bank_name: str) -> bool:
        """Determine if bank is a credit card (vs bank account)"""
        credit_card_banks = [
            'BMO',                    # BMO Credit Card
            'RBC Visa',              # RBC Visa Credit Card
            'Scotia Credit Card',     # Scotia Credit Card
            'Amex',                  # Amex Credit Card
            'Simplii',               # Simplii Credit Card  
            'Wise',                  # Wise Credit Card
            'TD Credit Card',        # TD Credit Card (NEW)
            'Tangerine Credit Card', # Tangerine Credit Card (NEW)
            'CIBC Visa'              # CIBC Visa Credit Card (NEW)
        ]
        return bank_name in credit_card_banks

class TDCreditCardProcessor(BankProcessor):
    """TD Credit Card processor - handles Cash Back Credit Card format"""
    
    def __init__(self):
        super().__init__("TD Credit Card")
    
    def can_process(self, text: str, filename: str) -> bool:
        # Check for TD Credit Card specific indicators
        td_credit_indicators = [
            "TD CASH BACK CARD", "CASH BACK CARD", "TD Credit Card"
        ]
        
        # Must have TD credit card indicators AND be a credit card (not bank statement)
        has_td_credit = any(indicator in text for indicator in td_credit_indicators)
        
        # Additional credit card indicators
        has_credit_card_features = any(term in text for term in [
            "PREVIOUS STATEMENT BALANCE", "Minimum Payment", "Credit Card",
            "ACTIVITY DESCRIPTION", "Cash Back Dollars"
        ])
        
        return has_td_credit and has_credit_card_features
    
    def extract_transactions(self, pdf_path: str) -> List[Dict[str, Any]]:
        logger.info(f"🏦 Processing TD Credit Card statement: {pdf_path}")
        transactions = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if not text:
                        continue
                    
                    lines = text.split('\n')
                    in_transaction_section = False
                    
                    for line in lines:
                        line = line.strip()
                        
                        # Look for transaction table headers
                        if "ACTIVITY DESCRIPTION" in line or "TRANSACTIO" in line:
                            in_transaction_section = True
                            continue
                        
                        # Stop processing when we hit summary sections
                        if any(keyword in line for keyword in [
                            "NET AMOUNT OF MONTHLY", "TOTAL NEW BALANCE", 
                            "CALCULATING YOUR BALANCE", "PAYMENT INFORMATION"
                        ]):
                            in_transaction_section = False
                            continue
                        
                        # Parse transactions if we're in the transaction section
                        if in_transaction_section and self._is_td_credit_transaction(line):
                            transaction = self._parse_td_credit_transaction(line, page_num)
                            if transaction:
                                transactions.append(transaction)
            
            logger.info(f"✅ TD Credit Card: Found {len(transactions)} transactions")
            return transactions
            
        except Exception as e:
            logger.error(f"❌ TD Credit Card processing failed: {e}")
            return []
    
    def _is_td_credit_transaction(self, line: str) -> bool:
        """Check if line is a TD Credit Card transaction"""
        # Skip header lines and summaries
        skip_patterns = [
            'previous statement', 'activity description', 'amount', 'date',
            'continued', 'net amount', 'total', 'balance', 'payment', 'foreign currency',
            '@exchange rate'
        ]
        
        if any(pattern in line.lower() for pattern in skip_patterns):
            return False
        
        # TD Credit Card format: Both "FEB 26 FEB 27" and "FEB26 FEB27" (page 4 condensed format)
        # Must have dual date pattern and amount (including negative amounts)
        has_dual_date = bool(re.search(r'^[A-Z]{3}\s*\d{1,2}\s+[A-Z]{3}\s*\d{1,2}', line))
        has_amount = bool(re.search(r'-?\$[\d,]+\.\d{2}', line))
        
        return has_dual_date and has_amount and len(line) > 15
    
    def _parse_td_credit_transaction(self, line: str, page_num: int) -> Optional[Dict[str, Any]]:
        """Parse TD Credit Card transaction line"""
        # Pattern handles both formats:
        # "FEB 26 FEB 27 DESCRIPTION $1.75" (pages 1-3)
        # "FEB26 FEB27 DESCRIPTION $1.75" (page 4 condensed)
        # Also handles negative amounts: "-$44.00"
        pattern = r'^([A-Z]{3}\s*\d{1,2})\s+([A-Z]{3}\s*\d{1,2})\s+(.*?)\s+(-?\$?[\d,]+\.\d{2})'
        match = re.search(pattern, line)
        
        if not match:
            return None
        
        trans_date = match.group(1)  # "FEB 26" or "FEB26"
        post_date = match.group(2)   # "FEB 27" or "FEB27"
        description = match.group(3).strip()  # "ROBARTS STARBUCKS – UOFT TORONTO"
        amount = self.clean_amount(match.group(4))  # "1.75" or "-44.00"
        
        # Convert dates to MM-DD format
        parsed_trans_date = self._parse_td_credit_date(trans_date)
        parsed_post_date = self._parse_td_credit_date(post_date)
        
        # Skip if we can't parse the date properly
        if parsed_trans_date == "Unknown":
            return None
        
        # For credit cards: positive amounts are spending (debits)
        transaction_type = "debit" if amount > 0 else "credit"
        is_spending = amount > 0
        
        return {
            'date': parsed_trans_date,
            'posting_date': parsed_post_date,
            'description': description,
            'amount': amount,
            'page': page_num,
            'bank': self.bank_name,
            'confidence': 0.9,
            'transaction_type': transaction_type,
            'is_spending': is_spending,
            'abs_amount': abs(amount),
            'processing_method': 'td_credit_card_processor',
            'confidence_level': 'high'
        }
    
    def _parse_td_credit_date(self, date_str: str) -> str:
        """Parse TD Credit Card date format 'FEB 26' or 'FEB26' to MM-DD"""
        try:
            month_map = {
                'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
                'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
                'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
            }
            
            # Handle both "FEB 26" and "FEB26" formats
            date_str = date_str.strip()
            
            # Try "FEB 26" format first (with space)
            parts = date_str.split()
            if len(parts) >= 2:
                month_abbr = parts[0].lower()
                day = parts[1].zfill(2)
                
                if month_abbr in month_map:
                    return f"{month_map[month_abbr]}-{day}"
            
            # Try "FEB26" format (no space) - extract with regex
            match = re.match(r'^([A-Z]{3})(\d{1,2})$', date_str.upper())
            if match:
                month_abbr = match.group(1).lower()
                day = match.group(2).zfill(2)
                
                if month_abbr in month_map:
                    return f"{month_map[month_abbr]}-{day}"
            
            return "Unknown"
        except:
            return "Unknown"

# Test the new processor
if __name__ == "__main__":
    processor = SmartDocumentProcessor()
    
    # Test with multiple files
    test_files = [
        "statements/BMO Credit Card.pdf",
        "statements/EB Bank Statement.pdf",
        "statements/TD-Bank-Statement.pdf",
        "statements/Tangerine Savings Statement.pdf",
        "statements/RBC-Bank-Statement.pdf",
        "statements/RBC-Visa.pdf",
        "statements/CIBC-Bank-Statement.pdf",
        "statements/Simplii Credit Card.pdf",
        "statements/Amex Credit Card.pdf"
    ]
    
    for test_file in test_files:
        if os.path.exists(test_file):
            result = processor.process_document(test_file)
            print(f"\n🎯 Testing {test_file}:")
            print(f"   Method: {result['processing_method']}")
            print(f"   Transactions: {len(result['transactions'])}")
            print(f"   Confidence: {result['confidence']}")
            
            # Show first few transactions
            if result['transactions']:
                print(f"📄 Sample transactions:")
                for i, trans in enumerate(result['transactions'][:2], 1):
                    print(f"   {i}: {trans['date']} - {trans['description']} - ${trans['amount']}")
        else:
            print(f"❌ File not found: {test_file}")
    
    print(f"\n🏦 Total processors: {len(processor.processors)}")
