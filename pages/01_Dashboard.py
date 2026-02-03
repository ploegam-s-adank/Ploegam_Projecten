import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from utils_agol import AGOL

st.header("📊 Dashboard – Kaart + Tabel")

cfg = st.secrets["arcgis"]
agol = AGOL(cfg["username"], cfg["password"], cfg["portal"])

projects_url = cfg["projects_layer_url"]

# Kaart
tab_map, tab_tbl = st.tabs(["🗺️ Kaart", "📋 Tabel"])

with tab_map:
    st.subheader("Projecten kaart")

    try:
        resp = agol.query(projects_url, out_fields="*", extra={"outSR": 4326})
        feats = resp.get("features", [])
    except Exception as e:
        st.error(f"Kan projectdata niet ophalen: {e}")
        st.stop()

    m = folium.Map(location=[52.1, 5.2], zoom_start=8)

    for f in feats:
        geom = f.get("geometry")
        if geom and "rings" in geom:
            for ring in geom["rings"]:
                latlon = [(y, x) for x, y in ring]
                folium.Polygon(latlon, color="blue", fill=True, weight=2).add_to(m)

    st_folium(m, height=600)

with tab_tbl:
    st.subheader("Tabeloverzicht")
    df = pd.DataFrame([f["attributes"] for f in feats])
    st.dataframe(df, use_container_width=True, height=600)
