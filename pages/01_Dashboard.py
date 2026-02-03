# -*- coding: utf-8 -*-
"""
Ploegam – Dashboard (Kaart + Tabel)
- Floating panel (Kaartopties)
- Esri World Topographic / Esri World Imagery
- Kaart default 500px hoog
- Altijd fit-to-layer bij laden + knop "Zoom volledige laag"
- Punten met assets/logo.png (CustomIcon)
- Tooltip = Projectnr, Popup = alle kolommen
- Selectie via kaart (klik) én via tabel (AG-Grid)
- Bewerken via Model B (Bewerken -> Opslaan) met update_features()
"""

from __future__ import annotations
import base64
import math
from typing import Any, Dict, List, Tuple

import streamlit as st
import pandas as pd
import folium
from folium.plugins import Fullscreen
from streamlit_folium import st_folium

# Tabelselectie met AG-Grid (optioneel, maar aanbevolen)
try:
    from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
    AGGRID_AVAILABLE = True
except Exception:
    AGGRID_AVAILABLE = False

# ✅ Juiste import van jouw helper (let op underscore)
from utils_agol import AGOL  # utils_agol.py bevat update_features/add_features/delete_features  # noqa: E402

# ──────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Ploegam – Kaart + Tabel", layout="wide")
st.markdown("## 📊 Dashboard – Kaart + Tabel")

# ──────────────────────────────────────────────────────────────────────────────
# CONFIG / CONSTANTS
# ──────────────────────────────────────────────────────────────────────────────
# Veldnamen
ID_CANDIDATES = ["OBJECTID", "FID", "Id", "id"]
LABEL_FIELD = "Projectnr"  # altijd tooltiplabel
ICON_PATH = "assets/logo.png"  # jouw PNG-icoon in de repo

# Map defaults
DEFAULT_BASEMAP = "Esri World Topographic"
DEFAULT_MAP_HEIGHT = 500  # px

# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────
def load_png_as_data_url(path: str) -> str | None:
    """Laad PNG en retourneer data-URI (base64) zodat Folium/Leaflet hem inline kan gebruiken."""
    try:
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        return f"data:image/png;base64,{b64}"
    except Exception:
        return None

def esri_to_struct(geom: Dict[str, Any]) -> Dict[str, Any] | None:
    """Zet ESRI geometry om naar generieke structuur met (lat, lon)."""
    if not geom:
        return None
    if "x" in geom and "y" in geom:
        return {"type": "point", "coords": [(geom["y"], geom["x"])]}
    if "paths" in geom:  # polyline
        paths = [[(y, x) for x, y in path] for path in geom["paths"]]
        return {"type": "polyline", "coords": paths}
    if "rings" in geom:  # polygon
        rings = [[(y, x) for x, y in ring] for ring in geom["rings"]]
        return {"type": "polygon", "coords": rings}
    return None

def struct_bounds(struct: Dict[str, Any]) -> Tuple[float, float, float, float] | None:
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

def struct_center(struct: Dict[str, Any]) -> Tuple[float, float] | None:
    """Ruwe center als gemiddelde van bounds (prima voor selectie/zoom)."""
    b = struct_bounds(struct)
    if not b:
        return None
    (min_lat, min_lon, max_lat, max_lon) = b
    return ((min_lat + max_lat) / 2.0, (min_lon + max_lon) / 2.0)

def haversine_m(lat1, lon1, lat2, lon2) -> float:
    """Afstand in meters tussen twee lat/lon punten."""
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = phi2 - phi1
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def popup_html(attrs: Dict[str, Any]) -> str:
    rows = "".join(
        f"<tr><th style='text-align:left;padding-right:8px;white-space:nowrap'>{k}</th>"
        f"<td>{'' if v is None else v}</td></tr>"
        for k, v in attrs.items()
    )
    return f"<table>{rows}</table>"

# ──────────────────────────────────────────────────────────────────────────────
# DATA LADEN VIA AGOL
# ──────────────────────────────────────────────────────────────────────────────
cfg = st.secrets["arcgis"]
agol = AGOL(cfg["username"], cfg["password"], cfg["portal"])  # gebruikt jouw utils_agol helper  # [1](https://ploegam-my.sharepoint.com/personal/s_adank_ploegam_nl/Documents/Microsoft%20Copilot%20Chat-bestanden/utils_agol%20(1).py).py)
layer_url = cfg["projects_layer_url"]

# Ophalen
try:
    res = agol.query(layer_url, out_fields="*", return_geometry=True,rue, extra={"outSR": 4326})
    featuresures = res.get("features", [])
except Exception as e:
    st.error(f"Fout bijFout bij ophalen data: {e}")
    st.stop()

if not features:
    st.warning("Geen features gevondengevonden in de laag.")
    st.stop()

# Attribuuttabel
df = pd.Data pd.DataFrame([f.get("attributes", {}) for f in features])

# Key-veld bepalen
id_field = None
for cand in ID_CANDIDATES:
    if cand in df.columns:
        id_field = cand
        break
if id_field is None:
    id_field = df.columns[0]

# LABEL veld controleren
if LABEL_FIELD not in df.columns:
    st.warning(f"Let op: labelveld '{LABEL_FIELD}' niet gevonden in kolommenmmen. Tooltip blijft leeg.")
# ──────────────────────────────────────────────────────────────────────────────
# VOORBEREIDING GEOMETRIE/BOUNDS
# ──────────────────────────────────────────────────────────────────────────────
# Normaliseer: maak een lijst met (et (attrs, struct, bounds, center)
norm: List[Dict[str, Any]] = []
global_bounds = None

for f inf in features:
    attrs = f.get("attributes", {})
    geom = f.get("geometrygeometry", {})
    struct = esri_to_struct(geom)
   eom)
    if not struct:
        continue
    b = struct_bounds(struct)
    c = struct_center(struct)
    item = {"attrs": attrs, "geom": geom, "struct": struct, "bounds": b, "center": c}
    normnorm.append(item)

    if b:
        if not global_bounds:
            global_bounds = b
        else:
            global_bounds = (
                min min(global_bounds[0], b[0]),
                    min(global_bounds[1], b[1]),
                max(global_bounds[2],[2], b[2]),
                max(global_bounds[3], b[, b[3]),
]),
            )

if not global_bounds:
    # fallback NL
   
    global_bounds = (50.5, 3.2, 53.7, 7.4)

# ──────────────────────────────────────────────────────────────────────────────
# STATE: SELECTIE + KAARTINSTELLINGEN
# ──────────────────────────────────────────────────────────────────────────────
if "selected_id" not in st.session_state:
    # geen autoselect; start zonder selectie
    st.session_state["selected_id"] = None

if "basemap" not in st.session_state:
    st.session_state["basemap"] = DEFAULT_BASEMAP

if "map_height" not in st.session_state:
    st.session_state["map_height"] = DEFAULT_MAP_HEIGHT

# ──────────────────────────────────────────────────────────────────────────────
# FLOATLOATING PANEL (POPOVER) – KAARTOPTIES
# ──────────────────────────────────────────────────────────────────────────────
right = st.columns([1, 0.140.14])[1]  # small right column voor de knop
with right:
    try:
        pop = st= st.popover("⚙ Kaartopties")
    except Exception:
        # Fallback voor oudere Streamlit-versies
        pop = st.expander("⚙r("⚙ Kaartopties", expanded=False)

with pop:
    st.write("**Ondergrond**nd**")
    st.session_state["basemap"] = st.radio(
        label="",
        options=["Esri World Topographic", "Esri World Imagery"],
        index=0 if st.session_state["basemap"] == "Esri World Topographic" else 1,
 1,
        horizontal=True
    )

   
    st.write("**Kaarthoogte**")
   
    st.session_state["map_height"] = st.slider(
        "Hoogte (px)", min_value=400, max_value=1000, value=st.session_state["map_height"], step=25,=25, label_visibility="collapsed"
    )

    if st.button("🔍 ZoomZoom volledige laag", use_container_width=True):
        # Zet een vlag die we bij het tekenen van de kaart gebruiken
        st.session_state["zoom_full_trigger"] = True
        st.experimental_rerunerun()

# ──────────────────────────────────────────────────────────────────────────────
# KAART TEKENEN (FOL(FOLIUM)
# ──────────────────────────────────────────────────────────────────────────────
icon_data_url = load_png_as_data_url(ICON_PATHPATH)
map_height = st.session_state["map_height"]
basemap = st.session_state["basemap"]

# Basiskaart initialiseren
default_center = [ (global_bounds[nds[0] + global_bounds[2]) / 2.0, (global_bounds[1] +1] + global_bounds[3]) / 2.0 ]
m = folium.Map(location=default_center, zoom_start=8, tiles=None, controltrol_scale=True)

# Ondergrond
if basemap == "Esri World Topographic":
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
        attr    attr="Esri World Topographic Map",
        name="Esri World Topographic Map",
        overlay=False
    ).add_to(m)
else:
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Imagery",
        name="Esri World Imagery",
            overlay=False
    ).  ).add_to(m)

fg_all = folium.FeatureGroup(namename="Projecten", show=True)
fg_sel = folium.FeatureGroup(name="🔶 Selectlectie", show=True)

# Teken alle features
for item in norm:
    attrs = item["attrs"]
    struct = item["struct"]

    tip = f"{LABEL_FIELD}: {attrsttrs.get(LABEL_FIELD, '')}" if LABEL_FIELD in attrs else None
    pop = foliumlium.Popup(popup_html(attrs), max_width=dth=520)

    if struct["type"] == "== "point":
        (lat, lon) = struct["coords"][0]
        if icon_data_url:
            folium.Marker(
                location=(lat, lon lon),
                icon=folium.CustomIcon(icon_image=icon_data_url, icon_size=(28,(28, 28)),
                tooltip=tip, popupp, popup=pop
            ).add_to(fg_all)
        else:
            fol folium.CircleMarker(
                location=(lat, lon), radius=7, color="#1f77b4", fill=True, fillfill_color="#1f77b4",
                tooltip=tip, popup=pop
            ).add.add_to(fg_all)
    elif struct["type"] == "polyline":
        for path in struct["coords"]:
            folium.PolyLine(path, color="#d62728", weight=3, tooltip=tip, popup=pup=pop).add_to(fgo(fg_all)
    elif struct["type"] == "polygon":
        for ring in struct["coords"]:
            folium.Polygon(ring, color="#1f77b4", weight=2, fill=True, fill_opacity=0.2, tooltip=tip, popup=pop=pop).add.add_to(fg_all)

#)

# Highlight selectie (indien aanwezig)
sel_id = st.session_state.get("selected_idd_id")
if)
if sel_id is not None:
    # zoek corresponderende feature
    for item in norm:
        attrs = item["attrs"]
        if attrs.get(id_field) != sel_id:
            continue
        struct = item["struct"]
        tip = f"{LABEL_FIELD}: {}: {attrs.get(LABEL_FIELD, '')}" if LABEL_FIELD in attrs else None
        pop = fol folium.Popup(popup_html(attrs),rs), max_width=520)

        if struct["type"] == "point":
                (lat, lon) = struct["coords"][0]
            if icon_data_url:
rl:
                folium.Marker(
                    location=(lat, lon),
                    icon=folium.CustomIcon(icon_image=icon_datadata_url, icon_size=(34, 34)),
                    tooltip=tip=tip, popup=pop
                ).add_to(fgo(fg_sel)
            else:
                folium.CircleMarker(
er(
                    location=(lat, lon), radius=10, color="#ffbf00", fill=True, fill_color="#ffbf00",
                    weight=2, tooltip=tip=tip, popup=pop
                ).add_to(fg_sel_sel)
        elif struct["type"] == "polyline":
            for path in struct["coords"]:
                        folium.PolyLine(path, color="#ffbf00", weight=6, tooltip=tip, popup=pop).add_to(fg_sel)
        elif struct["type"] == "polygon":
            for ring in struct["coords"]:
                folium.Polygon(ring, color="#ffbf00", weight=4, fill=True, fill_opacity=0.15, tooltip=tip, popup=pup=pop).add_to(fg_sel_sel)
        break

fg_all_all.add_to(m)
fgadd_to(m)
fg_sel.add_to(m)
Fullscreen().add_to(m)
folium)
folium.LayerControl(collapsed=False).add_to(m)

# Altijd naar volledige laag zoomen bij laden of bij expliciete trigger
(min_lat, min_lon,lon, max_lat, max_lon) = global_bounds
m.fit_bounds([[min_lat, min_lon], [], [max_lat, max_lon]])

#on]])

# Render kaart (volledige breedte)
st_map = st_folium(m, height=map_height, use_container_width=True)

# ──────────────────────────────────────────────────────────────────────────────
# SELECTIE DOOR TE KLIKKEN OP DE KAART
# ──────────────────────────────────────────────────────────────────────────────
# Standaard gedrag van st_folium: 'last_object_clicked' geeft lat/lon van laatste click/marker
loc = None
try:
    if st_map and "last_object_clicked" in st_map and st_map["last_object_clicked"]:
        loc = st_map["last_object_clicked"]
except Exception:
    loc = None

ifNone

if loc:
    lat_click = loc.get("lat")
    lon_click = loc.get("lng")
    # Vind dichtstbijzijndejnde feature(center) binnen 25 m (voor puntennten is dat exact)
    nearest = None
    nearest_dist = 25.0  # meter
    for item in norm:
        attrs = item["attrs"]
        cen = item["center"]
        if not cen:
            continue
        d = haversine_m(lat_click, lon_click, cen[0en[0], cen[1])
       
        if d <= nearest_dist:
            nearest = attrs.get(id_field)
            nearest_dist = d
    if nearest is not None and nearest != st.session_state.get("selected_id"):
        st.session_state["selected_id"_id"] = nearest
        st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
# TABEL – AG-Grid met single selection
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("### 🗂️"### 🗂️ Projecten")

df_show = df.copy()

# Visuele indicatorator (kolom 0)
df_show.insert(0, "🔶 geselecteerd", df_show[id_field].eq(st.session_state.get("selectedselected_id")))

if AGGRID_AVAILABLE:
    gb = GridOptionsBuilder.from_dataframe(df_show(df_show)
    gb.configure_selection(selection_mode="single", use_checkbox=False)
    gb.configure_gridgrid_options(domLayout='normal')  # basic stijl
    grid = AgGrid(
        df_show,
        gridgridOptions=gb.build(),
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        height=450,
        allow_unsafe_jscode=False,
        fit_columnsumns_on_grid_load=True
    )
    sel_rows = grid.get("selected_rowsrows", [])
    if sel_rows:
        new_id = sel_rows[0].get(idt(id_field)
        if new_id is not None and new_id != st.session_state.get.get("selected_id"):
            st.session_state["selected_id"] = new_id
                st.rerun()
else:
    st.info("Voor rijselectie in de tabel is **streamlit-aggrid** nodig. Voeg toe aan requirements.txt: `streamlit-agt-aggrid`.")
    st.dataframe(df_show, use_container_width=True, height=450=450)

# ──────────────────────────────────────────────────────────────────────────────
#──
# BEWERKEN (MODEL B) – Bewerken -> Opslaan
# ──────────────────────────────────────────────────────────────────────────────
st.markdowndown("---")
st.markdown("### ✏️ Bewerewerken")

sel_id = st= st.session_state.get("selected_id")
if sel_id is None:
   is None:
    st.info("Selecteer een record (in de kaart of de tabel) om te bewerken.")
else:
    current_attrs = df[df[id_field] == sel_id].iloc[0].to_dict()

    # Open/dicht edit mode
    if "edit_mode" not in st.session_state:
        st.session_state["edit_mode"] = False

    col_b, col_a = st.columns([0.15,.15, 0.85])
    with col_b:
        if not st.session_state["edit_mode"]:
            if st.button("Bewerken",en", use_container_width=True):
                st.session_state["edit_mode"] = True
        else:
            if st.button("Annuleren", use_container_widthidth=True):
                st.session_state["edit_mode"] = False
                st  st.rerun()

    if st.session_state["edit_mode"]:
        with st.form("edit_formform", clear_on_submit=False):
            st.captiontion(f"Record ID: **{sel_id}**")

            edited = {}
            for col, val val in current_attrs.items():
                # ID niet bewerkbaar
                if col == id_field:
_field:
                    st.text_input(col, str(val), disabled=True)
                    edited[col] = val
                    continue
                # type-heuristiek
                if isinstance(val, (intal, (int, float)) and not isinstance(val, bool):
                    # gebruik string->float fallbackback
                    default_val = float(val) if val is not None else 0.0
                    new_val = st.number_input(col,col, value=default_val)
                    if isinstance(val(val, int):
                        new_val = int(new(new_val)
                else:
                    new_val = st.text_input(col, "" if val is None else str(val(val))
                edited[col] = new_val

            submittedtted = st.form_submit_button("Opslaan")
                    if submitted:
                # Zoek geometrie van het geselecteerde object (optioneel bij update)
                selected_geom = None
                for item in norm:
                    if item["attrs"].get(id_field) == sel_id:
                        selected_geom = item["geom"]
                        break

                feature_payload = {"attributes": edited}
                # geometry meesturen is optioneel bij updateFeatures; we laten het achterwege tenzij je het expliciet wilt bijwerken.
                # Als je geometrie toch wilt meesturen, haal comment weg:
                # if selected_geom:
                #     feature_payload["geometry"] = selected_geom

                try:
                    # Gebruik jouw helper; update één feature
                    res_upd_upd = agol.update_features(layer_url, [feature_payload])  # gebruikt utils_agol.update_features  # [1](https://ploegam-my.sharepoint.com/personal/s_adank_ploegam_nl/Documents/Microsoft%20Copilot%20Chat-bestanden/utils_agol%20(1).py).py)
                    # Controle basisfeedback
ack
                    if isinstance(res_upd, dict)ict) and res_upd.get("updateResults"):
                        ok = res_upd["updateResults"][0].get("et("success", False)
                                if ok:
                            st.success("Wijzigingen opgeslagen.")
                            st.session_state["edit_mode"] = False
                            st.rerun()
                        else:
                            st.error(f"Opslaan mislukt:ukt: {res_upd['updateResults'][0]}")
                    else:
                        st.success("Wijzigingenngen verzonden.")
                        st.session_state["te["edit_mode"] = False
                        st.rerun()
                except Exception as e:
                    st.error(f"Opslaanlaan mislukt: {e}")

# ──────────────────────────────────────────────────────────────────────────────
# EINDE
# ──────────────────────────────────────────────────────────────────────────────
