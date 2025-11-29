import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# -----------------------------------------------------------------------------
# CONFIGURATION & STYLING
# -----------------------------------------------------------------------------
st.set_page_config(page_title="The Oracle's Lens", layout="wide", page_icon="📈")

# Custom CSS for that "Premium/Clean" look requested by the Trader Persona
st.markdown("""
<style>
    .metric-card {
        background-color: #1e1e1e;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #333;
        margin-bottom: 10px;
    }
    .big-font {
        font-size: 24px !important;
        font-weight: bold;
    }
    .stProgress > div > div > div > div {
        background-color: #4CAF50;
    }
    h1, h2, h3 {
        color: #f0f2f6;
    }
    .highlight {
        color: #4CAF50;
        font-weight: bold;
    }
    .warning {
        color: #FFC107;
        font-weight: bold;
    }
    .danger {
        color: #FF5252;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# PERSONA: DATA SPECIALIST (Logic & Data Retrieval)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def get_stock_data(ticker_symbol):
    """
    Fetches robust data, handling yfinance quirks and null values.
    """
    try:
        stock = yf.Ticker(ticker_symbol)
        
        # Fetch data
        info = stock.info
        financials = stock.financials
        balance_sheet = stock.balance_sheet
        cashflow = stock.cashflow
        
        # Check if data exists
        if financials.empty or balance_sheet.empty:
            return None, "Insufficient financial data available for this ticker."

        return {
            "info": info,
            "financials": financials,
            "balance_sheet": balance_sheet,
            "cashflow": cashflow,
            "history": stock.history(period="5y")
        }, None
    except Exception as e:
        return None, str(e)

def safe_get(data_dict, key, default=0):
    """Safely retrieves data from dictionary or dataframe."""
    try:
        if isinstance(data_dict, pd.DataFrame):
            if key in data_dict.index:
                return data_dict.loc[key].iloc[0] # Most recent
            else:
                return default
        return data_dict.get(key, default)
    except:
        return default

# -----------------------------------------------------------------------------
# PERSONA: WARREN BUFFETT (Analysis Logic)
# -----------------------------------------------------------------------------
def analyze_buffett_metrics(data):
    fin = data['financials']
    bs = data['balance_sheet']
    cf = data['cashflow']
    info = data['info']

    # 1. THE MOAT: Gross Margins > 40% consistently?
    try:
        gross_profit = fin.loc['Gross Profit']
        total_rev = fin.loc['Total Revenue']
        margins = (gross_profit / total_rev) * 100
        avg_margin = margins.mean()
        current_margin = margins.iloc[0]
        moat_score = True if avg_margin > 40 else False
    except:
        current_margin = 0
        moat_score = False

    # 2. MANAGEMENT: Return on Equity > 15%?
    try:
        net_income = fin.loc['Net Income'].iloc[0]
        equity = bs.loc['Stockholders Equity'].iloc[0]
        roe = (net_income / equity) * 100
        roe_score = True if roe > 15 else False
    except:
        roe = 0
        roe_score = False

    # 3. FINANCIAL STRENGTH: Can they pay off debt? (Long Term Debt < 5x Net Income)
    try:
        lt_debt = safe_get(bs, 'Long Term Debt', 0)
        net_income = safe_get(fin, 'Net Income', 1) # avoid div by zero
        debt_years = lt_debt / net_income if net_income > 0 else 99
        debt_score = True if debt_years < 5 else False
    except:
        debt_years = 0
        debt_score = False

    # 4. CASH IS KING: Free Cash Flow Growth
    try:
        fcf = cf.loc['Free Cash Flow']
        fcf_positive = True if fcf.iloc[0] > 0 else False
    except:
        # Fallback calculation
        try:
            op_cash = cf.loc['Total Cash From Operating Activities']
            capex = cf.loc['Capital Expenditures']
            fcf = op_cash + capex # Capex is usually negative
            fcf_positive = True if fcf.iloc[0] > 0 else False
        except:
            fcf_positive = False

    return {
        "gross_margin": current_margin,
        "moat_pass": moat_score,
        "roe": roe,
        "roe_pass": roe_score,
        "debt_years": debt_years,
        "debt_pass": debt_score,
        "fcf_positive": fcf_positive
    }

# -----------------------------------------------------------------------------
# PERSONA: UI DEVELOPER (Visual Components)
# -----------------------------------------------------------------------------
def draw_gauge(score):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = score,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Buffett Quality Score"},
        gauge = {
            'axis': {'range': [0, 100]},
            'bar': {'color': "#2E8B57"},
            'steps': [
                {'range': [0, 40], 'color': "#ff5252"},
                {'range': [40, 70], 'color': "#ffc107"},
                {'range': [70, 100], 'color': "#a5d6a7"}],
        }
    ))
    fig.update_layout(height=300, margin=dict(l=20, r=20, t=50, b=20), paper_bgcolor='rgba(0,0,0,0)')
    return fig

# -----------------------------------------------------------------------------
# MAIN APP LAYOUT
# -----------------------------------------------------------------------------

# Sidebar
st.sidebar.title("🔍 The Oracle's Lens")
st.sidebar.markdown("---")
ticker = st.sidebar.text_input("Enter Stock Ticker (e.g. AAPL)", "AAPL").upper()
analyze_btn = st.sidebar.button("Analyze Business")

st.sidebar.markdown("### How to read this tool")
st.sidebar.info(
    """
    **We don't use jargon here.**
    
    *   **Revenue** = Money coming in the door.
    *   **Net Income** = Money kept after paying everyone.
    *   **Moat** = Why it's hard to compete with this company.
    *   **Free Cash Flow** = Owner's Earnings.
    """
)

if analyze_btn or ticker:
    with st.spinner(f"Consulting the Oracle about {ticker}..."):
        data_pack, error = get_stock_data(ticker)

    if error:
        st.error(f"❌ {error}")
    else:
        # Extract Data
        info = data_pack['info']
        analysis = analyze_buffett_metrics(data_pack)
        
        # Calculate Score (Simple weighted average)
        score = 0
        score += 30 if analysis['moat_pass'] else 0
        score += 30 if analysis['roe_pass'] else 0
        score += 20 if analysis['debt_pass'] else 0
        score += 20 if analysis['fcf_positive'] else 0

        # --- HEADER SECTION ---
        col1, col2 = st.columns([3, 1])
        with col1:
            st.title(f"{info.get('longName', ticker)}")
            st.markdown(f"**Sector:** {info.get('sector', 'Unknown')} | **Industry:** {info.get('industry', 'Unknown')}")
            
            # The "Verdict"
            if score >= 80:
                st.success("🏆 **Verdict: A Wonderful Company.** High quality business with strong fundamentals.")
            elif score >= 50:
                st.warning("⚠️ **Verdict: A Mediocre Business.** Some good qualities, but has flaws.")
            else:
                st.error("🛑 **Verdict: Pass.** This does not meet the criteria of a high-quality compounder.")

        with col2:
            st.metric("Current Price", f"${info.get('currentPrice', 0)}")
            st.caption("Market Cap: " + "{:,}".format(info.get('marketCap', 0)))

        st.markdown("---")

        # --- THE BUFFETT SCORECARD ---
        c1, c2 = st.columns([1, 2])
        
        with c1:
            st.plotly_chart(draw_gauge(score), use_container_width=True)
        
        with c2:
            st.subheader("The 4 Pillars of Quality")
            
            # Pillar 1: The Moat
            check_mark = "✅" if analysis['moat_pass'] else "❌"
            st.markdown(f"### {check_mark} 1. The Moat (Competitive Advantage)")
            st.write(f"Does the company have high margins? We look for Gross Margins > 40%.")
            st.progress(min(int(analysis['gross_margin']), 100))
            st.caption(f"Current Gross Margin: {analysis['gross_margin']:.1f}%")

            # Pillar 2: Management
            check_mark = "✅" if analysis['roe_pass'] else "❌"
            st.markdown(f"### {check_mark} 2. Management Efficiency (ROE)")
            st.write("Is management good at using your money to make more money? Target > 15%.")
            st.caption(f"Return on Equity: {analysis['roe']:.1f}%")

            # Pillar 3: Debt
            check_mark = "✅" if analysis['debt_pass'] else "❌"
            st.markdown(f"### {check_mark} 3. Financial Fortress (Debt)")
            st.write("Can they pay off all long-term debt with less than 5 years of earnings?")
            if analysis['debt_years'] == 99:
                 st.caption("Earnings are negative, debt is risky.")
            else:
                st.caption(f"Years to pay off debt: {analysis['debt_years']:.1f} years")

        st.markdown("---")

        # --- PLAIN ENGLISH FINANCIALS ---
        st.header("📖 Financials Translated")
        st.markdown("Stop looking at complex spreadsheets. Here is the story of the money.")

        tab1, tab2, tab3 = st.tabs(["💰 The Income", "🏦 The Piggy Bank (Balance Sheet)", "💸 The Cash"])

        with tab1:
            # Visualizing Revenue vs Profit
            fin = data_pack['financials']
            years = fin.columns
            rev = fin.loc['Total Revenue']
            net = fin.loc['Net Income']
            
            fig_inc = go.Figure()
            fig_inc.add_trace(go.Bar(x=years, y=rev, name='Sales (Revenue)', marker_color='#444'))
            fig_inc.add_trace(go.Bar(x=years, y=net, name='Profit (Net Income)', marker_color='#4CAF50'))
            fig_inc.update_layout(title="Sales vs. Actual Profit", barmode='group')
            st.plotly_chart(fig_inc, use_container_width=True)
            
            st.info("""
            **How to read this:** 
            The **Grey bars** are the money the company collected from customers. 
            The **Green bars** are what is left over for YOU (the shareholder) after paying expenses, taxes, and interest.
            *We want to see both bars going up like a staircase.*
            """)

        with tab2:
            bs = data_pack['balance_sheet']
            # Plain English Translation
            cash = safe_get(bs, 'Cash And Cash Equivalents')
            debt = safe_get(bs, 'Total Debt')
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("Cash on Hand", f"${cash:,.0f}")
                st.markdown("*Money available to weather a storm.*")
            with col_b:
                st.metric("Total Debt", f"${debt:,.0f}")
                st.markdown("*Money they owe to banks/lenders.*")
            
            if cash > debt:
                st.success("✅ This company has more cash than debt. Very safe.")
            else:
                st.warning("⚠️ This company has more debt than cash. Not necessarily bad, but risky if earnings stop.")

        with tab3:
            st.subheader("Owner's Earnings (Free Cash Flow)")
            st.markdown("Earnings can be faked with accounting tricks. **Cash is fact.**")
            
            cf = data_pack['cashflow']
            try:
                op_cash = cf.loc['Operating Cash Flow']
                capex = cf.loc['Capital Expenditure']
                fcf = op_cash + capex
                
                fig_fcf = px.bar(x=fcf.index, y=fcf.values, title="Cash Left Over (Free Cash Flow)")
                fig_fcf.update_traces(marker_color='#2196F3')
                st.plotly_chart(fig_fcf, use_container_width=True)
            except:
                st.warning("Could not calculate Free Cash Flow from available data.")

            st.markdown("""
            **What is this?**
            Imagine you own a lemonade stand.
            1. You sell lemonade (Revenue).
            2. You pay for lemons and sugar (Expenses).
            3. You pay to fix the stand (Maintenance/Capex).
            4. Whatever cash is left in your pocket is **Free Cash Flow**. 
            """)

# Footer
st.markdown("---")
st.caption("Analyst: The Oracle's Lens Persona | Data: Yahoo Finance | Built with Streamlit")