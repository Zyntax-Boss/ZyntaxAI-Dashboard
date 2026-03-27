import streamlit as st
import pandas as pd
import os

# --- PAGE CONFIG ---
st.set_page_config(page_title="Zyntax Map Scanner", layout="wide", page_icon="🗺️")
st.title("🗺️ ZyntaxAI | Interactive Map Scanner")

# --- LOAD DATA ---
@st.cache_data
def load_data():
    file_path = "properties.csv"
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    else:
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.warning("⚠️ No properties.csv file found. Please ensure it is uploaded to GitHub.")
else:
    # --- SPLIT LAYOUT ---
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### Active Market Opportunities")
        # Streamlit's built-in map automatically looks for 'Latitude' and 'Longitude' columns
        st.map(df, zoom=12, use_container_width=True)
        
    with col2:
        st.markdown("### Target Property")
        # Dropdown to select a property from the CSV
        selected_address = st.selectbox("Select a pin to analyze:", df['Address'].tolist())
        
        # Pull the exact data for the chosen property
        property_data = df[df['Address'] == selected_address].iloc[0]
        
        st.divider()
        st.metric(label="Lot Size", value=f"{property_data['Lot_Size_sqm']} sqm")
        st.metric(label="Official Zoning", value=property_data['Zoning'])
        st.metric(label="Price Guide", value=property_data['Price_Guide'])
        
        st.divider()
        st.info("💡 In the next step, we will connect this data directly into the ZyntaxAI Feasibility Engine!")