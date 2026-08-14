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
    page_icon="🎯"
)

# ============================================================
# FYERS CREDENTIALS
# ============================================================
# IMPORTANT:
# Replace these 3 values with your actual FYERS App details.
#
# Example:
# CLIENT_ID = "JFBDGDNQ04-100"
# SECRET_KEY = "SENO8XK3VL"
# REDIRECT_URI = "https://oa-sniper.streamlit.app"
#
# The REDIRECT_URI must EXACTLY match the URI configured
# in your FYERS API application.
# ============================================================

CLIENT_ID = "YOUR_APP_ID-100"
SECRET_KEY = "YOUR_SECRET_KEY"
REDIRECT_URI = "https://oa-sniper.streamlit.app"

# ============================================================
# LOGIN
# ============================================================
def fyers_auto_login():

    # Already logged in
    if "access_token" in st.session_state:
        return st.session_state["access_token"]

    # --------------------------------------------------------
    # After FYERS redirects back to Streamlit
    # --------------------------------------------------------
    if "auth_code" in st.query_params:

        auth_code = st.query_params["auth_code"]

        try:
            session = fyersModel.SessionModel(
                client_id=CLIENT_ID,
                secret_key=SECRET_KEY,
                redirect_uri=REDIRECT_URI,
                response_type="code",
                grant_type="authorization_code"
            )

            session.set_token(auth_code)

            token_response = session.generate_token()

            # ------------------------------------------------
            # Check token response
            # ------------------------------------------------
            if (
                isinstance(token_response, dict)
                and token_response.get("s") == "ok"
                and "access_token" in token_response
            ):

                st.session_state["access_token"] = token_response["access_token"]

                # Remove auth_code from URL
                st.query_params.clear()

                st.rerun()

            else:
                st.error("❌ FYERS Token Generation Failed")
                st.write("FYERS Response:")
                st.json(token_response)
                st.stop()

        except Exception as e:

            st.error("❌ Error while generating FYERS access token")
            st.exception(e)
            st.stop()

    # --------------------------------------------------------
    # First time login
    # --------------------------------------------------------
    try:

        session = fyersModel.SessionModel(
            client_id=CLIENT_ID,
            secret_key=SECRET_KEY,
            redirect_uri=REDIRECT_URI,
            response_type="code",
            grant_type="authorization_code"
        )

        auth_link = session.generate_authcode()

        st.markdown(
            f"""
            <div style="
                display:flex;
                justify-content:center;
                margin-top:120px;
            ">
                <a href="{auth_link}" target="_self">
                    <button style="
                        background:#16a34a;
                        color:white;
                        border:none;
                        padding:16px 30px;
                        border-radius:10px;
                        font-size:20px;
                        cursor:pointer;
                    ">
                        🚀 Login with FYERS
                    </button>
                </a>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.info(
            "Click the button above, complete FYERS login, "
            "and you will be redirected back to this dashboard."
        )

        st.stop()

    except Exception as e:

        st.error("❌ Unable to create FYERS login URL")
        st.exception(e)
        st.stop()


# ============================================================
# CHECK CREDENTIALS
# ============================================================
if (
    CLIENT_ID == "YOUR_APP_ID-100"
    or SECRET_KEY == "YOUR_SECRET_KEY"
):

    st.error(
        "❌ Please enter your real FYERS CLIENT_ID and SECRET_KEY "
        "at the top of the code."
    )

    st.stop()


# ============================================================
# LOGIN + FYERS CLIENT
# ============================================================
access_token = fyers_auto_login()

try:

    fyers = fyersModel.FyersModel(
        client_id=CLIENT_ID,
        is_async=False,
        token=access_token,
        log_path=""
    )

except Exception as e:

    st.error("❌ Unable to initialize FYERS")
    st.exception(e)
    st.stop()


# ============================================================
# TEST FYERS PROFILE
# ============================================================
try:

    profile_response = fyers.get_profile()

    if profile_response.get("s") != "ok":

        st.error("❌ FYERS login/token is not valid")

        st.write("FYERS Profile Response:")
        st.json(profile_response)

        if "access_token" in st.session_state:
            del st.session_state["access_token"]

        st.stop()

except Exception as e:

    st.error("❌ FYERS profile test failed")
    st.exception(e)
    st.stop()


# ============================================================
# SUCCESS STATUS
# ============================================================
st.success("✅ FYERS Login Successful")

# ============================================================
# AUTO REFRESH
# ============================================================
st_autorefresh(
    interval=10000,
    limit=2000,
    key="sniper_refresh"
)


# ============================================================
# GET NIFTY SPOT
# ============================================================
spot_price = 0.0

try:

    quote_response = fyers.quotes(
        data={
            "symbols": "NSE:NIFTY50-INDEX"
        }
    )

    if (
        isinstance(quote_response, dict)
        and quote_response.get("s") == "ok"
        and len(quote_response.get("d", [])) > 0
    ):

        nifty_data = quote_response["d"][0]

        spot_price = float(
            nifty_data["v"].get("lp", 0)
        )

    else:

        st.warning("⚠️ Unable to get NIFTY spot price")
        st.json(quote_response)

except Exception as e:

    st.error("❌ NIFTY quote error")
    st.exception(e)


# ============================================================
# ATM STRIKE
# ============================================================
if spot_price > 0:

    atm_strike = int(round(spot_price / 50.0) * 50)

else:

    atm_strike = 0


# ============================================================
# HEADER
# ============================================================
st.markdown(
    f"""
    <h1 style="text-align:center;">
        🎯 Sniper OI Pro Dashboard
    </h1>

    <h2 style="text-align:center;">
        NIFTY Spot:
        <span style="color:#2563eb;">
            {spot_price:.2f}
        </span>
    </h2>
    """,
    unsafe_allow_html=True
)


# ============================================================
# STRIKE SELECTION
# ============================================================
strike_type = st.radio(
    "Select Strike Type:",
    ["ITM", "ATM", "OTM"],
    horizontal=True,
    index=1
)


if strike_type == "ITM":

    selected_strike = atm_strike - 50

elif strike_type == "OTM":

    selected_strike = atm_strike + 50

else:

    selected_strike = atm_strike


# ============================================================
# EXPIRY SELECTION
# ============================================================
st.markdown("### 📅 Expiry")

expiry_input = st.text_input(
    "Enter expiry in FYERS format if required",
    value="",
    help=(
        "Leave this empty when using the Option Chain API. "
        "The API will return the currently available chain."
    )
)

# ============================================================
# FETCH OPTION CHAIN
# ============================================================
option_chain_df = pd.DataFrame()

option_chain_response = {}

try:

    option_chain_request = {
        "symbol": "NSE:NIFTY50-INDEX",
        "strikecount": 25,
        "timestamp": ""
    }

    option_chain_response = fyers.optionchain(
        data=option_chain_request
    )

    if (
        isinstance(option_chain_response, dict)
        and option_chain_response.get("s") == "ok"
    ):

        options_data = (
            option_chain_response
            .get("data", {})
            .get("optionsChain", [])
        )

        if options_data:

            option_chain_df = pd.DataFrame(options_data)

        else:

            st.warning("⚠️ Option Chain returned no data.")

    else:

        st.error("❌ Option Chain API failed")

        st.json(option_chain_response)

except Exception as e:

    st.error("❌ Option Chain API Error")
    st.exception(e)


# ============================================================
# CLEAN OPTION CHAIN
# ============================================================
if not option_chain_df.empty:

    # Convert numeric columns
    for col in [
        "strike_price",
        "ltp",
        "oi",
        "volume"
    ]:

        if col in option_chain_df.columns:

            option_chain_df[col] = pd.to_numeric(
                option_chain_df[col],
                errors="coerce"
            )

    # Keep only CE / PE
    if "option_type" in option_chain_df.columns:

        option_chain_df = option_chain_df[
            option_chain_df["option_type"].isin(
                ["CE", "PE"]
            )
        ].copy()


# ============================================================
# FIND SELECTED STRIKE DATA
# ============================================================
ce_oi = 0
pe_oi = 0
ce_ltp = 0.0
pe_ltp = 0.0
ce_oi_chg = 0
pe_oi_chg = 0

if not option_chain_df.empty:

    # --------------------------------------------------------
    # CE
    # --------------------------------------------------------
    ce_rows = option_chain_df[
        (option_chain_df["option_type"] == "CE")
        &
        (
            option_chain_df["strike_price"]
            == selected_strike
        )
    ]

    if not ce_rows.empty:

        ce_oi = int(
            ce_rows.iloc[0].get("oi", 0)
            or 0
        )

        ce_ltp = float(
            ce_rows.iloc[0].get("ltp", 0)
            or 0
        )

    # --------------------------------------------------------
    # PE
    # --------------------------------------------------------
    pe_rows = option_chain_df[
        (option_chain_df["option_type"] == "PE")
        &
        (
            option_chain_df["strike_price"]
            == selected_strike
        )
    ]

    if not pe_rows.empty:

        pe_oi = int(
            pe_rows.iloc[0].get("oi", 0)
            or 0
        )

        pe_ltp = float(
            pe_rows.iloc[0].get("ltp", 0)
            or 0
        )


# ============================================================
# 3-MIN OI TRACKER
# ============================================================
if "oi_tracker" not in st.session_state:

    st.session_state.oi_tracker = {
        "ce_oi": ce_oi,
        "pe_oi": pe_oi,
        "timestamp": time.time(),
        "ce_diff": 0,
        "pe_diff": 0
    }


current_time = time.time()

elapsed_time = (
    current_time
    - st.session_state.oi_tracker["timestamp"]
)


if elapsed_time >= 180:

    st.session_state.oi_tracker["ce_diff"] = (
        ce_oi
        - st.session_state.oi_tracker["ce_oi"]
    )

    st.session_state.oi_tracker["pe_diff"] = (
        pe_oi
        - st.session_state.oi_tracker["pe_oi"]
    )

    st.session_state.oi_tracker["ce_oi"] = ce_oi
    st.session_state.oi_tracker["pe_oi"] = pe_oi
    st.session_state.oi_tracker["timestamp"] = current_time


ce_3min_diff = st.session_state.oi_tracker["ce_diff"]
pe_3min_diff = st.session_state.oi_tracker["pe_diff"]


# ============================================================
# TOP METRICS
# ============================================================
st.markdown("---")

c1, c2, c3, c4, c5 = st.columns(5)


with c1:

    st.markdown(
        "<h4 style='text-align:center;color:red;'>CE OI</h4>",
        unsafe_allow_html=True
    )

    st.markdown(
        f"<h3 style='text-align:center;'>{ce_oi:,}</h3>",
        unsafe_allow_html=True
    )

    diff_color = "green" if ce_3min_diff > 0 else "red"

    diff_sign = "+" if ce_3min_diff > 0 else ""

    st.markdown(
        f"""
        <p style="
            text-align:center;
            color:{diff_color};
        ">
            {diff_sign}{ce_3min_diff:,} in 3m
        </p>
        """,
        unsafe_allow_html=True
    )


with c2:

    st.markdown(
        "<h4 style='text-align:center;color:red;'>CE LTP</h4>",
        unsafe_allow_html=True
    )

    st.markdown(
        f"<h3 style='text-align:center;'>₹{ce_ltp:.2f}</h3>",
        unsafe_allow_html=True
    )


with c3:

    st.markdown(
        "<h4 style='text-align:center;color:orange;'>STRIKE</h4>",
        unsafe_allow_html=True
    )

    st.markdown(
        f"""
        <h2 style="
            text-align:center;
            background:#f0f2f6;
            padding:10px;
            border-radius:10px;
        ">
            {selected_strike}
        </h2>
        """,
        unsafe_allow_html=True
    )


with c4:

    st.markdown(
        "<h4 style='text-align:center;color:green;'>PE LTP</h4>",
        unsafe_allow_html=True
    )

    st.markdown(
        f"<h3 style='text-align:center;'>₹{pe_ltp:.2f}</h3>",
        unsafe_allow_html=True
    )


with c5:

    st.markdown(
        "<h4 style='text-align:center;color:green;'>PE OI</h4>",
        unsafe_allow_html=True
    )

    st.markdown(
        f"<h3 style='text-align:center;'>{pe_oi:,}</h3>",
        unsafe_allow_html=True
    )

    diff_color = "green" if pe_3min_diff > 0 else "red"

    diff_sign = "+" if pe_3min_diff > 0 else ""

    st.markdown(
        f"""
        <p style="
            text-align:center;
            color:{diff_color};
        ">
            {diff_sign}{pe_3min_diff:,} in 3m
        </p>
        """,
        unsafe_allow_html=True
    )


st.markdown("---")


# ============================================================
# FIND MAX CE OI / MAX PE OI
# ============================================================
max_ce_oi = 0
max_pe_oi = 0

res_strike = 0
sup_strike = 0


if not option_chain_df.empty:

    # --------------------------------------------------------
    # Maximum CE OI
    # --------------------------------------------------------
    ce_df = option_chain_df[
        option_chain_df["option_type"] == "CE"
    ].copy()

    if not ce_df.empty:

        ce_df = ce_df.dropna(
            subset=["oi", "strike_price"]
        )

        if not ce_df.empty:

            max_ce_row = ce_df.loc[
                ce_df["oi"].idxmax()
            ]

            max_ce_oi = int(
                max_ce_row["oi"]
            )

            res_strike = int(
                max_ce_row["strike_price"]
            )

    # --------------------------------------------------------
    # Maximum PE OI
    # --------------------------------------------------------
    pe_df = option_chain_df[
        option_chain_df["option_type"] == "PE"
    ].copy()

    if not pe_df.empty:

        pe_df = pe_df.dropna(
            subset=["oi", "strike_price"]
        )

        if not pe_df.empty:

            max_pe_row = pe_df.loc[
                pe_df["oi"].idxmax()
            ]

            max_pe_oi = int(
                max_pe_row["oi"]
            )

            sup_strike = int(
                max_pe_row["strike_price"]
            )


# ============================================================
# SUPPORT / RESISTANCE DISPLAY
# ============================================================
r1, r2 = st.columns(2)


with r1:

    st.markdown(
        f"""
        <div style="
            background:#fee2e2;
            padding:18px;
            border-radius:12px;
            text-align:center;
        ">

            <h4 style="color:#dc2626;">
                🔴 Resistance - Highest CE OI
            </h4>

            <h2>
                {res_strike if res_strike else "N/A"}
            </h2>

            <p>
                OI:
                {max_ce_oi:,}
            </p>

        </div>
        """,
        unsafe_allow_html=True
    )


with r2:

    st.markdown(
        f"""
        <div style="
            background:#dcfce7;
            padding:18px;
            border-radius:12px;
            text-align:center;
        ">

            <h4 style="color:#16a34a;">
                🟢 Support - Highest PE OI
            </h4>

            <h2>
                {sup_strike if sup_strike else "N/A"}
            </h2>

            <p>
                OI:
                {max_pe_oi:,}
            </p>

        </div>
        """,
        unsafe_allow_html=True
    )


# ============================================================
# OPTION CHAIN TABLE
# ============================================================
st.markdown("---")
st.markdown("### 📊 NIFTY Option Chain")


if not option_chain_df.empty:

    table_columns = []

    for column in [
        "symbol",
        "option_type",
        "strike_price",
        "ltp",
        "oi",
        "volume"
    ]:

        if column in option_chain_df.columns:

            table_columns.append(column)


    display_df = option_chain_df[table_columns].copy()

    display_df = display_df.sort_values(
        by=["strike_price", "option_type"]
    )

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )

else:

    st.warning(
        "⚠️ Option Chain data unavailable."
    )


# ============================================================
# NIFTY 5-MINUTE CHART
# ============================================================
st.markdown("---")
st.markdown("### 📈 NIFTY Live Structure Chart")


today = datetime.date.today().strftime(
    "%Y-%m-%d"
)


history_data = {
    "symbol": "NSE:NIFTY50-INDEX",
    "resolution": "5",
    "date_format": "1",
    "range_from": today,
    "range_to": today,
    "cont_flag": "1"
}


history_df = pd.DataFrame()


try:

    history_response = fyers.history(
        data=history_data
    )

    if (
        isinstance(history_response, dict)
        and history_response.get("s") == "ok"
    ):

        candles = history_response.get(
            "candles",
            []
        )

        if candles:

            history_df = pd.DataFrame(
                candles,
                columns=[
                    "Date",
                    "Open",
                    "High",
                    "Low",
                    "Close",
                    "Volume"
                ]
            )

            history_df["Date"] = (
                pd.to_datetime(
                    history_df["Date"],
                    unit="s",
                    utc=True
                )
                .dt.tz_convert("Asia/Kolkata")
            )

except Exception as e:

    st.error("❌ History API Error")
    st.exception(e)


# ============================================================
# DRAW CHART
# ============================================================
if not history_df.empty:

    fig = go.Figure()

    fig.add_trace(
        go.Candlestick(
            x=history_df["Date"],
            open=history_df["Open"],
            high=history_df["High"],
            low=history_df["Low"],
            close=history_df["Close"],
            name="NIFTY"
        )
    )

    # Resistance
    if res_strike > 0:

        fig.add_hline(
            y=res_strike,
            line_width=2,
            line_dash="dash",
            annotation_text=(
                f"Resistance: {res_strike}"
            )
        )

    # Support
    if sup_strike > 0:

        fig.add_hline(
            y=sup_strike,
            line_width=2,
            line_dash="dash",
            annotation_text=(
                f"Support: {sup_strike}"
            )
        )

    # ATM
    if atm_strike > 0:

        fig.add_hline(
            y=atm_strike,
            line_width=1,
            line_dash="dot",
            annotation_text=(
                f"ATM: {atm_strike}"
            )
        )

    fig.update_layout(
        xaxis_rangeslider_visible=False,
        height=550,
        margin=dict(
            l=0,
            r=0,
            t=30,
            b=0
        )
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

else:

    st.warning(
        "⚠️ NIFTY chart data is unavailable."
    )


# ============================================================
# DEBUG SECTION
# ============================================================
with st.expander("🔧 Debug Information"):

    st.write("FYERS Login: ✅")
    st.write("Client ID:", CLIENT_ID)
    st.write("Redirect URI:", REDIRECT_URI)
    st.write("NIFTY Spot:", spot_price)
    st.write("ATM Strike:", atm_strike)
    st.write("Selected Strike:", selected_strike)

    st.write("Option Chain Response:")

    if option_chain_response:
        st.json(option_chain_response)
    else:
        st.write("No response received.")
