import streamlit as st
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
from fyers_apiv3 import fyersModel
import pandas as pd
import datetime
import time

st.set_page_config(layout="wide", page_title="OA Sniper Dashboard")

# ==========================================
# 1. AUTO REFRESH
# ==========================================
st_autorefresh(interval=10000, limit=2000, key="auto_refresh")

# ==========================================
# 2. FYERS API CREDENTIALS
# ==========================================
CLIENT_ID = "BT8FRQLN19-200"  # உங்களின் Algo App ID
SECRET_KEY = "0ivLeQN8vdI2VyKA" # உங்களின் Algo Secret Key

# ஸ்லாஷ் இல்லாத பழைய ஒரிஜினல் லிங்க்
REDIRECT_URI = "https://oa-sniper.streamlit.app" 
EXPIRY = "26813" 

# ==========================================
# லூப் எரர் இல்லாத, மிக எளிய லாகின் சிஸ்டம்
# ==========================================
def fyers_auto_login():
    # ஏற்கனவே லாகின் ஆகியிருந்தால், டோக்கனைத் திருப்பி அனுப்பு
    if 'access_token' in st.session_state: 
        return st.session_state['access_token']
    
    # URL-ல் auth_code இருந்தால், டோக்கனை உருவாக்கு (எரர் வரக்கூடாது என்பதால் URL-ஐ கிளியர் செய்யவில்லை)
    if 'auth_code' in st.query_params:
        auth_code = st.query_params['auth_code']
        session = fyersModel.SessionModel(client_id=CLIENT_ID, secret_key=SECRET_KEY, redirect_uri=REDIRECT_URI, response_type="code", grant_type="authorization_code")
        session.set_token(auth_code)
        res = session.generate_token()
        
        if 'access_token' in res:
            st.session_state['access_token'] = res['access_token']
            return res['access_token']
    
    # லாகின் ஆகவில்லை என்றால் பட்டனைக் காட்டு
    session = fyersModel.SessionModel(client_id=CLIENT_ID, secret_key=SECRET_KEY, redirect_uri=REDIRECT_URI, response_type="code", grant_type="authorization_code")
    auth_link = session.generate_authcode()
    st.markdown(f'<a href="{auth_link}" target="_self"><button style="background-color:#4CAF50; color:white; padding:10px 20px; border:none; border-radius:5px; cursor:pointer;">🚀 Login with Fyers</button></a>', unsafe_allow_html=True)
    st.stop()

# Fyers Model-ஐ துவங்குதல்
fyers = fyersModel.FyersModel(client_id=CLIENT_ID, is_async=False, token=fyers_auto_login(), log_path="")

# ==========================================
# 3. GET NIFTY SPOT & CALCULATE STRIKES
# ==========================================
spot_price = 24200.0
try:
    res = fyers.quotes(data={"symbols": "NSE:NIFTY50-INDEX"})
    if res.get("s") == "ok": spot_price = res['d'][0]['v']['lp']
except: pass

atm_strike = int(round(spot_price / 50.0)) * 50

st.markdown(f"### 🎯 Nifty Spot: **{spot_price}**")

strike_type = st.radio("Select Strike Type:", ("ITM", "ATM", "OTM"), horizontal=True, index=1)
if strike_type == "ITM": selected_strike = atm_strike - 50
elif strike_type == "OTM": selected_strike = atm_strike + 50
else: selected_strike = atm_strike

# ==========================================
# 4. FETCH SELECTED STRIKE OI & 3-MIN LOGIC
# ==========================================
ce_sym = f"NSE:NIFTY{EXPIRY}{selected_strike}CE"
pe_sym = f"NSE:NIFTY{EXPIRY}{selected_strike}PE"

ce_oi, pe_oi, ce_chg, pe_chg = 0, 0, 0, 0

try:
    q_res = fyers.quotes(data={"symbols": f"{ce_sym},{pe_sym}"})
    if q_res.get("s") == "ok":
        for item in q_res['d']:
            val = item['v'].get('open_interest', 0)
            if item['n'] == ce_sym: ce_oi = val
            if item['n'] == pe_sym: pe_oi = val
except: pass

if 'tracker' not in st.session_state:
    st.session_state.tracker = {'ce_oi': ce_oi, 'pe_oi': pe_oi, 'time': time.time(), 'ce_diff': 0, 'pe_diff': 0}

current_time = time.time()
if current_time - st.session_state.tracker['time'] >= 180:
    st.session_state.tracker['ce_diff'] = ce_oi - st.session_state.tracker['ce_oi']
    st.session_state.tracker['pe_diff'] = pe_oi - st.session_state.tracker['pe_oi']
    st.session_state.tracker['ce_oi'] = ce_oi
    st.session_state.tracker['pe_oi'] = pe_oi
    st.session_state.tracker['time'] = current_time

ce_3min_diff = st.session_state.tracker['ce_diff']
pe_3min_diff = st.session_state.tracker['pe_diff']

# ==========================================
# 5. 5-COLUMN UI DESIGN
# ==========================================
st.markdown("---")
c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    st.markdown("<h4 style='text-align: center; color: red;'>CE OI</h4>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='text-align: center;'>{ce_oi}</h3>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: {'green' if ce_3min_diff > 0 else 'red'};'>({'+' if ce_3min_diff > 0 else ''}{ce_3min_diff} in 3m)</p>", unsafe_allow_html=True)

with c2:
    st.markdown("<h4 style='text-align: center; color: red;'>CE OI Chg</h4>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='text-align: center;'>{ce_chg}</h3>", unsafe_allow_html=True)

with c3:
    st.markdown("<h4 style='text-align: center; color: orange;'>STRIKE</h4>", unsafe_allow_html=True)
    st.markdown(f"<h2 style='text-align: center; background-color: #f0f2f6; padding: 10px; border-radius: 10px;'>{selected_strike}</h2>", unsafe_allow_html=True)

with c4:
    st.markdown("<h4 style='text-align: center; color: green;'>PE OI Chg</h4>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='text-align: center;'>{pe_chg}</h3>", unsafe_allow_html=True)

with c5:
    st.markdown("<h4 style='text-align: center; color: green;'>PE OI</h4>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='text-align: center;'>{pe_oi}</h3>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: {'green' if pe_3min_diff > 0 else 'red'};'>({'+' if pe_3min_diff > 0 else ''}{pe_3min_diff} in 3m)</p>", unsafe_allow_html=True)

st.markdown("---")

# ==========================================
# 6. CHART WITH AUTO SUPPORT/RESISTANCE
# ==========================================
symbols_list = [f"NSE:NIFTY{EXPIRY}{atm_strike + (i * 50)}CE" for i in range(-10, 11)] + [f"NSE:NIFTY{EXPIRY}{atm_strike + (i * 50)}PE" for i in range(-10, 11)]
max_ce_oi, max_pe_oi, res_strike, sup_strike = 0, 0, 0, 0

try:
    q_res2 = fyers.quotes(data={"symbols": ",".join(symbols_list)})
    if q_res2.get("s") == "ok":
        for item in q_res2['d']:
            oi = item['v'].get('open_interest', 0)
            val = int(item['n'][-7:-2])
            if "CE" in item['n'] and oi > max_ce_oi:
                max_ce_oi, res_strike = oi, val
            elif "PE" in item['n'] and oi > max_pe_oi:
                max_pe_oi, sup_strike = oi, val
except: pass

st.markdown("### 📈 Live Structure Chart")

hist_data = {"symbol": "NSE:NIFTY50-INDEX", "resolution": "5", "date_format": "1", 
             "range_from": datetime.date.today().strftime("%Y-%m-%d"), 
             "range_to": datetime.date.today().strftime("%Y-%m-%d"), "cont_flag": "1"}

df = pd.DataFrame()
try:
    hist_res = fyers.history(data=hist_data)
    if hist_res.get('s') == 'ok':
        df = pd.DataFrame(hist_res['candles'], columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df['Date'] = pd.to_datetime(df['Date'], unit='s').dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
except: pass

if not df.empty:
    fig = go.Figure(data=[go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Nifty")])
    if res_strike > 0: fig.add_hline(y=res_strike, line_width=2, line_dash="dash", line_color="red", annotation_text=f"Resistance: {res_strike}")
    if sup_strike > 0: fig.add_hline(y=sup_strike, line_width=2, line_dash="dash", line_color="green", annotation_text=f"Support: {sup_strike}")
    fig.update_layout(xaxis_rangeslider_visible=False, height=500, margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("மார்க்கெட் நேரம் முடிந்ததால் சார்ட் டேட்டா கிடைக்கவில்லை.")
