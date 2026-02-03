import streamlit as st
import pandas as pd
from utils_agol import AGOL, arcgis_polygon_from_geojson
from streamlit_folium import st_folium
import folium
from folium.plugins import Draw
from pathlib import Path

st.header("➕ Nieuw project invoeren")

cfg = st.secrets["arcgis"]
agol = AGOL(cfg["username"], cfg["password"], cfg["portal"])
projects_url = cfg["projects_layer_url"]
relation_field = cfg["relation_key_field"]

DOMAINS = Path("assets/domains")

def load_csv_list(fname: str):
    path = DOMAINS / fname
    if not path.exists():
        return []
    df = pd.read_csv(path)
    col = "waarde" if "waarde" in df.columns else df.columns[0]
    return df[col].astype(str).tolist()

# (name, type, required, maxlen, dropdown, source)
FIELDS = [
    ("Projectnr","text", True, 10,  False, None),
    ("Bedrijf","int",   True, None, True,  ["001","090","315"]),
    ("Omschrijving","text", True, 256, False, None),
    ("Opdrachtgever","text", True, 100, False, None),
    ("Calcnr","text", False, 10,  False, None),
    ("Soort","text", True, 20, True, ["Combinatie","Eigen beheer","Onder aanneming"]),
    ("Combinanten","text", False, 50, True, ["ACW","Den Ouden","Dura Vermeer","Dura Vermeer Jansma","GMB","Grondbank","Heijmans","Infrascoop","KOVANO","Lenthe","Peters","Uitert"]),
    ("Combinaam","text", False, 20, True, ["Biggelaar","Gebr. De Koning","GMB","Holandia","Uitert","Van Oord"]),
    ("Aanneemsom","float", False, None, False, None),
    ("Geplande_start","date", False, None, False, None),
    ("Geplande_oplev","date", False, None, False, None),
    ("Status","text", True, 20, True, ["Onderhanden","Gereed"]),
    ("MT_lid","text", False, 5, True, load_csv_list("Directie_MT.csv")),
    ("PL","text", True, 5, True, load_csv_list("Projectleiders.csv")),
    ("WVB_1","text", False, 5, True, load_csv_list("Werkvoorbereiders.csv")),
    ("WVB_2","text", False, 5, True, load_csv_list("Werkvoorbereiders.csv")),
    ("Uitvoerder","text", False, 5, True, load_csv_list("Uitvoerders.csv")),
    ("KAM_mer","text", False, 5, True, load_csv_list("KAM.csv")),
    ("Opdrachtbonnen","text", False, 5, False, None),
    ("Emailadres","text", False, 40, False, None),
    ("Financieel","text", False, 5, False, None),
    ("Directie_Combi","text", False, 5, False, None),
    ("Adres","text", True, 256, False, None),
    ("Factuur_aan","text", False, 256, False, None),
    ("Controller","text", False, 5, True, load_csv_list("Controllers.csv")),
    ("Projectmap","text", True, 256, False, None),
]

form_vals = {}
cols = st.columns(2)
for i, (name,typ,req,maxlen,dd,src) in enumerate(FIELDS):
    col = cols[i % 2]
    with col:
        label = f"{name}{' *' if req else ''}"
        if dd:
            options = src if isinstance(src, list) else []
            form_vals[name] = st.selectbox(label, options=options, key=name)
        else:
            if typ == "text":
                form_vals[name] = st.text_input(label, max_chars=maxlen, key=name)
            elif typ == "int":
                form_vals[name] = st.number_input(label, step=1, format="%d", key=name)
            elif typ == "float":
                form_vals[name] = st.number_input(label, step=1000.0, key=name)
            elif typ == "date":
                d = st.date_input(label, key=name)
                form_vals[name] = d.strftime("%Y-%m-%d") if d else None
            else:
                form_vals[name] = st.text_input(label, key=name)

st.caption("Velden met * zijn verplicht.")

st.subheader("Teken projectgebied")
m = folium.Map(location=[52.1, 5.2], zoom_start=8)
Draw(export=True).add_to(m)
out = st_folium(m, height=500)

geom = None
if out and out.get("last_active_drawing"):
    gj = out["last_active_drawing"].get("geometry")
    if gj:
        geom = arcgis_polygon_from_geojson(gj, wkid=4326)

if st.button("Opslaan"):
    missing = [nm for (nm,typ,req,_,_,_) in FIELDS if req and not form_vals.get(nm)]
    if missing:
        st.error("Ontbrekende verplichte velden: " + ", ".join(missing))
        st.stop()

    # lengte-checks
    too_long = []
    for (nm,typ,req,maxlen,_,_) in FIELDS:
        if maxlen and isinstance(form_vals.get(nm), str) and len(form_vals[nm]) > maxlen:
            too_long.append(nm)
    if too_long:
        st.error("Te lange invoer bij: " + ", ".join(too_long))
        st.stop()

    attrs = form_vals.copy()
    attrs[relation_field] = form_vals.get("Projectnr")

    feature = {"attributes": attrs}
    if geom:
        feature["geometry"] = geom

    try:
        res = agol.add_features(projects_url, [feature])
        st.success("Project opgeslagen.")
    except Exception as e:
        st.error(f"Fout bij opslaan: {e}")
