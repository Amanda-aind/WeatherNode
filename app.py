import streamlit as st
import requests
import numpy as np
import pandas as pd
import time
import datetime
import plotly.graph_objects as go
from scipy.interpolate import PchipInterpolator

# -----------------------------
# CONFIGURATION
# -----------------------------
FIREBASE_URL = "https://weathernode-d6c04-default-rtdb.asia-southeast1.firebasedatabase.app/data.json"
FETCH_LAST_N_LIVE = 300          
FETCH_LAST_N_HISTORY = 50000  # Cap historical fetch to prevent RAM crashes
DENSE_POINTS = 300          

# Local Timezone offset (UTC +5:30)
LOCAL_TZ = datetime.timezone(datetime.timedelta(hours=5, minutes=30))

st.set_page_config(
    page_title="WeatherNode Hub",
    page_icon="🌤️",
    layout="wide"
)

# -----------------------------
# SIDEBAR CONTROLS
# -----------------------------
st.sidebar.title("Dashboard Controls")

if st.sidebar.button("🔄 Reset Graphs"):
    try:
        requests.delete(FIREBASE_URL, timeout=5)
        st.sidebar.success("Graphs Reset!")
        time.sleep(1)
    except Exception as e:
        st.sidebar.error(f"Reset Failed\n{e}")
    st.rerun()

st.title("🌤️ WeatherNode : Live Edge-Processed Dashboard")

# -----------------------------
# MATH & DATA HELPERS
# -----------------------------
@st.cache_data(ttl=600)
def get_local_weather():
    """Fetches real-world ambient weather for the hardware's location."""
    try:
        # Open-Meteo API (No Key Required)
        url = "https://api.open-meteo.com/v1/forecast?latitude=7.027&longitude=79.951&current=temperature_2m,relative_humidity_2m&timezone=auto"
        res = requests.get(url, timeout=5).json()
        return res['current']['temperature_2m'], res['current']['relative_humidity_2m']
    except Exception:
        return None, None

def smooth_xy(x, y, num_dense=DENSE_POINTS):
    is_time = pd.api.types.is_datetime64_any_dtype(x)
    
    if is_time:
        x_num = x.astype(int) / 10**9
    else:
        x_num = np.asarray(x, dtype=float)
        
    y = np.asarray(y, dtype=float)

    if len(x_num) < 3 or len(np.unique(x_num)) < 3:
        return x, y
        
    try:
        interpolator = PchipInterpolator(x_num, y)
        x_dense = np.linspace(x_num.min(), x_num.max(), num_dense)
        y_dense = interpolator(x_dense)
        
        if is_time:
            x_dense = pd.to_datetime(x_dense, unit='s')
            
        return x_dense, y_dense
    except Exception:
        return x, y

def fetch_and_format(limit=FETCH_LAST_N_LIVE):
    try:
        params = {"orderBy": '"$key"', "limitToLast": limit}
        response = requests.get(FIREBASE_URL, params=params, timeout=10)
        data_json = response.json()

        if not data_json:
            return pd.DataFrame()

        processed = []
        for i, row in enumerate(data_json.values()):
            processed.append({
                "Time": row.get("Time", None),
                "Reading": i + 1,
                "LM35 (T1)": float(row.get("T1", 0)),
                "DHT22 (T2)": float(row.get("T2", 0)),
                "Fused Temp (FT)": float(row.get("FT", 0)),
                "Humidity": float(row.get("Hum", 0))
            })
            
        df = pd.DataFrame(processed)
        
        if "Time" in df.columns:
            df["Time"] = pd.to_datetime(df["Time"], errors="coerce")
            if df["Time"].isna().all():
                df["Time"] = df["Reading"]
        else:
            df["Time"] = df["Reading"]
            
        return df
    except Exception:
        return pd.DataFrame()

# -----------------------------
# PLOTTING HELPER
# -----------------------------
def plot_combined_graph(df, title, height=400):
    fig = go.Figure()
    
    x_s, y_s = smooth_xy(df["Time"], df["LM35 (T1)"])
    fig.add_trace(go.Scatter(x=x_s, y=y_s, mode="lines", name="LM35", line=dict(color="#1f77b4", width=2, shape="spline")))
    
    x_s, y_s = smooth_xy(df["Time"], df["DHT22 (T2)"])
    fig.add_trace(go.Scatter(x=x_s, y=y_s, mode="lines", name="DHT22", line=dict(color="#ff7f0e", width=2, shape="spline")))
    
    x_s, y_s = smooth_xy(df["Time"], df["Fused Temp (FT)"])
    fig.add_trace(go.Scatter(x=x_s, y=y_s, mode="lines", name="Fused Temp", line=dict(color="#d62728", width=3, shape="spline")))
    
    fig.update_layout(title=title, height=height, hovermode="x unified", xaxis=dict(title="Time", autorange=True), yaxis=dict(title="Temperature (°C)", autorange=True))
    return fig

# ===================================================
# TABS ARCHITECTURE
# ===================================================
tab_home, tab_history = st.tabs(["🏠 Live Home", "🕰️ Past Graphs"])

# -----------------------------
# TAB 1: LIVE HOME (Fragment)
# -----------------------------
@st.fragment(run_every=3)
def render_live_home():
    df = fetch_and_format(limit=FETCH_LAST_N_LIVE)

    if df.empty:
        st.info("Waiting for sensor data from ESP32...")
        return

    # 1. Real-Time Environment Header
    local_time = datetime.datetime.now(LOCAL_TZ).strftime("%A, %b %d | %I:%M %p")
    amb_temp, amb_hum = get_local_weather()
    
    env_col1, env_col2 = st.columns([1, 1])
    env_col1.markdown(f"**🕒 Local Time:** {local_time}")
    if amb_temp:
        env_col2.markdown(f"**🌍 Ambient Weather:** {amb_temp}°C, {amb_hum}% RH")
    else:
        env_col2.markdown("**🌍 Ambient Weather:** Syncing...")
    
    st.markdown("---")

    # 2. Hardware Metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Latest Fused Temp", f"{df['Fused Temp (FT)'].iloc[-1]:.2f} °C")
    c2.metric("Latest Humidity", f"{df['Humidity'].iloc[-1]:.1f} %")
    c3.metric("Live Feed Buffer", f"{len(df)} Points")
    st.markdown("---")

    # 3. Main Live Graph (Full Buffer)
    st.plotly_chart(plot_combined_graph(df, "Live Hardware Feed"), use_container_width=True, key="live_main")

    # 4. Short-Window (5-Minute Window) High Resolution Graph
    if pd.api.types.is_datetime64_any_dtype(df["Time"]):
        five_mins_ago = df["Time"].max() - pd.Timedelta(minutes=5)
        df_5min = df[df["Time"] >= five_mins_ago]
        if not df_5min.empty:
            st.plotly_chart(plot_combined_graph(df_5min, "Last 5 Minutes (High Resolution Focus)", height=300), use_container_width=True, key="live_5min")


# -----------------------------
# TAB 2: HISTORICAL EXPLORER
# -----------------------------
def render_history():
    st.markdown("### 🔍 Historical Analysis")
    st.write("Examine past data. Data is mathematically resampled to 5-minute precision averages to ensure smooth performance over long timeframes.")
    
    time_filter = st.radio("Select Timeframe:", ["1 Hour", "12 Hours", "24 Hours", "2 Days", "1 Week", "All"], horizontal=True)

    if st.button("Load Historical Data"):
        with st.spinner("Fetching and interpolating data from Firebase..."):
            df_hist = fetch_and_format(limit=FETCH_LAST_N_HISTORY)
            
            if df_hist.empty:
                st.warning("No historical data found.")
                return
                
            is_time = pd.api.types.is_datetime64_any_dtype(df_hist["Time"])
            
            # Filter Timeframe
            if is_time and time_filter != "All":
                latest_time = df_hist["Time"].max()
                
                deltas = {
                    "1 Hour": pd.Timedelta(hours=1),
                    "12 Hours": pd.Timedelta(hours=12),
                    "24 Hours": pd.Timedelta(hours=24),
                    "2 Days": pd.Timedelta(days=2),
                    "1 Week": pd.Timedelta(days=7)
                }
                
                cutoff = latest_time - deltas[time_filter]
                df_hist = df_hist[df_hist["Time"] >= cutoff]

            # Downsample to 5-minute precision if dealing with real datetime
            if is_time and not df_hist.empty:
                df_hist = df_hist.set_index("Time").resample("5min").mean().dropna().reset_index()
            
            if df_hist.empty:
                st.warning("No data recorded during the selected timeframe.")
                return

            st.success(f"Successfully loaded {len(df_hist)} aggregated 5-minute blocks.")
            
            # Render History Graph
            st.plotly_chart(plot_combined_graph(df_hist, f"Filtered History: {time_filter}"), use_container_width=True, key="history_main")


# ===================================================
# EXECUTE UI
# ===================================================
with tab_home:
    render_live_home()

with tab_history:
    render_history()
