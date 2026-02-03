import streamlit as st
import pandas as pd
from utils_agol import AGOL
from streamlit_folium import st_folium
import folium

st.header('🗺️ Dashboard – Kaart boven / Tabel onder')

cfg=st.secrets['arcgis']
agol=AGOL(cfg['username'],cfg['password'],cfg.get('portal','https://www.arcgis.com'))
projects_url=cfg['projects_layer_url']
proj=agol.query(projects_url,where='1=1',out_fields='*')
feats=proj.get('features',[])
rows=[f['attributes'] for f in feats]
df=pd.DataFrame(rows)

st.subheader('Kaart')
m=folium.Map(location=[52.1,5.2],zoom_start=8)
for f in feats:
    g=f.get('geometry')
    if g and 'rings' in g:
        for ring in g['rings']:
            latlons=[(y,x) for x,y in ring]
            folium.Polygon(latlons,color='blue',fill=True,weight=2,opacity=0.6).add_to(m)

st_folium(m,height=480)

st.subheader('Tabel (klik een regel en bewerk)')
if not df.empty:
    st.dataframe(df,use_container_width=True)
else:
    st.warning('Geen records gevonden in de projectlaag.')
