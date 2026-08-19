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
        st.session_state.pop("oi_history_by_contract", None)
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
#
# IMPORTANT FIX:
# Do NOT reset history when ATM / ITM / OTM strike changes.
# NIFTY can move across a 50-point ATM boundary and the old logic
# kept clearing the 3-minute history, so it could stay on
# "Building 3m..." continuously.
#
# Instead, store OI history separately for EVERY option contract
# returned by the option chain: Expiry + CE/PE + Strike.
# ============================================================
current_time = time.time()
OI_LOOKBACK_SECONDS = 180   # exactly 3 minutes
OI_KEEP_SECONDS = 900       # keep 15 minutes of samples

# Stable expiry identifier for history storage.
# Normalize numeric timestamps so 178... and "178..." become the same key.
if selected_expiry_timestamp not in (None, ""):
    try:
        expiry_history_key = str(int(float(selected_expiry_timestamp)))
    except Exception:
        expiry_history_key = str(selected_expiry_timestamp)
else:
    expiry_history_key = str(selected_expiry_label)

# Dictionary structure:
# {
#   "expiry|CE|24100": [{"timestamp": ..., "oi": ...}, ...],
#   "expiry|PE|24100": [{"timestamp": ..., "oi": ...}, ...]
# }
if "oi_history_by_contract" not in st.session_state:
    st.session_state["oi_history_by_contract"] = {}

oi_store = st.session_state["oi_history_by_contract"]

# Save the current OI of ALL CE/PE strikes on every 10-second refresh.
# This means even if ATM changes from 24100 -> 24150 -> 24100,
# each strike keeps its own history and the 3-minute comparison survives.
required_history_cols = {"option_type", "strike_price", "oi"}

if not option_chain_df.empty and required_history_cols.issubset(option_chain_df.columns):
    history_rows = option_chain_df.dropna(subset=["option_type", "strike_price", "oi"])

    for _, row in history_rows.iterrows():
        option_type_value = str(row.get("option_type", "")).upper().strip()
        strike_value = safe_int(row.get("strike_price", 0))
        oi_value = safe_int(row.get("oi", 0))

        if option_type_value not in ("CE", "PE") or strike_value <= 0:
            continue

        contract_key = f"{expiry_history_key}|{option_type_value}|{strike_value}"
        samples = oi_store.get(contract_key, [])

        samples.append({
            "timestamp": current_time,
            "oi": oi_value,
        })

        # Keep only recent history so session memory does not keep growing
        samples = [
            sample
            for sample in samples
            if current_time - sample["timestamp"] <= OI_KEEP_SECONDS
        ]

        oi_store[contract_key] = samples

# Remove expired/empty contract histories
for contract_key in list(oi_store.keys()):
    samples = [
        sample
        for sample in oi_store.get(contract_key, [])
        if current_time - sample["timestamp"] <= OI_KEEP_SECONDS
    ]

    if samples:
        oi_store[contract_key] = samples
    else:
        oi_store.pop(contract_key, None)

st.session_state["oi_history_by_contract"] = oi_store


def get_3min_oi_change(option_type, strike, current_oi):
    """
    Return:
        diff          -> current OI minus OI approximately 3 minutes ago
        ready         -> True only after a >=180-second baseline exists
        history_age   -> seconds since the oldest available sample
        sample_count  -> number of stored samples for this contract
    """
    contract_key = f"{expiry_history_key}|{option_type}|{int(strike)}"
    samples = oi_store.get(contract_key, [])

    if not samples:
        return 0, False, 0, 0

    oldest_timestamp = min(sample["timestamp"] for sample in samples)
    history_age = max(0, current_time - oldest_timestamp)

    target_time = current_time - OI_LOOKBACK_SECONDS
    eligible_samples = [
        sample for sample in samples
        if sample["timestamp"] <= target_time
    ]

    if not eligible_samples:
        return 0, False, history_age, len(samples)

    # Pick the closest sample at or before exactly 3 minutes ago
    baseline = max(eligible_samples, key=lambda sample: sample["timestamp"])
    diff = safe_int(current_oi) - safe_int(baseline.get("oi", 0))

    return diff, True, history_age, len(samples)


def building_text(history_age):
    remaining = max(0, OI_LOOKBACK_SECONDS - int(history_age))
    minutes, seconds = divmod(remaining, 60)
    return f"(Building {minutes}m {seconds:02d}s...)"


def oi_change_text(diff):
    if diff > 0:
        sign = "+"
    elif diff < 0:
        sign = "-"
    else:
        sign = ""

    return f"({sign}{format_lakhs(abs(diff))})"


ce_3min_diff, ce_3min_ready, ce_history_age, ce_history_samples = get_3min_oi_change(
    "CE", ce_selected_strike, ce_oi
)

pe_3min_diff, pe_3min_ready, pe_history_age, pe_history_samples = get_3min_oi_change(
    "PE", pe_selected_strike, pe_oi
)

# Kept for debug/backward compatibility
oi_3min_ready = ce_3min_ready and pe_3min_ready


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

    if ce_3min_ready:
        if ce_3min_diff < 0:
            diff_color = "#16a34a"  # Call writers exiting = bullish
        elif ce_3min_diff > 0:
            diff_color = "#dc2626"  # Call writers adding = bearish
        else:
            diff_color = "#64748b"
        diff_text = oi_change_text(ce_3min_diff)
    else:
        diff_color = "#64748b"
        diff_text = building_text(ce_history_age)

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

    if pe_3min_ready:
        if pe_3min_diff > 0:
            diff_color = "#16a34a"  # Put writers adding = bullish
        elif pe_3min_diff < 0:
            diff_color = "#dc2626"  # Put writers exiting = bearish
        else:
            diff_color = "#64748b"
        diff_text = oi_change_text(pe_3min_diff)
    else:
        diff_color = "#64748b"
        diff_text = building_text(pe_history_age)

    st.markdown(f"""<p style="text-align:center; font-weight:bold; color:{diff_color};">{diff_text}</p>""", unsafe_allow_html=True)

st.markdown("---")


# ============================================================
# NIFTY 5-MINUTE PRICE HISTORY
#
# Used BEFORE support/resistance calculation so the S/R engine can
# adapt itself to the current intraday volatility instead of blindly
# choosing the highest OI strike anywhere in the option chain.
# ============================================================
today_date = datetime.date.today()
range_from = (today_date - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
range_to = today_date.strftime("%Y-%m-%d")

history_data = {
    "symbol": "NSE:NIFTY50-INDEX",
    "resolution": "5",
    "date_format": "1",
    "range_from": range_from,
    "range_to": range_to,
    "cont_flag": "1",
}

history_df = pd.DataFrame()

try:
    history_response = fyers.history(data=history_data)

    if isinstance(history_response, dict) and history_response.get("s") == "ok":
        candles = history_response.get("candles", []) or []

        if candles:
            history_df = pd.DataFrame(
                candles,
                columns=["Date", "Open", "High", "Low", "Close", "Volume"],
            )

            history_df["Date"] = (
                pd.to_datetime(history_df["Date"], unit="s", utc=True)
                .dt.tz_convert("Asia/Kolkata")
            )

            latest_trade_date = history_df["Date"].dt.date.max()
            history_df = history_df[
                history_df["Date"].dt.date == latest_trade_date
            ].copy()

            for col in ["Open", "High", "Low", "Close", "Volume"]:
                history_df[col] = pd.to_numeric(history_df[col], errors="coerce")

            history_df = history_df.dropna(
                subset=["Open", "High", "Low", "Close"]
            ).sort_values("Date")

except Exception as e:
    st.warning("⚠️ 5-minute history unavailable for adaptive S/R. Using fallback range.")


# ============================================================
# ADAPTIVE INTRADAY SUPPORT / RESISTANCE ENGINE
# ============================================================
# OLD ISSUE:
# Highest CE/PE OI across the full option chain can select very distant
# strikes (example: 24500 resistance when NIFTY is around 24100).
# That can be useful as a positional OI wall, but is often not useful
# as an INTRADAY support/resistance level.
#
# NEW LOGIC:
# 1. Calculate current 5-minute ATR / recent one-hour price range.
# 2. Build an adaptive strike search band around current NIFTY price.
# 3. Resistance candidates = CE strikes above/near ATM inside the band.
# 4. Support candidates    = PE strikes below/near ATM inside the band.
# 5. Rank candidates using:
#       - Current OI strength
#       - 3-minute OI build-up / unwinding
#       - Option volume
#       - Recent price-action high/low proximity
#       - Distance from current spot
# This makes S/R move with the market instead of being anchored to a
# distant maximum-OI strike.
# ============================================================

atr_5m = 0.0
recent_1h_range = 0.0
recent_high = spot_price
recent_low = spot_price

if not history_df.empty:
    recent_candles = history_df.tail(12).copy()  # approx. last 60 minutes

    if not recent_candles.empty:
        recent_high = safe_float(recent_candles["High"].max())
        recent_low = safe_float(recent_candles["Low"].min())
        recent_1h_range = max(0.0, recent_high - recent_low)

        previous_close = recent_candles["Close"].shift(1)
        true_range = pd.concat(
            [
                recent_candles["High"] - recent_candles["Low"],
                (recent_candles["High"] - previous_close).abs(),
                (recent_candles["Low"] - previous_close).abs(),
            ],
            axis=1,
        ).max(axis=1)

        if not true_range.dropna().empty:
            atr_5m = safe_float(true_range.dropna().tail(12).mean())

# Adaptive range:
# - Minimum ±150 points: enough room to identify a genuine nearby wall.
# - Expands automatically when intraday volatility increases.
# - Hard cap ±350 points prevents positional/far OI from dominating.
raw_sr_band = max(
    150.0,
    atr_5m * 6.0,
    recent_1h_range * 0.90,
)

adaptive_sr_band = int(round(raw_sr_band / 50.0) * 50)
adaptive_sr_band = max(150, min(350, adaptive_sr_band))

# Candidate boundaries are based on live spot, not a fixed strike count.
support_floor = spot_price - adaptive_sr_band
resistance_ceiling = spot_price + adaptive_sr_band

max_ce_oi = 0
max_pe_oi = 0
res_strike = 0
sup_strike = 0
res_score = 0.0
sup_score = 0.0
res_3min_change = 0
sup_3min_change = 0


def build_sr_candidates(df, option_type):
    required = {"option_type", "strike_price", "oi"}
    if df.empty or not required.issubset(df.columns):
        return pd.DataFrame()

    side_df = df[df["option_type"] == option_type].copy()
    side_df = side_df.dropna(subset=["strike_price", "oi"])

    if side_df.empty:
        return side_df

    if option_type == "CE":
        # Resistance should be at/above ATM and within adaptive range.
        side_df = side_df[
            (side_df["strike_price"] >= atm_strike)
            & (side_df["strike_price"] <= resistance_ceiling)
        ].copy()
    else:
        # Support should be at/below ATM and within adaptive range.
        side_df = side_df[
            (side_df["strike_price"] <= atm_strike)
            & (side_df["strike_price"] >= support_floor)
        ].copy()

    return side_df


def rank_intraday_sr(candidate_df, option_type):
    """
    Returns the strongest nearby intraday OI wall.

    Score components:
        40% current OI
        25% 3-minute OI change
        15% recent price-action proximity
        10% option volume
        10% proximity to current spot
    """
    if candidate_df.empty:
        return None

    work = candidate_df.copy()

    # Current 3-minute OI change for every candidate strike.
    oi_changes = []
    oi_change_ready = []

    for _, row in work.iterrows():
        strike = safe_int(row.get("strike_price", 0))
        current_oi_value = safe_int(row.get("oi", 0))
        diff, ready, _, _ = get_3min_oi_change(
            option_type,
            strike,
            current_oi_value,
        )
        oi_changes.append(diff)
        oi_change_ready.append(ready)

    work["oi_3m_change"] = oi_changes
    work["oi_3m_ready"] = oi_change_ready

    # Normalized current OI strength.
    max_oi = max(safe_float(work["oi"].max()), 1.0)
    work["oi_strength"] = work["oi"].fillna(0).astype(float) / max_oi

    # Normalized volume strength (if FYERS provides volume).
    if "volume" in work.columns:
        max_volume = max(safe_float(work["volume"].fillna(0).max()), 1.0)
        work["volume_strength"] = (
            work["volume"].fillna(0).astype(float) / max_volume
        )
    else:
        work["volume_strength"] = 0.0

    # Positive OI addition strengthens a wall; OI unwinding weakens it.
    ready_changes = work.loc[work["oi_3m_ready"], "oi_3m_change"].abs()
    max_abs_change = max(safe_float(ready_changes.max()) if not ready_changes.empty else 0.0, 1.0)

    def change_strength(row):
        if not bool(row["oi_3m_ready"]):
            return 0.0
        value = safe_float(row["oi_3m_change"]) / max_abs_change
        return max(-1.0, min(1.0, value))

    work["change_strength"] = work.apply(change_strength, axis=1)

    # Recent price action confirmation:
    # CE resistance gets a bonus near the recent swing high.
    # PE support gets a bonus near the recent swing low.
    price_reference = recent_high if option_type == "CE" else recent_low
    price_scale = max(75.0, adaptive_sr_band * 0.60)
    work["price_action_strength"] = (
        1.0
        - ((work["strike_price"].astype(float) - price_reference).abs() / price_scale)
    ).clip(lower=0.0, upper=1.0)

    # Nearby strikes receive a small preference, but proximity alone
    # cannot overpower a genuine OI wall.
    work["spot_proximity"] = (
        1.0
        - ((work["strike_price"].astype(float) - spot_price).abs() / max(adaptive_sr_band, 1))
    ).clip(lower=0.0, upper=1.0)

    work["sr_score"] = (
        0.40 * work["oi_strength"]
        + 0.25 * work["change_strength"]
        + 0.15 * work["price_action_strength"]
        + 0.10 * work["volume_strength"]
        + 0.10 * work["spot_proximity"]
    )

    # If OI history has not completed 3 minutes yet, redistribute the
    # change weight to current OI so the level still works immediately.
    if not work["oi_3m_ready"].any():
        work["sr_score"] = (
            0.60 * work["oi_strength"]
            + 0.15 * work["price_action_strength"]
            + 0.10 * work["volume_strength"]
            + 0.15 * work["spot_proximity"]
        )

    return work.loc[work["sr_score"].idxmax()]


ce_candidates = build_sr_candidates(option_chain_df, "CE")
pe_candidates = build_sr_candidates(option_chain_df, "PE")

best_resistance = rank_intraday_sr(ce_candidates, "CE")
best_support = rank_intraday_sr(pe_candidates, "PE")

if best_resistance is not None:
    res_strike = safe_int(best_resistance.get("strike_price", 0))
    max_ce_oi = safe_int(best_resistance.get("oi", 0))
    res_score = safe_float(best_resistance.get("sr_score", 0))
    res_3min_change = safe_int(best_resistance.get("oi_3m_change", 0))

if best_support is not None:
    sup_strike = safe_int(best_support.get("strike_price", 0))
    max_pe_oi = safe_int(best_support.get("oi", 0))
    sup_score = safe_float(best_support.get("sr_score", 0))
    sup_3min_change = safe_int(best_support.get("oi_3m_change", 0))

# Fallback: if one side has no strike inside the adaptive band,
# use the nearest available strike on the correct side of ATM.
if res_strike <= 0 and not option_chain_df.empty:
    fallback_ce = option_chain_df[
        (option_chain_df["option_type"] == "CE")
        & (option_chain_df["strike_price"] >= atm_strike)
    ].copy()
    if not fallback_ce.empty:
        nearest_idx = (fallback_ce["strike_price"] - spot_price).abs().idxmin()
        nearest_row = fallback_ce.loc[nearest_idx]
        res_strike = safe_int(nearest_row.get("strike_price", 0))
        max_ce_oi = safe_int(nearest_row.get("oi", 0))

if sup_strike <= 0 and not option_chain_df.empty:
    fallback_pe = option_chain_df[
        (option_chain_df["option_type"] == "PE")
        & (option_chain_df["strike_price"] <= atm_strike)
    ].copy()
    if not fallback_pe.empty:
        nearest_idx = (fallback_pe["strike_price"] - spot_price).abs().idxmin()
        nearest_row = fallback_pe.loc[nearest_idx]
        sup_strike = safe_int(nearest_row.get("strike_price", 0))
        max_pe_oi = safe_int(nearest_row.get("oi", 0))


# ============================================================
# SUPPORT / RESISTANCE UI BOXES
# ============================================================
r1, r2 = st.columns(2)

with r1:
    st.markdown(f"""
        <div style="background:#fee2e2; padding:18px; border-radius:12px; text-align:center; border: 1px solid #fca5a5;">
            <h4 style="color:#dc2626; margin-bottom:5px;">🔴 Intraday Resistance</h4>
            <h2 style="color:#0f172a; margin:0px;">{res_strike if res_strike else "N/A"}</h2>
            <p style="color:#334155; margin-top:5px; margin-bottom:2px; font-weight:bold;">CE OI: {format_lakhs(max_ce_oi)}</p>
            <p style="color:#64748b; margin:0px; font-size:13px;">3m OI: {oi_change_text(res_3min_change)}</p>
        </div>
    """, unsafe_allow_html=True)

with r2:
    st.markdown(f"""
        <div style="background:#dcfce7; padding:18px; border-radius:12px; text-align:center; border: 1px solid #86efac;">
            <h4 style="color:#16a34a; margin-bottom:5px;">🟢 Intraday Support</h4>
            <h2 style="color:#0f172a; margin:0px;">{sup_strike if sup_strike else "N/A"}</h2>
            <p style="color:#334155; margin-top:5px; margin-bottom:2px; font-weight:bold;">PE OI: {format_lakhs(max_pe_oi)}</p>
            <p style="color:#64748b; margin:0px; font-size:13px;">3m OI: {oi_change_text(sup_3min_change)}</p>
        </div>
    """, unsafe_allow_html=True)

st.caption(
    f"Adaptive intraday S/R range: ±{adaptive_sr_band} pts"
    f" | 5m ATR: {atr_5m:.1f}"
    f" | Recent 1h range: {recent_1h_range:.1f}"
)


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
# NIFTY 5-MINUTE CHART (WITH ADAPTIVE S/R LINES & MOBILE ZOOM)
# ============================================================
st.markdown("---")
st.markdown("### 📈 NIFTY Live Structure Chart")

if not history_df.empty:
    fig = go.Figure()

    # Candlestick
    fig.add_trace(
        go.Candlestick(
            x=history_df["Date"],
            open=history_df["Open"],
            high=history_df["High"],
            low=history_df["Low"],
            close=history_df["Close"],
            name="NIFTY",
        )
    )

    # Adaptive Resistance Line (Red)
    if res_strike > 0:
        fig.add_hline(
            y=res_strike,
            line_width=2,
            line_dash="dash",
            line_color="red",
            annotation_text=f"Resistance: {res_strike}",
            annotation_position="top left",
            annotation_font_color="red",
        )

    # Adaptive Support Line (Green)
    if sup_strike > 0:
        fig.add_hline(
            y=sup_strike,
            line_width=2,
            line_dash="dash",
            line_color="green",
            annotation_text=f"Support: {sup_strike}",
            annotation_position="bottom left",
            annotation_font_color="green",
        )

    # ATM Line
    if atm_strike > 0:
        fig.add_hline(
            y=atm_strike,
            line_width=1,
            line_dash="dot",
            line_color="gray",
            annotation_text=f"ATM: {atm_strike}",
            annotation_position="top right",
        )

    # Chart Mobile & Touch Settings
    fig.update_layout(
        xaxis_rangeslider_visible=False,
        dragmode="pan",
        height=550,
        margin=dict(l=0, r=0, t=30, b=0),
    )

    # Plotly Chart with Mobile Scroll/Pinch Zoom enabled
    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "scrollZoom": True,
            "displayModeBar": False,
        },
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
    st.write("CE 3-Min Ready:", ce_3min_ready)
    st.write("PE 3-Min Ready:", pe_3min_ready)
    st.write("CE History Age (sec):", round(ce_history_age, 1))
    st.write("PE History Age (sec):", round(pe_history_age, 1))
    st.write("CE History Samples:", ce_history_samples)
    st.write("PE History Samples:", pe_history_samples)
    st.write("Tracked OI Contracts:", len(st.session_state.get("oi_history_by_contract", {})))
    st.write("Adaptive S/R Band:", adaptive_sr_band)
    st.write("5m ATR:", round(atr_5m, 2))
    st.write("Recent 1h Range:", round(recent_1h_range, 2))
    st.write("Recent High:", round(recent_high, 2))
    st.write("Recent Low:", round(recent_low, 2))
    st.write("Resistance Score:", round(res_score, 4))
    st.write("Support Score:", round(sup_score, 4))
    st.write("Resistance 3m OI Change:", res_3min_change)
    st.write("Support 3m OI Change:", sup_3min_change)
    st.write("Option Chain Columns:", list(option_chain_df.columns) if not option_chain_df.empty else [])
    
    st.write("Option Chain Response:")
    if option_chain_response: st.json(option_chain_response)
    else: st.write("No option chain response received.")

    st.write("Quote Response:")
    if quote_response: st.json(quote_response)
    else: st.write("No quote response received.")
