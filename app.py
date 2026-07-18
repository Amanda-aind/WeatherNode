import streamlit as st
import requests
import pandas as pd
import time
import plotly.graph_objects as go

# --- CLOUD CONFIG ---
FIREBASE_URL = "https://weathernode-d6c04-default-rtdb.asia-southeast1.firebasedatabase.app/data.json"

st.set_page_config(page_title="WeatherNode Hub", layout="wide")
st.title("WeatherNode: Live Edge-Processed Hub")

def fetch_and_format():
    response = requests.get(FIREBASE_URL)
    data_json = response.json()
    
    if not data_json:
        st.warning("No data found in Firebase yet.")
        return None
        
    raw_data = list(data_json.values())
    processed_data = []
    
    for index, row in enumerate(raw_data):
        T1 = float(row.get('T1', 0))
        T2 = float(row.get('T2', 0))
        FT = float(row.get('FT', 0))
        Hum = float(row.get('Hum', 0))
        
        processed_data.append({
            "Reading": index + 1,
            "LM35 (T1)": round(T1, 2),
            "DHT22 (T2)": round(T2, 2),
            "Fused Temp": round(FT, 2),
            "Humidity": round(Hum, 2)
        })
        
    return pd.DataFrame(processed_data)

df = fetch_and_format()

if df is not None and not df.empty:
    col1, col2, col3 = st.columns(3)
    col1.metric("Latest Fused Temp", f"{df['Fused Temp'].iloc[-1]} °C")
    col2.metric("Latest Humidity", f"{df['Humidity'].iloc[-1]} %")
    col3.metric("Total Readings", len(df))
    
    st.markdown("---")
    
    # 1. ALL-IN-ONE GRAPH
    st.subheader("Combined Sensor Fusion")
    fig_all = go.Figure()
    fig_all.add_trace(go.Scatter(x=df['Reading'], y=df['LM35 (T1)'], name='LM35 (T1)', line=dict(width=1, color='#1f77b4')))
    fig_all.add_trace(go.Scatter(x=df['Reading'], y=df['DHT22 (T2)'], name='DHT22 (T2)', line=dict(width=1, color='#ff7f0e')))
    fig_all.add_trace(go.Scatter(x=df['Reading'], y=df['Fused Temp'], name='Fused Temp (FT)', line=dict(width=2, color='#d62728')))
    fig_all.update_layout(xaxis_title="Reading Number", yaxis_title="Temperature (°C)", hovermode="x unified")
    st.plotly_chart(fig_all, use_container_width=True)

    st.markdown("---")
    
    # 2. INDIVIDUAL GRAPHS GRID
    colA, colB = st.columns(2)
    
    with colA:
        st.subheader("LM35 Raw Data")
        fig_t1 = go.Figure()
        fig_t1.add_trace(go.Scatter(x=df['Reading'], y=df['LM35 (T1)'], name='LM35 (T1)', line=dict(width=2, color='#1f77b4')))
        fig_t1.update_layout(margin=dict(l=0, r=0, t=30, b=0), hovermode="x unified")
        st.plotly_chart(fig_t1, use_container_width=True)
        
        st.subheader("DHT22 Raw Data")
        fig_t2 = go.Figure()
        fig_t2.add_trace(go.Scatter(x=df['Reading'], y=df['DHT22 (T2)'], name='DHT22 (T2)', line=dict(width=2, color='#ff7f0e')))
        fig_t2.update_layout(margin=dict(l=0, r=0, t=30, b=0), hovermode="x unified")
        st.plotly_chart(fig_t2, use_container_width=True)

    with colB:
        st.subheader("Fused Temperature Output")
        fig_ft = go.Figure()
        fig_ft.add_trace(go.Scatter(x=df['Reading'], y=df['Fused Temp'], name='Fused Temp', line=dict(width=2, color='#d62728')))
        fig_ft.update_layout(margin=dict(l=0, r=0, t=30, b=0), hovermode="x unified")
        st.plotly_chart(fig_ft, use_container_width=True)

        st.subheader("Ambient Humidity")
        fig_hum = go.Figure()
        fig_hum.add_trace(go.Scatter(x=df['Reading'], y=df['Humidity'], name='Humidity (%)', line=dict(width=2, color='#2ca02c')))
        fig_hum.update_layout(margin=dict(l=0, r=0, t=30, b=0), hovermode="x unified")
        st.plotly_chart(fig_hum, use_container_width=True)

# Auto-Refresh Logic
time.sleep(10)
st.rerun()
