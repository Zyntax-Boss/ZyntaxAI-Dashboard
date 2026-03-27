import streamlit as st
import pandas as pd
import os
import io
import requests
from PIL import Image
from google import genai
import pydeck as pdk # <--- Added PyDeck for the interactive map

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
        st.info("🖱️ **Click any red pin on the map to instantly load its data.**")
        
        # 1. Define the Clickable Map Layer
        layer = pdk.Layer(
            "ScatterplotLayer",
            data=df,
            get_position=["Longitude", "Latitude"],
            get_fill_color=[231, 76, 60, 200], # Zyntax Red
            get_radius=100,
            pickable=True, # THIS is the magic word that makes it clickable!
            id="property_pins"
        )
        
        # 2. Set the Map Camera (Centered on the average coordinates)
        view_state = pdk.ViewState(
            latitude=df["Latitude"].mean(),
            longitude=df["Longitude"].mean(),
            zoom=12.5,
            pitch=0
        )
        
        # 3. Render the advanced map and listen for clicks
        deck = pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            tooltip={"text": "{Address}\nPrice: {Price_Guide}"}
        )
        
        # map_event captures the data when a user clicks a pin!
        map_event = st.pydeck_chart(deck, on_select="rerun", selection_mode="single-object")
        
    with col2:
        st.markdown("### Target Property")
        
        # 4. Read the Click Event!
        selected_address = df['Address'].iloc[0] # Default to the first one
        
        try:
            # If the user clicked the map, grab the address from the pin
            if hasattr(map_event, "selection") and map_event.selection.get("objects"):
                if map_event.selection["objects"].get("property_pins"):
                    selected_address = map_event.selection["objects"]["property_pins"][0]["Address"]
        except Exception as e:
            pass
            
        property_data = df[df['Address'] == selected_address].iloc[0]
        
        st.success(f"📍 **{selected_address}**")
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
