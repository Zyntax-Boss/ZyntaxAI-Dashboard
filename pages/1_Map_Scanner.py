import streamlit as st
import pandas as pd
import os
import io
import requests
from PIL import Image
from google import genai

# --- PAGE CONFIG ---
st.set_page_config(page_title="Zyntax Map Scanner", layout="wide", page_icon="🗺️")

# --- INITIALIZE AI ---
# Pulling keys from your hidden safe
API_KEY = st.secrets["GEMINI_API_KEY"]
MAPS_API_KEY = st.secrets["MAPS_API_KEY"]

try:
    client = genai.Client(api_key=API_KEY)
except Exception as e:
    st.error(f"API Key Error: {e}")

# --- MAPS FUNCTION ---
def get_google_maps_images(address):
    try:
        sat_url = f"https://maps.googleapis.com/maps/api/staticmap?center={address}&zoom=20&size=640x640&maptype=satellite&key={MAPS_API_KEY}"
        sat_response = requests.get(sat_url)
        sat_img = Image.open(io.BytesIO(sat_response.content))

        street_url = f"https://maps.googleapis.com/maps/api/streetview?size=640x640&location={address}&key={MAPS_API_KEY}"
        street_response = requests.get(street_url)
        street_img = Image.open(io.BytesIO(street_response.content))

        return sat_img, street_img
    except Exception as e:
        return None, None

# --- LOAD DATA ---
@st.cache_data
def load_data():
    file_path = "properties.csv"
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    return pd.DataFrame()

df = load_data()

st.title("🗺️ ZyntaxAI | Interactive Map Scanner")

if df.empty:
    st.warning("⚠️ No properties.csv file found in GitHub. Please upload it.")
else:
    # --- SPLIT LAYOUT ---
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### Active Market Opportunities")
        # THE FIX: Explicitly telling Streamlit which columns are the coordinates
        st.map(df, latitude="Latitude", longitude="Longitude", zoom=12, use_container_width=True)
        
    with col2:
        st.markdown("### Target Property")
        selected_address = st.selectbox("Select a pin to analyze:", df['Address'].tolist())
        property_data = df[df['Address'] == selected_address].iloc[0]
        
        st.divider()
        st.metric(label="Verified Lot Size", value=f"{property_data['Lot_Size_sqm']} sqm")
        st.metric(label="Official Zoning", value=property_data['Zoning'])
        st.metric(label="Price Guide", value=property_data['Price_Guide'])
        st.divider()
        
        # --- THE MAGIC BUTTON ---
        run_btn = st.button("🚀 RUN AI FEASIBILITY", type="primary", use_container_width=True)

# --- AI EXECUTION LOGIC ---
if run_btn:
    with st.spinner(f"Fetching Map imagery and analyzing {selected_address}..."):
        # 1. Fetch the Images
        sat_img, street_img = get_google_maps_images(selected_address)
        
        if sat_img and street_img:
            # Show the images to the user
            st.image([sat_img, street_img], width=300, caption=["Satellite View", "Street View"])
            
            # 2. Build the "Auto-Prompt" using the Hard Data from the CSV
            HARD_DATA_CONTEXT = f"""
            You are ZyntaxAI, a Senior Property Analyst.
            Analyze the provided images (Satellite/Street View) for {selected_address}.
            
            CRITICAL INSTRUCTION: Do NOT guess the price, zoning, or lot size. You MUST base all your development math on this verified data:
            - Verified Lot Size: {property_data['Lot_Size_sqm']} sqm
            - Official Zoning: {property_data['Zoning']}
            - Target Purchase Price (Price Guide): {property_data['Price_Guide']}
            
            Provide a fast, high-level professional feasibility summary. Tell me:
            1. Are there visual risks on the block? (Slopes, large trees, etc.)
            2. Based on the lot size and zoning, what is the realistic maximum yield?
            3. Provide a quick "back-of-the-napkin" construction cost estimate.
            4. State a final verdict on whether this is a viable development site at the current price guide.
            """
            
            try:
                # 3. Send the Prompt and Images to Gemini
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[HARD_DATA_CONTEXT, sat_img, street_img]
                )
                
                # 4. Display the result!
                st.success("Analysis Complete!")
                st.markdown(response.text)
                
            except Exception as e:
                st.error(f"AI Generation Error: {e}")
        else:
            st.error("Could not fetch maps imagery from Google.")
