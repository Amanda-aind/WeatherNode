import streamlit as st
import requests
import pandas as pd
import time
import plotly.graph_objects as go

# -----------------------------
# CONFIGURATION
# -----------------------------
FIREBASE_URL = "https://weathernode-d6c04-default-rtdb.asia-southeast1.firebasedatabase.app/data.json"

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
# FETCH DATA
# -----------------------------
def fetch_and_format():

    try:

        response = requests.get(FIREBASE_URL, timeout=5)

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

    # ===================================================
    # COMBINED GRAPH
    # ===================================================

    st.subheader("Combined Sensor Fusion")

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["Reading"],
            y=df["LM35 (T1)"],
            mode="lines",
            name="LM35",
            line=dict(color="#1f77b4", width=2)
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df["Reading"],
            y=df["DHT22 (T2)"],
            mode="lines",
            name="DHT22",
            line=dict(color="#ff7f0e", width=2)
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df["Reading"],
            y=df["Fused Temp (FT)"],
            mode="lines",
            name="Fused Temp",
            line=dict(color="#d62728", width=3)
        )
    )

    fig.update_layout(

        height=450,

        hovermode="x unified",

        xaxis=dict(
            title="Reading Number",
            autorange=True
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

        fig1 = go.Figure()

        fig1.add_trace(
            go.Scatter(
                x=df["Reading"],
                y=df["LM35 (T1)"],
                mode="lines",
                line=dict(color="#1f77b4", width=2)
            )
        )

        fig1.update_layout(
            height=300,
            xaxis=dict(autorange=True),
            yaxis=dict(autorange=True),
            margin=dict(l=20, r=20, t=30, b=20)
        )

        st.plotly_chart(fig1, use_container_width=True)

        # ---------------------

        st.subheader("DHT22 Raw Temperature")

        fig2 = go.Figure()

        fig2.add_trace(
            go.Scatter(
                x=df["Reading"],
                y=df["DHT22 (T2)"],
                mode="lines",
                line=dict(color="#ff7f0e", width=2)
            )
        )

        fig2.update_layout(
            height=300,
            xaxis=dict(autorange=True),
            yaxis=dict(autorange=True),
            margin=dict(l=20, r=20, t=30, b=20)
        )

        st.plotly_chart(fig2, use_container_width=True)

    # ===================================================

    with right:

        st.subheader("Fused Temperature")

        fig3 = go.Figure()

        fig3.add_trace(
            go.Scatter(
                x=df["Reading"],
                y=df["Fused Temp (FT)"],
                mode="lines",
                line=dict(color="red", width=3)
            )
        )

        fig3.update_layout(
            height=300,
            xaxis=dict(autorange=True),
            yaxis=dict(autorange=True),
            margin=dict(l=20, r=20, t=30, b=20)
        )

        st.plotly_chart(fig3, use_container_width=True)

        # -----------------------

        st.subheader("Humidity")

        fig4 = go.Figure()

        fig4.add_trace(
            go.Scatter(
                x=df["Reading"],
                y=df["Humidity"],
                mode="lines",
                line=dict(color="green", width=2)
            )
        )

        fig4.update_layout(
            height=300,
            xaxis=dict(autorange=True),
            yaxis=dict(autorange=True),
            margin=dict(l=20, r=20, t=30, b=20)
        )

        st.plotly_chart(fig4, use_container_width=True)

# -----------------------------
# AUTO REFRESH
# -----------------------------
time.sleep(3)
st.rerun()
