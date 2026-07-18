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
    # 1. Fetch edge-computed data from your database API
    response = requests.get(FIREBASE_URL)
    data_json = response.json()
    
    if data_json is None:
        st.warning("No data found in Firebase yet.")
        return None
        
    raw_data = list(data_json.values())
    processed_data = []
    
    # 2. Extract the data (Math is already done by the ESP32!)
    for index, row in enumerate(raw_data):
        T1 = float(row.get('T1', 0))
        T2 = float(row.get('T2', 0))
        FT = float(row.get('FT', 0)) # Fetching the edge-computed Fused Temp
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

# 3. Render Layout
if df is not None and not df.empty:
    # Key Summary Metrics Top Bar
    col1, col2, col3 = st.columns(3)
    col1.metric("Latest Edge Fused Temp", f"{df['Fused Temp'].iloc[-1]} °C")
    col2.metric("Latest Humidity", f"{df['Humidity'].iloc[-1]} %")
    col3.metric("Total Recorded Points", len(df))
    
    st.markdown("---")
    
    # Detailed Visualizations (Plotly)
    st.subheader("High-Resolution Sensor Analysis")
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['Reading'], y=df['LM35 (T1)'], name='LM35 (T1)', line=dict(width=1)))
    fig.add_trace(go.Scatter(x=df['Reading'], y=df['DHT22 (T2)'], name='DHT22 (T2)', line=dict(width=1)))
    fig.add_trace(go.Scatter(x=df['Reading'], y=df['Fused Temp'], name='Edge Fused Temp', line=dict(width=2)))
    
    fig.update_layout(
        xaxis_title="Reading Number",
        yaxis_title="Temperature (°C)",
        hovermode="x unified",
        dragmode="zoom" 
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("Ambient Humidity Trend")
    st.line_chart(df.set_index("Reading")[["Humidity"]], color="#008080")

# 4. Auto-Refresh Logic
time.sleep(10)
st.rerun()
