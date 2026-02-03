import streamlit as st
import pandas as pd
from utils_agol import AGOL
from streamlit_folium import st_folium
import folium

st.header("🗺️ Dashboard – Kaart & Tabel")

cfg = st.secrets["arcgis"]
agol = AGOL(cfg["username"], cfg["password"], cfg.get("portal"))

projects_url = cfg["projects_layer_url"]

try:
    resp = agol.query(projects_url)
except Exception as e:
    st.error(f"Fout bij ophalen projectlaag: {e}")
    st.stop()

feats = resp.get("features", [])
df = pd.DataFrame([f["attributes"] for f in feats])

st.subheader("Kaart")

m = folium.Map(location=[52.1, 5.2], zoom_start=8)

for f in feats:
    geom = f.get("geometry")
    if geom and "rings" in geom:
        for ring in geom["rings"]:
            latlon = [(y, x) for x, y in ring]
            folium.Polygon(latlon, color="blue", fill=True).add_to(m)

st_folium(m, height=480)

st.subheader("Tabel")
st.dataframe(df, use_container_width=True)