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
FETCH_LAST_N_HISTORY = 50000  
DENSE_POINTS = 300          

# Local Timezone offset (UTC +5:30)
LOCAL_TZ = datetime.timezone(datetime.timedelta(hours=5, minutes=30))

st.set_page_config(
    page_title="WeatherNode Hub",
    page_icon="🌤️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# -----------------------------
# SIDEBAR CONTROLS
# -----------------------------
st.sidebar.title("⚙️ Dashboard Controls")

if st.sidebar.button("🔄 Reset All Data"):
    try:
        requests.delete(FIREBASE_URL, timeout=5)
        st.sidebar.success("Database Cleared!")
        time.sleep(1)
    except Exception as e:
        st.sidebar.error(f"Reset Failed\n{e}")
    st.rerun()

# -----------------------------
# MATH & DATA HELPERS
# -----------------------------
@st.cache_data(ttl=600)
def get_local_weather():
    """Fetches real-world ambient weather for Kadawatha, Sri Lanka."""
    try:
        # Coordinates for Kadawatha region
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
# BEAUTIFUL PLOTTING HELPER
# -----------------------------
def plot_beautiful_graph(df, title, height=450):
    fig = go.Figure()
    
    # 1. LM35 Trace (Cyan)
    x_s, y_s = smooth_xy(df["Time"], df["LM35 (T1)"])
    fig.add_trace(go.Scatter(
        x=x_s, y=y_s, mode="lines", name="LM35 (T1)", 
        line=dict(color="#00d2ff", width=3, shape="spline")
    ))
    
    # 2. DHT22 Trace (Orange)
    x_s, y_s = smooth_xy(df["Time"], df["DHT22 (T2)"])
    fig.add_trace(go.Scatter(
        x=x_s, y=y_s, mode="lines", name="DHT22 (T2)", 
        line=dict(color="#ff9900", width=3, shape="spline")
    ))
    
    # 3. Fused Temp Trace (Bold Red)
    x_s, y_s = smooth_xy(df["Time"], df["Fused Temp (FT)"])
    fig.add_trace(go.Scatter(
        x=x_s, y=y_s, mode="lines", name="Edge Fused Temp", 
        line=dict(color="#ff0055", width=4, shape="spline")
    ))
    
    # Make it look sleek and modern
    fig.update_layout(
        title=dict(text=f"<b>{title}</b>", font=dict(size=24, color="white")),
        height=height,
        hovermode="x unified",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(
            title="Time", 
            showgrid=True, 
            gridcolor='rgba(255,255,255,0.1)', 
            tickfont=dict(size=14)
        ),
        yaxis=dict(
            title="Temperature (°C)", 
            showgrid=True, 
            gridcolor='rgba(255,255,255,0.1)', 
            tickfont=dict(size=14),
            autorange=True  # Automatically zooms in tightly around the data points
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=14)),
        margin=dict(l=40, r=40, t=80, b=40)
    )
    return fig


# ===================================================
# UI ARCHITECTURE
# ===================================================
st.markdown("<h1 style='text-align: center; margin-bottom: 20px;'>🌤️ WeatherNode Dashboard</h1>", unsafe_allow_html=True)

tab_home, tab_history = st.tabs(["🏠 LIVE HOME", "🕰️ PAST GRAPHS & HISTORY"])

# -----------------------------
# TAB 1: LIVE HOME (Fragment)
# -----------------------------
@st.fragment(run_every=3)
def render_live_home():
    df = fetch_and_format(limit=FETCH_LAST_N_LIVE)

    if df.empty:
        st.info("Waiting for sensor data from ESP32...")
        return

    # --- MASSIVE HEADER UI ---
    local_time = datetime.datetime.now(LOCAL_TZ).strftime("%I:%M:%S %p")
    local_date = datetime.datetime.now(LOCAL_TZ).strftime("%A, %b %d")
    amb_temp, amb_hum = get_local_weather()
    
    weather_display = f"{amb_temp}°C | 💧 {amb_hum}%" if amb_temp else "Syncing..."

    st.markdown(f"""
        <div style="background-color: #1a1a1a; padding: 40px; border-radius: 20px; text-align: center; border: 1px solid #333; margin-bottom: 30px;">
            <p style="font-size: 1.5rem; color: #888; margin: 0;">{local_date}</p>
            <h1 style="font-size: 5rem; color: #ffffff; margin: -10px 0 10px 0; font-weight: 800; letter-spacing: 2px;">🕒 {local_time}</h1>
            <h2 style="font-size: 2.5rem; color: #4dabf7; margin: 0; font-weight: 400;">📍 Kadawatha, LK : <b>{weather_display}</b></h2>
        </div>
    """, unsafe_allow_html=True)

    # --- SENSOR METRICS ---
    c1, c2, c3 = st.columns(3)
    c1.metric("Latest Fused Temp", f"{df['Fused Temp (FT)'].iloc[-1]:.2f} °C")
    c2.metric("Latest Humidity", f"{df['Humidity'].iloc[-1]:.1f} %")
    c3.metric("Live Feed Buffer", f"{len(df)} Points")
    st.markdown("<br>", unsafe_allow_html=True)

    # --- MAIN LIVE GRAPH (Strict 10-Minute Rolling Window) ---
    if pd.api.types.is_datetime64_any_dtype(df["Time"]):
        # Find the newest time and subtract 10 minutes to create a cutoff point
        ten_mins_ago = df["Time"].max() - pd.Timedelta(minutes=10)
        df_plot = df[df["Time"] >= ten_mins_ago]
    else:
        # Fallback if timestamps are missing
        df_plot = df

    st.plotly_chart(plot_beautiful_graph(df_plot, "Live Hardware Feed (Last 10 Minutes)"), use_container_width=True, key="live_main")


# -----------------------------
# TAB 2: HISTORICAL EXPLORER
# -----------------------------
def render_history():
    st.markdown("## 🔍 Sensor Data History")
    
    # --- 5 MINUTE GRAPH (MOVED HERE) ---
    df_live = fetch_and_format(limit=FETCH_LAST_N_LIVE)
    if not df_live.empty and pd.api.types.is_datetime64_any_dtype(df_live["Time"]):
        five_mins_ago = df_live["Time"].max() - pd.Timedelta(minutes=5)
        df_5min = df_live[df_live["Time"] >= five_mins_ago]
        if not df_5min.empty:
            st.plotly_chart(plot_beautiful_graph(df_5min, "Last 5 Minutes (High Resolution)", height=350), use_container_width=True, key="hist_5min")
            
    st.markdown("---")
    
    # --- LONG TERM HISTORY ---
    st.markdown("### 🕰️ Long-Term Analysis")
    st.write("*Data is mathematically resampled to 5-minute precision averages to ensure ultra-smooth performance over long timeframes.*")
    
    time_filter = st.radio("Select Timeframe:", ["1 Hour", "12 Hours", "24 Hours", "2 Days", "1 Week", "All"], horizontal=True)

    if st.button("Load Historical Data", type="primary"):
        with st.spinner("Fetching massive dataset from Firebase..."):
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

            # Downsample to 5-minute precision
            if is_time and not df_hist.empty:
                # Add numeric_only=True to prevent Pandas crashing
                df_hist = df_hist.set_index("Time").resample("5min").mean(numeric_only=True).dropna().reset_index()
            
            if df_hist.empty:
                st.warning("No data recorded during the selected timeframe.")
                return

            st.success(f"Successfully loaded and compressed {len(df_hist)} data blocks.")
            st.plotly_chart(plot_beautiful_graph(df_hist, f"Filtered History: {time_filter}"), use_container_width=True, key="history_main")


# ===================================================
# EXECUTE UI
# ===================================================
with tab_home:
    render_live_home()

with tab_history:
    render_history()
