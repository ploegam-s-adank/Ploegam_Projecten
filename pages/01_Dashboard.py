import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
from utils_agol import AGOL

st.header("📊 Dashboard – Overzicht & Kaart")

cfg = st.secrets["arcgis"]
agol = AGOL(cfg["username"], cfg["password"], cfg["portal"])

projects_url = cfg["projects_layer_url"]
webmap_id = cfg.get("webmap_id", "")

tab_map, tab_tbl = st.tabs(["🗺️ Kaart", "📋 Tabel"])

with tab_map:
    st.subheader("AGOL kaart")
    if not webmap_id:
        st.error("Geen 'webmap_id' ingesteld in secrets.toml – voeg deze toe onder [arcgis].")
    else:
        # iFrame embed van Map Viewer "Embed" app (publiek gedeelde webmap)
        embed_url = (
            f"https://www.arcgis.com/apps/Embed/index.html"
            f"?webmap={webmap_id}"
            f"&zoom=true&legend=true&scale=true&details=false&theme=light"
        )
        components.iframe(embed_url, height=600, scrolling=True)

with tab_tbl:
    st.subheader("Projecten tabel")
    try:
        # outSR=4326 → coördinaten bruikbaar buiten ArcGIS indien nodig
        data = agol.query(projects_url, out_fields="*", extra={"outSR": 4326})
        feats = data.get("features", [])
        df = pd.DataFrame([f["attributes"] for f in feats])
    except Exception as e:
        st.error(f"Fout bij laden van projectlaag: {e}")
        st.stop()

    if df.empty:
        st.info("Geen records gevonden in de projectlaag.")
    else:
        st.dataframe(df, use_container_width=True, height=640)
