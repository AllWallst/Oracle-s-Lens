import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests

# -----------------------------------------------------------------------------
# CONFIGURATION & STYLING
# -----------------------------------------------------------------------------
st.set_page_config(page_title="The Oracle's Lens V3", layout="wide", page_icon="🔮")

st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    .metric-container {
        background-color: #262730;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #d4af37;
        margin-bottom: 10px;
    }
    .big-number { font-size: 26px; font-weight: bold; color: #ffffff; }
    .sub-text { font-size: 14px; color: #b0b0b0; }
    .search-result {
        padding: 10px;
        border-radius: 5px;
        border: 1px solid #444;
        margin-bottom: 5px;
        cursor: pointer;
    }
    .stButton button { width: 100%; }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# PERSONA: DATA SPECIALIST (Search & Data Logic)
# -----------------------------------------------------------------------------

def search_symbol(query):
    """
    Uses Yahoo Finance's public autocomplete API to find tickers from names.
    """
    url = "https://query2.finance.yahoo.com/v1/finance/search"
    params = {"q": query, "quotesCount": 5, "newsCount": 0}
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        r = requests.get(url, params=params, headers=headers)
        data = r.json()
        if 'quotes' in data and len(data['quotes']) > 0:
            return data['quotes']
        return []
    except:
        return []

@st.cache_data(ttl=3600)
def fetch_financial_data(ticker):
    """
    Robust fetcher that avoids caching the Unserializable yf.Ticker object.
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        if 'regularMarketPrice' not in info and 'currentPrice' not in info:
            return None, "Ticker not found or delisted."

        financials = stock.financials
        balance_sheet = stock.balance_sheet
        cashflow = stock.cashflow
        
        # Safe extraction of basic data for calculations
        return {
            "info": info,
            "fin": financials,
            "bs": balance_sheet,
            "cf": cashflow,
        }, None
    except Exception as e:
        return None, str(e)

# -----------------------------------------------------------------------------
# PERSONA: WARREN BUFFETT (Valuation Logic: DCF & Graham)
# -----------------------------------------------------------------------------

def calculate_dcf(data):
    """
    Performs a simplified 2-stage Discounted Cash Flow analysis.
    Buffett Style: 10% Discount Rate, Conservative Growth.
    """
    try:
        cf = data['cf']
        info = data['info']
        
        # 1. Calculate Free Cash Flow (Operating Cash - CapEx)
        # Note: CapEx is usually negative in Yahoo data
        try:
            ocf = cf.loc['Operating Cash Flow'].iloc[0]
            capex = cf.loc['Capital Expenditure'].iloc[0]
            fcf = ocf + capex
        except:
            # Fallback for different naming conventions
            ocf = cf.loc['Total Cash From Operating Activities'].iloc[0]
            capex = cf.loc['Capital Expenditures'].iloc[0]
            fcf = ocf + capex

        if fcf < 0:
            return None, "Negative Free Cash Flow (Unprofitable)"

        # 2. Estimate Growth Rate (Capped at 15% for safety)
        # We'd ideally look at historical growth, but for this tool we'll use a conservative estimate
        # based on Analyst growth projections or default to 8% if missing.
        growth_rate = info.get('revenueGrowth', 0.05)
        if growth_rate > 0.15: growth_rate = 0.15 # Buffett Cap
        
        discount_rate = 0.10 # Buffett's hurdle rate
        terminal_growth = 0.03 # Inflation
        
        # 3. Project 10 Years
        future_cash_flows = []
        for i in range(1, 11):
            fcf = fcf * (1 + growth_rate)
            discounted_fcf = fcf / ((1 + discount_rate) ** i)
            future_cash_flows.append(discounted_fcf)
            
        # 4. Terminal Value
        last_fcf = fcf
        terminal_value = (last_fcf * (1 + terminal_growth)) / (discount_rate - terminal_growth)
        discounted_tv = terminal_value / ((1 + discount_rate) ** 10)
        
        total_value = sum(future_cash_flows) + discounted_tv
        shares = info.get('sharesOutstanding', 1)
        
        fair_value = total_value / shares
        return fair_value, f"Growth est: {growth_rate*100:.1f}%"
        
    except Exception as e:
        return None, "Insufficient Data for DCF"

def calculate_graham(data):
    """
    Graham Number: Sqrt(22.5 * EPS * BookValuePerShare)
    """
    try:
        info = data['info']
        eps = info.get('trailingEps')
        bvps = info.get('bookValue')
        
        if eps and bvps and eps > 0 and bvps > 0:
            return (22.5 * eps * bvps) ** 0.5
        return None
    except:
        return None

# -----------------------------------------------------------------------------
# MAIN APP LAYOUT
# -----------------------------------------------------------------------------

# --- SIDEBAR: SEARCH & SELECT ---
st.sidebar.title("🔮 The Oracle's Lens V3")

st.sidebar.subheader("🔎 Stock Finder")
search_query = st.sidebar.text_input("Company Name (e.g., 'Google')", "")

selected_ticker = "AAPL" # Default

if search_query:
    results = search_symbol(search_query)
    if results:
        st.sidebar.markdown("**Found:**")
        # create a simplified dict for the radio button
        options = {f"{x['symbol']} - {x.get('shortname', x.get('longname'))} ({x.get('exchange')})": x['symbol'] for x in results}
        selection = st.sidebar.radio("Select Ticker:", list(options.keys()))
        selected_ticker = options[selection]
    else:
        st.sidebar.warning("No results found.")
else:
    st.sidebar.info("Type a company name above to find its ticker.")
    manual_ticker = st.sidebar.text_input("Or type ticker manually:", "")
    if manual_ticker:
        selected_ticker = manual_ticker.upper()

st.sidebar.markdown("---")
st.sidebar.markdown("### 🏛️ Methodology")
st.sidebar.info("""
**1. Graham Number:** For stable, asset-heavy companies (Banks, Industry).
**2. DCF:** For modern compounders (Tech, Services).
**3. Market Mood:** What Wall St. Analysts think.
""")

# --- MAIN CONTENT ---

if selected_ticker:
    with st.spinner(f"Consulting the Oracle about {selected_ticker}..."):
        data, error = fetch_financial_data(selected_ticker)

    if error:
        st.error(f"❌ {error}")
    else:
        info = data['info']
        curr = info.get('currency', 'USD')
        price = info.get('currentPrice', info.get('regularMarketPrice', 0))

        # --- HEADER ---
        col1, col2 = st.columns([3, 1])
        with col1:
            st.title(f"{info.get('longName', selected_ticker)}")
            st.caption(f"Sector: {info.get('sector')} | Industry: {info.get('industry')}")
        with col2:
            st.metric("Current Price", f"{curr} {price}")

        # --- VALUATION TRIANGULATION ---
        st.subheader("⚖️ Valuation Triangulation")
        st.markdown("Comparing different ways to value the business.")

        # Calculate Valuations
        graham_val = calculate_graham(data)
        dcf_val, dcf_msg = calculate_dcf(data)
        analyst_val = info.get('targetMeanPrice')

        # Prepare Data for Chart
        vals = {'Price': price}
        if graham_val: vals['Graham Number'] = graham_val
        if dcf_val: vals['DCF (Intrinsic)'] = dcf_val
        if analyst_val: vals['Analyst Target'] = analyst_val

        # Visualizing with Plotly
        fig = go.Figure()
        
        # Current Price Line
        fig.add_hline(y=price, line_dash="dash", line_color="white", annotation_text=f"Current: {price}")

        colors = {'Graham Number': '#ff9800', 'DCF (Intrinsic)': '#4CAF50', 'Analyst Target': '#2196F3'}
        
        for name, value in vals.items():
            if name != 'Price':
                color = colors.get(name, 'grey')
                fig.add_trace(go.Bar(x=[name], y=[value], name=name, marker_color=color, text=[f"{value:.2f}"], textposition='auto'))

        fig.update_layout(title=f"Valuation Models ({curr})", height=400, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

        # --- INTERPRETATION ---
        c1, c2, c3 = st.columns(3)
        
        with c1:
            st.markdown("#### 1. Ben Graham (The Floor)")
            if graham_val:
                st.metric("Graham Number", f"{graham_val:.2f}", delta=round(graham_val - price, 2))
                if price < graham_val:
                    st.success("Undervalued based on Assets.")
                else:
                    st.caption("Price exceeds asset base (Normal for Tech).")
            else:
                st.warning("N/A (Negative Earnings/Book)")

        with c2:
            st.markdown("#### 2. DCF (The Modern Lens)")
            if dcf_val:
                st.metric("DCF Value", f"{dcf_val:.2f}", delta=round(dcf_val - price, 2))
                st.caption(f"Based on {dcf_msg}")
                if price < dcf_val:
                    st.success("Trading below Intrinsic Value.")
                else:
                    st.warning("Price assumes higher growth than 15%.")
            else:
                st.warning(dcf_msg)

        with c3:
            st.markdown("#### 3. The Market (Sentiment)")
            if analyst_val:
                st.metric("Analyst Target", f"{analyst_val:.2f}", delta=round(analyst_val - price, 2))
                rec = info.get('recommendationKey', 'none').upper()
                st.caption(f"Consensus: {rec}")
            else:
                st.warning("No Analyst Coverage")

        st.markdown("---")

        # --- BUFFETT'S CHECKLIST (Quick View) ---
        st.subheader("📋 The Quality Scorecard")
        
        # Calculate Metrics
        try:
            roe = info.get('returnOnEquity', 0) * 100
            debt_equity = info.get('debtToEquity', 0) / 100
            gross_margins = info.get('grossMargins', 0) * 100
            fcf_yield = (info.get('freeCashflow', 0) / info.get('marketCap', 1)) * 100
        except:
            roe, debt_equity, gross_margins, fcf_yield = 0, 0, 0, 0

        k1, k2, k3, k4 = st.columns(4)
        
        with k1:
            st.markdown("**Management (ROE)**")
            st.metric("ROE", f"{roe:.1f}%", delta="Target > 15%", delta_color="off" if roe > 15 else "inverse")
        
        with k2:
            st.markdown("**Safety (Debt)**")
            st.metric("Debt/Eq", f"{debt_equity:.2f}", delta="Target < 0.8", delta_color="inverse" if debt_equity > 0.8 else "normal")
            
        with k3:
            st.markdown("**Moat (Margins)**")
            st.metric("Gross Margin", f"{gross_margins:.1f}%", delta="Target > 40%", delta_color="off" if gross_margins > 40 else "inverse")

        with k4:
            st.markdown("**Yield**")
            st.metric("FCF Yield", f"{fcf_yield:.1f}%", help="Free Cash Flow / Market Cap. Higher is better.")

# Footer
st.markdown("---")
st.caption("The Oracle's Lens V3 | Data: Yahoo Finance | Built with Streamlit")
