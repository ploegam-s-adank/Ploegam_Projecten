import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from utils_agol import AGOL

st.header("📊 Dashboard – Kaart + Tabel")

cfg = st.secrets["arcgis"]
agol = AGOL(cfg["username"], cfg["password"], cfg["portal"])
projects_url = cfg["projects_layer_url"]

# Data ophalen
try:
    res = agol.query(projects_url, out_fields="*", return_geometry=True, extra={"outSR": 4326})
    feats = res.get("features", [])
except Exception as e:
    st.error(f"Fout bij ophalen projectdata: {e}")
    st.stop()

# Kaart
m = folium.Map(location=[52.1, 5.2], zoom_start=8)

for f in feats:
    geom = f.get("geometry")
    if not geom:
        continue

    # POLYGON / MULTIPOLYGON
    if "rings" in geom:
        for ring in geom["rings"]:
            folium.Polygon([(y, x) for x, y in ring], color="blue", fill=True).add_to(m)

    # POLYLINE
    elif "paths" in geom:
        for path in geom["paths"]:
            folium.PolyLine([(y, x) for x, y in path], color="red").add_to(m)

    # POINT
    elif "x" in geom and "y" in geom:
        folium.Marker((geom["y"], geom["x"])).add_to(m)

st_folium(m, height=600)

# Tabel
df = pd.DataFrame([f["attributes"] for f in feats])
st.subheader("📋 Projecten")
st.dataframe(df, use_container_width=True, height=600)
