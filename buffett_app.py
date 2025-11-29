import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np

# -----------------------------------------------------------------------------
# CONFIGURATION & STYLING
# -----------------------------------------------------------------------------
st.set_page_config(page_title="The Oracle's Lens V2", layout="wide", page_icon="👓")

st.markdown("""
<style>
    /* Premium Dark Theme Adjustments */
    .stApp {
        background-color: #0e1117;
    }
    .metric-container {
        background-color: #262730;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #d4af37; /* Berkshire Gold */
        margin-bottom: 10px;
    }
    .big-number {
        font-size: 28px;
        font-weight: bold;
        color: #ffffff;
    }
    .sub-text {
        font-size: 14px;
        color: #b0b0b0;
    }
    .success-badge {
        background-color: #1b5e20;
        color: white;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 12px;
    }
    .fail-badge {
        background-color: #b71c1c;
        color: white;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 12px;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# PERSONA: DATA SPECIALIST (Logic & Global Handling)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def fetch_company_data(ticker):
    """
    Fetches comprehensive data including historicals for consistency checks.
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # We need to verify if data exists
        if 'regularMarketPrice' not in info and 'currentPrice' not in info:
            return None, "Ticker not found or delisted. Try adding a suffix (e.g., .TO for Toronto)."

        # Fetch Financials (Annual)
        financials = stock.financials
        balance_sheet = stock.balance_sheet
        cashflow = stock.cashflow
        
        # Transpose for easier time-series analysis (Rows = Years)
        fin_T = financials.T if not financials.empty else pd.DataFrame()
        bs_T = balance_sheet.T if not balance_sheet.empty else pd.DataFrame()
        cf_T = cashflow.T if not cashflow.empty else pd.DataFrame()

        return {
            "stock": stock,
            "info": info,
            "fin": financials,
            "bs": balance_sheet,
            "cf": cashflow,
            "fin_T": fin_T,
            "bs_T": bs_T
        }, None
    except Exception as e:
        return None, str(e)

def safe_calc(numerator, denominator, default=0):
    try:
        if denominator == 0 or pd.isna(denominator) or pd.isna(numerator):
            return default
        return numerator / denominator
    except:
        return default

# -----------------------------------------------------------------------------
# PERSONA: WARREN BUFFETT (Deep Analysis Logic)
# -----------------------------------------------------------------------------
def analyze_buffett_v2(data):
    info = data['info']
    fin = data['fin']
    bs = data['bs']
    
    # 1. RETURN ON EQUITY (ROE) - Management Quality
    # Formula: Net Income / Stockholder Equity
    try:
        net_income = fin.loc['Net Income']
        equity = bs.loc['Stockholders Equity']
        # Calculate for available years
        roe_series = (net_income / equity) * 100
        avg_roe = roe_series.mean()
        current_roe = roe_series.iloc[0]
    except:
        avg_roe = 0
        current_roe = 0
        roe_series = []

    # 2. THE MOAT (Gross Margin Stability)
    try:
        gross_profit = fin.loc['Gross Profit']
        revenue = fin.loc['Total Revenue']
        margin_series = (gross_profit / revenue) * 100
        avg_margin = margin_series.mean()
        # Check if margins are consistent (std dev)
        margin_volatility = margin_series.std()
    except:
        avg_margin = 0
        margin_volatility = 100
        margin_series = []

    # 3. FINANCIAL FORTRESS (Debt to Equity)
    try:
        total_debt = bs.loc['Total Debt'].iloc[0]
        total_equity = bs.loc['Stockholders Equity'].iloc[0]
        debt_to_equity = total_debt / total_equity
    except:
        try:
            # Fallback for older API versions or different accounting
            lt_debt = bs.loc['Long Term Debt'].iloc[0]
            debt_to_equity = lt_debt / bs.loc['Stockholders Equity'].iloc[0]
        except:
            debt_to_equity = 0

    # 4. BOOK VALUE GROWTH (Intrinsic Value Proxy)
    # We look at the trend of Stockholders Equity over time
    try:
        equity_history = bs.loc['Stockholders Equity']
        # Is the most recent year higher than 3 years ago?
        book_growth = equity_history.iloc[0] > equity_history.iloc[-1] 
    except:
        book_growth = False

    return {
        "current_roe": current_roe,
        "avg_roe": avg_roe,
        "roe_pass": avg_roe > 15,
        "current_margin": 0 if isinstance(margin_series, list) else margin_series.iloc[0],
        "margin_series": margin_series,
        "debt_to_equity": debt_to_equity,
        "debt_pass": debt_to_equity < 0.8, # Strict Buffett preference
        "book_growth": book_growth,
        "currency": info.get('currency', 'USD')
    }

# -----------------------------------------------------------------------------
# MAIN APP
# -----------------------------------------------------------------------------

# --- SIDEBAR: Global Lookups ---
st.sidebar.title("👓 The Oracle's Lens V2")
st.sidebar.caption("Data provided by Yahoo Finance")

input_ticker = st.sidebar.text_input("Enter Ticker", "RY.TO").upper()

with st.sidebar.expander("🌍 How to find Global Stocks"):
    st.markdown("""
    **USA:** `AAPL`, `MSFT`, `KO`
    **Canada (TSX):** Add `.TO` (e.g., `RY.TO`, `SHOP.TO`)
    **UK (London):** Add `.L` (e.g., `SHEL.L`)
    **Australia:** Add `.AX` (e.g., `BHP.AX`)
    **India:** Add `.NS` (e.g., `RELIANCE.NS`)
    """)

st.sidebar.markdown("---")
st.sidebar.markdown("### The Buffett Philosophy")
st.sidebar.info("""
1. **Understand the Business:** Simple & boring is good.
2. **Moat:** Competitive advantage.
3. **Management:** Honest & competent (High ROE).
4. **Price:** Margin of Safety.
""")

# --- MAIN LOGIC ---
if input_ticker:
    with st.spinner(f"Analyzing {input_ticker} across the globe..."):
        data_pack, error = fetch_company_data(input_ticker)

    if error:
        st.error(f"❌ {error}")
    else:
        # Run Analysis
        analysis = analyze_buffett_v2(data_pack)
        info = data_pack['info']
        
        # --- HEADER ---
        col1, col2 = st.columns([3, 1])
        with col1:
            st.title(f"{info.get('longName', input_ticker)}")
            st.markdown(f"**Sector:** {info.get('sector', 'N/A')} | **Industry:** {info.get('industry', 'N/A')}")
            
            # Currency Warning for International Traders
            curr = info.get('currency', 'USD')
            if curr != 'USD':
                st.caption(f"⚠️ Note: All financial figures are in **{curr}**")

        with col2:
            price = info.get('currentPrice', info.get('regularMarketPrice', 0))
            st.metric("Stock Price", f"{curr} {price}")
            
            # Simple Valuation Badge
            pe = info.get('trailingPE', 0)
            if pe > 0 and pe < 15:
                st.markdown("<span class='success-badge'>Valuation: Cheap (P/E < 15)</span>", unsafe_allow_html=True)
            elif pe > 30:
                st.markdown("<span class='fail-badge'>Valuation: Expensive</span>", unsafe_allow_html=True)
            else:
                st.markdown("<span class='success-badge' style='background-color:#888'>Valuation: Moderate</span>", unsafe_allow_html=True)

        st.markdown("---")

        # --- EXECUTIVE SUMMARY (Pass/Fail) ---
        st.subheader("📋 The Oracle's Scorecard")
        
        sc1, sc2, sc3, sc4 = st.columns(4)
        
        # 1. ROE Check
        with sc1:
            is_good = analysis['roe_pass']
            color = "green" if is_good else "red"
            st.markdown(f"""
            <div class='metric-container' style='border-left-color: {color}'>
                <div class='sub-text'>Management Quality</div>
                <div class='big-number'>{analysis['avg_roe']:.1f}%</div>
                <div class='sub-text'>5-Yr Avg ROE (>15% target)</div>
            </div>
            """, unsafe_allow_html=True)

        # 2. Debt Check
        with sc2:
            is_good = analysis['debt_pass']
            color = "green" if is_good else "red"
            st.markdown(f"""
            <div class='metric-container' style='border-left-color: {color}'>
                <div class='sub-text'>Financial Health</div>
                <div class='big-number'>{analysis['debt_to_equity']:.2f}</div>
                <div class='sub-text'>Debt-to-Equity (<0.8 target)</div>
            </div>
            """, unsafe_allow_html=True)

        # 3. Moat Check (Margin Stability)
        with sc3:
            # Simple check: Is current margin > 40%?
            margin = analysis['current_margin']
            is_good = margin > 40
            color = "green" if is_good else "orange" # Orange for medium margins
            st.markdown(f"""
            <div class='metric-container' style='border-left-color: {color}'>
                <div class='sub-text'>The Moat</div>
                <div class='big-number'>{margin:.1f}%</div>
                <div class='sub-text'>Gross Margins (>40% target)</div>
            </div>
            """, unsafe_allow_html=True)

        # 4. Growth Check
        with sc4:
            is_good = analysis['book_growth']
            color = "green" if is_good else "red"
            status = "Growing" if is_good else "Declining"
            st.markdown(f"""
            <div class='metric-container' style='border-left-color: {color}'>
                <div class='sub-text'>Intrinsic Value</div>
                <div class='big-number'>{status}</div>
                <div class='sub-text'>Book Value Trend</div>
            </div>
            """, unsafe_allow_html=True)

        # --- DEEP DIVE TABS ---
        st.markdown("### 🔍 Deep Dive Analysis")
        tab1, tab2, tab3 = st.tabs(["💎 Management & ROE", "🏰 The Moat & Margins", "⚖️ Valuation & Price"])

        with tab1:
            st.markdown("**Warren's Favorite Number: Return on Equity (ROE)**")
            st.write("This measures how efficiently management uses shareholder money. Consistency is key.")
            
            # Visualize ROE History
            try:
                fin = data_pack['fin']
                bs = data_pack['bs']
                roe_hist = (fin.loc['Net Income'] / bs.loc['Stockholders Equity']) * 100
                
                # Sort by date ascending for chart
                roe_hist = roe_hist.sort_index()
                
                fig_roe = px.line(x=roe_hist.index, y=roe_hist.values, markers=True, 
                                  title="ROE History (Are they consistent?)")
                fig_roe.add_hline(y=15, line_dash="dash", line_color="green", annotation_text="Buffett Target (15%)")
                fig_roe.update_layout(yaxis_title="ROE %", xaxis_title="Year")
                st.plotly_chart(fig_roe, use_container_width=True)
            except:
                st.warning("Not enough historical data to plot ROE trend.")

        with tab2:
            st.markdown("**The Moat: Gross Margins**")
            st.write("Companies with a durable competitive advantage (Moat) can keep margins high without fighting price wars.")
            
            try:
                m_hist = analysis['margin_series'].sort_index()
                fig_margin = px.bar(x=m_hist.index, y=m_hist.values, title="Gross Margin History")
                fig_margin.update_traces(marker_color='#d4af37') # Gold color
                fig_margin.update_layout(yaxis_title="Gross Margin %")
                st.plotly_chart(fig_margin, use_container_width=True)
            except:
                st.warning("Margin data unavailable.")

        with tab3:
            st.markdown("**Price vs. Value (The Benjamin Graham Check)**")
            
            col_v1, col_v2 = st.columns(2)
            
            with col_v1:
                st.markdown("#### The Price Ratios")
                pe = info.get('trailingPE', 'N/A')
                pb = info.get('priceToBook', 'N/A')
                
                st.metric("P/E Ratio", pe, delta_color="inverse", help="Price to Earnings. Lower is usually better. < 15 is cheap.")
                st.metric("P/B Ratio", pb, delta_color="inverse", help="Price to Book Value. Lower is better. < 1.5 is value territory.")
            
            with col_v2:
                st.markdown("#### The Graham Number (Simplified)")
                st.write("Benjamin Graham (Buffett's teacher) suggested a 'Fair Value' estimation.")
                
                try:
                    # Graham Number Formula: Sqrt(22.5 * EPS * BookValuePerShare)
                    eps = info.get('trailingEps')
                    bvps = info.get('bookValue')
                    
                    if eps and bvps and eps > 0 and bvps > 0:
                        graham_num = (22.5 * eps * bvps) ** 0.5
                        st.metric("Graham Fair Value", f"{curr} {graham_num:.2f}")
                        
                        current_p = info.get('currentPrice')
                        if current_p < graham_num:
                            st.success(f"✅ The stock is trading BELOW the Graham Number (Undervalued).")
                        else:
                            st.warning(f"⚠️ The stock is trading ABOVE the Graham Number.")
                    else:
                        st.warning("Cannot calculate Graham Number (Negative Earnings or Book Value).")
                except:
                    st.write("Data insufficient for Graham calculation.")

# Footer
st.markdown("---")
st.caption("The Oracle's Lens V2 | Supports TSX, LSE, ASX, NYSE, NASDAQ | Data: Yahoo Finance")
