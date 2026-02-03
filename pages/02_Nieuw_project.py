import streamlit as st
import pandas as pd
import requests
from utils_agol import AGOL, arcgis_polygon_from_geojson
from streamlit_folium import st_folium
import folium
from folium.plugins import Draw

st.header('➕ Nieuw project – Formulier + Geometrie')

cfg=st.secrets['arcgis']
agol=AGOL(cfg['username'],cfg['password'],cfg.get('portal','https://www.arcgis.com'))
projects_url=cfg['projects_layer_url']
workareas_url=cfg['workareas_layer_url']
rel_key=cfg.get('relation_key_field','Projectnr')
domains_fs=cfg['domains_feature_server_url']

svc=agol.get(domains_fs)
layer_id=None
if 'layers' in svc and svc['layers']:
    layer_id=svc['layers'][0]['id']
elif 'tables' in svc and svc['tables']:
    layer_id=svc['tables'][0]['id']
if layer_id is None:
    st.error('Kon de domeinenlaag niet detecteren.'); st.stop()

domains_url=domains_fs.rstrip('/') + '/' + str(layer_id)
D=agol.query(domains_url,where='active=1',out_fields='*')
dom_records=D.get('features',[])
from collections import defaultdict
opts=defaultdict(list)
email_by_value={}
for f in dom_records:
    a=f['attributes']; fn=a.get('field_name'); val=a.get('domain_value'); lab=a.get('domain_label') or val
    if fn and val: opts[fn].append({'value':val,'label':lab})
    if a.get('email'): email_by_value[val]=a['email']

st.write('Formulier ingekort voorbeeld (volledige versie in productie)')
