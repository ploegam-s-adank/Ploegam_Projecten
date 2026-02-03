import streamlit as st
from utils_agol import AGOL, arcgis_polygon_from_geojson
from streamlit_folium import st_folium
import folium
from folium.plugins import Draw

st.header("➕ Nieuw project / Project bewerken")

cfg = st.secrets["arcgis"]
agol = AGOL(cfg["username"], cfg["password"], cfg.get("portal"))

projects_url = cfg["projects_layer_url"]
workareas_url = cfg["workareas_layer_url"]
relation_field = cfg["relation_key_field"]

# ===========================
# FORMULIER
# ===========================

st.subheader("Projectgegevens")

projectnr = st.text_input("Projectnummer")
naam = st.text_input("Naam project")
status = st.selectbox("Status", ["Actief", "Afgerond", "Pauze"])

st.subheader("Teken projectgebied")

m = folium.Map(location=[52.1, 5.2], zoom_start=8)
draw = Draw(export=True)
draw.add_to(m)

output = st_folium(m, height=500)

geom = None
if output and "last_active_drawing" in output:
    geom = output["last_active_drawing"]

if st.button("Opslaan"):
    if not projectnr:
        st.error("Projectnummer is verplicht.")
        st.stop()

    feat = {
        "attributes": {
            relation_field: projectnr,
            "Naam": naam,
            "Status": status
        }
    }

    if geom:
        feat["geometry"] = arcgis_polygon_from_geojson(geom["geometry"])

    try:
        agol.add_features(projects_url, [feat])
        st.success("Project opgeslagen.")
    except Exception as e:
        st.error(f"Fout bij opslaan: {e}")