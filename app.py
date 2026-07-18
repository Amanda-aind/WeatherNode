import streamlit as st
import requests
import numpy as np
import pandas as pd
import time
import plotly.graph_objects as go
from scipy.interpolate import PchipInterpolator

# -----------------------------
# CONFIGURATION
# -----------------------------
FIREBASE_URL = "https://weathernode-d6c04-default-rtdb.asia-southeast1.firebasedatabase.app/data.json"
FETCH_LAST_N = 200          
DENSE_POINTS = 300          

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
st.markdown("---")

# -----------------------------
# MATH & DATA HELPERS
# -----------------------------
def smooth_xy(x, y, num_dense=DENSE_POINTS):
    """Upgraded to handle pure Datetime arrays for real-time tracking."""
    is_time = pd.api.types.is_datetime64_any_dtype(x)
    
    # Convert datetime to UNIX timestamp for math interpolation
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
        
        # Convert UNIX timestamps back to Datetime objects for plotting
        if is_time:
            x_dense = pd.to_datetime(x_dense, unit='s')
            
        return x_dense, y_dense
    except Exception:
        return x, y

def fetch_and_format():
    try:
        params = {"orderBy": '"$key"', "limitToLast": FETCH_LAST_N}
        response = requests.get(FIREBASE_URL, params=params, timeout=5)
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
        
        # Convert to Datetime. Fall back to reading number if Time is missing.
        if "Time" in df.columns:
            df["Time"] = pd.to_datetime(df["Time"], errors="coerce")
            # If Time is fully NaT (Not a Time), revert to Reading index
            if df["Time"].isna().all():
                df["Time"] = df["Reading"]
        else:
            df["Time"] = df["Reading"]
            
        return df
    except Exception:
        return pd.DataFrame()

# -----------------------------
# LIVE UPDATING FRAGMENT
# -----------------------------
@st.fragment(run_every=3)
def live_dashboard():
    df = fetch_and_format()

    if df.empty:
        st.info("Waiting for sensor data...")
        return

    # --- 1. METRICS ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Latest Fused Temp", f"{df['Fused Temp (FT)'].iloc[-1]:.2f} °C")
    col2.metric("Latest Humidity", f"{df['Humidity'].iloc[-1]:.1f} %")
    col3.metric("Total Readings", len(df))
    st.markdown("---")

    # --- 2. COMBINED GRAPH ---
    st.subheader("Combined Sensor Fusion")
    fig = go.Figure()
    
    x_s, y_s = smooth_xy(df["Time"], df["LM35 (T1)"])
    fig.add_trace(go.Scatter(x=x_s, y=y_s, mode="lines", name="LM35", line=dict(color="#1f77b4", width=2, shape="spline")))
    
    x_s, y_s = smooth_xy(df["Time"], df["DHT22 (T2)"])
    fig.add_trace(go.Scatter(x=x_s, y=y_s, mode="lines", name="DHT22", line=dict(color="#ff7f0e", width=2, shape="spline")))
    
    x_s, y_s = smooth_xy(df["Time"], df["Fused Temp (FT)"])
    fig.add_trace(go.Scatter(x=x_s, y=y_s, mode="lines", name="Fused Temp", line=dict(color="#d62728", width=3, shape="spline")))
    
    fig.update_layout(height=450, hovermode="x unified", xaxis=dict(title="Time", autorange=True), yaxis=dict(title="Temperature (°C)", autorange=True))
    st.plotly_chart(fig, use_container_width=True, key="combo_chart")

    st.markdown("---")

    # --- 3. INDIVIDUAL GRAPHS ---
    left, right = st.columns(2)

    with left:
        st.subheader("LM35 Raw Temperature")
        x_s, y_s = smooth_xy(df["Time"], df["LM35 (T1)"])
        fig1 = go.Figure(go.Scatter(x=x_s, y=y_s, mode="lines", line=dict(color="#1f77b4", width=2, shape="spline")))
        fig1.update_layout(height=300, xaxis=dict(title="Time", autorange=True), yaxis=dict(autorange=True), margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig1, use_container_width=True, key="lm35_chart")

        st.subheader("DHT22 Raw Temperature")
        x_s, y_s = smooth_xy(df["Time"], df["DHT22 (T2)"])
        fig2 = go.Figure(go.Scatter(x=x_s, y=y_s, mode="lines", line=dict(color="#ff7f0e", width=2, shape="spline")))
        fig2.update_layout(height=300, xaxis=dict(title="Time", autorange=True), yaxis=dict(autorange=True), margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig2, use_container_width=True, key="dht22_chart")

    with right:
        st.subheader("Fused Temperature")
        x_s, y_s = smooth_xy(df["Time"], df["Fused Temp (FT)"])
        fig3 = go.Figure(go.Scatter(x=x_s, y=y_s, mode="lines", line=dict(color="red", width=3, shape="spline")))
        fig3.update_layout(height=300, xaxis=dict(title="Time", autorange=True), yaxis=dict(autorange=True), margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig3, use_container_width=True, key="ft_chart")

        st.subheader("Humidity")
        x_s, y_s = smooth_xy(df["Time"], df["Humidity"])
        fig4 = go.Figure(go.Scatter(x=x_s, y=y_s, mode="lines", line=dict(color="green", width=2, shape="spline")))
        fig4.update_layout(height=300, xaxis=dict(title="Time", autorange=True), yaxis=dict(autorange=True), margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig4, use_container_width=True, key="hum_chart")

live_dashboard()
