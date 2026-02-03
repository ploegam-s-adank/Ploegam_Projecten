import streamlit as st
import pandas as pd
import folium
from folium.plugins import Fullscreen
from streamlit_folium import st_folium
from utils_agol import AGOL

st.set_page_config(page_title="Dashboard – Kaart + Tabel", layout="wide")
st.header("📊 Dashboard – Kaart + Tabel")

# ──────────────────────────────────────────────────────────────────────────────
# DATA OPHALEN VAN AGOL
# ──────────────────────────────────────────────────────────────────────────────
cfg = st.secrets["arcgis"]
agol = AGOL(cfg["username"], cfg["password"], cfg["portal"])
projects_url = cfg["projects_layer_url"]

try:
    res = agol.query(
        projects_url, out_fields="*", return_geometry=True, extra={"outSR": 4326}
    )
    feats = res.get("features", [])
    if not feats:
        st.warning("Geen features gevonden in de laag.")
except Exception as e:
    st.error(f"Fout bij ophalen projectdata: {e}")
    st.stop()

# DataFrame met attributen
df = pd.DataFrame([f.get("attributes", {}) for f in feats])

# Kies een ID-veld (OBJECTID komt het meeste voor in ArcGIS)
id_field_candidates = [c for c in ["OBJECTID", "FID", "Id", "id"] if c in df.columns]
id_field = id_field_candidates[0] if id_field_candidates else (df.columns[0] if len(df.columns) else None)

# Bepaal een handig weergaveveld voor labels (indien aanwezig)
display_candidates = [c for c in df.columns if c.lower() in ("projectnaam", "naam", "title", "name")]
default_label_field = display_candidates[0] if display_candidates else (df.columns[0] if len(df.columns) else None)

# ──────────────────────────────────────────────────────────────────────────────
# ZIJBALK – UI VOOR WEERGAVE/CONFIG
# ──────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.subheader("🛠️ Weergave & interactie")

    basemap = st.selectbox(
        "Ondergrond",
        options=["OpenStreetMap", "CartoDB Positron", "CartoDB DarkMatter", "Stamen Terrain", "Esri WorldImagery"],
        index=0,
    )

    map_height = st.slider("Hoogte kaart (px)", min_value=400, max_value=1000, value=600, step=50)

    show_tooltips = st.toggle("Labels tonen (tooltip)", value=True)
    label_fields = st.multiselect(
        "Labelvelden (tooltip)",
        options=df.columns.tolist(),
        default=[default_label_field] if default_label_field else [],
        help="Kies 1 of meer kolommen die als tooltip op kaartobjecten verschijnen."
    )

    show_popup_all = st.toggle("Popup met alle attribuutwaarden", value=True)

    point_radius = st.slider("Puntgrootte (radius)", min_value=3, max_value=14, value=6)

    zoom_to_selection = st.toggle("Zoom naar selectie op kaart", value=True)

    table_height = st.slider("Tabelhoogte (px)", min_value=300, max_value=900, value=600, step=50)

    # Tabelkolommen kiezen
    visible_columns = st.multiselect(
        "Kolommen in tabel",
        options=df.columns.tolist(),
        default=df.columns.tolist()
    )

    # Selectie via ID (eenvoudig en robuust)
    selection_options = df[id_field].tolist() if id_field and not df.empty else []
    # Mapping naar leesbare labeltekst
    if default_label_field and default_label_field in df.columns:
        id_to_label = dict(zip(df[id_field], df[default_label_field]))
        fmt = lambda oid: f"{oid} – {id_to_label.get(oid, '')}"
    else:
        fmt = lambda oid: str(oid)

    selected_id = st.selectbox(
        "Selecteer record om uit te lichten",
        options=selection_options,
        format_func=fmt if selection_options else str,
        index=0 if selection_options else None
    )

# ──────────────────────────────────────────────────────────────────────────────
# HULPFUNCTIES VOOR GEOMETRIE
# ──────────────────────────────────────────────────────────────────────────────
def _coords_from_esri_geom(geom):
    """
    Zet ESRI-geometrie om naar lijst(en) met (lat, lon)-coördinaten.
    Retourneert dict met type: 'point'|'polyline'|'polygon' en 'coords':
      - point: [(lat, lon)]
      - polyline: [ [(lat, lon), ...], ... ]  (meerdere paths)
      - polygon:  [ [(lat, lon), ...], ... ]  (meerdere ringen)
    """
    if not geom:
        return None
    if "x" in geom and "y" in geom:
        return {"type": "point", "coords": [(geom["y"], geom["x"])]}
    if "paths" in geom:
        paths = []
        for path in geom["paths"]:
            paths.append([(y, x) for x, y in path])
        return {"type": "polyline", "coords": paths}
    if "rings" in geom:
        rings = []
        for ring in geom["rings"]:
            rings.append([(y, x) for x, y in ring])
        return {"type": "polygon", "coords": rings}
    return None

def _bounds_of_coords(struct):
    """
    Bepaal (min_lat, min_lon, max_lat, max_lon) voor een coords-structuur zoals hierboven.
    """
    lats, lons = [], []
    t = struct["type"]
    if t == "point":
        for (lat, lon) in struct["coords"]:
            lats.append(lat); lons.append(lon)
    else:
        for part in struct["coords"]:
            for (lat, lon) in part:
                lats.append(lat); lons.append(lon)
    if not lats or not lons:
        return None
    return (min(lats), min(lons), max(lats), max(lons))

def _tooltip_text(props, fields):
    if not fields:
        return None
    vals = []
    for c in fields:
        v = props.get(c, "")
        vals.append(f"{c}: {v}")
    return " | ".join(vals) if vals else None

def _popup_html(props, fields=None):
    """
    Bouw HTML voor popup. Als fields=None of empty => toon alle velden.
    """
    keys = fields if fields else list(props.keys())
    rows = "".join(
        f"<tr><th style='text-align:left; padding-right:8px;'>{k}</th><td>{props.get(k, '')}</td></tr>"
        for k in keys
    )
    return f"<table>{rows}</table>"

# ──────────────────────────────────────────────────────────────────────────────
# KAART OPBOUWEN
# ──────────────────────────────────────────────────────────────────────────────
# Bepaal totale dataset-bounds voor initiële extent
global_bounds = None
feature_bounds_by_id = {}

for f in feats:
    geom = f.get("geometry")
    struct = _coords_from_esri_geom(geom)
    if not struct:
        continue
    b = _bounds_of_coords(struct)
    if not b:
        continue
    feature_id = f.get("attributes", {}).get(id_field) if id_field else None
    if feature_id is not None:
