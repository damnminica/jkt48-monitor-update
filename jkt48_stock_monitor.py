"""
JKT48 Stock Monitor - Streamlit App
Auto-monitor stock changes with Telegram notifications
Optimized version with WIB timezone only
"""

import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, timedelta
import json
import plotly.express as px
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import pytz
import locale
import os

# Constants
WIB = pytz.timezone('Asia/Jakarta')
TELEGRAM_BOT_TOKEN = "8541605155:AAFlFyF1g2DkW-ZonmX2H_7S-k67n3JKjWE"
TELEGRAM_CHAT_ID = "824000905"

# Helper Functions
def format_event_date(api_date_str):
    """Convert API date (YYYY-MM-DD) to display format with +1 day offset
    Returns: 'Jumat, 09 Mei 2026' format
    """
    try:
        # Parse API date and add 1 day
        date_obj = datetime.strptime(api_date_str, '%Y-%m-%d') + timedelta(days=1)
        
        # Set locale for Indonesian day/month names
        try:
            locale.setlocale(locale.LC_TIME, 'id_ID.UTF-8')
        except:
            pass  # Fallback to English if Indonesian locale not available
        
        # Format: "Jumat, 09 Mei 2026"
        return date_obj.strftime("%A, %d %B %Y")
    except:
        return api_date_str

def get_adjusted_event_date(api_date_str):
    """Get event date with +1 day offset in YYYY-MM-DD format"""
    try:
        date_obj = datetime.strptime(api_date_str, '%Y-%m-%d') + timedelta(days=1)
        return date_obj.strftime('%Y-%m-%d')
    except:
        return api_date_str

def now_wib():
    """Get current time in WIB"""
    return datetime.now(WIB)

def format_timestamp_wib(timestamp_str):
    """Convert any timestamp to WIB format"""
    try:
        if isinstance(timestamp_str, str):
            if 'T' in timestamp_str:
                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            else:
                dt = datetime.fromisoformat(timestamp_str)
            
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=pytz.UTC)
            
            wib_dt = dt.astimezone(WIB)
            return wib_dt.strftime("%d/%m/%Y %H:%M:%S")
        return str(timestamp_str)
    except:
        return str(timestamp_str)

# Telegram notification
def send_telegram_notification(message):
    """Send notification to Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, data=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        st.error(f"Telegram error: {e}")
        return False

# API and Data Functions
API_ENDPOINTS = {
    "We Are Love, Dream, Passion on Fire": "https://jkt48.com/api/v1/exclusives/EXBE10?lang=id"
}

PREVIOUS_DATA_FILE = "/mnt/user-data/outputs/previous_data.json"

def load_data_from_worker():
    """Load data from background worker's saved file"""
    try:
        if os.path.exists(PREVIOUS_DATA_FILE):
            with open(PREVIOUS_DATA_FILE, 'r') as f:
                data = json.load(f)
                # Check if file was updated recently (within last 2 minutes)
                mtime = os.path.getmtime(PREVIOUS_DATA_FILE)
                seconds_ago = time.time() - mtime
                
                if seconds_ago < 120:  # Less than 2 minutes old
                    return data
                else:
                    st.warning(f"⚠️ Background worker data is {int(seconds_ago)}s old. Worker might be stopped.")
                    return data
        else:
            st.info(f"ℹ️ Worker file not found at: {PREVIOUS_DATA_FILE}")
            st.info("Background worker is probably still starting. First fetch takes ~30 seconds.")
            return None
    except json.JSONDecodeError as e:
        st.error(f"Error parsing worker data: {e}")
        return None
    except Exception as e:
        st.error(f"Error loading worker data: {e}")
        return None

# Member-Team Mapping
MEMBER_TEAM_MAP = {
    # LOVE Team (15 members)
    'Fiony Alveria Tantri': 'LOVE',
    'Michelle Alexandra Lim': 'LOVE',
    'Cathleen Nixie': 'LOVE',
    'Cornelia Vanisa': 'LOVE',
    'Jesslyn Callista Yolanda': 'LOVE',
    'Flora Shafiq': 'LOVE',
    'Yessica Tamara': 'LOVE',
    'Erika Ebisawa Kuswan': 'LOVE',
    'Indira Seruni': 'LOVE',
    'Lulu Salsabila': 'LOVE',
    'Olla Mulyani Cipta': 'LOVE',
    'Gita Sekar Andarini': 'LOVE',
    'Marsha Lenathea': 'LOVE',
    'Christy Aurora': 'LOVE',
    'Shani Indira Natio': 'LOVE',
    
    # PASSION Team (15 members)
    'Jessica Chandra': 'PASSION',
    'Mutiara Azzahra': 'PASSION',
    'Desy Natalia': 'PASSION',
    'Feni Fitriyanti': 'PASSION',
    'Jesslyn Elly': 'PASSION',
    'Fiony Alveria': 'PASSION',
    'Febriola Sinambela': 'PASSION',
    'Angelina Christy': 'PASSION',
    'Azizi Asadel': 'PASSION',
    'Adzana Shaliha': 'PASSION',
    'Zee JKT48': 'PASSION',
    'Indah Cahya': 'PASSION',
    'Kathrina Irene': 'PASSION',
    'Ella Adila': 'PASSION',
    'Amanda Sukma Mulyana': 'PASSION',
    
    # DREAM Team (14 members)
    'Marsha Lenathea Lapian': 'DREAM',
    'Freya Jayawardana': 'DREAM',
    'Febriola Sinambela': 'DREAM',
    'Angelina Christy': 'DREAM',
    'Greesel Saskia': 'DREAM',
    'Gabriela Abigail': 'DREAM',
    'Cornelia Vanisa Marentek': 'DREAM',
    'Indah Cahya Nabila': 'DREAM',
    'Adzana Shaliha Herdina': 'DREAM',
    'Shani Indira Natio Tumpuan': 'DREAM',
    'Kathrina Irene Indarto Putri': 'DREAM',
    'Raisha Syifa Firdausi': 'DREAM',
    'Amanda Sukma': 'DREAM',
    'Olla Mulyani': 'DREAM',
    
    # TRAINEE (19 members)
    'Jemima': 'TRAINEE',
    'Nur Intan Permata Sari': 'TRAINEE',
    'Ribka Budiman': 'TRAINEE',
    'Humaira Ramadhani': 'TRAINEE',
    'Victoria Kimberly': 'TRAINEE',
    'Raisha Syifa': 'TRAINEE',
    'Dena Natalia': 'TRAINEE',
    'Lana': 'TRAINEE',
    'Putry Jaszyta': 'TRAINEE',
    'Nayla': 'TRAINEE',
    'Heidi Suyangga': 'TRAINEE',
    'Fahira Putri': 'TRAINEE',
    'Afera Thalia': 'TRAINEE',
    'Fatimah Azzahra': 'TRAINEE',
    'Nathalieya Erwina': 'TRAINEE',
    'Nadhifa Salsabila': 'TRAINEE',
    'Delynn Eryka': 'TRAINEE',
    'Chelsea': 'TRAINEE',
    'Alya': 'TRAINEE',
}

TEAM_COLORS = {
    'LOVE': '#FF69B4',      # Pink
    'PASSION': '#FF4500',   # Orange Red
    'DREAM': '#9370DB',     # Purple
    'TRAINEE': '#FFD700',   # Gold
}

def fetch_data():
    """Fetch data from JKT48 API with retry logic"""
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            response = requests.get(
                list(API_ENDPOINTS.values())[0],
                timeout=15,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                    'Accept': 'application/json',
                    'Referer': 'https://jkt48.com/exclusive'
                }
            )
            
            # Check for HTML response (waiting room)
            content_type = response.headers.get('Content-Type', '')
            if 'text/html' in content_type:
                if attempt < max_retries - 1:
                    st.warning(f"⚠️ Cloudflare waiting room detected. Retrying in {retry_delay}s... (Attempt {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                    continue
                else:
                    st.error("❌ Cloudflare waiting room active. Please wait a few minutes and refresh.")
                    return None
            
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') and data.get('data'):
                return data['data']
            else:
                st.error(f"⚠️ API returned invalid data structure")
                return None
                
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                st.warning(f"⏱️ Request timeout. Retrying... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
                continue
            else:
                st.error("❌ Connection timeout. Please check your internet connection.")
                return None
                
        except requests.exceptions.HTTPError as e:
            st.error(f"❌ HTTP Error {e.response.status_code}: {e}")
            return None
            
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                st.warning(f"🔄 Connection error. Retrying... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
                continue
            else:
                st.error(f"❌ Network error: {e}")
                return None
                
        except json.JSONDecodeError:
            st.error("❌ Invalid JSON response from API")
            return None
            
        except Exception as e:
            st.error(f"❌ Unexpected error: {e}")
            return None
    
    return None

def process_data(data):
    """Process API data into dataframe with adjusted dates"""
    if not data:
        return pd.DataFrame()
    
    rows = []
    for session in data.get('session', []):
        # Get original date and adjust (+1 day)
        original_date = session.get('date', '')
        adjusted_date = get_adjusted_event_date(original_date)
        formatted_date = format_event_date(original_date)
        
        for detail in session.get('detail', []):
            member_name = detail.get('jkt48_member_name', 'Unknown')
            team = MEMBER_TEAM_MAP.get(member_name, 'Unknown')
            
            tickets_sold = detail.get('tickets_sold', 0)
            total_quota = detail.get('total_quota', 0)
            available_quota = detail.get('available_quota', 0)
            
            # Determine status
            if available_quota == 0:
                status = 'Sold Out'
            elif available_quota <= total_quota * 0.2:
                status = 'Low Stock'
            else:
                status = 'Available'
            
            sold_percentage = (tickets_sold / total_quota * 100) if total_quota > 0 else 0
            
            rows.append({
                'Session': session['label'],
                'Date': adjusted_date,  # YYYY-MM-DD format for filtering
                'Date_Display': formatted_date,  # Display format
                'Time': f"{session['start_time']} - {session['end_time']}",
                'Lane': detail['label'],
                'Member': member_name,
                'Team': team,
                'Tickets Sold': tickets_sold,
                'Available': available_quota,
                'Total': total_quota,
                'Sold %': round(sold_percentage, 2),
                'Status': status
            })
    
    return pd.DataFrame(rows)

# Configure page
st.set_page_config(
    page_title="JKT48 Stock Monitor",
    page_icon="🎵",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        color: #FF1493;
        margin-bottom: 1rem;
    }
    .subtitle {
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header">🎵 JKT48 Stock Monitor</div>', unsafe_allow_html=True)

# Initialize session state
if 'data' not in st.session_state:
    st.session_state.data = None
if 'last_update' not in st.session_state:
    st.session_state.last_update = None
if 'notifications_enabled' not in st.session_state:
    st.session_state.notifications_enabled = False
if 'previous_data' not in st.session_state:
    st.session_state.previous_data = None
if 'changes' not in st.session_state:
    st.session_state.changes = []

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    
    # Event Selection (simplified - only one event)
    st.subheader("📅 Event")
    st.info("Monitoring: **We Are Love, Dream, Passion on Fire**")
    
    # Telegram Notification Settings
    st.divider()
    st.subheader("🔔 Notifications")
    
    with st.expander("📱 Telegram Bot", expanded=False):
        st.info(f"""
        **Status:** ✅ Configured
        
        Notifications will be sent to:
        - Bot Token: `...{TELEGRAM_BOT_TOKEN[-10:]}`
        - Chat ID: `{TELEGRAM_CHAT_ID}`
        """)
        
        # Test notification
        if st.button("🧪 Test Notification", use_container_width=True):
            test_msg = f"🧪 *Test Notification*\n\nJKT48 Monitor aktif!\n\nTime: {now_wib().strftime('%H:%M:%S WIB')}"
            if send_telegram_notification(test_msg):
                st.success("✅ Test notification sent!")
            else:
                st.error("❌ Failed to send test notification")
        
        st.session_state.notifications_enabled = st.checkbox(
            "Enable Notifications",
            value=st.session_state.notifications_enabled,
            help="Receive Telegram alerts for stock changes"
        )
    
    # Auto-refresh
    st.divider()
    st.subheader("🔄 Auto-Refresh")
    
    enable_auto_refresh = st.checkbox("Enable Auto-Refresh", value=False)
    
    if enable_auto_refresh:
        refresh_interval = st.slider(
            "Refresh Interval (seconds)",
            min_value=30,
            max_value=300,
            value=60,
            step=30
        )
        st_autorefresh(interval=refresh_interval * 1000, key="data_refresh")
        st.info(f"🔄 Auto-refreshing every {refresh_interval}s")
    
    # Manual refresh
    if st.button("🔄 Refresh Now", use_container_width=True):
        st.rerun()
    
    # API Status (debug info)
    st.divider()
    with st.expander("🔍 API Status & Debug", expanded=False):
        st.caption(f"**API Endpoint:**")
        st.code("https://jkt48.com/api/v1/exclusives/EXBE10?lang=id", language="text")
        
        if st.session_state.last_update:
            st.caption(f"**Last Successful Fetch:**")
            st.text(st.session_state.last_update.strftime("%Y-%m-%d %H:%M:%S WIB"))
        else:
            st.warning("No successful fetch yet")
        
        if st.button("🧪 Test API Connection", use_container_width=True):
            with st.spinner("Testing API..."):
                test_data = fetch_data()
                if test_data:
                    st.success("✅ API connection successful!")
                    session_count = len(test_data.get('session', []))
                    st.info(f"Found {session_count} sessions")
                else:
                    st.error("❌ API connection failed")

# Fetch data
with st.spinner("Loading data..."):
    # Try loading from background worker file first
    data = load_data_from_worker()
    
    if data:
        st.session_state.data = data
        st.session_state.last_update = now_wib()
        st.session_state.data_source = "background_worker"
    else:
        # Fallback: Try fetching from API directly
        st.info("📡 Background worker data not available. Trying API directly...")
        data = fetch_data()
        if data:
            st.session_state.data = data
            st.session_state.last_update = now_wib()
            st.session_state.data_source = "api_direct"

# Check for changes and send notifications
if st.session_state.data and st.session_state.previous_data:
    df_new = process_data(st.session_state.data)
    df_old = process_data(st.session_state.previous_data)
    
    # Detect changes logic here (simplified for this version)
    # Full implementation in background_monitor.py

# Update previous data
st.session_state.previous_data = st.session_state.data

# Process dataframe
df = process_data(st.session_state.data) if st.session_state.data else pd.DataFrame()

if df.empty:
    st.error("❌ No data available")
    st.info("""
    **Possible causes:**
    1. Background worker hasn't started yet
    2. Background worker hasn't completed first fetch
    3. Network connectivity issue
    
    **Solutions:**
    - Wait 30-60 seconds for background worker to fetch data
    - Check Railway logs to verify worker is running
    - Click "Refresh Now" to retry
    """)
    
    # Show retry button
    if st.button("🔄 Retry Now", type="primary"):
        st.rerun()
    
    st.stop()

# Event info subtitle
event_dates = df['Date_Display'].unique()
if len(event_dates) > 0:
    st.markdown(f'<div class="subtitle">📅 {event_dates[0]}</div>', unsafe_allow_html=True)

# Metrics
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("Total Sold", f"{df['Tickets Sold'].sum():,}")

with col2:
    st.metric("Available", f"{df['Available'].sum():,}")

with col3:
    sold_out_count = len(df[df['Status'] == 'Sold Out'])
    st.metric("Sold Out", sold_out_count)

with col4:
    # Count changes from change log
    change_count = len(st.session_state.changes)
    st.metric("Changes", change_count)

with col5:
    if st.session_state.last_update:
        update_time = st.session_state.last_update.strftime("%H:%M:%S")
        source = st.session_state.get('data_source', 'unknown')
        source_emoji = "🤖" if source == "background_worker" else "📡"
        st.metric(
            f"Last Update {source_emoji}",
            update_time,
            delta="WIB" if source == "background_worker" else "API",
            delta_color="off"
        )

# Tabs
tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "👥 Per Team", "📋 Data Table"])

with tab1:
    # Top 10 Members by Tickets Sold
    st.subheader("🏆 Top 10 Members - Tickets Sold")
    
    member_sales = df.groupby('Member')['Tickets Sold'].sum().sort_values(ascending=False).head(10)
    member_teams = df.groupby('Member')['Team'].first()
    
    fig_top = go.Figure()
    
    for member in member_sales.index:
        team = member_teams[member]
        color = TEAM_COLORS.get(team, '#999999')
        
        fig_top.add_trace(go.Bar(
            name=member,
            x=[member],
            y=[member_sales[member]],
            marker_color=color,
            text=[member_sales[member]],
            textposition='auto',
            hovertemplate=f'<b>{member}</b><br>Team: {team}<br>Sold: %{{y}}<extra></extra>'
        ))
    
    fig_top.update_layout(
        showlegend=False,
        height=400,
        xaxis_title="Member",
        yaxis_title="Tickets Sold",
        hovermode='x unified'
    )
    
    st.plotly_chart(fig_top, use_container_width=True)
    
    # Status Distribution
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Status Distribution")
        status_counts = df['Status'].value_counts()
        
        fig_status = px.pie(
            values=status_counts.values,
            names=status_counts.index,
            color=status_counts.index,
            color_discrete_map={
                'Available': '#4CAF50',
                'Low Stock': '#FFC107',
                'Sold Out': '#F44336'
            }
        )
        fig_status.update_traces(textposition='inside', textinfo='percent+label')
        fig_status.update_layout(height=350)
        st.plotly_chart(fig_status, use_container_width=True)
    
    with col2:
        st.subheader("👥 Sales by Team")
        team_sales = df.groupby('Team')['Tickets Sold'].sum().sort_values(ascending=False)
        
        fig_team = go.Figure(data=[
            go.Bar(
                x=team_sales.index,
                y=team_sales.values,
                marker_color=[TEAM_COLORS.get(team, '#999') for team in team_sales.index],
                text=team_sales.values,
                textposition='auto'
            )
        ])
        fig_team.update_layout(
            height=350,
            xaxis_title="Team",
            yaxis_title="Tickets Sold"
        )
        st.plotly_chart(fig_team, use_container_width=True)

with tab2:
    st.subheader("👥 Team Analysis")
    
    for team in ['LOVE', 'PASSION', 'DREAM', 'TRAINEE']:
        team_df = df[df['Team'] == team]
        
        if team_df.empty:
            continue
        
        with st.expander(f"{team} Team", expanded=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Sold", f"{team_df['Tickets Sold'].sum():,}")
            with col2:
                st.metric("Available", f"{team_df['Available'].sum():,}")
            with col3:
                sold_out = len(team_df[team_df['Status'] == 'Sold Out'])
                st.metric("Sold Out Sessions", sold_out)
            
            # Member list
            st.dataframe(
                team_df[['Member', 'Session', 'Tickets Sold', 'Available', 'Status']]
                .sort_values('Tickets Sold', ascending=False),
                use_container_width=True,
                hide_index=True
            )

with tab3:
    st.subheader("📋 Data Table")
    
    # Filters - 5 columns including Member filter
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        # Date filter
        unique_dates = sorted(df['Date'].unique(), reverse=True)
        date_filter_options = ['All Dates'] + list(unique_dates)
        selected_date_filter = st.selectbox(
            "Event Date",
            options=date_filter_options,
            index=0
        )
    
    with col2:
        # Member filter (NEW!)
        unique_members = sorted(df['Member'].unique())
        member_filter_options = ['All Members'] + list(unique_members)
        selected_member_filter = st.selectbox(
            "Member",
            options=member_filter_options,
            index=0
        )
    
    with col3:
        session_filter = st.multiselect(
            "Session",
            options=df['Session'].unique(),
            default=df['Session'].unique()
        )
    
    with col4:
        team_filter = st.multiselect(
            "Team",
            options=df['Team'].unique(),
            default=df['Team'].unique()
        )
    
    with col5:
        status_filter = st.multiselect(
            "Status",
            options=df['Status'].unique(),
            default=df['Status'].unique()
        )
    
    # Apply filters
    filtered_df = df.copy()
    
    if selected_date_filter != 'All Dates':
        filtered_df = filtered_df[filtered_df['Date'] == selected_date_filter]
    
    if selected_member_filter != 'All Members':
        filtered_df = filtered_df[filtered_df['Member'] == selected_member_filter]
    
    filtered_df = filtered_df[
        (filtered_df['Session'].isin(session_filter)) &
        (filtered_df['Team'].isin(team_filter)) &
        (filtered_df['Status'].isin(status_filter))
    ]
    
    # Display with formatted date
    display_df = filtered_df.copy()
    display_df['Date'] = display_df['Date_Display']
    display_df = display_df.drop(columns=['Date_Display'])
    
    # Show table
    st.dataframe(
        display_df.style.map(
            lambda x: 'background-color: #ffebee' if x == 'Sold Out' else
                      'background-color: #fff9c4' if x == 'Low Stock' else
                      'background-color: #e8f5e9' if x == 'Available' else '',
            subset=['Status']
        ),
        use_container_width=True,
        hide_index=True
    )
    
    st.info(f"Showing {len(filtered_df)} of {len(df)} rows")
    
    # Download button
    csv = filtered_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        "📥 Download CSV",
        csv,
        f"jkt48_stock_{now_wib().strftime('%Y%m%d_%H%M%S')}.csv",
        "text/csv",
        use_container_width=True
    )

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: #666; padding: 1rem;'>
    Made with ❤️ for JKT48 fans | Auto-refresh untuk monitoring real-time | Timezone: WIB
</div>
""", unsafe_allow_html=True)
