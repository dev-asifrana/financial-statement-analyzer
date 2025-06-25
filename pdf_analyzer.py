import pdfplumber
import pandas as pd
import re
from typing import List, Dict, Any
import os
from pathlib import Path

class BankStatementAnalyzer:
    def __init__(self):
        self.statements_dir = "statements"
        self.analysis_results = {}
    
    def analyze_all_statements(self):
        """Analyze all PDF statements to understand their structure"""
        print("🔍 Analyzing Bank Statement Structures...\n")
        
        pdf_files = list(Path(self.statements_dir).glob("*.pdf"))
        
        for pdf_file in pdf_files:
            print(f"📄 Analyzing: {pdf_file.name}")
            print("=" * 50)
            
            try:
                analysis = self.analyze_single_pdf(str(pdf_file))
                self.analysis_results[pdf_file.name] = analysis
                self.print_analysis(pdf_file.name, analysis)
                print("\n")
                
            except Exception as e:
                print(f"❌ Error analyzing {pdf_file.name}: {str(e)}\n")
    
    def analyze_single_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """Analyze a single PDF to understand its structure"""
        analysis = {
            'pages': 0,
            'tables_found': [],
            'text_patterns': [],
            'potential_transaction_tables': [],
            'column_structures': [],
            'date_patterns': set(),
            'amount_patterns': set(),
            'sample_rows': []
        }
        
        with pdfplumber.open(pdf_path) as pdf:
            analysis['pages'] = len(pdf.pages)
            
            for page_num, page in enumerate(pdf.pages, 1):
                # Extract text
                text = page.extract_text()
                if text:
                    # Find tables
                    tables = page.extract_tables()
                    if tables:
                        for table_idx, table in enumerate(tables):
                            table_analysis = self.analyze_table(table, page_num, table_idx)
                            analysis['tables_found'].append(table_analysis)
                    
                    # Analyze text patterns
                    patterns = self.analyze_text_patterns(text)
                    analysis['text_patterns'].extend(patterns)
                    
                    # Find date patterns
                    dates = self.find_date_patterns(text)
                    analysis['date_patterns'].update(dates)
                    
                    # Find amount patterns
                    amounts = self.find_amount_patterns(text)
                    analysis['amount_patterns'].update(amounts)
        
        # Identify potential transaction tables
        analysis['potential_transaction_tables'] = self.identify_transaction_tables(analysis['tables_found'])
        
        return analysis
    
    def analyze_table(self, table: List[List[str]], page_num: int, table_idx: int) -> Dict[str, Any]:
        """Analyze a single table structure"""
        if not table or not table[0]:
            return {}
        
        # Clean table data
        cleaned_table = []
        for row in table:
            if row and any(cell and str(cell).strip() for cell in row):
                cleaned_row = [str(cell).strip() if cell else "" for cell in row]
                cleaned_table.append(cleaned_row)
        
        if not cleaned_table:
            return {}
        
        analysis = {
            'page': page_num,
            'table_index': table_idx,
            'rows': len(cleaned_table),
            'columns': len(cleaned_table[0]) if cleaned_table else 0,
            'headers': cleaned_table[0] if cleaned_table else [],
            'sample_rows': cleaned_table[1:4] if len(cleaned_table) > 1 else [],
            'column_types': [],
            'has_dates': False,
            'has_amounts': False,
            'has_descriptions': False,
            'transaction_score': 0
        }
        
        # Analyze column types
        if len(cleaned_table) > 1:
            for col_idx in range(analysis['columns']):
                col_data = [row[col_idx] if col_idx < len(row) else "" for row in cleaned_table[1:6]]
                col_type = self.identify_column_type(col_data)
                analysis['column_types'].append(col_type)
                
                if col_type == 'date':
                    analysis['has_dates'] = True
                    analysis['transaction_score'] += 3
                elif col_type == 'amount':
                    analysis['has_amounts'] = True
                    analysis['transaction_score'] += 3
                elif col_type == 'description':
                    analysis['has_descriptions'] = True
                    analysis['transaction_score'] += 2
        
        # Check headers for transaction indicators
        header_text = ' '.join(analysis['headers']).lower()
        transaction_keywords = ['date', 'transaction', 'description', 'amount', 'debit', 'credit', 'balance']
        for keyword in transaction_keywords:
            if keyword in header_text:
                analysis['transaction_score'] += 1
        
        return analysis
    
    def identify_column_type(self, column_data: List[str]) -> str:
        """Identify the type of data in a column"""
        if not column_data:
            return 'unknown'
        
        # Remove empty cells
        non_empty = [cell for cell in column_data if cell.strip()]
        if not non_empty:
            return 'empty'
        
        date_count = 0
        amount_count = 0
        
        for cell in non_empty[:5]:  # Check first 5 non-empty cells
            if self.is_date(cell):
                date_count += 1
            elif self.is_amount(cell):
                amount_count += 1
        
        if date_count >= len(non_empty) * 0.6:
            return 'date'
        elif amount_count >= len(non_empty) * 0.6:
            return 'amount'
        elif any(len(cell) > 10 for cell in non_empty):
            return 'description'
        else:
            return 'text'
    
    def is_date(self, text: str) -> bool:
        """Check if text looks like a date"""
        date_patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            r'\d{4}[/-]\d{1,2}[/-]\d{1,2}',
            r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}',
            r'\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'
        ]
        
        for pattern in date_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def is_amount(self, text: str) -> bool:
        """Check if text looks like a monetary amount"""
        # Remove common formatting
        cleaned = text.replace(',', '').replace(' ', '')
        
        amount_patterns = [
            r'^\$?\d+\.\d{2}$',
            r'^\$?\d+$',
            r'^\(\$?\d+\.\d{2}\)$',  # Negative amounts in parentheses
            r'^-\$?\d+\.\d{2}$'
        ]
        
        for pattern in amount_patterns:
            if re.match(pattern, cleaned):
                return True
        return False
    
    def analyze_text_patterns(self, text: str) -> List[str]:
        """Analyze text for common patterns"""
        patterns = []
        
        # Look for table-like structures in text
        lines = text.split('\n')
        for line in lines:
            if self.is_date(line) and self.is_amount(line):
                patterns.append('transaction_line')
        
        return patterns
    
    def find_date_patterns(self, text: str) -> set:
        """Find all date patterns in text"""
        patterns = set()
        
        date_regex = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            r'\d{4}[/-]\d{1,2}[/-]\d{1,2}',
            r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}',
        ]
        
        for pattern in date_regex:
            matches = re.findall(pattern, text, re.IGNORECASE)
            patterns.update(matches)
        
        return patterns
    
    def find_amount_patterns(self, text: str) -> set:
        """Find all amount patterns in text"""
        patterns = set()
        
        amount_regex = [
            r'\$\d{1,3}(?:,\d{3})*\.\d{2}',
            r'\$\d+\.\d{2}',
            r'\(\$\d+\.\d{2}\)',
        ]
        
        for pattern in amount_regex:
            matches = re.findall(pattern, text)
            patterns.update(matches)
        
        return patterns
    
    def identify_transaction_tables(self, tables: List[Dict]) -> List[Dict]:
        """Identify which tables likely contain transactions"""
        transaction_tables = []
        
        for table in tables:
            if table.get('transaction_score', 0) >= 5:  # Threshold for transaction tables
                transaction_tables.append(table)
        
        return sorted(transaction_tables, key=lambda x: x.get('transaction_score', 0), reverse=True)
    
    def print_analysis(self, filename: str, analysis: Dict):
        """Print analysis results"""
        print(f"📊 Pages: {analysis['pages']}")
        print(f"📋 Tables Found: {len(analysis['tables_found'])}")
        
        if analysis['potential_transaction_tables']:
            print(f"💳 Transaction Tables: {len(analysis['potential_transaction_tables'])}")
            
            for i, table in enumerate(analysis['potential_transaction_tables'][:2]):  # Show top 2
                print(f"\n  Table {i+1} (Page {table['page']}, Score: {table['transaction_score']}):")
                print(f"    Columns: {table['columns']}")
                print(f"    Headers: {table['headers']}")
                print(f"    Column Types: {table['column_types']}")
                
                if table['sample_rows']:
                    print(f"    Sample Row: {table['sample_rows'][0]}")
        
        if analysis['date_patterns']:
            print(f"📅 Date Patterns Found: {len(analysis['date_patterns'])}")
            sample_dates = list(analysis['date_patterns'])[:3]
            print(f"    Examples: {sample_dates}")
        
        if analysis['amount_patterns']:
            print(f"💰 Amount Patterns Found: {len(analysis['amount_patterns'])}")
            sample_amounts = list(analysis['amount_patterns'])[:3]
            print(f"    Examples: {sample_amounts}")
    
    def generate_summary_report(self):
        """Generate a comprehensive summary of all statements"""
        print("\n" + "="*80)
        print("📋 COMPREHENSIVE ANALYSIS SUMMARY")
        print("="*80)
        
        total_files = len(self.analysis_results)
        total_tables = sum(len(analysis['tables_found']) for analysis in self.analysis_results.values())
        total_transaction_tables = sum(len(analysis['potential_transaction_tables']) for analysis in self.analysis_results.values())
        
        print(f"📊 Total Files Analyzed: {total_files}")
        print(f"📋 Total Tables Found: {total_tables}")
        print(f"💳 Total Transaction Tables: {total_transaction_tables}")
        
        print(f"\n🏦 Bank Statement Formats:")
        for filename, analysis in self.analysis_results.items():
            bank_name = filename.replace('.pdf', '').replace('-', ' ').replace('_', ' ')
            transaction_count = len(analysis['potential_transaction_tables'])
            print(f"  • {bank_name}: {transaction_count} transaction table(s)")
        
        # Analyze common patterns
        all_column_types = []
        all_headers = []
        
        for analysis in self.analysis_results.values():
            for table in analysis['potential_transaction_tables']:
                all_column_types.extend(table['column_types'])
                all_headers.extend([h.lower() for h in table['headers'] if h])
        
        print(f"\n📊 Common Column Types:")
        from collections import Counter
        type_counts = Counter(all_column_types)
        for col_type, count in type_counts.most_common():
            print(f"  • {col_type}: {count} occurrences")
        
        print(f"\n📋 Common Headers:")
        header_counts = Counter(all_headers)
        for header, count in header_counts.most_common(10):
            print(f"  • '{header}': {count} occurrences")


if __name__ == "__main__":
    analyzer = BankStatementAnalyzer()
    analyzer.analyze_all_statements()
    analyzer.generate_summary_report() 