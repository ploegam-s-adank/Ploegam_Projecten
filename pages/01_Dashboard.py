# -*- coding: utf-8 -*-
import base64
import math
import streamlit as st
import pandas as pd
import folium
from folium.plugins import Fullscreen
from streamlit_folium import st_folium

# ✅ Let op: underscore, geen backslash!
from utils_agol import AGOL

st.set_page_config(page_title="Dashboard", layout="wide")
st.header("📊 Dashboard")

# ──────────────────────────────────────────────────────────────────────────────
# CONFIG & DATA
# ──────────────────────────────────────────────────────────────────────────────
cfg = st.secrets["arcgis"]
agol = AGOL(cfg["username"], cfg["password"], cfg["portal"])
projects_url = cfg["projects_layer_url"]

# Pad naar je PNG-icoon voor punten (pas aan naar jouw pad)
POINT_ICON_PATH = "assets/Logo.png"   # <-- zet jouw PNG hier neer (bijv. uit je repo)

def load_png_as_data_url(path: str) -> str | None:
    try:
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        return f"data:image/png;base64,{b64}"
    except Exception:
        return None

point_icon_data_url = load_png_as_data_url(POINT_ICON_PATH)

try:
    res = agol.query(projects_url, out_fields="*", return_geometry=True, extra={"outSR": 4326})
    feats = res.get("features", [])
    if not feats:
        st.warning("Geen features gevonden in de laag.")
except Exception as e:
    st.error(f"Fout bij ophalen projectdata: {e}")
    st.stop()

df = pd.DataFrame([f.get("attributes", {}) for f in feats])

# ID-veld bepalen
id_candidates = [c for c in ["OBJECTID", "FID", "Id", "id"] if c in df.columns]
ID_FIELD = id_candidates[0] if id_candidates else (df.columns[0] if len(df.columns) else None)

# Labelveld
label_candidates = [c for c in df.columns if c.lower() in ("projectnaam", "naam", "title", "name")]
DEFAULT_LABEL = label_candidates[0] if label_candidates else (df.columns[0] if len(df.columns) else None)

# ──────────────────────────────────────────────────────────────────────────────
# ZIJBALK – instellingen
# ──────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.subheader("🛠️ Weergave & interactie")

    basemap = st.selectbox(
        "Ondergrond",
        options=["OpenStreetMap", "CartoDB Positron", "CartoDB DarkMatter", "Stamen Terrain", "Esri WorldImagery"],
        index=0,
    )

    map_height = st.slider("Hoogte kaart (px)", 450, 1000, 650, 50)

    # Tooltip label(s)
    show_tooltips = st.toggle("Labels (tooltip) tonen", True)
    label_fields = st.multiselect(
        "Labelvelden",
        options=df.columns.tolist(),
        default=[DEFAULT_LABEL] if DEFAULT_LABEL else []
    )

    # Popup toont alle kolommen
    show_popup_all = st.toggle("Popup alle kolommen", True)

    # Icoongrootte voor het PNG-symbool
    icon_px = st.slider("Punticoon grootte (px)", 12, 64, 28)

    zoom_to_selection = st.toggle("Automatisch zoomen naar selectie", True)

    # Selectie via ID
    if ID_FIELD and not df.empty:
        # Mooiere label-tekst voor selectie
        if DEFAULT_LABEL and DEFAULT_LABEL in df.columns:
            id_to_label = dict(zip(df[ID_FIELD], df[DEFAULT_LABEL]))
            fmt = lambda oid: f"{oid} – {id_to_label.get(oid, '')}"
        else:
            fmt = lambda oid: str(oid)

        # State voor selectie
        if "selected_id" not in st.session_state:
            st.session_state["selected_id"] = df[ID_FIELD].iloc[0]

        st.session_state["selected_id"] = st.selectbox(
            "Selecteer record",
            options=df[ID_FIELD].tolist(),
            format_func=fmt
        )
    else:
        st.info("Geen ID-veld gevonden voor selectie.")

# ──────────────────────────────────────────────────────────────────────────────
# GEOMETRIE HELPERS
# ──────────────────────────────────────────────────────────────────────────────
def esri_to_struct(geom: dict) -> dict | None:
    """Zet ESRI-geom om naar {'type': 'point'|'polyline'|'polygon', 'coords': [...]} met (lat, lon)."""
    if not geom:
        return None
    if "x" in geom and "y" in geom:
        return {"type": "point", "coords": [(geom["y"], geom["x"])]}
    if "paths" in geom:
        paths = [[(y, x) for x, y in path] for path in geom["paths"]]
        return {"type": "polyline", "coords": paths}
    if "rings" in geom:
        rings = [[(y, x) for x, y in ring] for ring in geom["rings"]]
        return {"type": "polygon", "coords": rings}
    return None

def bounds_of_struct(struct: dict) -> tuple | None:
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

def tooltip_text(attrs: dict, fields: list[str] | None) -> str | None:
    if not fields:
        return None
    parts = []
    for c in fields:
        parts.append(f"{c}: {attrs.get(c, '')}")
    return " | ".join(parts) if parts else None

def popup_html(attrs: dict) -> str:
    rows = "".join(
        f"<tr><th style='text-align:left;padding-right:8px;'>{k}</th><td>{attrs.get(k, '')}</td></tr>"
        for k in attrs.keys()
    )
    return f"<table>{rows}</table>"

# ──────────────────────────────────────────────────────────────────────────────
# KAART OPBOUWEN
# ──────────────────────────────────────────────────────────────────────────────
default_center = [52.1, 5.2]
m = folium.Map(location=default_center, zoom_start=8, tiles=None, control_scale=True)

# Tiles
if basemap == "OpenStreetMap":
    folium.TileLayer("OpenStreetMap", name="OpenStreetMap").add_to(m)
elif basemap == "CartoDB Positron":
    folium.TileLayer("CartoDB positron", name="CartoDB Positron").add_to(m)
elif basemap == "CartoDB DarkMatter":
    folium.TileLayer("CartoDB dark_matter", name="CartoDB DarkMatter").add_to(m)
elif basemap == "Stamen Terrain":
    folium.TileLayer("Stamen Terrain", name="Stamen Terrain").add_to(m)
elif basemap == "Esri WorldImagery":
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles © Esri",
        name="Esri WorldImagery"
    ).add_to(m)

fg_all = folium.FeatureGroup(name="Projecten", show=True)
fg_sel = folium.FeatureGroup(name="🔶 Selectie", show=True)

global_bounds = None
bounds_by_id = {}

# Teken alles + bepaal bounds
for f in feats:
    attrs = f.get("attributes", {})
    geom = f.get("geometry", {})
    struct = esri_to_struct(geom)
    if not struct:
        continue

    b = bounds_of_struct(struct)
    if b:
        if global_bounds is None:
            global_bounds = b
        else:
            global_bounds = (
                min(global_bounds[0], b[0]),
                min(global_bounds[1], b[1]),
                max(global_bounds[2], b[2]),
                max(global_bounds[3], b[3])
            )

    fid = attrs.get(ID_FIELD) if ID_FIELD else None
    if fid is not None and b:
        bounds_by_id[fid] = b

    tip = tooltip_text(attrs, label_fields) if show_tooltips else None
    pop = folium.Popup(popup_html(attrs), max_width=500) if show_popup_all else None

    if struct["type"] == "point":
        (lat, lon) = struct["coords"][0]
        # PNG-icoon indien beschikbaar, anders CircleMarker
        if point_icon_data_url:
            folium.Marker(
                location=(lat, lon),
                icon=folium.CustomIcon(icon_image=point_icon_data_url, icon_size=(icon_px, icon_px)),
                tooltip=tip,
                popup=pop
            ).add_to(fg_all)
        else:
            folium.CircleMarker(
                location=(lat, lon),
                radius=max(6, icon_px // 2),
                color="#1f77b4",
                fill=True,
                fill_color="#1f77b4",
                weight=1,
                tooltip=tip,
                popup=pop
            ).add_to(fg_all)
    elif struct["type"] == "polyline":
        for path in struct["coords"]:
            folium.PolyLine(path, color="#d62728", weight=3, tooltip=tip, popup=pop).add_to(fg_all)
    elif struct["type"] == "polygon":
        for ring in struct["coords"]:
            folium.Polygon(
                ring, color="#1f77b4", weight=2, fill=True, fill_opacity=0.2, tooltip=tip, popup=pop
            ).add_to(fg_all)

# Highlight selectie
sel_id = st.session_state.get("selected_id", None)
if sel_id is not None:
    for f in feats:
        attrs = f.get("attributes", {})
        if attrs.get(ID_FIELD) != sel_id:
            continue
        geom = f.get("geometry", {})
        struct = esri_to_struct(geom)
        if not struct:
            break

        tip = tooltip_text(attrs, label_fields) if show_tooltips else None
        pop = folium.Popup(popup_html(attrs), max_width=500) if show_popup_all else None

        if struct["type"] == "point":
            (lat, lon) = struct["coords"][0]
            # Iets groter icoon of amber kleur als fallback
            if point_icon_data_url:
                folium.Marker(
                    location=(lat, lon),
                    icon=folium.CustomIcon(icon_image=point_icon_data_url, icon_size=(max(icon_px + 6, icon_px), max(icon_px + 6, icon_px))),
                    tooltip=tip, popup=pop
                ).add_to(fg_sel)
            else:
                folium.CircleMarker(
                    location=(lat, lon),
                    radius=max(8, icon_px // 2 + 2),
                    color="#ffbf00", fill=True, fill_color="#ffbf00", weight=2, tooltip=tip, popup=pop
                ).add_to(fg_sel)
        elif struct["type"] == "polyline":
            for path in struct["coords"]:
                folium.PolyLine(path, color="#ffbf00", weight=6, tooltip=tip, popup=pop).add_to(fg_sel)
        elif struct["type"] == "polygon":
            for ring in struct["coords"]:
                folium.Polygon(ring, color="#ffbf00", weight=4, fill=True, fill_opacity=0.15, tooltip=tip, popup=pop).add_to(fg_sel)

        # Zoomen naar selectie
        if zoom_to_selection and sel_id in bounds_by_id:
            (min_lat, min_lon, max_lat, max_lon) = bounds_by_id[sel_id]
            m.fit_bounds([[min_lat, min_lon], [max_lat, max_lon]])
        break

fg_all.add_to(m)
fg_sel.add_to(m)
Fullscreen().add_to(m)
folium.LayerControl(collapsed=False).add_to(m)

# Als geen selectie/zoom, fit op alle data
if (sel_id is None or not zoom_to_selection) and global_bounds:
    (min_lat, min_lon, max_lat, max_lon) = global_bounds
    m.fit_bounds([[min_lat, min_lon], [max_lat, max_lon]])

# KAART tonen, over volledige breedte
st_map = st_folium(m, height=map_height, use_container_width=True)

# ──────────────────────────────────────────────────────────────────────────────
# TABEL – volledige breedte
# ──────────────────────────────────────────────────────────────────────────────
st.subheader("🗂️ Projecten")
if not df.empty:
    # Visuele indicator voor selectie
    if ID_FIELD:
        df_show = df.copy()
        df_show.insert(0, "🔶 geselecteerd", df_show[ID_FIELD].eq(sel_id))
        st.dataframe(df_show, use_container_width=True, height=600)
    else:
        st.dataframe(df, use_container_width=True, height=600)
else:
    st.info("Geen data om te tonen in de tabel.")

# ──────────────────────────────────────────────────────────────────────────────
# BEWERKEN – formulier voor geselecteerde feature
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("✏️ Bewerken")

if sel_id is None or df.empty or ID_FIELD not in df.columns:
    st.info("Selecteer eerst een record om te bewerken.")
else:
    # Attributen van het geselecteerde record ophalen
    current_attrs = df[df[ID_FIELD] == sel_id].iloc[0].to_dict()

    # Toggle bewerkmodus
    if "edit_mode" not in st.session_state:
        st.session_state["edit_mode"] = False

    cols_btn = st.columns([1, 4, 1])
    with cols_btn[0]:
        if st.button("Bewerken", use_container_width=True):
            st.session_state["edit_mode"] = True
    with cols_btn[2]:
        if st.session_state["edit_mode"]:
            if st.button("Annuleren", use_container_width=True):
                st.session_state["edit_mode"] = False

    if st.session_state["edit_mode"]:
        with st.form("edit_form", clear_on_submit=False):
            st.caption(f"Record ID: **{sel_id}**")

            edited = {}
            for col, val in current_attrs.items():
                # ID-veld niet bewerkbaar
                if col == ID_FIELD:
                    st.text_input(col, str(val), disabled=True)
                    edited[col] = val
                    continue

                # Eenvoudige type-afleiding
                if isinstance(val, (int, float)) and not isinstance(val, bool):
                    new_val = st.number_input(col, value=float(val) if val is not None else 0.0)
                    # Probeer integer terug te geven als origineel int was
                    if isinstance(val, int):
                        new_val = int(new_val)
                else:
                    new_val = st.text_input(col, "" if val is None else str(val))
                edited[col] = new_val

            submitted = st.form_submit_button("Wijzigingen opslaan")
            if submitted:
                # Bouw payload voor applyEdits/update
                payload = {"attributes": edited}

                try:
                    # 1) Probeer apply_edits (ArcGIS REST)
                    if hasattr(agol, "apply_edits"):
                        res = agol.apply_edits(projects_url, updates=[payload])
                    # 2) Anders probeer update (custom helper)
                    elif hasattr(agol, "update"):
                        res = agol.update(projects_url, updates=[payload])
                    else:
                        raise RuntimeError(
                            "AGOL-helper mist een methode om te schrijven (apply_edits/update)."
                        )
                    st.success("Wijzigingen opgeslagen.")
                    st.session_state["edit_mode"] = False
                    st.rerun()
                except Exception as e:
                    st.error(f"Opslaan mislukt: {e}")
