import streamlit as st
import pandas as pd
from utils_agol import AGOL

st.header('🗂️ Beheer – Domeinlijsten per veld')

cfg=st.secrets['arcgis']
agol=AGOL(cfg['username'],cfg['password'],cfg.get('portal','https://www.arcgis.com'))
domains_fs=cfg['domains_feature_server_url']

svc=agol.get(domains_fs)
layer_id=None
if 'layers' in svc and svc['layers']:
    layer_id=svc['layers'][0]['id']
elif 'tables' in svc and svc['tables']:
    layer_id=svc['tables'][0]['id']
if layer_id is None:
    st.error('Kon de domeinenlaag niet detecteren.'); st.stop()

domain_url=domains_fs.rstrip('/') + '/' + str(layer_id)
data=agol.query(domain_url, where='1=1', out_fields='*')
df=pd.DataFrame([f['attributes'] for f in data.get('features',[])])
st.dataframe(df)
