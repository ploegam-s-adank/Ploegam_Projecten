import streamlit as st
import pandas as pd
from utils_agol import AGOL

st.header("🧩 Domeinbeheer")

cfg = st.secrets["arcgis"]
agol = AGOL(cfg["username"], cfg["password"], cfg.get("portal"))

domains_fs = cfg["domains_feature_server_url"]

svc = agol.get(domains_fs)

layer_id = None
if "layers" in svc and svc["layers"]:
    layer_id = svc["layers"][0]["id"]
elif "tables" in svc and svc["tables"]:
    layer_id = svc["tables"][0]["id"]

if layer_id is None:
    st.error("Kon domeinenlaag niet vinden.")
    st.stop()

domain_url = domains_fs.rstrip("/") + f"/{layer_id}"

data = agol.query(domain_url)
records = [f["attributes"] for f in data.get("features", [])]

df = pd.DataFrame(records)

st.dataframe(df, use_container_width=True)