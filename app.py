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
RIGHT_PADDING = 3           
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
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    if len(x) < 3 or len(np.unique(x)) < 3:
        return x, y
    try:
        interpolator = PchipInterpolator(x, y)
    except Exception:
        return x, y

    x_dense = np.linspace(x.min(), x.max(), num_dense)
    y_dense = interpolator(x_dense)
    return x_dense, y_dense

def x_range_with_padding(x, pad=RIGHT_PADDING):
    if len(x) == 0:
        return [0, pad]
    return [float(np.min(x)), float(np.max(x)) + pad]

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
                "Reading": i + 1,
                "LM35 (T1)": float(row.get("T1", 0)),
                "DHT22 (T2)": float(row.get("T2", 0)),
                "Fused Temp (FT)": float(row.get("FT", 1)),
                "Humidity": float(row.get("Hum", 0))
            })
        return pd.DataFrame(processed)
    except Exception:
        return pd.DataFrame()

# -----------------------------
# LIVE UPDATING FRAGMENT
# -----------------------------
# This decorator tells Streamlit to run ONLY this specific function every 3 seconds.
# It updates the charts smoothly without reloading the entire webpage!
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

    x_range = x_range_with_padding(df["Reading"])

    # --- 2. COMBINED GRAPH ---
    st.subheader("Combined Sensor Fusion")
    fig = go.Figure()
    
    x_s, y_s = smooth_xy(df["Reading"], df["LM35 (T1)"])
    fig.add_trace(go.Scatter(x=x_s, y=y_s, mode="lines", name="LM35", line=dict(color="#1f77b4", width=2, shape="spline")))
    
    x_s, y_s = smooth_xy(df["Reading"], df["DHT22 (T2)"])
    fig.add_trace(go.Scatter(x=x_s, y=y_s, mode="lines", name="DHT22", line=dict(color="#ff7f0e", width=2, shape="spline")))
    
    x_s, y_s = smooth_xy(df["Reading"], df["Fused Temp (FT)"])
    fig.add_trace(go.Scatter(x=x_s, y=y_s, mode="lines", name="Fused Temp", line=dict(color="#d62728", width=3, shape="spline")))
    
    fig.update_layout(height=450, hovermode="x unified", xaxis=dict(title="Reading Number", range=x_range, autorange=False), yaxis=dict(title="Temperature (°C)", autorange=True))
    st.plotly_chart(fig, use_container_width=True, key="combo_chart")

    st.markdown("---")

    # --- 3. INDIVIDUAL GRAPHS ---
    left, right = st.columns(2)

    with left:
        st.subheader("LM35 Raw Temperature")
        x_s, y_s = smooth_xy(df["Reading"], df["LM35 (T1)"])
        fig1 = go.Figure(go.Scatter(x=x_s, y=y_s, mode="lines", line=dict(color="#1f77b4", width=2, shape="spline")))
        fig1.update_layout(height=300, xaxis=dict(range=x_range, autorange=False), yaxis=dict(autorange=True), margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig1, use_container_width=True, key="lm35_chart")

        st.subheader("DHT22 Raw Temperature")
        x_s, y_s = smooth_xy(df["Reading"], df["DHT22 (T2)"])
        fig2 = go.Figure(go.Scatter(x=x_s, y=y_s, mode="lines", line=dict(color="#ff7f0e", width=2, shape="spline")))
        fig2.update_layout(height=300, xaxis=dict(range=x_range, autorange=False), yaxis=dict(autorange=True), margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig2, use_container_width=True, key="dht22_chart")

    with right:
        st.subheader("Fused Temperature")
        x_s, y_s = smooth_xy(df["Reading"], df["Fused Temp (FT)"])
        fig3 = go.Figure(go.Scatter(x=x_s, y=y_s, mode="lines", line=dict(color="red", width=3, shape="spline")))
        fig3.update_layout(height=300, xaxis=dict(range=x_range, autorange=False), yaxis=dict(autorange=True), margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig3, use_container_width=True, key="ft_chart")

        st.subheader("Humidity")
        x_s, y_s = smooth_xy(df["Reading"], df["Humidity"])
        fig4 = go.Figure(go.Scatter(x=x_s, y=y_s, mode="lines", line=dict(color="green", width=2, shape="spline")))
        fig4.update_layout(height=300, xaxis=dict(range=x_range, autorange=False), yaxis=dict(autorange=True), margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig4, use_container_width=True, key="hum_chart")

# Start the live dashboard!
live_dashboard()
