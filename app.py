import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import date
import json
import plotly.express as px
import plotly.graph_objects as go

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Student Money Tracker",
    page_icon="💸",
    layout="wide",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}
h1, h2, h3 {
    font-family: 'Syne', sans-serif !important;
}

.main { background-color: #0f0f13; }
[data-testid="stAppViewContainer"] { background-color: #0f0f13; color: #f0ede8; }
[data-testid="stSidebar"] { background-color: #16161d; border-right: 1px solid #2a2a35; }

.metric-card {
    background: #1a1a24;
    border: 1px solid #2a2a35;
    border-radius: 16px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 0.5rem;
}
.metric-label { font-size: 0.75rem; color: #888; letter-spacing: 0.1em; text-transform: uppercase; }
.metric-value { font-family: 'Syne', sans-serif; font-size: 2rem; font-weight: 800; }
.metric-green { color: #4ade80; }
.metric-red { color: #f87171; }
.metric-yellow { color: #fbbf24; }
.metric-blue { color: #60a5fa; }

.big-title {
    font-family: 'Syne', sans-serif;
    font-size: 2.4rem;
    font-weight: 800;
    background: linear-gradient(135deg, #f0ede8 0%, #fbbf24 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0;
}
.subtitle { color: #888; font-size: 0.9rem; margin-top: -0.3rem; margin-bottom: 1.5rem; }

div[data-testid="stButton"] > button {
    background: linear-gradient(135deg, #fbbf24, #f59e0b);
    color: #0f0f13;
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    border: none;
    border-radius: 10px;
    padding: 0.55rem 1.5rem;
    width: 100%;
}
div[data-testid="stButton"] > button:hover { opacity: 0.88; }

.stSelectbox > div, .stNumberInput > div, .stTextInput > div {
    background-color: #1a1a24 !important;
    border-radius: 10px !important;
}

.section-header {
    font-family: 'Syne', sans-serif;
    font-size: 1.1rem;
    font-weight: 700;
    color: #fbbf24;
    margin: 1.2rem 0 0.6rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.tag-income {
    background: #14532d; color: #4ade80;
    padding: 2px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600;
}
.tag-food {
    background: #431407; color: #fb923c;
    padding: 2px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600;
}
.tag-entertainment {
    background: #312e81; color: #a78bfa;
    padding: 2px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600;
}
.tag-transport {
    background: #0c4a6e; color: #38bdf8;
    padding: 2px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600;
}
.tag-other {
    background: #1c1917; color: #a8a29e;
    padding: 2px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600;
}

[data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Google Sheets connection ──────────────────────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SHEET_NAME = "StudentMoneyTracker"
HEADERS = ["Date", "Type", "Category", "Description", "Amount"]

@st.cache_resource
def get_gspread_client():
    """Connect using the service account key stored in Streamlit secrets."""
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)

def get_or_create_sheet(client):
    """Open the spreadsheet, or create it if it doesn't exist yet."""
    try:
        sh = client.open(SHEET_NAME)
    except gspread.SpreadsheetNotFound:
        sh = client.create(SHEET_NAME)
        sh.share(None, perm_type="anyone", role="writer")  # optional: make accessible
    ws = sh.sheet1
    if ws.row_count == 0 or ws.cell(1, 1).value != "Date":
        ws.clear()
        ws.append_row(HEADERS)
    return ws

@st.cache_data(ttl=30)
def load_data(_ws):
    """Load all rows from the sheet into a DataFrame."""
    records = _ws.get_all_records()
    if not records:
        return pd.DataFrame(columns=HEADERS)
    df = pd.DataFrame(records)
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    return df

def add_row(ws, row: list):
    ws.append_row(row)
    load_data.clear()

# ── App layout ────────────────────────────────────────────────────────────────
st.markdown('<p class="big-title">💸 Money Tracker</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Student edition — know where every rupiah goes</p>', unsafe_allow_html=True)

# Sidebar — add transaction
with st.sidebar:
    st.markdown("### ➕ Log a Transaction")

    txn_type = st.selectbox("Type", ["Expense", "Income"])
    
    if txn_type == "Expense":
        category = st.selectbox("Category", ["🍔 Food & Dining", "🎮 Entertainment", "🚌 Transport", "📦 Other"])
    else:
        category = st.selectbox("Category", ["💰 Allowance from Parents", "💼 Part-time / Freelance", "🎁 Gift", "📦 Other"])

    description = st.text_input("Description", placeholder="e.g. Lunch at canteen")
    amount = st.number_input("Amount (Rp)", min_value=1.0, step=1000.0, format="%.0f")
    txn_date = st.date_input("Date", value=date.today())

    if st.button("Save Transaction"):
        try:
            client = get_gspread_client()
            ws = get_or_create_sheet(client)
            add_row(ws, [str(txn_date), txn_type, category, description, amount])
            st.success("✅ Saved!")
        except Exception as e:
            st.error(f"Error: {e}")

# Main content
try:
    client = get_gspread_client()
    ws = get_or_create_sheet(client)
    df = load_data(ws)
except Exception as e:
    st.error(f"⚠️ Could not connect to Google Sheets: {e}")
    st.stop()

if df.empty:
    st.info("No transactions yet. Add your first one in the sidebar! 👈")
    st.stop()

# ── Summary metrics ───────────────────────────────────────────────────────────
total_income = df[df["Type"] == "Income"]["Amount"].sum()
total_expense = df[df["Type"] == "Expense"]["Amount"].sum()
balance = total_income - total_expense

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Total Income</div>
        <div class="metric-value metric-green">Rp{total_income:,.0f}</div>
    </div>""", unsafe_allow_html=True)
with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Total Expenses</div>
        <div class="metric-value metric-red">Rp{total_expense:,.0f}</div>
    </div>""", unsafe_allow_html=True)
with col3:
    color_class = "metric-green" if balance >= 0 else "metric-red"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Balance</div>
        <div class="metric-value {color_class}">Rp{balance:,.0f}</div>
    </div>""", unsafe_allow_html=True)

st.markdown("---")

# ── Charts ────────────────────────────────────────────────────────────────────
expenses_df = df[df["Type"] == "Expense"]

if not expenses_df.empty:
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown('<p class="section-header">Spending by Category</p>', unsafe_allow_html=True)
        cat_totals = expenses_df.groupby("Category")["Amount"].sum().reset_index()
        fig_pie = px.pie(
            cat_totals, values="Amount", names="Category",
            color_discrete_sequence=["#fb923c", "#a78bfa", "#38bdf8", "#a8a29e", "#4ade80"],
            hole=0.45,
        )
        fig_pie.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#f0ede8", legend_font_size=11,
            margin=dict(t=10, b=10, l=10, r=10),
            showlegend=True,
        )
        fig_pie.update_traces(textfont_color="#0f0f13")
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_b:
        st.markdown('<p class="section-header">Daily Expenses (Last 14 Days)</p>', unsafe_allow_html=True)
        recent = expenses_df[expenses_df["Date"] >= pd.Timestamp.now() - pd.Timedelta(days=14)]
        if not recent.empty:
            daily = recent.groupby("Date")["Amount"].sum().reset_index()
            fig_bar = px.bar(
                daily, x="Date", y="Amount",
                color_discrete_sequence=["#fbbf24"],
            )
            fig_bar.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color="#f0ede8", xaxis_title="", yaxis_title="Rp",
                margin=dict(t=10, b=10, l=10, r=10),
            )
            fig_bar.update_xaxes(gridcolor="#2a2a35")
            fig_bar.update_yaxes(gridcolor="#2a2a35")
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("No expenses in the last 14 days.")

# ── Transaction history ───────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<p class="section-header">📋 Transaction History</p>', unsafe_allow_html=True)

filter_type = st.radio("Show", ["All", "Income", "Expense"], horizontal=True)
filtered = df if filter_type == "All" else df[df["Type"] == filter_type]
filtered = filtered.sort_values("Date", ascending=False)

# Display nicely
display_df = filtered.copy()
display_df["Date"] = display_df["Date"].dt.strftime("%b %d, %Y")
display_df["Amount"] = display_df["Amount"].apply(lambda x: f"Rp{x:,.0f}")
st.dataframe(
    display_df[["Date", "Type", "Category", "Description", "Amount"]],
    use_container_width=True,
    hide_index=True,
)
