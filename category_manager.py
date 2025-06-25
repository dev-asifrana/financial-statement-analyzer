import streamlit as st
import json
import os
from typing import Dict, List, Any
import pandas as pd

class CategoryManager:
    """
    Advanced category management system for transaction categorization
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
        """Default category structure"""
        return {
            "food_dining": {
                "name": "Food & Dining",
                "master_category": "Lifestyle",
                "keywords": ["restaurant", "mcdonald", "starbucks", "tim hortons", "subway", "pizza", "coffee", "food", "dining", "cafe", "bistro", "grill", "kitchen", "burger", "taco", "sushi"],
                "color": "#FF6B6B",
                "icon": "🍽️"
            },
            "groceries": {
                "name": "Groceries",
                "master_category": "Essential",
                "keywords": ["walmart", "superstore", "loblaws", "metro", "sobeys", "costco", "grocery", "supermarket", "food basics", "no frills", "freshco"],
                "color": "#4ECDC4",
                "icon": "🛒"
            },
            "gas_fuel": {
                "name": "Gas & Fuel",
                "master_category": "Transportation",
                "keywords": ["shell", "esso", "petro", "chevron", "gas", "fuel", "gasoline", "station", "pump"],
                "color": "#45B7D1",
                "icon": "⛽"
            },
            "shopping": {
                "name": "Shopping",
                "master_category": "Lifestyle",
                "keywords": ["amazon", "target", "best buy", "canadian tire", "home depot", "ikea", "walmart", "shopping", "store", "retail"],
                "color": "#96CEB4",
                "icon": "🛍️"
            },
            "entertainment": {
                "name": "Entertainment",
                "master_category": "Lifestyle",
                "keywords": ["netflix", "spotify", "cinema", "movie", "theater", "entertainment", "gaming", "xbox", "playstation", "steam"],
                "color": "#FFEAA7",
                "icon": "🎬"
            },
            "bills_utilities": {
                "name": "Bills & Utilities",
                "master_category": "Essential",
                "keywords": ["hydro", "electricity", "gas bill", "water", "internet", "phone", "rogers", "bell", "telus", "utility", "bill"],
                "color": "#DDA0DD",
                "icon": "📄"
            },
            "healthcare": {
                "name": "Healthcare",
                "master_category": "Essential",
                "keywords": ["pharmacy", "medical", "doctor", "hospital", "health", "dental", "vision", "prescription", "clinic"],
                "color": "#98D8C8",
                "icon": "🏥"
            },
            "financial_services": {
                "name": "Financial Services",
                "master_category": "Financial",
                "keywords": ["bank", "atm", "fee", "interest", "transfer", "payment", "financial", "credit", "loan", "mortgage"],
                "color": "#F7DC6F",
                "icon": "🏦"
            },
            "transportation": {
                "name": "Transportation",
                "master_category": "Transportation",
                "keywords": ["uber", "lyft", "taxi", "transit", "bus", "subway", "train", "parking", "transport"],
                "color": "#BB8FCE",
                "icon": "🚗"
            },
            "other": {
                "name": "Other",
                "master_category": "Other",
                "keywords": ["misc", "other", "unknown"],
                "color": "#BDC3C7",
                "icon": "❓"
            }
        }
    
    def save_categories(self):
        """Save categories to config file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.categories, f, indent=2)
            st.success("✅ Categories saved successfully!")
        except Exception as e:
            st.error(f"❌ Error saving categories: {e}")
    
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
    
    def render_management_interface(self):
        """Render the category management interface"""
        st.header("🏷️ Category Management")
        
        # Tabs for different management functions
        tab1, tab2, tab3, tab4 = st.tabs(["📋 View Categories", "➕ Add Category", "✏️ Edit Categories", "📊 Statistics"])
        
        with tab1:
            self._render_view_categories()
        
        with tab2:
            self._render_add_category()
        
        with tab3:
            self._render_edit_categories()
        
        with tab4:
            self._render_statistics()
    
    def _render_view_categories(self):
        """Render category viewing interface"""
        st.subheader("Current Categories")
        
        # Group by master category
        master_categories = {}
        for cat_id, cat_data in self.categories.items():
            master = cat_data["master_category"]
            if master not in master_categories:
                master_categories[master] = []
            master_categories[master].append((cat_id, cat_data))
        
        # Display categories grouped by master category
        for master_cat, categories in master_categories.items():
            st.markdown(f"### {master_cat}")
            
            cols = st.columns(3)
            for i, (cat_id, cat_data) in enumerate(categories):
                with cols[i % 3]:
                    with st.container():
                        st.markdown(f"""
                        <div style="background: {cat_data['color']}20; padding: 1rem; border-radius: 10px; border-left: 4px solid {cat_data['color']};">
                            <h4>{cat_data['icon']} {cat_data['name']}</h4>
                            <p><strong>Keywords:</strong> {len(cat_data['keywords'])} items</p>
                            <p><small>{', '.join(cat_data['keywords'][:3])}{'...' if len(cat_data['keywords']) > 3 else ''}</small></p>
                        </div>
                        """, unsafe_allow_html=True)
    
    def _render_add_category(self):
        """Render add category interface"""
        st.subheader("Add New Category")
        
        with st.form("add_category_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                category_name = st.text_input("Category Name", placeholder="e.g., Online Shopping")
                category_icon = st.text_input("Icon (Emoji)", placeholder="🛒", max_chars=2)
                category_color = st.color_picker("Category Color", "#FF6B6B")
            
            with col2:
                master_categories = list(set(cat["master_category"] for cat in self.categories.values()))
                master_category = st.selectbox("Master Category", master_categories + ["Create New"])
                
                if master_category == "Create New":
                    master_category = st.text_input("New Master Category", placeholder="e.g., Entertainment")
            
            keywords_input = st.text_area(
                "Keywords (one per line)", 
                placeholder="amazon\nonline\nshopping\ne-commerce",
                height=100
            )
            
            if st.form_submit_button("➕ Add Category"):
                if category_name and keywords_input:
                    # Generate category ID
                    category_id = category_name.lower().replace(" ", "_").replace("&", "and")
                    
                    # Parse keywords
                    keywords = [kw.strip() for kw in keywords_input.split('\n') if kw.strip()]
                    
                    # Add category
                    self.categories[category_id] = {
                        "name": category_name,
                        "master_category": master_category,
                        "keywords": keywords,
                        "color": category_color,
                        "icon": category_icon or "📁"
                    }
                    
                    self.save_categories()
                    st.rerun()
                else:
                    st.error("Please fill in all required fields")
    
    def _render_edit_categories(self):
        """Render edit categories interface"""
        st.subheader("Edit Existing Categories")
        
        # Select category to edit
        category_options = {f"{cat_data['icon']} {cat_data['name']}": cat_id 
                          for cat_id, cat_data in self.categories.items()}
        
        selected_display = st.selectbox("Select Category to Edit", list(category_options.keys()))
        
        if selected_display:
            selected_id = category_options[selected_display]
            category = self.categories[selected_id]
            
            with st.form(f"edit_category_{selected_id}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    new_name = st.text_input("Category Name", value=category["name"])
                    new_icon = st.text_input("Icon", value=category["icon"])
                    new_color = st.color_picker("Color", value=category["color"])
                
                with col2:
                    master_categories = list(set(cat["master_category"] for cat in self.categories.values()))
                    new_master = st.selectbox("Master Category", master_categories, 
                                            index=master_categories.index(category["master_category"]))
                
                # Keywords editing
                keywords_text = '\n'.join(category["keywords"])
                new_keywords_input = st.text_area("Keywords (one per line)", value=keywords_text, height=150)
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.form_submit_button("💾 Save Changes"):
                        new_keywords = [kw.strip() for kw in new_keywords_input.split('\n') if kw.strip()]
                        
                        self.categories[selected_id] = {
                            "name": new_name,
                            "master_category": new_master,
                            "keywords": new_keywords,
                            "color": new_color,
                            "icon": new_icon
                        }
                        
                        self.save_categories()
                        st.rerun()
                
                with col2:
                    if st.form_submit_button("🗑️ Delete Category", type="secondary"):
                        if selected_id != "other":  # Prevent deleting "other" category
                            del self.categories[selected_id]
                            self.save_categories()
                            st.rerun()
                        else:
                            st.error("Cannot delete the 'Other' category")
                
                with col3:
                    if st.form_submit_button("🔄 Reset to Default"):
                        if st.session_state.get('confirm_reset', False):
                            self.categories = self._get_default_categories()
                            self.save_categories()
                            st.session_state.confirm_reset = False
                            st.rerun()
                        else:
                            st.session_state.confirm_reset = True
                            st.warning("Click again to confirm reset")
    
    def _render_statistics(self):
        """Render category statistics"""
        st.subheader("Category Statistics")
        
        # Calculate statistics
        total_categories = len(self.categories)
        total_keywords = sum(len(cat["keywords"]) for cat in self.categories.values())
        master_category_counts = {}
        
        for cat_data in self.categories.values():
            master = cat_data["master_category"]
            master_category_counts[master] = master_category_counts.get(master, 0) + 1
        
        # Display metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Categories", total_categories)
        
        with col2:
            st.metric("Total Keywords", total_keywords)
        
        with col3:
            st.metric("Master Categories", len(master_category_counts))
        
        # Master category breakdown
        st.subheader("Categories by Master Category")
        
        df = pd.DataFrame([
            {
                "Master Category": master,
                "Categories": count,
                "Percentage": f"{(count/total_categories)*100:.1f}%"
            }
            for master, count in master_category_counts.items()
        ])
        
        st.dataframe(df, use_container_width=True)
        
        # Keywords per category
        st.subheader("Keywords Distribution")
        
        keyword_data = []
        for cat_id, cat_data in self.categories.items():
            keyword_data.append({
                "Category": cat_data["name"],
                "Keywords": len(cat_data["keywords"]),
                "Master Category": cat_data["master_category"]
            })
        
        keyword_df = pd.DataFrame(keyword_data)
        st.bar_chart(keyword_df.set_index("Category")["Keywords"])
    
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


# Integration with existing AI categorizer
class AICategorizer:
    """Updated AI categorizer using the category manager"""
    
    def __init__(self):
        self.category_manager = CategoryManager()
        self.categories = self.category_manager.categories
    
    def categorize_transaction(self, description: str) -> Dict[str, Any]:
        """Categorize transaction using the category manager"""
        return self.category_manager.categorize_transaction(description) 