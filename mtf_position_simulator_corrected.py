
import streamlit as st
import requests

st.set_page_config(page_title="MTF Position Simulator", layout="wide")

# Fetch latest LTP from NSE API
@st.cache_data(ttl=60)
def fetch_ltp(symbol):
    url = f"https://www.nseindia.com/api/quote-equity?symbol={symbol.upper()}"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.nseindia.com/"
    }
    try:
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=headers, timeout=5)
        response = session.get(url, headers=headers, timeout=5)
        data = response.json()
        ltp_str = data["priceInfo"]["lastPrice"]
        return float(ltp_str.replace(",", ""))
    except:
        return None

# App UI
st.title("📊 MTF Position Simulator - Kotak Securities")

st.header("🔧 Position Setup")
symbol = st.text_input("Stock NSE Symbol", value="RELIANCE").upper()
ltp = fetch_ltp(symbol)

if ltp:
    st.success(f"Auto-fetched LTP for {symbol}: ₹{ltp}")
else:
    ltp = st.number_input("Enter LTP manually (NSE fetch failed)", value=2000.0)

investment = st.number_input("Investment Value (₹)", value=200000.0)
exposure = st.selectbox("Exposure (e.g. 3x, 4x, 5x)", [3, 4, 5], index=2)
target_price = st.number_input("Exit Target Price", value=2200.0)
stop_loss = st.number_input("Exit Stop Loss Price", value=1900.0)
holding_days = st.number_input("Position Duration (Days)", value=10)
interest_rate = st.number_input("Interest Rate p.a. (%)", value=18.0, format="%.8f")
brokerage_pct = st.number_input("Brokerage Rate (%)", value=0.03, format="%.8f")
txn_charges_pct = st.number_input("Transaction Charges (%)", value=0.00325, format="%.8f")
stt_pct = st.number_input("STT/CTT (%)", value=0.1, format="%.8f")
sebi_pct = st.number_input("SEBI Tax (%)", value=0.0001, format="%.8f")
stamp_pct = st.number_input("Stamp Duty (%)", value=0.015, format="%.8f")
gst_pct = st.number_input("GST (%)", value=18.0, format="%.8f")

# Calculations
position_value = investment * exposure
quantity = position_value / ltp
margin_funded = position_value - investment
interest_cost = (margin_funded * (interest_rate / 100)) * (holding_days / 365)
brokerage = position_value * (brokerage_pct / 100)
txn_charges = position_value * (txn_charges_pct / 100)
stt = position_value * (stt_pct / 100)
sebi = position_value * (sebi_pct / 100)
stamp = position_value * (stamp_pct / 100)
gst = (brokerage + txn_charges) * (gst_pct / 100)
total_charges = interest_cost + brokerage + txn_charges + stt + sebi + stamp + gst
breakeven_price = ltp + (total_charges / quantity)
daily_interest = (margin_funded * interest_rate / 100) / 365
ideal_days_to_breakeven = round(total_charges / daily_interest)

# Output
st.header("📈 Simulation Results")
col1, col2 = st.columns(2)
with col1:
    st.metric("Total Position Value (₹)", f"{position_value:,.2f}")
    st.metric("Quantity", f"{quantity:,.0f}")
    st.metric("Margin Funded by Broker (₹)", f"{margin_funded:,.2f}")
    st.metric("Per Day Interest (₹)", f"{daily_interest:,.2f}")
with col2:
    st.metric("Total Charges (₹)", f"{total_charges:,.2f}")
    st.metric("Breakeven Price (₹)", f"{breakeven_price:,.2f}")
    st.metric("Net P&L at Target (₹)", f"{(target_price - ltp) * quantity - total_charges:,.2f}")
    st.metric("Net P&L at Stop Loss (₹)", f"{(stop_loss - ltp) * quantity - total_charges:,.2f}")

st.info(f"📌 You will start making profit only if stock price rises above ₹{breakeven_price:,.2f}")

with st.expander("ℹ️ How is Ideal Holding Days calculated?"):
    st.markdown(f"""
        **Ideal Holding Days to Breakeven** tells you how many days you can hold this MTF position
        before charges eat into your capital.

        **Formula:**  
        `= Total Charges / Daily Interest Cost`  

        Daily Interest = (Margin Funded × Interest Rate p.a.) / 365  
        → ₹{margin_funded:,.2f} × {interest_rate}% / 365 = ₹{daily_interest:,.2f}

        👉 You should exit within **{ideal_days_to_breakeven} days** to avoid loss.
    """)
