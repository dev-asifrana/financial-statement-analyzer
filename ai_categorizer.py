import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
import streamlit as st
from sklearn.metrics.pairwise import cosine_similarity

class AICategorizer:
    def __init__(self):
        # Initialize the model (will download on first use)
        self.model = None
        self.category_embeddings = None
        
        # Enhanced category mapping with more keywords
        self.categories = {
            'Food & Dining': {
                'keywords': [
                    # Restaurants & Fast Food
                    'mcdonalds', 'mcdonald', 'subway', 'kfc', 'pizza', 'dominos', 'tim hortons', 'tims', 
                    'starbucks', 'burger king', 'wendy', 'taco bell', 'arby', 'dunkin',
                    # Grocery Stores  
                    'sobeys', 'loblaws', 'metro', 'walmart', 'costco', 'safeway', 'iga', 'foodland',
                    'grocery', 'supermarket', 'market', 'foodmart', 'food', 'restaurant', 'cafe',
                    'bakery', 'deli', 'bistro', 'grill', 'dining', 'eatery', 'kitchen', 'bar',
                    # Convenience Stores
                    'hasty market', 'circle k', '7-eleven', 'quickie', 'convenience', 'corner store'
                ],
                'description': 'restaurants, cafes, fast food, groceries, convenience stores, dining, food delivery',
                'master_category': 'Living Expenses'
            },
            'Transportation': {
                'keywords': [
                    # Gas Stations
                    'shell', 'exxon', 'bp', 'chevron', 'mobil', 'texaco', 'sunoco', 'esso', 'petro',
                    'gas', 'fuel', 'gasoline', 'costco gas', 'canadian tire gas',
                    # Transportation Services
                    'uber', 'lyft', 'taxi', 'cab', 'metro', 'bus', 'train', 'transit', 'parking',
                    'go train', 'ttc', 'presto', 'transport', 'rideshare'
                ],
                'description': 'gas stations, fuel, rideshare, taxi, public transport, parking fees, automotive',
                'master_category': 'Living Expenses'
            },
            'Shopping': {
                'keywords': [
                    # Department Stores
                    'walmart', 'target', 'amazon', 'costco', 'bestbuy', 'future shop', 'staples',
                    'canadian tire', 'home depot', 'lowes', 'ikea', 'bed bath', 'winners',
                    # Specialty Stores
                    'dollarama', 'dollar tree', 'giant tiger', 'shoppers drug mart', 'rexall',
                    'michaels', 'hobby lobby', 'sport chek', 'marks', 'old navy', 'gap',
                    'store', 'shop', 'retail', 'mall', 'plaza', 'electronics', 'clothing',
                    'department', 'warehouse', 'outlet', 'boutique'
                ],
                'description': 'retail stores, department stores, electronics, clothing, home goods, specialty shops',
                'master_category': 'Living Expenses'
            },
            'Bills & Utilities': {
                'keywords': [
                    'hydro', 'electric', 'electricity', 'power', 'gas bill', 'water', 'sewer',
                    'internet', 'phone', 'cell', 'mobile', 'cable', 'satellite', 'rogers',
                    'bell', 'telus', 'shaw', 'cogeco', 'utility', 'utilities', 'enbridge',
                    'toronto hydro', 'bc hydro', 'ontario hydro'
                ],
                'description': 'electricity, water, gas, internet, phone bills, cable, utilities, telecom',
                'master_category': 'Fixed Expenses'
            },
            'Healthcare': {
                'keywords': [
                    'pharmacy', 'shoppers drug', 'rexall', 'cvs', 'walgreens', 'london drugs',
                    'doctor', 'medical', 'hospital', 'clinic', 'dental', 'dentist', 'optical',
                    'health', 'wellness', 'physio', 'therapy', 'prescription', 'medicine',
                    'urgent care', 'walk-in', 'family practice'
                ],
                'description': 'pharmacies, doctors, hospitals, dental, medical services, prescriptions',
                'master_category': 'Living Expenses'
            },
            'Entertainment': {
                'keywords': [
                    'netflix', 'spotify', 'apple music', 'youtube', 'disney', 'hulu', 'prime video',
                    'movie', 'cinema', 'theater', 'theatre', 'concert', 'game', 'gaming',
                    'xbox', 'playstation', 'steam', 'entertainment', 'recreation', 'leisure',
                    'gym', 'fitness', 'sports', 'club', 'membership'
                ],
                'description': 'streaming services, movies, concerts, gaming, fitness, entertainment venues',
                'master_category': 'Discretionary'
            },
            'Cannabis': {
                'keywords': [
                    'cannabis', 'thc', 'cbd', 'marijuana', 'weed', 'dispensary', 'pot', 'hunny pot',
                    'tokyo smoke', 'meta cannabis', 'fire flower', 'canopy', 'aurora'
                ],
                'description': 'cannabis dispensaries, marijuana products, recreational cannabis',
                'master_category': 'Discretionary'
            },
            'ATM/Cash': {
                'keywords': [
                    'atm', 'cash withdrawal', 'withdrawal', 'cash advance', 'interac', 'cash back',
                    'bank machine', 'instant teller'
                ],
                'description': 'ATM withdrawals, cash advances, cash back, banking transactions',
                'master_category': 'Cash'
            },
            'Financial Services': {
                'keywords': [
                    'bank', 'fee', 'interest', 'transfer', 'payment', 'credit', 'loan', 'mortgage',
                    'insurance', 'investment', 'bmo', 'rbc', 'td bank', 'scotia', 'cibc',
                    'mastercard', 'visa', 'amex', 'paypal', 'etransfer'
                ],
                'description': 'banking fees, interest charges, loan payments, financial services, insurance',
                'master_category': 'Financial'
            },
            'Other': {
                'keywords': [],
                'description': 'uncategorized transactions',
                'master_category': 'Uncategorized'
            }
        }
    
    @st.cache_resource
    def load_model(_self):
        """Load the sentence transformer model (cached)"""
        with st.spinner("Loading AI model (one-time download)..."):
            model = SentenceTransformer('all-MiniLM-L6-v2')
            return model
    
    def initialize_embeddings(self):
        """Initialize category embeddings"""
        if self.model is None:
            self.model = self.load_model()
        
        if self.category_embeddings is None:
            descriptions = [cat['description'] for cat in self.categories.values()]
            self.category_embeddings = self.model.encode(descriptions)
    
    def keyword_match(self, description):
        """Enhanced keyword matching with fuzzy matching"""
        description_lower = description.lower().strip()
        
        # Remove common location suffixes for better matching
        description_clean = description_lower
        location_suffixes = ['on', 'ontario', 'canada', 'inc', 'ltd', 'corp']
        for suffix in location_suffixes:
            description_clean = description_clean.replace(f' {suffix}', '')
        
        best_match = {'category': None, 'confidence': 0, 'keyword': ''}
        
        for category, data in self.categories.items():
            for keyword in data['keywords']:
                keyword_lower = keyword.lower()
                
                # Exact match (highest confidence)
                if keyword_lower == description_clean:
                    return {
                        'category': category,
                        'confidence': 1.0,
                        'method': 'keyword_exact',
                        'matched_keyword': keyword
                    }
                
                # Contains match
                if keyword_lower in description_clean:
                    confidence = len(keyword_lower) / len(description_clean)  # Longer matches = higher confidence
                    if confidence > best_match['confidence']:
                        best_match = {
                            'category': category,
                            'confidence': min(0.9, confidence * 1.2),  # Cap at 0.9 for contains matches
                            'keyword': keyword
                        }
                
                # Partial word match (for brand names)
                words = description_clean.split()
                for word in words:
                    if keyword_lower in word or word in keyword_lower:
                        if len(word) > 3 and len(keyword_lower) > 3:  # Only for meaningful words
                            confidence = 0.7
                            if confidence > best_match['confidence']:
                                best_match = {
                                    'category': category,
                                    'confidence': confidence,
                                    'keyword': keyword
                                }
        
        if best_match['category']:
            return {
                'category': best_match['category'],
                'confidence': best_match['confidence'],
                'method': 'keyword',
                'matched_keyword': best_match['keyword']
            }
        
        return None
    
    def ai_categorize(self, description):
        """AI-based categorization using semantic similarity"""
        self.initialize_embeddings()
        
        # Get embedding for the description
        desc_embedding = self.model.encode([description])
        
        # Calculate similarities
        similarities = cosine_similarity(desc_embedding, self.category_embeddings)[0]
        
        # Get best match
        best_idx = np.argmax(similarities)
        best_score = similarities[best_idx]
        category_names = list(self.categories.keys())
        best_category = category_names[best_idx]
        
        return {
            'category': best_category,
            'confidence': float(best_score),
            'method': 'ai',
            'matched_keyword': 'AI semantic match'
        }
    
    def categorize_transaction(self, description):
        """Hybrid categorization: keywords first, then AI"""
        # Try keyword matching first (fast)
        keyword_result = self.keyword_match(description)
        if keyword_result:
            return keyword_result
        
        # Fallback to AI categorization
        ai_result = self.ai_categorize(description)
        
        # Only use AI result if confidence is reasonable
        if ai_result['confidence'] > 0.3:
            return ai_result
        
        # Default fallback
        return {
            'category': 'Other',
            'confidence': 0.0,
            'method': 'default',
            'matched_keyword': 'No match found'
        }
    
    def categorize_dataframe(self, df):
        """Categorize all transactions in DataFrame"""
        if df.empty:
            return df
        
        results = []
        progress_bar = st.progress(0)
        
        for i, (_, row) in enumerate(df.iterrows()):
            result = self.categorize_transaction(row['Description'])
            
            new_row = row.to_dict()
            new_row.update({
                'Matched_Keyword': result['matched_keyword'],
                'Detailed_Category': result['category'],
                'Master_Category': self.categories[result['category']]['master_category'],
                'Confidence': result['confidence'],
                'Method': result['method']
            })
            results.append(new_row)
            
            # Update progress
            progress_bar.progress((i + 1) / len(df))
        
        progress_bar.empty()
        return pd.DataFrame(results) 