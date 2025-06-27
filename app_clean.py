import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
from datetime import datetime, timedelta
import numpy as np

# Import our processors and categorization
from smart_document_processor_v2 import SmartDocumentProcessor

# Page Configuration
st.set_page_config(
    page_title="Statement Breakdown Tool",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for clean, professional design
st.markdown("""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global Styles */
    .main {
        padding: 0;
        background-color: #f8fafc;
        min-height: 100vh;
        font-family: 'Inter', sans-serif;
    }
    
    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}
    
    /* Override Streamlit default styles */
    .stApp {
        background-color: #f8fafc;
        font-family: 'Inter', sans-serif;
    }
    
    /* Sidebar styling - Dark theme */
    section[data-testid="stSidebar"] {
        background: #1a202c !important;
        border-right: 1px solid #2d3748;
        width: 350px !important;
    }
    
    section[data-testid="stSidebar"] > div {
        background: transparent;
        padding: 0 !important;
    }
    
    /* Logo section - no padding */
    .sidebar-logo {
        text-align: center;
        padding: 0;
        margin-bottom: 2rem;
    }
    
    /* Sidebar text styling */
    section[data-testid="stSidebar"] {
        font-family: 'Inter', sans-serif !important;
    }
    
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] div:not([data-testid="stFileUploader"]),
    section[data-testid="stSidebar"] span:not([data-testid="stFileUploader"] span) {
        color: #e2e8f0;
    }
    
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #ffffff !important;
        font-weight: 600;
        margin: 0 0 1rem 0 !important;
    }
    
    /* Navigation styling */
    section[data-testid="stSidebar"] .stRadio > div {
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
    }
    
    section[data-testid="stSidebar"] .stRadio label {
        background: rgba(255,255,255,0.05) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 8px !important;
        padding: 12px 16px !important;
        margin: 4px 0 !important;
        cursor: pointer !important;
        transition: all 0.2s ease !important;
        font-weight: 500 !important;
    }
    
    section[data-testid="stSidebar"] .stRadio label:hover {
        background: rgba(255,255,255,0.1) !important;
        border-color: rgba(255,255,255,0.3) !important;
    }
    
    section[data-testid="stSidebar"] .stRadio input:checked + label {
        background: #3182ce !important;
        border-color: #3182ce !important;
        color: #ffffff !important;
    }
    

    
    section[data-testid="stSidebar"] [data-testid="stFileUploader"] {
        background: white !important;
        border: 2px dashed #cbd5e0 !important;
        border-radius: 8px !important;
        padding: 1rem !important;
        text-align: center !important;
    }
    
    section[data-testid="stSidebar"] [data-testid="stFileUploader"]:hover {
        border-color: #3182ce !important;
        background: #f7fafc !important;
    }
    
    section[data-testid="stSidebar"] [data-testid="stFileUploader"] label {
        color: #2d3748 !important;
        font-weight: 500 !important;
    }
    
    section[data-testid="stSidebar"] [data-testid="stFileUploader"] div {
        color: #4a5568 !important;
    }
    
    section[data-testid="stSidebar"] [data-testid="stFileUploader"] span {
        color: #4a5568 !important;
    }
    
    section[data-testid="stSidebar"] [data-testid="stFileUploader"] p {
        color: #4a5568 !important;
    }
    
    section[data-testid="stSidebar"] [data-testid="stFileUploader"] small {
        color: #718096 !important;
    }
    
    /* Primary button styling */
    section[data-testid="stSidebar"] button[data-testid="baseButton-primary"] {
        background: linear-gradient(135deg, #3182ce 0%, #2c5aa0 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 1rem 1.5rem !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 12px rgba(49, 130, 206, 0.3) !important;
        margin-top: 1rem !important;
    }
    
    section[data-testid="stSidebar"] button[data-testid="baseButton-primary"]:hover {
        background: linear-gradient(135deg, #2c5aa0 0%, #2a4a7c 100%) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 20px rgba(49, 130, 206, 0.5) !important;
    }
    
    section[data-testid="stSidebar"] button[data-testid="baseButton-primary"]:active {
        transform: translateY(0px) !important;
        box-shadow: 0 2px 8px rgba(49, 130, 206, 0.3) !important;
    }
    
    /* Section headers in sidebar */
    .sidebar-section {
        padding: 0 1rem;
        margin: 0.5rem 0;
    }
    
    .sidebar-section:first-of-type {
        border-top: 1px solid #2d3748;
        padding-top: 1rem;
    }
    
    .sidebar-section h3 {
        color: #a0aec0 !important;
        font-size: 0.75rem !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        margin-bottom: 1rem !important;
    }
    
    /* Main content area */
    .main-content {
        max-width: 1400px;
        margin: 0 auto;
        padding: 2rem;
    }
    
    /* Page header */
    .page-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 16px;
        padding: 3rem 2rem;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
    }
    
    .page-header h1 {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0 0 0.5rem 0;
        color: white !important;
    }
    
    .page-header p {
        font-size: 1.125rem;
        opacity: 0.9;
        margin: 0;
        color: white !important;
    }
    
    /* Dashboard cards */
    .dashboard-cards {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: 1.5rem;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: white;
        border-radius: 16px;
        padding: 2rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        border: 1px solid #e2e8f0;
        transition: all 0.2s ease;
        cursor: pointer;
    }
    
    .metric-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 32px rgba(0,0,0,0.12);
        border-color: #3182ce;
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1a202c;
        margin-bottom: 0.5rem;
    }
    
    .metric-label {
        font-size: 0.875rem;
        color: #718096;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .metric-icon {
        width: 48px;
        height: 48px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.5rem;
        margin-bottom: 1rem;
    }
    
    .metric-icon.blue { background: #ebf8ff; color: #3182ce; }
    .metric-icon.green { background: #f0fff4; color: #38a169; }
    .metric-icon.purple { background: #faf5ff; color: #805ad5; }
    .metric-icon.orange { background: #fffaf0; color: #dd6b20; }
    
    /* Custom tabs */
    .custom-tabs {
        background: white;
        border-radius: 16px;
        padding: 0.5rem;
        margin-bottom: 2rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        border: 1px solid #e2e8f0;
    }
    
    .tab-list {
        display: flex;
        gap: 0.5rem;
    }
    
    .tab-button {
        flex: 1;
        padding: 1rem 1.5rem;
        background: transparent;
        border: none;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.875rem;
        cursor: pointer;
        transition: all 0.2s ease;
        color: #718096;
    }
    
    .tab-button:hover {
        background: #f7fafc;
        color: #4a5568;
    }
    
    .tab-button.active {
        background: #3182ce;
        color: white;
        box-shadow: 0 4px 12px rgba(49, 130, 206, 0.3);
    }
    
    /* Content sections */
    .content-section {
        background: white;
        border-radius: 16px;
        padding: 2rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        border: 1px solid #e2e8f0;
        margin-bottom: 2rem;
    }
    
    .section-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #1a202c;
        margin-bottom: 1.5rem;
    }
    
    /* Chart containers */
    .chart-container {
        background: white;
        border-radius: 16px;
        padding: 2rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        border: 1px solid #e2e8f0;
        margin-bottom: 2rem;
    }
    
    /* Table styling */
    .stDataFrame {
        border-radius: 12px !important;
        overflow: hidden !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important;
        border: 1px solid #e2e8f0 !important;
    }
    
    /* Welcome section */
    .welcome-section {
        text-align: center;
        padding: 4rem 2rem;
        background: white;
        border-radius: 16px;
        border: 2px dashed #cbd5e0;
        margin: 2rem 0;
    }
    
    .welcome-icon {
        font-size: 4rem;
        color: #cbd5e0;
        margin-bottom: 1.5rem;
    }
    
    .welcome-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: #1a202c;
        margin-bottom: 0.5rem;
    }
    
    .welcome-subtitle {
        color: #718096;
        font-size: 1rem;
        line-height: 1.6;
    }
    
    /* Responsive design */
    @media (max-width: 768px) {
        .main {
            padding: 1rem;
        }
        
        .dashboard-cards {
            grid-template-columns: 1fr;
        }
        
        .page-header {
            padding: 2rem 1rem;
        }
        
        .page-header h1 {
            font-size: 2rem;
        }
        
        .tab-list {
            flex-direction: column;
        }
    }
</style>
""", unsafe_allow_html=True)

# Load spending plan
def load_spending_plan():
    """Load the spending plan configuration"""
    if os.path.exists('spending_plan.json'):
        with open('spending_plan.json', 'r') as f:
            return json.load(f)
    return {}

def save_spending_plan(plan):
    """Save the spending plan configuration"""
    with open('spending_plan.json', 'w') as f:
        json.dump(plan, f, indent=2)

def format_currency(amount):
    """Format amount as currency"""
    return f"${amount:,.2f}"

def create_header():
    """Create the page header"""
    st.markdown("""
    <div class="main-content">
        <div class="page-header">
            <h1>Statement Breakdown Tool</h1>
            <p>Professional Canadian bank statement processing and analysis</p>
        </div>
    </div>
    """, unsafe_allow_html=True)



def create_dashboard_cards(transactions_df):
    """Create modern dashboard metric cards"""
    if transactions_df.empty:
        st.markdown("""
        <div class="dashboard-cards">
            <div class="metric-card" onclick="document.querySelector('[data-testid=\\"stTabs\\"] button:nth-child(3)').click()">
                <div class="metric-icon blue"></div>
                <div class="metric-value">0</div>
                <div class="metric-label">Total Transactions</div>
            </div>
            <div class="metric-card" onclick="document.querySelector('[data-testid=\\"stTabs\\"] button:nth-child(2)').click()">
                <div class="metric-icon green"></div>
                <div class="metric-value">$0.00</div>
                <div class="metric-label">Total Spending</div>
            </div>
            <div class="metric-card" onclick="document.querySelector('[data-testid=\\"stTabs\\"] button:nth-child(4)').click()">
                <div class="metric-icon orange"></div>
                <div class="metric-value">0</div>
                <div class="metric-label">Categories</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Calculate metrics
    total_transactions = len(transactions_df)
    
    # Handle different possible column names
    if 'is_spending' in transactions_df.columns:
        spending_transactions = transactions_df[transactions_df['is_spending'] == True]
    else:
        # Assume all transactions with positive amounts are spending
        spending_transactions = transactions_df[transactions_df.get('amount', 0) > 0]
    
    if 'abs_amount' in transactions_df.columns:
        total_spending = spending_transactions['abs_amount'].sum()
    elif 'amount' in transactions_df.columns:
        total_spending = spending_transactions['amount'].abs().sum()
    else:
        total_spending = 0
    

    
    # Count categories
    category_col = None
    for col in ['category', 'Detailed_Category', 'Category']:
        if col in spending_transactions.columns:
            category_col = col
            break
    
    unique_categories = len(spending_transactions[category_col].unique()) if category_col and not spending_transactions.empty else 0
    
    # Display metrics
    st.markdown(f"""
    <div class="dashboard-cards">
        <div class="metric-card" onclick="document.querySelector('[data-testid=\\"stTabs\\"] button:nth-child(3)').click()">
            <div class="metric-icon blue"></div>
            <div class="metric-value">{total_transactions:,}</div>
            <div class="metric-label">Total Transactions</div>
        </div>
        <div class="metric-card" onclick="document.querySelector('[data-testid=\\"stTabs\\"] button:nth-child(2)').click()">
            <div class="metric-icon green"></div>
            <div class="metric-value">{format_currency(total_spending)}</div>
            <div class="metric-label">Total Spending</div>
        </div>
        <div class="metric-card" onclick="document.querySelector('[data-testid=\\"stTabs\\"] button:nth-child(4)').click()">
            <div class="metric-icon orange"></div>
            <div class="metric-value">{unique_categories}</div>
            <div class="metric-label">Categories</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def create_spending_overview_chart(transactions_df):
    """Create spending overview chart"""
    if transactions_df.empty:
        st.info("Upload bank statements to see spending analysis")
        return
    
    # Handle different possible column names
    if 'is_spending' in transactions_df.columns:
        spending_df = transactions_df[transactions_df['is_spending'] == True].copy()
    else:
        # Assume all transactions with positive amounts are spending
        spending_df = transactions_df[transactions_df.get('amount', 0) > 0].copy()
    
    if spending_df.empty:
        st.info("No spending transactions found")
        return
    
    # Find the category column
    category_col = None
    for col in ['category', 'Detailed_Category', 'Category']:
        if col in spending_df.columns:
            category_col = col
            break
    
    if not category_col:
        st.info("No category information found")
        return
    
    # Find the amount column
    amount_col = None
    if 'abs_amount' in spending_df.columns:
        amount_col = 'abs_amount'
    elif 'amount' in spending_df.columns:
        amount_col = 'amount'
        spending_df[amount_col] = spending_df[amount_col].abs()
    else:
        st.info("No amount information found")
        return
    
    # Group by category
    category_spending = spending_df.groupby(category_col)[amount_col].sum().sort_values(ascending=False)
    
    # Create donut chart
    fig = go.Figure(data=[go.Pie(
        labels=category_spending.index,
        values=category_spending.values,
        hole=.4,
        textinfo='label+percent',
        textposition='outside',
        marker=dict(
            colors=px.colors.qualitative.Set3,
            line=dict(color='white', width=2)
        )
    )])
    
    fig.update_layout(
        title=dict(
            text="Spending by Category",
            font=dict(size=18, color='#1f2937'),
            x=0.5
        ),
        font=dict(family="Inter, sans-serif"),
        showlegend=False,
        height=400,
        margin=dict(t=60, b=20, l=20, r=20),
        paper_bgcolor='white',
        plot_bgcolor='white'
    )
    
    st.plotly_chart(fig, use_container_width=True)

def create_monthly_trend_chart(transactions_df, spending_plan):
    """Create monthly spending trend chart"""
    if transactions_df.empty:
        return
    
    # Handle different possible column names for spending identification
    if 'is_spending' in transactions_df.columns:
        spending_df = transactions_df[transactions_df['is_spending'] == True].copy()
    else:
        # Assume all transactions with positive amounts are spending
        spending_df = transactions_df[transactions_df.get('amount', 0) > 0].copy()
    
    if spending_df.empty:
        return
    
    # Find date column and convert dates
    date_col = None
    for col in ['date', 'Date', 'transaction_date']:
        if col in spending_df.columns:
            date_col = col
            break
    
    if not date_col:
        return
    
    try:
        spending_df['parsed_date'] = pd.to_datetime(spending_df[date_col], errors='coerce')
        spending_df['month'] = spending_df['parsed_date'].dt.month
    except:
        return
    
    # Find amount column
    amount_col = None
    if 'abs_amount' in spending_df.columns:
        amount_col = 'abs_amount'
    elif 'amount' in spending_df.columns:
        amount_col = 'amount'
        spending_df[amount_col] = spending_df[amount_col].abs()
    else:
        return
    
    monthly_spending = spending_df.groupby('month')[amount_col].sum().reset_index()
    monthly_spending['month_name'] = monthly_spending['month'].apply(
        lambda x: datetime(2023, x, 1).strftime('%B')
    )
    
    # Calculate budget line (if available)
    total_budget = sum(spending_plan.values()) if spending_plan else 0
    
    fig = go.Figure()
    
    # Add spending line
    fig.add_trace(go.Scatter(
        x=monthly_spending['month_name'],
        y=monthly_spending[amount_col],
        mode='lines+markers',
        name='Actual Spending',
        line=dict(color='#3b82f6', width=3),
        marker=dict(size=8, color='#3b82f6')
    ))
    
    # Add budget line if available
    if total_budget > 0:
        fig.add_hline(
            y=total_budget,
            line_dash="dash",
            line_color="#ef4444",
            annotation_text=f"Budget: {format_currency(total_budget)}"
        )
    
    fig.update_layout(
        title=dict(
            text="Monthly Spending Trend",
            font=dict(size=18, color='#1f2937'),
            x=0.5
        ),
        xaxis_title="Month",
        yaxis_title="Amount ($)",
        font=dict(family="Inter, sans-serif"),
        height=400,
        margin=dict(t=60, b=60, l=60, r=20),
        paper_bgcolor='white',
        plot_bgcolor='white',
        showlegend=True
    )
    
    fig.update_layout(
        xaxis=dict(showgrid=True, gridwidth=1, gridcolor='#f3f4f6'),
        yaxis=dict(showgrid=True, gridwidth=1, gridcolor='#f3f4f6')
    )
    
    st.plotly_chart(fig, use_container_width=True)

def create_category_breakdown_table(transactions_df, spending_plan):
    """Create detailed category breakdown table"""
    if transactions_df.empty:
        return
    
    # Handle different possible column names for spending identification
    if 'is_spending' in transactions_df.columns:
        spending_df = transactions_df[transactions_df['is_spending'] == True].copy()
    else:
        # Assume all transactions with positive amounts are spending
        spending_df = transactions_df[transactions_df.get('amount', 0) > 0].copy()
    
    if spending_df.empty:
        return
    
    # Find the category column
    category_col = None
    for col in ['category', 'Detailed_Category', 'Category']:
        if col in spending_df.columns:
            category_col = col
            break
    
    if not category_col:
        return
    
    # Find the amount column
    amount_col = None
    if 'abs_amount' in spending_df.columns:
        amount_col = 'abs_amount'
    elif 'amount' in spending_df.columns:
        amount_col = 'amount'
        spending_df[amount_col] = spending_df[amount_col].abs()
    else:
        return
    
    # Group by category
    category_stats = spending_df.groupby(category_col).agg({
        amount_col: ['sum', 'count', 'mean']
    }).round(2)
    
    category_stats.columns = ['Total', 'Transactions', 'Average']
    category_stats = category_stats.sort_values('Total', ascending=False)
    
    st.markdown("""
    <div class="content-card">
        <div class="card-header">
            <h3 class="card-title">Category Breakdown</h3>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Display as styled dataframe
    st.dataframe(
        category_stats,
        use_container_width=True,
        column_config={
            "Total": st.column_config.NumberColumn(
                "Total Spent",
                format="$%.2f"
            ),
            "Average": st.column_config.NumberColumn(
                "Avg per Transaction",
                format="$%.2f"
            )
        }
    )




def create_sidebar():
    """Create the sidebar with logo and navigation"""
    with st.sidebar:
        # Logo section
        st.markdown('<div class="sidebar-logo">', unsafe_allow_html=True)
        
        if os.path.exists('assets/logo.png'):
            st.image('assets/logo.png', width=250)
        else:
            st.markdown("### Financial Analyzer")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Navigation
        st.markdown("""
        <div class="sidebar-section">
            <h3>Navigation</h3>
        </div>
        """, unsafe_allow_html=True)
        
        page = st.radio(
            "",
            ["Dashboard", "Category Management"],
            label_visibility="collapsed"
        )
        
        # Document Upload Section
        st.markdown("""
        <div class="sidebar-section">
            <h3>Upload Documents</h3>
        </div>
        """, unsafe_allow_html=True)
        
        uploaded_files = st.file_uploader(
            "",
            type=['pdf'],
            accept_multiple_files=True,
            help="Upload bank statement PDFs"
        )
        
        if uploaded_files:
            st.success(f"{len(uploaded_files)} files ready for processing")
            
            if st.button("Process Documents", type="primary", use_container_width=True):
                process_uploaded_files(uploaded_files)
        
        return page

def process_uploaded_files(uploaded_files):
    """Process uploaded files and categorize transactions"""
    processor = SmartDocumentProcessor()
    
    # Use CategoryManager for categorization (managed categories)
    if 'category_manager' not in st.session_state:
        st.session_state.category_manager = CategoryManager()
    category_manager = st.session_state.category_manager
    
    all_transactions = []
    processing_results = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, uploaded_file in enumerate(uploaded_files):
        status_text.text(f"Processing {uploaded_file.name}...")
        
        # Save uploaded file temporarily
        temp_path = f"temp_{uploaded_file.name}"
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.read())
        
        try:
            # Process the document
            result = processor.process_document(temp_path)
            
            if result and 'transactions' in result:
                transactions = result['transactions']
                
                # Categorize transactions using CategoryManager
                transactions_df = pd.DataFrame(transactions)
                
                # Ensure required column exists for categorization
                if 'description' in transactions_df.columns:
                    description_col = 'description'
                elif 'Description' in transactions_df.columns:
                    description_col = 'Description'
                elif 'desc' in transactions_df.columns:
                    description_col = 'desc'
                elif 'transaction_description' in transactions_df.columns:
                    description_col = 'transaction_description'
                else:
                    description_col = transactions_df.columns[0]  # fallback to first column
                
                # Apply categorization using CategoryManager
                categorized_rows = []
                for _, row in transactions_df.iterrows():
                    row_dict = row.to_dict()
                    description = str(row_dict.get(description_col, ''))
                    
                    # Get categorization from CategoryManager
                    cat_result = category_manager.categorize_transaction(description)
                    
                    # Add categorization fields to transaction
                    row_dict['category'] = cat_result['category']
                    row_dict['category_name'] = cat_result['category_name']
                    row_dict['master_category'] = cat_result['master_category']
                    row_dict['matched_keyword'] = cat_result['matched_keyword']
                    row_dict['confidence'] = cat_result['confidence']
                    row_dict['category_color'] = cat_result['color']
                    row_dict['category_icon'] = cat_result['icon']
                    
                    # Ensure Description column exists for display
                    if 'Description' not in row_dict:
                        row_dict['Description'] = description
                    
                    categorized_rows.append(row_dict)
                
                categorized_transactions = categorized_rows
                
                all_transactions.extend(categorized_transactions)
                
                processing_results.append({
                    'filename': uploaded_file.name,
                    'bank': result.get('bank', 'Unknown'),
                    'transactions': len(transactions),
                    'status': 'Success'
                })
            else:
                processing_results.append({
                    'filename': uploaded_file.name,
                    'bank': 'Unknown',
                    'transactions': 0,
                    'status': 'Failed'
                })
        
        except Exception as e:
            processing_results.append({
                'filename': uploaded_file.name,
                'bank': 'Unknown',
                'transactions': 0,
                'status': f'Error: {str(e)}'
            })
        
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
        progress_bar.progress((i + 1) / len(uploaded_files))
    
    progress_bar.empty()
    status_text.empty()
    
    # Store results in session state
    if all_transactions:
        st.session_state.transactions = pd.DataFrame(all_transactions)
        st.session_state.processing_results = processing_results
        st.success(f"Successfully processed {len(all_transactions)} transactions!")
    else:
        st.error("No transactions were extracted from the uploaded files.")

def main():
    """Main application"""
    # Initialize session state
    if 'transactions' not in st.session_state:
        st.session_state.transactions = pd.DataFrame()
    if 'processing_results' not in st.session_state:
        st.session_state.processing_results = []
    
    # Create sidebar and get selected page
    selected_page = create_sidebar()
    
    # Create header
    create_header()
    
    # Route to appropriate page
    if selected_page == "Dashboard":
        dashboard_page()
    elif selected_page == "Category Management":
        category_management_page()

def category_management_page():
    """Category Management page with proper categories and subcategories"""
    st.markdown("""
    <div class="main-content">
        <div class="content-section">
            <div class="section-title">Transaction Category Management</div>
            <p>Manage categories, subcategories, keywords, and rules for transaction classification</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize category manager
    if 'category_manager' not in st.session_state:
        st.session_state.category_manager = CategoryManager()
    
    category_manager = st.session_state.category_manager
    
    # Tabs for different management functions
    tab1, tab2, tab3, tab4 = st.tabs(["View Categories", "Add Category", "Edit Categories", "Statistics"])
    
    with tab1:
        render_view_categories(category_manager)
    
    with tab2:
        render_add_category(category_manager)
    
    with tab3:
        render_edit_categories(category_manager)
    
    with tab4:
        render_statistics(category_manager)

class CategoryManager:
    """Advanced category management system for transaction categorization"""
    
    def __init__(self, config_file: str = "category_config.json"):
        self.config_file = config_file
        self.categories = self._load_categories()
    
    def _load_categories(self):
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
    
    def _get_default_categories(self):
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
            st.success("Categories saved successfully!")
        except Exception as e:
            st.error(f"Error saving categories: {e}")
    
    def categorize_transaction(self, description: str):
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

def render_view_categories(category_manager):
    """Render category viewing interface"""
    st.markdown("""
    <div class="content-section">
        <div class="section-title">Current Categories</div>
        <p>Categories grouped by master category with keywords and styling</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Group by master category
    master_categories = {}
    for cat_id, cat_data in category_manager.categories.items():
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
                st.markdown(f"""
                <div class="content-section" style="background: {cat_data['color']}20; border-left: 4px solid {cat_data['color']};">
                    <h4 style="margin-top: 0;">{cat_data['icon']} {cat_data['name']}</h4>
                    <p><strong>Keywords:</strong> {len(cat_data['keywords'])} items</p>
                    <p><small>{', '.join(cat_data['keywords'][:3])}{'...' if len(cat_data['keywords']) > 3 else ''}</small></p>
                </div>
                """, unsafe_allow_html=True)

def render_add_category(category_manager):
    """Render add category interface"""
    st.markdown("""
    <div class="content-section">
        <div class="section-title">Add New Category</div>
        <p>Create a new category with keywords for transaction matching</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("add_category_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            category_name = st.text_input("Category Name", placeholder="e.g., Online Shopping")
            category_icon = st.text_input("Icon (Emoji)", placeholder="🛒", max_chars=2)
            category_color = st.color_picker("Category Color", "#FF6B6B")
        
        with col2:
            master_categories = list(set(cat["master_category"] for cat in category_manager.categories.values()))
            master_category = st.selectbox("Master Category", master_categories + ["Create New"])
            
            if master_category == "Create New":
                master_category = st.text_input("New Master Category", placeholder="e.g., Entertainment")
        
        keywords_input = st.text_area(
            "Keywords (one per line)", 
            placeholder="amazon\nonline\nshopping\ne-commerce",
            height=100,
            help="Enter keywords that will be used to match transactions to this category"
        )
        
        if st.form_submit_button("Add Category", type="primary", use_container_width=True):
            if category_name and keywords_input:
                # Generate category ID
                category_id = category_name.lower().replace(" ", "_").replace("&", "and")
                
                # Parse keywords
                keywords = [kw.strip() for kw in keywords_input.split('\n') if kw.strip()]
                
                # Add category
                category_manager.categories[category_id] = {
                    "name": category_name,
                    "master_category": master_category,
                    "keywords": keywords,
                    "color": category_color,
                    "icon": category_icon or "📁"
                }
                
                category_manager.save_categories()
                st.rerun()
            else:
                st.error("Please fill in all required fields")

def render_edit_categories(category_manager):
    """Render edit categories interface"""
    st.markdown("""
    <div class="content-section">
        <div class="section-title">Edit Existing Categories</div>
        <p>Modify category properties, keywords, and settings</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Select category to edit
    category_options = {f"{cat_data['icon']} {cat_data['name']}": cat_id 
                      for cat_id, cat_data in category_manager.categories.items()}
    
    selected_display = st.selectbox("Select Category to Edit", list(category_options.keys()))
    
    if selected_display:
        selected_id = category_options[selected_display]
        category = category_manager.categories[selected_id]
        
        with st.form(f"edit_category_{selected_id}"):
            col1, col2 = st.columns(2)
            
            with col1:
                new_name = st.text_input("Category Name", value=category["name"])
                new_icon = st.text_input("Icon", value=category["icon"])
                new_color = st.color_picker("Color", value=category["color"])
            
            with col2:
                master_categories = list(set(cat["master_category"] for cat in category_manager.categories.values()))
                current_index = master_categories.index(category["master_category"]) if category["master_category"] in master_categories else 0
                new_master = st.selectbox("Master Category", master_categories, index=current_index)
            
            # Keywords editing
            keywords_text = '\n'.join(category["keywords"])
            new_keywords_input = st.text_area("Keywords (one per line)", value=keywords_text, height=150)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.form_submit_button("Save Changes", type="primary"):
                    new_keywords = [kw.strip() for kw in new_keywords_input.split('\n') if kw.strip()]
                    
                    category_manager.categories[selected_id] = {
                        "name": new_name,
                        "master_category": new_master,
                        "keywords": new_keywords,
                        "color": new_color,
                        "icon": new_icon
                    }
                    
                    category_manager.save_categories()
                    st.rerun()
            
            with col2:
                if st.form_submit_button("Delete Category"):
                    if selected_id != "other":  # Prevent deleting "other" category
                        del category_manager.categories[selected_id]
                        category_manager.save_categories()
                        st.rerun()
                    else:
                        st.error("Cannot delete the 'Other' category")
            
            with col3:
                if st.form_submit_button("Reset to Default"):
                    if st.session_state.get('confirm_reset', False):
                        category_manager.categories = category_manager._get_default_categories()
                        category_manager.save_categories()
                        st.session_state.confirm_reset = False
                        st.rerun()
                    else:
                        st.session_state.confirm_reset = True
                        st.warning("Click again to confirm reset")

def render_statistics(category_manager):
    """Render category statistics"""
    st.markdown("""
    <div class="content-section">
        <div class="section-title">Category Statistics</div>
        <p>Overview of your category system</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Calculate statistics
    total_categories = len(category_manager.categories)
    total_keywords = sum(len(cat["keywords"]) for cat in category_manager.categories.values())
    master_category_counts = {}
    
    for cat_data in category_manager.categories.values():
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
    st.markdown("### Categories by Master Category")
    
    df = pd.DataFrame([
        {
            "Master Category": master,
            "Categories": count,
            "Percentage": f"{(count/total_categories)*100:.1f}%"
        }
        for master, count in master_category_counts.items()
    ])
    
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Keywords per category
    st.markdown("### Keywords Distribution")
    
    keyword_data = []
    for cat_id, cat_data in category_manager.categories.items():
        keyword_data.append({
            "Category": cat_data["name"],
            "Keywords": len(cat_data["keywords"]),
            "Master Category": cat_data["master_category"]
        })
    
    keyword_df = pd.DataFrame(keyword_data)
    st.bar_chart(keyword_df.set_index("Category")["Keywords"])

def dashboard_page():
    """Dashboard page with tabs"""
    transactions_df = st.session_state.transactions
    
    # Show metrics cards
    create_dashboard_cards(transactions_df)
    
    if not transactions_df.empty:
        # Create tabs
        tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Charts", "Transactions", "Reports"])
        
        with tab1:
            show_overview_tab(transactions_df)
        
        with tab2:
            show_charts_tab(transactions_df)
        
        with tab3:
            show_transactions_tab(transactions_df)
        
        with tab4:
            show_reports_tab(transactions_df)
    else:
        show_welcome_screen()

def show_overview_tab(transactions_df):
    """Show overview information"""
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="content-section">
            <div class="section-title">Quick Summary</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Show processing results if available
        if st.session_state.processing_results:
            results_df = pd.DataFrame(st.session_state.processing_results)
            st.dataframe(results_df, use_container_width=True, hide_index=True)
    
    with col2:
        st.markdown("""
        <div class="content-section">
            <div class="section-title">Recent Activity</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Show recent transactions
        if not transactions_df.empty:
            recent_transactions = transactions_df.head(10)
            if 'Description' in recent_transactions.columns:
                display_cols = ['Description']
                if 'amount' in recent_transactions.columns:
                    display_cols.append('amount')
                elif 'abs_amount' in recent_transactions.columns:
                    display_cols.append('abs_amount')
                
                st.dataframe(recent_transactions[display_cols], use_container_width=True, hide_index=True)

def show_charts_tab(transactions_df):
    """Show charts and visualizations"""
    spending_plan = load_spending_plan()
    
    # Main charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="chart-container">
        """, unsafe_allow_html=True)
        create_spending_overview_chart(transactions_df)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="chart-container">
        """, unsafe_allow_html=True)
        create_monthly_trend_chart(transactions_df, spending_plan)
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Advanced analytics section
    st.markdown("""
    <div class="content-section">
        <div class="section-title">Advanced Analytics</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Detailed breakdown
    create_category_breakdown_table(transactions_df, spending_plan)

def show_transactions_tab(transactions_df):
    """Show detailed transactions table"""
    st.markdown("""
    <div class="content-section">
        <div class="section-title">All Transactions</div>
    </div>
    """, unsafe_allow_html=True)
    
    if not transactions_df.empty:
        st.dataframe(transactions_df, use_container_width=True, hide_index=True)
    else:
        st.info("No transactions available")

def show_reports_tab(transactions_df):
    """Show detailed reports and analysis"""
    st.markdown("""
    <div class="content-section">
        <div class="section-title">Financial Analysis Report</div>
    </div>
    """, unsafe_allow_html=True)
    
    spending_plan = load_spending_plan()
    create_category_breakdown_table(transactions_df, spending_plan)

def show_welcome_screen():
    """Show welcome screen when no data is available"""
    st.markdown("""
    <div class="welcome-section">
        <div class="welcome-title">Welcome to Statement Breakdown Tool</div>
        <div class="welcome-subtitle">Upload your bank statements using the sidebar to get started with professional financial analysis</div>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main() 