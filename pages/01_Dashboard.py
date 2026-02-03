import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
from utils_agol import AGOL

st.header("📊 Dashboard – Overzicht & Kaart")

cfg = st.secrets["arcgis"]
agol = AGOL(cfg["username"], cfg["password"], cfg["portal"])

projects_url = cfg["projects_layer_url"]
webmap_id = cfg.get("webmap_id", "")

# --- Embedded AGOL kaart ---
st.subheader("🗺️ Kaartweergave")

if not webmap_id:
    st.error("Geen webmap_id ingesteld in secrets.toml")
else:
    embed_url = f"https://www.arcgis.com/apps/Embed/index.html?webmap={webmap_id}&zoom=true&legend=true&scale=true&theme=light"
    components.iframe(embed_url, height=600, scrolling=True)

# --- Tabel ---
st.subheader("📋 Projecten tabel")

try:
    data = agol.query(projects_url, out_fields="*", extra={"outSR":4326})
    feats = data.get("features", [])
    df = pd.DataFrame([f["attributes"] for f in feats])
except Exception as e:
    st.error(f"Fout bij laden: {e}")
    st.stop()

st.dataframe(df, use_container_width=True, height=600)
