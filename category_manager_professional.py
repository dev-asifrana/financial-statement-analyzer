import streamlit as st
import json
import os
from typing import Dict, List, Any
import pandas as pd

class CategoryManager:
    """
    Professional category management system for transaction categorization
    """
    
    def __init__(self, config_file: str = "category_config.json"):
        self.config_file = config_file
        self.categories = self._load_categories()
    
    def _load_categories(self) -> Dict[str, Any]:
        """Load categories from config file or create default"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                st.error(f"Error loading categories: {e}")
                return self._get_default_categories()
        else:
            return self._get_default_categories()
    
    def _get_default_categories(self) -> Dict[str, Any]:
        """Default category structure - professional without emojis"""
        return {
            "food_dining": {
                "name": "Food & Dining",
                "master_category": "Living Expenses",
                "keywords": ["restaurant", "mcdonald", "starbucks", "tim hortons", "subway", "pizza", "coffee", "food", "dining", "cafe", "bistro", "grill", "kitchen", "burger", "taco", "sushi"],
                "color": "#f1416c",
                "icon": "utensils"
            },
            "groceries": {
                "name": "Groceries",
                "master_category": "Essential Expenses",
                "keywords": ["walmart", "superstore", "loblaws", "metro", "sobeys", "costco", "grocery", "supermarket", "food basics", "no frills", "freshco"],
                "color": "#50cd89",
                "icon": "shopping-cart"
            },
            "transportation": {
                "name": "Transportation",
                "master_category": "Essential Expenses",
                "keywords": ["shell", "esso", "petro", "chevron", "gas", "fuel", "gasoline", "station", "pump", "uber", "lyft", "taxi", "transit", "bus", "subway", "train", "parking"],
                "color": "#3699ff",
                "icon": "car"
            },
            "shopping": {
                "name": "Shopping",
                "master_category": "Discretionary Spending",
                "keywords": ["amazon", "target", "best buy", "canadian tire", "home depot", "ikea", "walmart", "shopping", "store", "retail"],
                "color": "#ffc700",
                "icon": "shopping-bag"
            },
            "entertainment": {
                "name": "Entertainment",
                "master_category": "Discretionary Spending",
                "keywords": ["netflix", "spotify", "cinema", "movie", "theater", "entertainment", "gaming", "xbox", "playstation", "steam"],
                "color": "#7239ea",
                "icon": "film"
            },
            "bills_utilities": {
                "name": "Bills & Utilities",
                "master_category": "Fixed Expenses",
                "keywords": ["hydro", "electricity", "gas bill", "water", "internet", "phone", "rogers", "bell", "telus", "utility", "bill"],
                "color": "#009ef7",
                "icon": "file-invoice"
            },
            "healthcare": {
                "name": "Healthcare",
                "master_category": "Essential Expenses",
                "keywords": ["pharmacy", "medical", "doctor", "hospital", "health", "dental", "vision", "prescription", "clinic"],
                "color": "#f64e60",
                "icon": "heartbeat"
            },
            "financial_services": {
                "name": "Financial Services",
                "master_category": "Financial",
                "keywords": ["bank", "atm", "fee", "interest", "transfer", "payment", "financial", "credit", "loan", "mortgage"],
                "color": "#fd7e14",
                "icon": "university"
            },
            "other": {
                "name": "Other",
                "master_category": "Uncategorized",
                "keywords": ["misc", "other", "unknown"],
                "color": "#7e8299",
                "icon": "question"
            }
        }
    
    def save_categories(self):
        """Save categories to config file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.categories, f, indent=2)
            return True
        except Exception as e:
            st.error(f"Error saving categories: {e}")
            return False
    
    def categorize_transaction(self, description: str) -> Dict[str, Any]:
        """Categorize a transaction based on description"""
        description_lower = description.lower()
        
        # Check each category for keyword matches
        for category_id, category_data in self.categories.items():
            for keyword in category_data["keywords"]:
                if keyword.lower() in description_lower:
                    return {
                        "category": category_id,
                        "category_name": category_data["name"],
                        "master_category": category_data["master_category"],
                        "matched_keyword": keyword,
                        "confidence": 0.9,
                        "color": category_data["color"],
                        "icon": category_data["icon"]
                    }
        
        # Default to "other" if no match found
        other_category = self.categories["other"]
        return {
            "category": "other",
            "category_name": other_category["name"],
            "master_category": other_category["master_category"],
            "matched_keyword": "no_match",
            "confidence": 0.1,
            "color": other_category["color"],
            "icon": other_category["icon"]
        }
    
    def get_category_stats(self, transactions_df: pd.DataFrame) -> Dict[str, Any]:
        """Get statistics about category usage"""
        if 'category' not in transactions_df.columns:
            return {}
        
        stats = {}
        for category_id, category_data in self.categories.items():
            category_transactions = transactions_df[transactions_df['category'] == category_data['name']]
            stats[category_id] = {
                'name': category_data['name'],
                'count': len(category_transactions),
                'total': category_transactions['amount_numeric'].sum() if 'amount_numeric' in category_transactions.columns else 0,
                'percentage': (len(category_transactions) / len(transactions_df) * 100) if len(transactions_df) > 0 else 0
            }
        
        return stats
    
    def export_categories(self) -> str:
        """Export categories as JSON string"""
        return json.dumps(self.categories, indent=2)
    
    def import_categories(self, json_data: str) -> bool:
        """Import categories from JSON string"""
        try:
            imported_categories = json.loads(json_data)
            # Validate structure
            for cat_id, cat_data in imported_categories.items():
                required_fields = ["name", "master_category", "keywords", "color", "icon"]
                if not all(field in cat_data for field in required_fields):
                    return False
            
            self.categories = imported_categories
            self.save_categories()
            return True
        except Exception:
            return False 