import streamlit as st
import xmlrpc.client
import os
import pandas as pd
import math
from dotenv import load_dotenv
from datetime import datetime

# 1. Load Environment Variables
load_dotenv()

# Get environment variables
ODOO_URL = os.getenv('ODOO_URL')
ODOO_DB = os.getenv('ODOO_DB')
ODOO_USERNAME = os.getenv('ODOO_USERNAME')
ODOO_PASSWORD = os.getenv('ODOO_PASSWORD')
APP_USERNAME = os.getenv('APP_USERNAME')
APP_PASSWORD = os.getenv('APP_PASSWORD')

# --- CONSTANTS ---
SOURCE_STORE_NAME = "Wedtree eStore Private Limited - HO"

# --- SESSION STATE INITIALIZATION ---
def init_session_state():
    """Initialize all session state variables"""
    defaults = {
        'logged_in': False,
        'selected_products': set(),
        'products_df': None,
        'ref_cost_map': {},
        'page_number': 1,
        'results_df': None,
        'last_action': None,
        'login_error': None,
        'uid': None,
        'models': None,
        'companies': [],
        'target_store_id': None,
        'source_store_id': None,
        'target_store_name': '',
        'source_store_name': SOURCE_STORE_NAME # Default to hardcoded value
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# --- CALLBACKS ---
def toggle_selection(product_idx):
    """Callback to handle checkbox toggles efficiently"""
    if product_idx in st.session_state.selected_products:
        st.session_state.selected_products.discard(product_idx)
    else:
        st.session_state.selected_products.add(product_idx)

def on_target_change():
    """Callback to update target store ID when dropdown changes"""
    # 1. Get the new name from the widget key
    new_name = st.session_state.target_store_select
    st.session_state.target_store_name = new_name
    
    # 2. Find and update the ID
    company_map = {c['name']: c['id'] for c in st.session_state.companies}
    if new_name in company_map:
        st.session_state.target_store_id = company_map[new_name]
    
    # 3. Clear existing data since store changed
    st.session_state.products_df = None
    st.session_state.selected_products = set()
    st.session_state.ref_cost_map = {}
    st.session_state.results_df = None
    st.session_state.page_number = 1

# --- CUSTOM CSS FOR ENHANCED UI ---
st.markdown("""
<style>
    /* Main container styling */
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 1rem;
    }
    
    /* Card styling */
    .card {
        background: white;
        border-radius: 12px;
        padding: 1.25rem;
        box-shadow: 0 3px 10px rgba(0, 0, 0, 0.08);
        margin-bottom: 1rem;
        border: 1px solid #e6e6e6;
        transition: all 0.3s ease;
    }
    
    .card:hover {
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
    }
    
    /* Hero/Landing Page Styling */
    .hero-container {
        text-align: center;
        padding: 3rem 1rem;
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        border-radius: 15px;
        margin-bottom: 2rem;
    }
    
    .feature-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid #eee;
        height: 100%;
        text-align: center;
    }
    
    /* Button styling */
    .stButton > button {
        border-radius: 8px;
        padding: 0.5rem 1.25rem;
        font-weight: 500;
        transition: all 0.2s ease;
        border: none;
        font-size: 0.9rem;
    }
    
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 3px 6px rgba(0, 0, 0, 0.15);
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f8f9fa 0%, #ffffff 100%);
        border-right: 1px solid #e9ecef;
    }
    
    /* Store config card */
    .store-config-card {
        background: white;
        border-radius: 10px;
        padding: 1rem;
        border: 1px solid #e9ecef;
        margin: 0.75rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    /* Login container */
    .login-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        padding: 1.5rem;
        color: white;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    /* Product card */
    .product-card {
        border: 1px solid #e9ecef;
        border-radius: 8px;
        padding: 0.9rem;
        margin-bottom: 0.6rem;
        background: white;
        transition: all 0.2s ease;
    }
    
    .product-card:hover {
        border-color: #667eea;
        box-shadow: 0 2px 8px rgba(102, 126, 234, 0.1);
    }
    
    .product-card.selected {
        border-left: 4px solid #28a745;
        background: linear-gradient(to right, #f8fff8, #ffffff);
    }
    
    /* Stats card */
    .stats-card {
        background: white;
        border-radius: 10px;
        padding: 1rem;
        border: 1px solid #e9ecef;
        margin-bottom: 0.75rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        padding: 0 0.25rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 6px;
        padding: 0.6rem 1.2rem;
        font-weight: 500;
        font-size: 0.9rem;
        border: 1px solid #e9ecef;
        background: white;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border-color: #667eea !important;
    }
    
    /* Status badges */
    .status-badge {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 500;
    }
    
    /* Metrics styling */
    [data-testid="stMetricValue"] {
        font-size: 1.4rem;
    }
    
    /* Compact spacing */
    .stColumn {
        padding: 0.25rem;
    }
    
    /* Responsive adjustments */
    @media (max-width: 768px) {
        .stButton > button {
            width: 100%;
            margin-bottom: 0.5rem;
        }
        
        .card {
            padding: 0.9rem;
        }
        
        .main .block-container {
            padding-top: 1rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }
    }
    
    /* Divider styling */
    hr {
        margin: 0.5rem 0;
        border: none;
        height: 1px;
        background: linear-gradient(to right, transparent, #e9ecef, transparent);
    }
</style>
""", unsafe_allow_html=True)

# --- ODOO CONNECTION FUNCTIONS ---
@st.cache_resource
def get_odoo_connection(_uid, _password):
    """Cached connection to Odoo"""
    try:
        common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
        uid = common.authenticate(ODOO_DB, _uid, _password, {})
        models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
        return uid, models
    except Exception as e:
        return None, str(e)

def fetch_companies(uid, models):
    """Fetch companies from Odoo"""
    try:
        ids = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'res.company', 'search', [[]])
        companies = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'res.company', 'read', 
                                     [ids], {'fields': ['id', 'name']})
        return companies
    except Exception as e:
        return []

def fetch_target_products(uid, models, company_id):
    """Fetch products with Cost=0 in the Target Store"""
    domain = [
        ("type", "in", ["consu", "product"]),
        ("standard_price", "=", 0)
    ]
    context = {'allowed_company_ids': [company_id]}
    
    try:
        products = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'product.product', 'search_read', 
                                    [domain], 
                                    {'fields': ['id', 'default_code', 'name', 'standard_price', 'categ_id'], 
                                     'context': context, 
                                     'limit': 10000})
        return products
    except Exception as e:
        st.error(f"Error fetching products: {e}")
        return []

def fetch_reference_costs(uid, models, source_company_id, product_refs, product_names):
    """Fetch reference costs from source store"""
    context = {'allowed_company_ids': [source_company_id]}
    domain = ['|', ('default_code', 'in', product_refs), ('name', 'in', product_names)]
    
    try:
        source_products = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'product.product', 'search_read', 
                                           [domain], 
                                           {'fields': ['default_code', 'name', 'standard_price'], 
                                            'context': context})
        return source_products
    except Exception as e:
        st.error(f"Error fetching reference costs: {e}")
        return []

def update_product_cost(uid, models, product_id, new_cost, company_id):
    """Update product cost in Odoo"""
    try:
        context = {'allowed_company_ids': [company_id]}
        models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'product.product', 'write', 
                         [[product_id], {'standard_price': new_cost}], 
                         {'context': context})
        return True, None
    except Exception as e:
        return False, str(e)

# --- LOGIN FUNCTION ---
def login(username, password):
    """Handle login authentication"""
    if username == APP_USERNAME and password == APP_PASSWORD:
        # Connect to Odoo after app login
        uid, models = get_odoo_connection(ODOO_USERNAME, ODOO_PASSWORD)
        if uid is None:
            return False, "Failed to connect to Odoo. Check credentials."
        
        # Fetch companies
        companies = fetch_companies(uid, models)
        if not companies:
            return False, "No companies found in Odoo"
        
        # Generate Map
        company_map = {c['name']: c['id'] for c in companies}
        
        # FIX: Validate Source Store Exists
        if SOURCE_STORE_NAME not in company_map:
            return False, f"Source Store '{SOURCE_STORE_NAME}' not found in Odoo."
            
        st.session_state.uid = uid
        st.session_state.models = models
        st.session_state.companies = companies
        st.session_state.logged_in = True
        st.session_state.login_error = None
        
        store_names = list(company_map.keys())
        
        # Set Source Store (Hardcoded)
        st.session_state.source_store_name = SOURCE_STORE_NAME
        st.session_state.source_store_id = company_map[SOURCE_STORE_NAME]
        
        # Set Default Target Store (First one that isn't the source)
        available_targets = [name for name in store_names if name != SOURCE_STORE_NAME]
        default_target = available_targets[0] if available_targets else SOURCE_STORE_NAME
        
        st.session_state.target_store_name = default_target
        st.session_state.target_store_id = company_map.get(default_target)
        
        return True, "Login successful"
    else:
        return False, "Invalid username or password"

# --- LOGOUT FUNCTION ---
def logout():
    """Handle logout"""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# --- LANDING PAGE FUNCTION ---
def show_landing_page():
    """Display content for non-logged-in users"""
    st.markdown("""
    <div class="hero-container">
        <h1 style="color: #4a5568; font-size: 2.5rem; margin-bottom: 0.5rem;">🔄 Odoo Cost Sync</h1>
        <p style="font-size: 1.2rem; color: #718096; max-width: 600px; margin: 0 auto;">
            The automated solution for synchronizing standard prices across your Odoo multi-company environment.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Features Grid
    st.markdown("### 🚀 How it works")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="feature-card">
            <div style="font-size: 2rem; margin-bottom: 1rem;">🔍</div>
            <h4 style="margin-bottom: 0.5rem;">Detect Zero Costs</h4>
            <p style="color: #666; font-size: 0.9rem;">
                Instantly scan your target store to find products that are missing standard prices (Cost = 0).
            </p>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown("""
        <div class="feature-card">
            <div style="font-size: 2rem; margin-bottom: 1rem;">📊</div>
            <h4 style="margin-bottom: 0.5rem;">Fetch References</h4>
            <p style="color: #666; font-size: 0.9rem;">
                Automatically lookup the correct cost from your Head Office or Source Store using SKU or Name matching.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
    with col3:
        st.markdown("""
        <div class="feature-card">
            <div style="font-size: 2rem; margin-bottom: 1rem;">⚡</div>
            <h4 style="margin-bottom: 0.5rem;">Bulk Update</h4>
            <p style="color: #666; font-size: 0.9rem;">
                Review the proposed changes and update hundreds of products in Odoo with a single click.
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    
    # Call to Action
    st.markdown("""
    <div style="text-align: center; padding: 2rem; color: #666;">
        <p>👈 <strong>To get started, please log in using the panel on the left.</strong></p>
        <p style="font-size: 0.8rem; margin-top: 1rem;">Ensure you have your Odoo credentials and App password ready.</p>
    </div>
    """, unsafe_allow_html=True)

# --- MAIN APP ---
def main():
    # Initialize session state
    init_session_state()
    
    # Set page config
    st.set_page_config(
        page_title="Odoo Cost Sync",
        page_icon="🔄",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Sidebar
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; margin-bottom: 1.5rem;">
            <h1 style="color: #667eea; font-size: 1.6rem; margin-bottom: 0.25rem;">🔄 Cost Sync</h1>
            <p style="color: #666; font-size: 0.8rem; margin: 0;">Odoo Synchronization Tool</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Login Container
        if not st.session_state.logged_in:
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            st.markdown('<h3 style="color: white; font-size: 1.2rem; margin-bottom: 1rem;">🔐 Login</h3>', unsafe_allow_html=True)
            
            with st.form("login_form", clear_on_submit=False):
                username = st.text_input("Username", placeholder="Enter username", key="login_user")
                password = st.text_input("Password", type="password", placeholder="Enter password", key="login_pass")
                
                col1, col2 = st.columns(2)
                with col1:
                    login_btn = st.form_submit_button("Login", type="primary", width='stretch')
                with col2:
                    if st.form_submit_button("Clear", width='stretch'):
                        st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            if login_btn and username and password:
                success, message = login(username, password)
                if success:
                    st.success("✅ " + message)
                    st.rerun()
                else:
                    st.error("❌ " + message)
                    st.session_state.login_error = message
            
            if st.session_state.login_error:
                st.error(f"**Login Error:** {st.session_state.login_error}")
            
            st.markdown("---")
            st.info("💡 Default credentials are in .env file")
        
        # Logged In View
        else:
            # User Info Card
            st.markdown(f"""
            <div class="card" style="padding: 0.9rem; margin-bottom: 1rem;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <div style="font-size: 1.8rem;">👤</div>
                    <div style="flex: 1;">
                        <div style="font-weight: 600; font-size: 1rem;">{APP_USERNAME}</div>
                        <div style="font-size: 0.75rem; color: #666; margin-top: 2px;">Logged In</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Connection Status
            if st.session_state.uid:
                st.success("✅ **Connected to Odoo**", icon="🔗")
            else:
                st.error("❌ **Not connected to Odoo**", icon="⚠️")
            
            st.markdown("---")
            
            # Store Configuration
            st.markdown("### 🏪 Store Configuration")
            
            if st.session_state.companies:
                company_names = [c['name'] for c in st.session_state.companies]
                
                # 1. Source Store (Static Display)
                st.markdown("**📊 Source Store**")
                st.info(f"{st.session_state.source_store_name}", icon="🏢")
                
                # 2. Target Store (Dropdown with Fixed Callback)
                current_index = 0
                if st.session_state.target_store_name in company_names:
                    current_index = company_names.index(st.session_state.target_store_name)
                
                st.selectbox(
                    "🎯 **Target Store**",
                    options=company_names,
                    index=current_index,
                    key="target_store_select", # Widget key
                    help="Store where products need cost updates",
                    on_change=on_target_change # Dedicated callback
                )
                
                # Store icons / IDs
                col1, col2 = st.columns(2)
                with col1:
                    st.caption(f"Target ID: `{st.session_state.target_store_id or '?'}`")
                with col2:
                    st.caption(f"Source ID: `{st.session_state.source_store_id}`")
            
            st.markdown("---")
            
            # Quick Actions
            st.markdown("### ⚡ Quick Actions")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Refresh Data", width='stretch', help="Clear all data and refresh"):
                    st.session_state.products_df = None
                    st.session_state.selected_products = set()
                    st.session_state.ref_cost_map = {}
                    st.session_state.results_df = None
                    st.session_state.page_number = 1
                    st.rerun()
            
            with col2:
                if st.button("🚪 Logout", width='stretch', type="secondary", help="Logout from the application"):
                    logout()
            
            # Current Stats
            if st.session_state.products_df is not None:
                st.markdown("---")
                st.markdown("### 📊 Current Stats")
                
                selected_count = len(st.session_state.selected_products)
                total_count = len(st.session_state.products_df)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Selected", selected_count)
                with col2:
                    st.metric("Total", total_count)
                
                if selected_count > 0:
                    st.progress(selected_count / max(total_count, 1))
                    st.caption(f"{selected_count} of {total_count} selected")

    # Main content area logic
    if st.session_state.logged_in:
        # Main Header
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("## 🔄 Odoo Cost Synchronizer")
            st.caption(f"Syncing costs from **{st.session_state.source_store_name}** to **{st.session_state.target_store_name}**")
        
        with col2:
            if st.session_state.products_df is not None:
                st.metric("Products Loaded", len(st.session_state.products_df), delta=None)
        
        # Tabs
        tab1, tab2 = st.tabs(["📋 Product Management", "🚀 Sync & Results"])
        
        # TAB 1: PRODUCT MANAGEMENT
        with tab1:
            col1, col2 = st.columns([3, 1])
            
            with col2:
                st.markdown("### Actions")
                
                # Fetch Products Button
                if st.button("🔍 **Fetch Products**", 
                           type="primary", 
                           width='stretch',
                           help=f"Load products from {st.session_state.target_store_name}"):
                    
                    if not st.session_state.target_store_id:
                         st.error("Please select a target store first.")
                    else:
                        with st.spinner(f"Fetching products from {st.session_state.target_store_name} (ID: {st.session_state.target_store_id})..."):
                            products = fetch_target_products(st.session_state.uid, 
                                                           st.session_state.models, 
                                                           st.session_state.target_store_id)
                            if products:
                                df = pd.DataFrame(products)
                                if 'categ_id' in df.columns:
                                    df['category'] = df['categ_id'].apply(
                                        lambda x: x[1] if isinstance(x, list) else ''
                                    )
                                st.session_state.products_df = df
                                st.session_state.selected_products = set()
                                st.session_state.page_number = 1
                                st.success(f"✅ Found {len(df)} products with zero cost")
                            else:
                                st.warning("⚠️ No products found with zero cost")
                
                # Clear Selection Button
                if st.session_state.products_df is not None:
                    if st.button("🗑️ **Clear Selection**", 
                               width='stretch',
                               help="Deselect all products"):
                        st.session_state.selected_products = set()
                        # FIX: Clear checkbox widgets on Deselect All
                        for key in list(st.session_state.keys()):
                            if key.startswith("chk_"):
                                del st.session_state[key]
                        st.rerun()
            
            with col1:
                # Search and Filter
                st.markdown("### Filter Products")
                search_query = st.text_input(
                    "🔍 Search by Name or SKU",
                    placeholder="Type to filter products...",
                    help="Search in product names or SKU codes",
                    label_visibility="collapsed"
                )
                
                # Display products if available
                if st.session_state.products_df is not None:
                    df = st.session_state.products_df
                    
                    # Apply search filter
                    if search_query:
                        filtered_df = df[
                            df['name'].str.contains(search_query, case=False, na=False) |
                            df['default_code'].astype(str).str.contains(search_query, case=False, na=False)
                        ]
                    else:
                        filtered_df = df
                    
                    # Bulk actions row
                    if not filtered_df.empty:
                        col1, col2, col3 = st.columns([1, 1, 2])
                        with col1:
                            if st.button("✅ Select All", width='stretch'):
                                # Update set with all IDs from filtered list
                                st.session_state.selected_products.update(filtered_df.index.tolist())
                                # FIX: Clear widget history so Streamlit respects the new TRUE value
                                for key in list(st.session_state.keys()):
                                    if key.startswith("chk_"):
                                        del st.session_state[key]
                                st.rerun()
                        with col2:
                            if st.button("❌ Deselect All", width='stretch'):
                                # Remove filtered IDs from set
                                st.session_state.selected_products.difference_update(filtered_df.index.tolist())
                                # FIX: Clear widget history so Streamlit respects the new FALSE value
                                for key in list(st.session_state.keys()):
                                    if key.startswith("chk_"):
                                        del st.session_state[key]
                                st.rerun()
                        with col3:
                            st.caption(f"**{len(filtered_df)}** products matched • **{len(st.session_state.selected_products)}** selected")
                    
                    # Pagination
                    if not filtered_df.empty:
                        items_per_page = 20
                        total_pages = max(1, math.ceil(len(filtered_df) / items_per_page))
                        
                        # Pagination controls
                        col1, col2, col3 = st.columns([2, 2, 2])
                        with col1:
                            if st.button("◀ Previous", 
                                       disabled=st.session_state.page_number <= 1, 
                                       width='stretch'):
                                st.session_state.page_number -= 1
                                st.rerun()
                        with col2:
                            current_page = st.session_state.page_number
                            st.markdown(f"**Page {current_page} of {total_pages}**", help=f"Showing {items_per_page} items per page")
                        with col3:
                            if st.button("Next ▶", 
                                       disabled=st.session_state.page_number >= total_pages,
                                       width='stretch'):
                                st.session_state.page_number += 1
                                st.rerun()
                        
                        # Display products for current page
                        start_idx = (st.session_state.page_number - 1) * items_per_page
                        end_idx = min(start_idx + items_per_page, len(filtered_df))
                        display_batch = filtered_df.iloc[start_idx:end_idx]
                        
                        # Product cards
                        st.markdown("---")
                        st.markdown(f"### Selected Products ({len(st.session_state.selected_products)})")
                        
                        for original_idx, row in display_batch.iterrows():
                            # Determine current state
                            is_selected = original_idx in st.session_state.selected_products
                            
                            col1, col2 = st.columns([0.8, 9.2])
                            
                            with col1:
                                st.checkbox(
                                    f"Select {row['name']}",
                                    value=is_selected,
                                    key=f"chk_{original_idx}",
                                    label_visibility="collapsed",
                                    on_change=toggle_selection,
                                    args=(original_idx,)
                                )
                            
                            with col2:
                                category = row.get('category', 'N/A')
                                price = float(row.get('standard_price', 0))
                                
                                st.markdown(f"""
                                <div class="product-card {'selected' if is_selected else ''}">
                                    <div style="font-weight: 600; font-size: 0.95rem; margin-bottom: 0.2rem; color: #333;">
                                        {row['name']}
                                    </div>
                                    <div style="font-size: 0.8rem; color: #666;">
                                        <span style="background: #f0f0f0; padding: 0.1rem 0.4rem; border-radius: 4px; margin-right: 0.5rem;">
                                            SKU: <strong>{row['default_code'] or 'N/A'}</strong>
                                        </span>
                                        <span style="margin-right: 0.5rem;">📁 {category}</span>
                                        <span style="color: #dc3545;">💰 ₹{price:,.2f}</span>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
                    else:
                        st.info("No products match your search criteria.")
                else:
                    st.info("👈 Click 'Fetch Products' to load products from the target store.")
        
        # TAB 2: SYNC & RESULTS
        with tab2:
            if not st.session_state.selected_products:
                st.warning("""
                ⚠️ **No products selected**
                
                Please go to the **Product Management** tab and select products to synchronize.
                """)
            else:
                # Get selected products
                selected_indices = list(st.session_state.selected_products)
                target_batch = st.session_state.products_df.loc[selected_indices]
                
                st.success(f"✅ **{len(target_batch)} products selected** for synchronization")
                
                # Two-step process
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    # Step 1: Fetch Reference Costs
                    st.markdown("### Step 1: Get Reference Costs")
                    
                    if st.button("📥 **Fetch Reference Costs**", 
                               type="primary",
                               width='stretch',
                               help="Get costs from source store"):
                        with st.spinner(f"Fetching costs from {st.session_state.source_store_name}..."):
                            refs = target_batch['default_code'].dropna().unique().tolist()
                            names = target_batch['name'].unique().tolist()
                            
                            ref_data = fetch_reference_costs(st.session_state.uid,
                                                           st.session_state.models,
                                                           st.session_state.source_store_id, 
                                                           refs, names)
                            
                            # Build cost map
                            cost_map = {}
                            for item in ref_data:
                                price = item.get('standard_price', 0.0)
                                if price > 0:
                                    if item.get('default_code'):
                                        cost_map[item['default_code']] = price
                                    cost_map[item['name']] = price
                            
                            st.session_state.ref_cost_map = cost_map
                            
                            # Calculate matches
                            matches = sum(1 for _, row in target_batch.iterrows()
                                        if row['default_code'] in cost_map or row['name'] in cost_map)
                            
                            if matches > 0:
                                st.success(f"✅ Found reference costs for **{matches}** out of **{len(target_batch)}** items")
                            else:
                                st.warning("⚠️ No reference costs found for selected products")
                    
                    # Step 2: Execute Updates
                    if st.session_state.ref_cost_map:
                        st.markdown("---")
                        st.markdown("### Step 2: Execute Updates")
                        
                        if st.button("🚀 **Execute Cost Updates**", 
                                   type="primary",
                                   width='stretch',
                                   key="execute_updates",
                                   help="Apply cost updates to target store"):
                            
                            # Progress tracking
                            progress_bar = st.progress(0)
                            status_text = st.empty()
                            results_container = st.container()
                            
                            total = len(target_batch)
                            results = []
                            
                            with results_container:
                                success = 0
                                fail = 0
                                skip = 0
                                
                                for i, (idx, row) in enumerate(target_batch.iterrows()):
                                    p_ref = row['default_code']
                                    p_name = row['name']
                                    p_id = int(row['id'])
                                    
                                    new_cost = st.session_state.ref_cost_map.get(
                                        p_ref, 
                                        st.session_state.ref_cost_map.get(p_name, 0.0)
                                    )
                                    
                                    if new_cost > 0:
                                        success_flag, error_msg = update_product_cost(
                                            st.session_state.uid,
                                            st.session_state.models,
                                            p_id,
                                            new_cost,
                                            st.session_state.target_store_id
                                        )
                                        
                                        if success_flag:
                                            success += 1
                                            status = "✅ Updated"
                                        else:
                                            fail += 1
                                            status = f"❌ Failed"
                                    else:
                                        skip += 1
                                        status = "⚠️ No Reference"
                                    
                                    results.append({
                                        'Product': p_name[:50] + ("..." if len(p_name) > 50 else ""),
                                        'SKU': p_ref or "N/A",
                                        'New Cost': f"₹{new_cost:,.2f}",
                                        'Status': status
                                    })
                                    
                                    # Update progress
                                    progress = (i + 1) / total
                                    progress_bar.progress(progress)
                                    status_text.text(f"Processing {i+1}/{total}...")
                                
                                # Final results
                                progress_bar.empty()
                                status_text.empty()
                                
                                # Display summary
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("✅ Successful", success, delta=None)
                                with col2:
                                    st.metric("⚠️ Skipped", skip, delta=None)
                                with col3:
                                    st.metric("❌ Failed", fail, delta=None)
                                
                                # Save results
                                st.session_state.results_df = pd.DataFrame(results)
                                st.session_state.last_action = datetime.now()
                
                with col2:
                    st.markdown("### Export")
                    
                    if st.session_state.results_df is not None:
                        st.download_button(
                            label="📥 Download Report",
                            data=st.session_state.results_df.to_csv(index=False).encode('utf-8'),
                            file_name=f"cost_sync_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                            mime="text/csv",
                            width='stretch'
                        )
                    
                    if st.session_state.last_action:
                        st.caption(f"**Last sync:** {st.session_state.last_action.strftime('%H:%M')}")
                
                # Display results table if available
                if st.session_state.results_df is not None:
                    st.markdown("---")
                    st.markdown("### 📊 Update Results")
                    
                    # Display dataframe
                    st.dataframe(
                        st.session_state.results_df,
                        width='stretch',
                        hide_index=True,
                        height=300
                    )
    # Landing page for non-logged in users
    else:
        show_landing_page()

# Run the app
if __name__ == "__main__":
    main()
