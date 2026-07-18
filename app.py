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
FETCH_LAST_N = 200          # cap how much history we pull each refresh (Firebase grows unbounded)
RIGHT_PADDING = 1           # keep the newest point ~3 "readings" in from the right edge
DENSE_POINTS = 300          # resolution of the smoothed curve, independent of data size

st.set_page_config(
    page_title="WeatherNode Hub",
    page_icon="🌤️",
    layout="wide"
)

# -----------------------------
# SIDEBAR
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
# SMOOTHING HELPER
# -----------------------------
def smooth_xy(x, y, num_dense=DENSE_POINTS):
    """Shape-preserving spline (PCHIP) so the curve stays smooth without
    inventing overshoot between real readings. Falls back to raw points
    when there isn't enough data to interpolate."""
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

# -----------------------------
# FETCH DATA
# -----------------------------
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

                "Fused Temp (FT)": float(row.get("FT", 0)),

                "Humidity": float(row.get("Hum", 0))

            })

        return pd.DataFrame(processed)

    except Exception as e:

        st.error(f"Error fetching data : {e}")

        return pd.DataFrame()


df = fetch_and_format()

# -----------------------------
# NO DATA
# -----------------------------
if df.empty:

    st.info("Waiting for sensor data...")

# -----------------------------
# DATA AVAILABLE
# -----------------------------
else:

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Latest Fused Temp",
        f"{df['Fused Temp (FT)'].iloc[-1]:.2f} °C"
    )

    col2.metric(
        "Latest Humidity",
        f"{df['Humidity'].iloc[-1]:.1f} %"
    )

    col3.metric(
        "Total Readings",
        len(df)
    )

    st.markdown("---")

    x_range = x_range_with_padding(df["Reading"])

    # ===================================================
    # COMBINED GRAPH
    # ===================================================

    st.subheader("Combined Sensor Fusion")

    fig = go.Figure()

    x_s, y_s = smooth_xy(df["Reading"], df["LM35 (T1)"])
    fig.add_trace(
        go.Scatter(
            x=x_s,
            y=y_s,
            mode="lines",
            name="LM35",
            line=dict(color="#1f77b4", width=2, shape="spline")
        )
    )

    x_s, y_s = smooth_xy(df["Reading"], df["DHT22 (T2)"])
    fig.add_trace(
        go.Scatter(
            x=x_s,
            y=y_s,
            mode="lines",
            name="DHT22",
            line=dict(color="#ff7f0e", width=2, shape="spline")
        )
    )

    x_s, y_s = smooth_xy(df["Reading"], df["Fused Temp (FT)"])
    fig.add_trace(
        go.Scatter(
            x=x_s,
            y=y_s,
            mode="lines",
            name="Fused Temp",
            line=dict(color="#d62728", width=3, shape="spline")
        )
    )

    fig.update_layout(

        height=450,

        hovermode="x unified",

        xaxis=dict(
            title="Reading Number",
            range=x_range,
            autorange=False
        ),

        yaxis=dict(
            title="Temperature (°C)",
            autorange=True
        )
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # ===================================================
    # INDIVIDUAL GRAPHS
    # ===================================================

    left, right = st.columns(2)

    # -------------------------
    # LM35
    # -------------------------
    with left:

        st.subheader("LM35 Raw Temperature")

        x_s, y_s = smooth_xy(df["Reading"], df["LM35 (T1)"])
        fig1 = go.Figure()

        fig1.add_trace(
            go.Scatter(
                x=x_s,
                y=y_s,
                mode="lines",
                line=dict(color="#1f77b4", width=2, shape="spline")
            )
        )

        fig1.update_layout(
            height=300,
            xaxis=dict(range=x_range, autorange=False),
            yaxis=dict(autorange=True),
            margin=dict(l=20, r=20, t=30, b=20)
        )

        st.plotly_chart(fig1, use_container_width=True)

        # ---------------------

        st.subheader("DHT22 Raw Temperature")

        x_s, y_s = smooth_xy(df["Reading"], df["DHT22 (T2)"])
        fig2 = go.Figure()

        fig2.add_trace(
            go.Scatter(
                x=x_s,
                y=y_s,
                mode="lines",
                line=dict(color="#ff7f0e", width=2, shape="spline")
            )
        )

        fig2.update_layout(
            height=300,
            xaxis=dict(range=x_range, autorange=False),
            yaxis=dict(autorange=True),
            margin=dict(l=20, r=20, t=30, b=20)
        )

        st.plotly_chart(fig2, use_container_width=True)

    # ===================================================

    with right:

        st.subheader("Fused Temperature")

        x_s, y_s = smooth_xy(df["Reading"], df["Fused Temp (FT)"])
        fig3 = go.Figure()

        fig3.add_trace(
            go.Scatter(
                x=x_s,
                y=y_s,
                mode="lines",
                line=dict(color="red", width=3, shape="spline")
            )
        )

        fig3.update_layout(
            height=300,
            xaxis=dict(range=x_range, autorange=False),
            yaxis=dict(autorange=True),
            margin=dict(l=20, r=20, t=30, b=20)
        )

        st.plotly_chart(fig3, use_container_width=True)

        # -----------------------

        st.subheader("Humidity")

        x_s, y_s = smooth_xy(df["Reading"], df["Humidity"])
        fig4 = go.Figure()

        fig4.add_trace(
            go.Scatter(
                x=x_s,
                y=y_s,
                mode="lines",
                line=dict(color="green", width=2, shape="spline")
            )
        )

        fig4.update_layout(
            height=300,
            xaxis=dict(range=x_range, autorange=False),
            yaxis=dict(autorange=True),
            margin=dict(l=20, r=20, t=30, b=20)
        )

        st.plotly_chart(fig4, use_container_width=True)

# -----------------------------
# AUTO REFRESH
# -----------------------------
time.sleep(3)
st.rerun()
