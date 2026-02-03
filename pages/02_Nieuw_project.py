import streamlit as st
import pandas as pd
from utils_agol import AGOL, arcgis_polygon_from_geojson
from streamlit_folium import st_folium
import folium
from folium.plugins import Draw
from pathlib import Path
from datetime import datetime

st.header("➕ Nieuw project invoeren")

cfg = st.secrets["arcgis"]
agol = AGOL(cfg["username"], cfg["password"], cfg["portal"])
projects_url = cfg["projects_layer_url"]
relation_field = cfg["relation_key_field"]

# CSV map
DOMAINS = Path("assets/domains")

def load_csv(name):
    csv = DOMAINS / name
    if not csv.exists(): return []
    df = pd.read_csv(csv)
    return df["waarde"].astype(str).tolist()


# --- JOUW FORMULIER SCHEMA (volledig) ---
FIELDS = [
    ("Projectnr","text",True,10,False,None),
    ("Bedrijf","int",True,None,True,["001","090","315"]),
    ("Omschrijving","text",True,256,False,None),
    ("Opdrachtgever","text",True,100,False,None),
    ("Calcnr","text",False,10,False,None),
    ("Soort","text",True,20,True,["Combinatie","Eigen beheer","Onder aanneming"]),
    ("Combinanten","text",False,50,True,["ACW","Den Ouden","Dura Vermeer","Dura Vermeer Jansma","GMB","Grondbank","Heijmans","Infrascoop","KOVANO","Lenthe","Peters","Uitert"]),
    ("Combinaam","text",False,20,True,["Biggelaar","Gebr. De Koning","GMB","Holandia","Uitert","Van Oord"]),
    ("Aanneemsom","float",False,None,False,None),
    ("Geplande_start","date",False,None,False,None),
    ("Geplande_oplev","date",False,None,False,None),
    ("Status","text",True,20,True,["Onderhanden","Gereed"]),
    ("MT_lid","text",False,5,True,load_csv("Directie_MT.csv")),
    ("PL","text",True,5,True,load_csv("Projectleiders.csv")),
    ("WVB_1","text",False,5,True,load_csv("Werkvoorbereiders.csv")),
    ("WVB_2","text",False,5,True,load_csv("Werkvoorbereiders.csv")),
    ("Uitvoerder","text",False,5,True,load_csv("Uitvoerders.csv")),
    ("KAM_mer","text",False,5,True,load_csv("KAM.csv")),
    ("Opdrachtbonnen","text",False,5,False,None),
    ("Emailadres","text",False,40,False,None),
    ("Financieel","text",False,5,False,None),
    ("Directie_Combi","text",False,5,False,None),
    ("Adres","text",True,256,False,None),
    ("Factuur_aan","text",False,256,False,None),
    ("Controller","text",False,5,True,load_csv("Controllers.csv")),
    ("Projectmap","text",True,256,False,None),
]

form_vals = {}

cols = st.columns(2)
for i, (name,t,v,l,dd,opts) in enumerate(FIELDS):
    col = cols[i % 2]
    with col:
        label = name + (" *" if v else "")
        if dd:
            form_vals[name] = st.selectbox(label, options=opts)
        else:
            if t=="text": form_vals[name] = st.text_input(label, max_chars=l)
            if t=="int": form_vals[name] = st.number_input(label, step=1, format="%d")
            if t=="float": form_vals[name] = st.number_input(label, step=1000.0)
            if t=="date":
                d = st.date_input(label)
                form_vals[name] = d.strftime("%Y-%m-%d") if d else None

st.caption("Velden met * zijn verplicht.")

# --- Geometrie tekenen ---
st.subheader("Teken projectgebied")
m = folium.Map(location=[52.1,5.2], zoom_start=8)
Draw(export=True).add_to(m)
out = st_folium(m, height=500)
geom = None
if out.get("last_active_drawing"):
    gj = out["last_active_drawing"]["geometry"]
    geom = arcgis_polygon_from_geojson(gj)

# --- Opslaan ---
if st.button("Opslaan"):
    missing = [name for (name,t,v,l,dd,opts) in FIELDS if v and not form_vals[name]]
    if missing:
        st.error(f"Ontbrekende verplichte velden: {', '.join(missing)}")
        st.stop()

    attrs = form_vals.copy()
    attrs[relation_field] = form_vals["Projectnr"]

    feature = {"attributes": attrs}
    if geom: feature["geometry"] = geom

    try:
        res = agol.add_features(projects_url, [feature])
        st.success("Project opgeslagen.")
    except Exception as e:
        st.error(f"Fout: {e}")
