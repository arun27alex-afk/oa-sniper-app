import streamlit as st
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
from fyers_apiv3 import fyersModel
import pandas as pd
import datetime
import time


# ============================================================
# PAGE SETTINGS
# ============================================================
st.set_page_config(
    layout="wide",
    page_title="Sniper OI Pro Dashboard",
    page_icon="🎯",
)


# ============================================================
# HEADER
# ============================================================
st.markdown(
    """
    <h1 style="text-align:center; margin-bottom:0;">
        🎯 Sniper OI Pro Dashboard
    </h1>

    <p style="
        text-align:center;
        color:#64748b;
        margin-top:6px;
    ">
        NIFTY Option Interest • Live Structure • Support / Resistance
    </p>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# FYERS CREDENTIALS
# ============================================================
try:

    CLIENT_ID = st.secrets["FYERS_CLIENT_ID"]
    SECRET_KEY = st.secrets["FYERS_SECRET_KEY"]
    REDIRECT_URI = st.secrets["FYERS_REDIRECT_URI"]

except Exception:

    st.error(
        "❌ FYERS credentials are missing from Streamlit Secrets."
    )

    st.code(
        """
FYERS_CLIENT_ID = "YOUR_APP_ID-100"
FYERS_SECRET_KEY = "YOUR_SECRET_KEY"
FYERS_REDIRECT_URI = "https://oa-sniper.streamlit.app"
        """.strip(),
        language="toml",
    )

    st.stop()


# ============================================================
# CREATE FYERS SESSION
# ============================================================
def create_fyers_session():

    return fyersModel.SessionModel(
        client_id=CLIENT_ID,
        secret_key=SECRET_KEY,
        redirect_uri=REDIRECT_URI,
        response_type="code",
        grant_type="authorization_code",
        state="sniper_oi",
    )


# ============================================================
# FYERS LOGIN
# ============================================================
def fyers_login():

    if st.session_state.get("access_token"):
        return st.session_state["access_token"]

    auth_code = st.query_params.get("auth_code")

    if auth_code:

        with st.status(
            "🔄 FYERS callback received. Generating access token...",
            expanded=True,
        ) as status:

            try:

                session = create_fyers_session()
                session.set_token(auth_code)
                token_response = session.generate_token()

                if (
                    isinstance(token_response, dict)
                    and token_response.get("s") == "ok"
                    and token_response.get("access_token")
                ):

                    st.session_state["access_token"] = (
                        token_response["access_token"]
                    )
                    st.session_state.pop("fyers_profile_verified", None)
                    st.query_params.clear()

                    status.update(
                        label="✅ FYERS access token generated",
                        state="complete",
                        expanded=False,
                    )
                    time.sleep(0.5)
                    st.rerun()

                st.error("❌ FYERS token generation failed.")
                st.json(token_response)
                status.update(
                    label="❌ FYERS token generation failed",
                    state="error",
                    expanded=True,
                )
                st.stop()

            except Exception as e:

                status.update(
                    label="❌ Exception during FYERS token generation",
                    state="error",
                    expanded=True,
                )
                st.exception(e)
                st.stop()

    try:

        session = create_fyers_session()
        auth_link = session.generate_authcode()
        st.info("FYERS login is required. Click the button below and complete login.")
        st.link_button(
            "🚀 Login with FYERS",
            auth_link,
            type="primary",
            use_container_width=True,
        )
        st.stop()

    except Exception as e:

        st.error("❌ Unable to create FYERS login URL.")
        st.exception(e)
        st.stop()


# ============================================================
# GET ACCESS TOKEN
# ============================================================
access_token = fyers_login()


# ============================================================
# CREATE FYERS CLIENT
# ============================================================
try:

    fyers = fyersModel.FyersModel(
        client_id=CLIENT_ID,
        is_async=False,
        token=access_token,
        log_path="",
    )

except Exception as e:

    st.error("❌ Unable to initialize FYERS.")
    st.exception(e)
    st.stop()


# ============================================================
# VALIDATE FYERS TOKEN
# ============================================================
if not st.session_state.get("fyers_profile_verified"):

    with st.status("🔄 Validating FYERS connection...", expanded=True) as status:
        try:
            profile_response = fyers.get_profile()

            if isinstance(profile_response, dict) and profile_response.get("s") == "ok":
                st.session_state["fyers_profile_verified"] = True
                status.update(label="✅ FYERS connected successfully", state="complete", expanded=False)
            else:
                st.error("❌ FYERS token/profile validation failed.")
                st.json(profile_response)
                st.session_state.pop("access_token", None)
                st.session_state.pop("fyers_profile_verified", None)
                status.update(label="❌ FYERS validation failed", state="error", expanded=True)
                st.stop()

        except Exception as e:
            status.update(label="❌ FYERS profile API failed", state="error", expanded=True)
            st.exception(e)
            st.stop()


# ============================================================
# CONNECTION STATUS
# ============================================================
top_left, top_right = st.columns([4, 1])

with top_left:
    st.success("✅ FYERS Connected")

with top_right:
    if st.button("🔄 Re-login FYERS", use_container_width=True):
        st.session_state.pop("access_token", None)
        st.session_state.pop("fyers_profile_verified", None)
        st.session_state.pop("oi_history", None)
        st.query_params.clear()
        st.rerun()


# ============================================================
# AUTO REFRESH (10 seconds)
# ============================================================
st_autorefresh(
    interval=10000,
    limit=2000,
    key="sniper_refresh",
)


# ============================================================
# FORMAT LAKHS HELPER FUNCTION
# ============================================================
def format_lakhs(value):
    try:
        val_in_lakhs = float(value) / 100000.0
        return f"{val_in_lakhs:.2f} L"
    except Exception:
        return "0.00 L"


# ============================================================
# GET NIFTY SPOT
# ============================================================
spot_price = 0.0
quote_response = {}

try:
    quote_response = fyers.quotes(data={"symbols": "NSE:NIFTY50-INDEX"})

    if isinstance(quote_response, dict) and quote_response.get("s") == "ok" and quote_response.get("d"):
        nifty_data = quote_response["d"][0]
        spot_price = float(nifty_data.get("v", {}).get("lp", 0) or 0)
    else:
        st.warning("⚠️ Unable to get NIFTY spot price.")

except Exception as e:
    st.error("❌ NIFTY quote error.")
    st.exception(e)


# ============================================================
# ATM STRIKE
# ============================================================
if spot_price > 0:
    atm_strike = int(round(spot_price / 50.0) * 50)
else:
    atm_strike = 0


# ============================================================
# DISPLAY NIFTY SPOT
# ============================================================
st.markdown(
    f"""
    <h2 style="text-align:center; margin-top:4px;">
        NIFTY Spot: <span style="color:#2563eb;">{spot_price:.2f}</span>
    </h2>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# FIRST OPTION CHAIN CALL
# ============================================================
base_option_chain_response = {}

try:
    base_option_chain_response = fyers.optionchain(
        data={"symbol": "NSE:NIFTY50-INDEX", "strikecount": 25, "timestamp": ""}
    )
except Exception as e:
    st.error("❌ Initial Option Chain API Error.")
    st.exception(e)


# ============================================================
# EXPIRY HELPERS
# ============================================================
def get_expiry_timestamp(item):
    for key in ("expiry", "timestamp", "expiryTimestamp", "expiry_timestamp"):
        value = item.get(key)
        if value not in (None, ""):
            return value
    return ""

def get_expiry_label(item):
    for key in ("date", "expiryDate", "expiry_date", "displayDate", "display_date"):
        value = item.get(key)
        if value:
            return str(value)

    timestamp = get_expiry_timestamp(item)
    if timestamp:
        try:
            ts = int(float(timestamp))
            dt = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
            ist = dt.astimezone(datetime.timezone(datetime.timedelta(hours=5, minutes=30)))
            return ist.strftime("%d-%b-%Y")
        except Exception:
            return str(timestamp)
    return "Current Expiry"


# ============================================================
# READ EXPIRY DATA
# ============================================================
expiry_data = []

if isinstance(base_option_chain_response, dict) and base_option_chain_response.get("s") == "ok":
    expiry_data = base_option_chain_response.get("data", {}).get("expiryData", []) or []


# ============================================================
# USER CONTROLS
# ============================================================
control1, control2 = st.columns(2)

with control1:
    strike_type = st.radio("Select Strike Type", ["ITM", "ATM", "OTM"], horizontal=True, index=1)

with control2:
    if expiry_data:
        expiry_labels = [get_expiry_label(item) for item in expiry_data]
        selected_expiry_index = st.selectbox(
            "Select Expiry", options=list(range(len(expiry_data))), format_func=lambda i: expiry_labels[i], index=0
        )
        selected_expiry_item = expiry_data[selected_expiry_index]
        selected_expiry_timestamp = get_expiry_timestamp(selected_expiry_item)
        selected_expiry_label = expiry_labels[selected_expiry_index]
    else:
        selected_expiry_timestamp = ""
        selected_expiry_label = "Current Expiry"
        st.text_input("Expiry", value=selected_expiry_label, disabled=True)


# ============================================================
# CE / PE STRIKE LOGIC
# ============================================================
if strike_type == "ITM":
    ce_selected_strike = atm_strike - 50
    pe_selected_strike = atm_strike + 50
elif strike_type == "OTM":
    ce_selected_strike = atm_strike + 50
    pe_selected_strike = atm_strike - 50
else:
    ce_selected_strike = atm_strike
    pe_selected_strike = atm_strike


# ============================================================
# FETCH SELECTED EXPIRY OPTION CHAIN
# ============================================================
option_chain_response = base_option_chain_response

if selected_expiry_timestamp:
    try:
        selected_chain_response = fyers.optionchain(
            data={"symbol": "NSE:NIFTY50-INDEX", "strikecount": 25, "timestamp": selected_expiry_timestamp}
        )
        if isinstance(selected_chain_response, dict) and selected_chain_response.get("s") == "ok":
            option_chain_response = selected_chain_response
        else:
            st.warning("⚠️ Selected expiry chain failed. Showing default current chain.")
    except Exception as e:
        st.warning("⚠️ Selected expiry request failed. Showing default current chain.")


# ============================================================
# CREATE OPTION CHAIN DATAFRAME
# ============================================================
option_chain_df = pd.DataFrame()

if isinstance(option_chain_response, dict) and option_chain_response.get("s") == "ok":
    options_data = option_chain_response.get("data", {}).get("optionsChain", []) or []
    if options_data:
        option_chain_df = pd.DataFrame(options_data)
    else:
        st.warning("⚠️ Option Chain returned no data.")
else:
    st.error("❌ Option Chain API failed.")


# ============================================================
# NORMALIZE COLUMN NAMES
# ============================================================
column_aliases = {
    "strikePrice": "strike_price",
    "strike": "strike_price",
    "optionType": "option_type",
    "last_price": "ltp",
    "lastPrice": "ltp",
    "open_interest": "oi",
    "openInterest": "oi",
}

pcr_value = 0.0

if not option_chain_df.empty:
    rename_map = {old: new for old, new in column_aliases.items() if old in option_chain_df.columns and new not in option_chain_df.columns}
    if rename_map:
        option_chain_df = option_chain_df.rename(columns=rename_map)

    for col in ["strike_price", "ltp", "oi", "volume"]:
        if col in option_chain_df.columns:
            option_chain_df[col] = pd.to_numeric(option_chain_df[col], errors="coerce")

    if "option_type" in option_chain_df.columns:
        option_chain_df["option_type"] = option_chain_df["option_type"].astype(str).str.upper().str.strip()

        # Calculate PCR dynamically based on all strikes returned in the chain
        tot_ce_oi = option_chain_df[option_chain_df["option_type"] == "CE"]["oi"].sum()
        tot_pe_oi = option_chain_df[option_chain_df["option_type"] == "PE"]["oi"].sum()
        if tot_ce_oi > 0:
            pcr_value = float(tot_pe_oi) / float(tot_ce_oi)

        option_chain_df = option_chain_df[option_chain_df["option_type"].isin(["CE", "PE"])].copy()


# ============================================================
# SAFE HELPERS
# ============================================================
def find_option_row(df, option_type, strike):
    required = {"option_type", "strike_price"}
    if df.empty or not required.issubset(df.columns):
        return None
    rows = df[(df["option_type"] == option_type) & (df["strike_price"] == strike)]
    if rows.empty:
        return None
    return rows.iloc[0]

def safe_int(value):
    try:
        if pd.isna(value): return 0
        return int(float(value))
    except Exception:
        return 0

def safe_float(value):
    try:
        if pd.isna(value): return 0.0
        return float(value)
    except Exception:
        return 0.0


# ============================================================
# GET SELECTED CE / PE DATA
# ============================================================
ce_oi = 0
pe_oi = 0
ce_ltp = 0.0
pe_ltp = 0.0

ce_row = find_option_row(option_chain_df, "CE", ce_selected_strike)
pe_row = find_option_row(option_chain_df, "PE", pe_selected_strike)

if ce_row is not None:
    ce_oi = safe_int(ce_row.get("oi", 0))
    ce_ltp = safe_float(ce_row.get("ltp", 0))

if pe_row is not None:
    pe_oi = safe_int(pe_row.get("oi", 0))
    pe_ltp = safe_float(pe_row.get("ltp", 0))


# ============================================================
# TRUE ROLLING 3-MINUTE OI TRACKER
# ============================================================
current_time = time.time()
oi_context_key = f"{selected_expiry_timestamp}|{strike_type}|CE:{ce_selected_strike}|PE:{pe_selected_strike}"

if st.session_state.get("oi_context_key") != oi_context_key:
    st.session_state["oi_context_key"] = oi_context_key
    st.session_state["oi_history"] = []

oi_history = st.session_state.get("oi_history", [])
oi_history.append({"timestamp": current_time, "ce_oi": ce_oi, "pe_oi": pe_oi})

oi_history = [sample for sample in oi_history if (current_time - sample["timestamp"] <= 600)]
st.session_state["oi_history"] = oi_history

target_time = current_time - 180
eligible_samples = [sample for sample in oi_history if (sample["timestamp"] <= target_time)]

if eligible_samples:
    baseline = max(eligible_samples, key=lambda sample: sample["timestamp"])
    ce_3min_diff = ce_oi - baseline["ce_oi"]
    pe_3min_diff = pe_oi - baseline["pe_oi"]
    oi_3min_ready = True
else:
    ce_3min_diff = 0
    pe_3min_diff = 0
    oi_3min_ready = False


# ============================================================
# TOP METRICS
# ============================================================
st.markdown("---")

c1, c2, c3, c4, c5 = st.columns(5)

# ------------------------------------------------------------
# CE OI
# ------------------------------------------------------------
with c1:
    st.markdown("""<h4 style="text-align:center; color:#dc2626; margin-bottom:5px;">CE OI</h4>""", unsafe_allow_html=True)
    st.markdown(f"""<h3 style="text-align:center; margin-top:0px;">{format_lakhs(ce_oi)}</h3>""", unsafe_allow_html=True)

    if oi_3min_ready:
        diff_color = "#16a34a" if ce_3min_diff < 0 else "#dc2626"  # Call writers exiting is bullish (Green), adding is bearish (Red)
        diff_sign = "+" if ce_3min_diff > 0 else "-"
        diff_val = format_lakhs(abs(ce_3min_diff))
        diff_text = f"({diff_sign}{diff_val})"
    else:
        diff_color = "#64748b"
        diff_text = "(Building 3m...)"

    st.markdown(f"""<p style="text-align:center; font-weight:bold; color:{diff_color};">{diff_text}</p>""", unsafe_allow_html=True)


# ------------------------------------------------------------
# CE LTP
# ------------------------------------------------------------
with c2:
    st.markdown("""<h4 style="text-align:center; color:#dc2626; margin-bottom:5px;">CE LTP</h4>""", unsafe_allow_html=True)
    st.markdown(f"""<h3 style="text-align:center; margin-top:0px;">₹{ce_ltp:.2f}</h3>""", unsafe_allow_html=True)
    st.caption(f"Strike: {ce_selected_strike}")


# ------------------------------------------------------------
# ATM & PCR
# ------------------------------------------------------------
with c3:
    st.markdown("""<h4 style="text-align:center; color:#f59e0b; margin-bottom:5px;">ATM</h4>""", unsafe_allow_html=True)
    st.markdown(f"""
        <h2 style="text-align:center; background:#f1f5f9; padding:10px; border-radius:10px; color:#0f172a; margin-top:0px;">
            {atm_strike}
        </h2>
    """, unsafe_allow_html=True)

    pcr_color = "#16a34a" if pcr_value >= 1.0 else "#dc2626"
    st.markdown(f"""
        <div style="text-align:center; margin-top:-5px; margin-bottom:10px;">
            <span style="font-size:14px; font-weight:bold; color:#64748b;">PCR: </span>
            <span style="font-size:18px; font-weight:bold; color:{pcr_color};">{pcr_value:.2f}</span>
        </div>
    """, unsafe_allow_html=True)


# ------------------------------------------------------------
# PE LTP
# ------------------------------------------------------------
with c4:
    st.markdown("""<h4 style="text-align:center; color:#16a34a; margin-bottom:5px;">PE LTP</h4>""", unsafe_allow_html=True)
    st.markdown(f"""<h3 style="text-align:center; margin-top:0px;">₹{pe_ltp:.2f}</h3>""", unsafe_allow_html=True)
    st.caption(f"Strike: {pe_selected_strike}")


# ------------------------------------------------------------
# PE OI
# ------------------------------------------------------------
with c5:
    st.markdown("""<h4 style="text-align:center; color:#16a34a; margin-bottom:5px;">PE OI</h4>""", unsafe_allow_html=True)
    st.markdown(f"""<h3 style="text-align:center; margin-top:0px;">{format_lakhs(pe_oi)}</h3>""", unsafe_allow_html=True)

    if oi_3min_ready:
        diff_color = "#16a34a" if pe_3min_diff > 0 else "#dc2626"  # Put writers adding is bullish (Green), exiting is bearish (Red)
        diff_sign = "+" if pe_3min_diff > 0 else "-"
        diff_val = format_lakhs(abs(pe_3min_diff))
        diff_text = f"({diff_sign}{diff_val})"
    else:
        diff_color = "#64748b"
        diff_text = "(Building 3m...)"

    st.markdown(f"""<p style="text-align:center; font-weight:bold; color:{diff_color};">{diff_text}</p>""", unsafe_allow_html=True)

st.markdown("---")


# ============================================================
# DYNAMIC S/R (ALGORITHM-BASED FROM ENTIRE OPTION CHAIN)
# ============================================================
max_ce_oi = 0
max_pe_oi = 0
res_strike = 0
sup_strike = 0

if not option_chain_df.empty:
    required_cols = {"option_type", "oi", "strike_price"}
    if required_cols.issubset(option_chain_df.columns):
        
        ce_df = option_chain_df[option_chain_df["option_type"] == "CE"].dropna(subset=["oi", "strike_price"]).copy()
        pe_df = option_chain_df[option_chain_df["option_type"] == "PE"].dropna(subset=["oi", "strike_price"]).copy()

        if not ce_df.empty:
            max_ce_row = ce_df.loc[ce_df["oi"].idxmax()]
            max_ce_oi = safe_int(max_ce_row["oi"])
            res_strike = safe_int(max_ce_row["strike_price"])

        if not pe_df.empty:
            max_pe_row = pe_df.loc[pe_df["oi"].idxmax()]
            max_pe_oi = safe_int(max_pe_row["oi"])
            sup_strike = safe_int(max_pe_row["strike_price"])


# ============================================================
# SUPPORT / RESISTANCE UI BOXES
# ============================================================
r1, r2 = st.columns(2)

with r1:
    st.markdown(f"""
        <div style="background:#fee2e2; padding:18px; border-radius:12px; text-align:center; border: 1px solid #fca5a5;">
            <h4 style="color:#dc2626; margin-bottom:5px;">🔴 Dynamic Resistance</h4>
            <h2 style="color:#0f172a; margin:0px;">{res_strike if res_strike else "N/A"}</h2>
            <p style="color:#334155; margin-top:5px; font-weight:bold;">Highest CE OI: {format_lakhs(max_ce_oi)}</p>
        </div>
    """, unsafe_allow_html=True)

with r2:
    st.markdown(f"""
        <div style="background:#dcfce7; padding:18px; border-radius:12px; text-align:center; border: 1px solid #86efac;">
            <h4 style="color:#16a34a; margin-bottom:5px;">🟢 Dynamic Support</h4>
            <h2 style="color:#0f172a; margin:0px;">{sup_strike if sup_strike else "N/A"}</h2>
            <p style="color:#334155; margin-top:5px; font-weight:bold;">Highest PE OI: {format_lakhs(max_pe_oi)}</p>
        </div>
    """, unsafe_allow_html=True)


# ============================================================
# OPTION CHAIN TABLE
# ============================================================
st.markdown("---")
st.markdown("### 📊 NIFTY Option Chain")

if not option_chain_df.empty:
    table_columns = [column for column in ["symbol", "option_type", "strike_price", "ltp", "oi", "volume"] if column in option_chain_df.columns]
    display_df = option_chain_df[table_columns].copy()
    sort_cols = [col for col in ["strike_price", "option_type"] if col in display_df.columns]

    if sort_cols:
        display_df = display_df.sort_values(by=sort_cols)
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
else:
    st.warning("⚠️ Option Chain data unavailable.")


# ============================================================
# NIFTY 5-MINUTE CHART (WITH DYNAMIC S/R LINES & MOBILE ZOOM)
# ============================================================
st.markdown("---")
st.markdown("### 📈 NIFTY Live Structure Chart")

today_date = datetime.date.today()
range_from = (today_date - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
range_to = today_date.strftime("%Y-%m-%d")

history_data = {"symbol": "NSE:NIFTY50-INDEX", "resolution": "5", "date_format": "1", "range_from": range_from, "range_to": range_to, "cont_flag": "1"}
history_df = pd.DataFrame()

try:
    history_response = fyers.history(data=history_data)
    if isinstance(history_response, dict) and history_response.get("s") == "ok":
        candles = history_response.get("candles", []) or []
        if candles:
            history_df = pd.DataFrame(candles, columns=["Date", "Open", "High", "Low", "Close", "Volume"])
            history_df["Date"] = pd.to_datetime(history_df["Date"], unit="s", utc=True).dt.tz_convert("Asia/Kolkata")
            latest_trade_date = history_df["Date"].dt.date.max()
            history_df = history_df[history_df["Date"].dt.date == latest_trade_date].copy()
except Exception as e:
    st.error("❌ History API Error.")
    st.exception(e)

if not history_df.empty:
    fig = go.Figure()

    # Candlestick
    fig.add_trace(go.Candlestick(x=history_df["Date"], open=history_df["Open"], high=history_df["High"], low=history_df["Low"], close=history_df["Close"], name="NIFTY"))

    # Dynamic Resistance Line (Red)
    if res_strike > 0:
        fig.add_hline(y=res_strike, line_width=2, line_dash="dash", line_color="red", annotation_text=f"Resistance: {res_strike}", annotation_position="top left", annotation_font_color="red")

    # Dynamic Support Line (Green)
    if sup_strike > 0:
        fig.add_hline(y=sup_strike, line_width=2, line_dash="dash", line_color="green", annotation_text=f"Support: {sup_strike}", annotation_position="bottom left", annotation_font_color="green")

    # ATM Line
    if atm_strike > 0:
        fig.add_hline(y=atm_strike, line_width=1, line_dash="dot", line_color="gray", annotation_text=f"ATM: {atm_strike}", annotation_position="top right")

    # Chart Mobile & Touch Settings
    fig.update_layout(
        xaxis_rangeslider_visible=False,
        dragmode='pan', # Enables 1-finger pan on mobile
        height=550,
        margin=dict(l=0, r=0, t=30, b=0),
    )

    # Plotly Chart with Mobile Scroll/Pinch Zoom enabled
    st.plotly_chart(
        fig, 
        use_container_width=True, 
        config={
            'scrollZoom': True,       # Enables 2-finger pinch-to-zoom
            'displayModeBar': False   # Hides the distracting modebar on mobile
        }
    )
else:
    st.warning("⚠️ NIFTY chart data is unavailable for the last 7 days.")

# ============================================================
# DEBUG INFORMATION
# ============================================================
with st.expander("🔧 Debug Information"):
    st.write("FYERS Login:", "✅")
    st.write("Client ID:", CLIENT_ID)
    st.write("Redirect URI:", REDIRECT_URI)
    st.write("NIFTY Spot:", spot_price)
    st.write("ATM Strike:", atm_strike)
    st.write("Strike Type:", strike_type)
    st.write("CE Selected Strike:", ce_selected_strike)
    st.write("PE Selected Strike:", pe_selected_strike)
    st.write("Selected Expiry:", selected_expiry_label)
    st.write("Selected Expiry Timestamp:", selected_expiry_timestamp)
    st.write("3-Min OI Ready:", oi_3min_ready)
    st.write("Option Chain Columns:", list(option_chain_df.columns) if not option_chain_df.empty else [])
    
    st.write("Option Chain Response:")
    if option_chain_response: st.json(option_chain_response)
    else: st.write("No option chain response received.")

    st.write("Quote Response:")
    if quote_response: st.json(quote_response)
    else: st.write("No quote response received.")
