import streamlit as st
import requests
import numpy as np
import pandas as pd

# --- CLOUD CONFIG ---
# Direct API endpoint to your working WeatherNode database
FIREBASE_URL = "https://weathernode-d6c04-default-rtdb.asia-southeast1.firebasedatabase.app/data.json"

st.set_page_config(page_title="WeatherNode Hub", layout="wide")
st.title("WeatherNode: Live Sensor Fusion Hub")

def fetch_and_process():
    # 1. Fetch data from your database API
    response = requests.get(FIREBASE_URL)
    data_json = response.json()
    
    if data_json is None:
        st.warning("No data found in Firebase yet.")
        return None
        
    # Convert JSON dictionary (unique keys) into a list of readings
    raw_data = list(data_json.values())
    
    # 2. Setup custom tracking variables for your filter
    t_f = None
    t_p = None
    dtm = 1.0
    T01 = None
    
    processed_data = []
    
    # 3. Process the historical data stream sequential-style
    for index, row in enumerate(raw_data):
        T1 = float(row.get('T1', 0))
        T2 = float(row.get('T2', 0))
        Hum = float(row.get('Hum', 0))
        
        if t_f is None: t_f = T1; t_p = T1
        if T01 is None: T01 = T1
        
        # --- CUSTOM ALGORITHM ---
        DT1 = (np.log1p(abs(T1 - T01)))**2
        T1 = (T01 * DT1 + T1 * 1) / (DT1 + 1)
        T01 = T1

        wp = 1 / (abs(T1) ** (((((T1+1)**2)**0.5)-(T1+1))/(2*(((T1+1)**2)**0.5)+0.000001)))
        
        d1, d2 = 1.201, 0.501 
        w1 = (abs(d2)* wp)/(abs(d1) + abs(d2) * wp)
        w2 = (abs(d1)* wp)/(abs(d1) + abs(d2) * wp)

        T_w = float((w1*T1) + (w2*T2))
        dtp = dtm
        dtm = (abs(T_w - t_f)) + 100 
        
        t_f = (T_w * dtp + t_p * dtm)/(dtp + dtm)
        t_p = t_f
        # ------------------------
        
        # Append data along with a pseudo-index or loop timestamp
        processed_data.append({
            "Reading": index + 1,
            "LM35 (T1)": round(T1, 2),
            "DHT22 (T2)": round(T2, 2),
            "Fused Temp": round(t_f, 2),
            "Humidity": round(Hum, 2)
        })
        
    return pd.DataFrame(processed_data)

df = fetch_and_process()

# 4. Render Layout
if df is not None and not df.empty:
    # Key Summary Metrics Top Bar
    col1, col2, col3 = st.columns(3)
    col1.metric("Latest Fused Temp", f"{df['Fused Temp'].iloc[-1]} °C")
    col2.metric("Latest Humidity", f"{df['Humidity'].iloc[-1]} %")
    col3.metric("Total Recorded Points", len(df))
    
    st.markdown("---")
    
    # Main Dashboard Visualizations
    st.subheader("Temperature Sensor Fusion Performance")
    st.line_chart(df.set_index("Reading")[["LM35 (T1)", "DHT22 (T2)", "Fused Temp"]])
    
    st.subheader("Ambient Humidity Trend")
    st.line_chart(df.set_index("Reading")[["Humidity"]], color="#008080")
    
    # Dynamic page trigger
    if st.button("Fetch Fresh Data"):
        st.rerun()
