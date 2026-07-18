import streamlit as st
import requests
import pandas as pd
import time
import plotly.graph_objects as go

# --- CLOUD CONFIG ---
FIREBASE_URL = "https://weathernode-d6c04-default-rtdb.asia-southeast1.firebasedatabase.app/data.json"

st.set_page_config(page_title="WeatherNode Hub", layout="wide")

# --- SIDEBAR CONTROLS ---
st.sidebar.title("Dashboard Controls")
if st.sidebar.button("Reset Graphs"):
    st.cache_data.clear()  # Clears cached data
    st.rerun()             # Forces a fresh reload

st.title("WeatherNode: Live Edge-Processed Hub")

def fetch_and_format():
    try:
        response = requests.get(FIREBASE_URL, timeout=5)
        data_json = response.json()
        
        if not data_json:
            st.warning("No data found in Firebase yet.")
            return None
            
        raw_data = list(data_json.values())
        processed_data = []
        
        for index, row in enumerate(raw_data):
            processed_data.append({
                "Reading": index + 1,
                "LM35 (T1)": float(row.get('T1', 0)),
                "DHT22 (T2)": float(row.get('T2', 0)),
                "Fused Temp (FT)": float(row.get('FT', 0)),
                "Humidity": float(row.get('Hum', 0))
            })
        return pd.DataFrame(processed_data)
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return None

df = fetch_and_format()

if df is not None and not df.empty:
    col1, col2, col3 = st.columns(3)
    col1.metric("Latest Fused Temp", f"{df['Fused Temp (FT)'].iloc[-1]:.2f} °C")
    col2.metric("Latest Humidity", f"{df['Humidity'].iloc[-1]:.1f} %")
    col3.metric("Total Readings", len(df))
    
    st.markdown("---")
    
    # 1. ALL-IN-ONE GRAPH
    st.subheader("Combined Sensor Fusion")
    fig_all = go.Figure()
    fig_all.add_trace(go.Scatter(x=df['Reading'], y=df['LM35 (T1)'], name='LM35 (T1)', line=dict(width=1, color='#1f77b4')))
    fig_all.add_trace(go.Scatter(x=df['Reading'], y=df['DHT22 (T2)'], name='DHT22 (T2)', line=dict(width=1, color='#ff7f0e')))
    fig_all.add_trace(go.Scatter(x=df['Reading'], y=df['Fused Temp (FT)'], name='Fused Temp (FT)', line=dict(width=2, color='#d62728')))
    fig_all.update_layout(height=400, xaxis_title="Reading Number", yaxis_title="Temp (°C)", hovermode="x unified")
    st.plotly_chart(fig_all, use_container_width=True)

    st.markdown("---")
    
    # 2. INDIVIDUAL GRAPHS GRID
    colA, colB = st.columns(2)
    
    with colA:
        st.subheader("LM35 Raw Data")
        fig_t1 = go.Figure()
        fig_t1.add_trace(go.Scatter(x=df['Reading'], y=df['LM35 (T1)'], name='LM35 (T1)', line=dict(width=2, color='#1f77b4')))
        fig_t1.update_layout(height=300, margin=dict(l=0, r=0, t=30, b=0), hovermode="x unified")
        st.plotly_chart(fig_t1, use_container_width=True)
        
        st.subheader("DHT22 Raw Data")
        fig_t2 = go.Figure()
        fig_t2.add_trace(go.Scatter(x=df['Reading'], y=df['DHT22 (T2)'], name='DHT22 (T2)', line=dict(width=2, color='#ff7f0e')))
        fig_t2.update_layout(height=300, margin=dict(l=0, r=0, t=30, b=0), hovermode="x unified")
        st.plotly_chart(fig_t2, use_container_width=True)

    with colB:
        st.subheader("Fused Temperature Output")
        fig_ft = go.Figure()
        fig_ft.add_trace(go.Scatter(x=df['Reading'], y=df['Fused Temp (FT)'], name='FT', line=dict(width=2, color='#d62728')))
        fig_ft.update_layout(height=300, margin=dict(l=0, r=0, t=30, b=0), hovermode="x unified")
        st.plotly_chart(fig_ft, use_container_width=True)

        st.subheader("Ambient Humidity")
        fig_hum = go.Figure()
        fig_hum.add_trace(go.Scatter(x=df['Reading'], y=df['Humidity'], name='Humidity', line=dict(width=2, color='#2ca02c')))
        fig_hum.update_layout(height=300, margin=dict(l=0, r=0, t=30, b=0), hovermode="x unified")
        st.plotly_chart(fig_hum, use_container_width=True)

# Auto-Refresh Logic
time.sleep(10)
st.rerun()
