import streamlit as st
import pandas as pd
from pathlib import Path
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw
from utils_agol import AGOL, arcgis_polygon_from_geojson

st.header("➕ Nieuw project invoeren")

cfg = st.secrets["arcgis"]
agol = AGOL(cfg["username"], cfg["password"], cfg.get("portal"))
projects_url = cfg["projects_layer_url"]
relation_field = cfg["relation_key_field"]

DOMAINS = Path("assets/domains")

def load_csv(name):
    p = DOMAINS / name
    if not p.exists():
        return []
    try:
        df = pd.read_csv(p, sep=None, engine="python")
        col = "waarde" if "waarde" in df.columns else df.columns[0]
        return [""] + df[col].astype(str).tolist()
    except:
        return [""]

# ───────────────────────────────
# VELDEN
# (name, label, type, required, maxlen, dropdown_source)
# ───────────────────────────────
FIELDS = [
    ("Projectnr", "Projectnummer", "text", True, 10, None),
    ("Bedrijf", "Bedrijf", "text", True, None, ["001","090","315"]),
    ("Omschrijving", "Omschrijving", "text", True, 256, None),
    ("Opdrachtgever", "Opdrachtgever", "text", True, 100, None),
    ("Calcnr", "Calcnr", "text", False, 10, None),
    ("Soort", "Soort", "text", True, 20, ["Combinatie","Eigen beheer","Onder aanneming"]),
    ("Combinanten", "Combinanten", "text", False, 50, ["ACW","Den Ouden","Dura Vermeer"]),
    ("Combinaam", "Combinaam", "text", False, 20, ["Biggelaar","Gebr. De Koning"]),
    ("Aanneemsom","Aanneemsom","float",False,None,None),
    ("Geplande_start","Geplande start","date",False,None,None),
    ("Geplande_oplev","Geplande oplevering","date",False,None,None),
    ("Status","Status","text",True,20,["Onderhanden","Gereed"]),
    ("MT_lid","MT lid","text",False,5, load_csv("Directie_MT.csv")),
    ("PL","Projectleider","text",True,5, load_csv("Projectleiders.csv")),
    ("WVB_1","Werkvoorbereider 1","text",False,5, load_csv("Werkvoorbereiders.csv")),
    ("WVB_2","Werkvoorbereider 2","text",False,5, load_csv("Werkvoorbereiders.csv")),
    ("Uitvoerder","Uitvoerder","text",False,5, load_csv("Uitvoerders.csv")),
    ("KAM_mer","KAM medewerker","text",False,5, load_csv("KAM.csv")),
    ("Opdrachtbonnen","Opdrachtbonnen","text",False,5,None),
    ("Emailadres","Emailadres","text",False,40,None),
    ("Financieel","Financieel","text",False,5,None),
    ("Directie_Combi","Directie Combinatie","text",False,5,None),
    ("Adres","Adres","text",True,256,None),
    ("Factuur_aan","Factuur aan","text",False,256,None),
    ("Controller","Controller","text",False,5,load_csv("Controllers.csv")),
    ("Projectmap","Projectmap","text",True,256,None),
]

form_vals = {}
cols = st.columns(2)

for idx, (key,label,typ,req,maxlen,opts) in enumerate(FIELDS):
    col = cols[idx % 2]
    with col:
        label2 = label + (" *" if req else "")
        if opts:
            form_vals[key] = st.selectbox(label2, options=opts, key=key)
        else:
            if typ=="text":
                form_vals[key] = st.text_input(label2, max_chars=maxlen, key=key)
            elif typ=="float":
                form_vals[key] = st.number_input(label2, key=key)
            elif typ=="date":
                d = st.date_input(label2, key=key)
                form_vals[key] = d.strftime("%Y-%m-%d")
            else:
                form_vals[key] = st.text_input(label2, key=key)

st.caption("Velden met * zijn verplicht.")

# GEOMETRIE
st.subheader("Teken projectgebied")
m = folium.Map(location=[52.1,5.2], zoom_start=8)
Draw(export=True).add_to(m)
out = st_folium(m, height=500)

geometry = None
if out.get("last_active_drawing"):
    gj = out["last_active_drawing"]["geometry"]
    geometry = arcgis_polygon_from_geojson(gj)

# OPSLAAN
if st.button("Opslaan"):
    missing = [label for (key,label,_,req,_,_) in FIELDS if req and not form_vals[key]]
    if missing:
        st.error("Ontbrekende velden: " + ", ".join(missing))
        st.stop()

    attrs = {k:v for k,v in form_vals.items()}
    attrs[relation_field] = attrs["Projectnr"]

    feature = {"attributes": attrs}
    if geometry:
        feature["geometry"] = geometry

    try:
        resp = agol.add_features(projects_url, [feature])
        st.success("Project opgeslagen.")
        st.write(resp)
    except Exception as e:
        st.error(f"Fout bij opslaan: {e}")
