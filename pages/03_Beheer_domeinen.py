import streamlit as st
import pandas as pd
from utils_agol import AGOL

st.header("🧩 Domeinbeheer per veld")

cfg = st.secrets["arcgis"]
agol = AGOL(cfg["username"], cfg["password"], cfg.get("portal"))

domains_fs = cfg["domains_feature_server_url"]
svc = agol.get(domains_fs)

# Detecteer DomainValues-laag en optioneel FieldConfig-tabel
domain_layer_id = None
fieldcfg_table_id = None

if "layers" in svc and svc["layers"]:
    domain_layer_id = svc["layers"][0]["id"]  # verwacht: records met field_name, domain_value, domain_label, active, email/...
if "tables" in svc and svc["tables"]:
    # probeer een tabel te vinden met geschikte kolommen
    for t in svc["tables"]:
        tbl_url = domains_fs.rstrip("/") + f"/{t['id']}"
        meta = agol.get(tbl_url)
        flds = [f["name"].lower() for f in meta.get("fields", [])]
        if {"field_name","is_dropdown","input_type","max_len","required"}.issubset(set(flds)):
            fieldcfg_table_id = t["id"]
            break

if domain_layer_id is None:
    st.error("Kon Domains-laag niet vinden.")
    st.stop()

domain_url = domains_fs.rstrip("/") + f"/{domain_layer_id}"
fieldcfg_url = domains_fs.rstrip("/") + f"/{fieldcfg_table_id}" if fieldcfg_table_id is not None else None

# 1) Keuze veldnaam (alle unieke field_name uit DomainValues ophalen)
D = agol.query(domain_url, out_fields="field_name, domain_value, domain_label, active, email", return_geometry=False)
rows = [f["attributes"] for f in D.get("features", [])]
df = pd.DataFrame(rows)
all_fields = sorted(df["field_name"].dropna().unique().tolist())
field_name = st.selectbox("Kies veld", options=all_fields)

# 2) Config (alleen als FieldConfig bestaat)
is_dropdown = False
input_type = "text"
max_len = None
required = 0

if fieldcfg_url:
    FC = agol.query(fieldcfg_url, where=f"field_name='{field_name}'", out_fields="*", return_geometry=False)
    fc_rows = [f["attributes"] for f in FC.get("features", [])]
    existing_fc = fc_rows[0] if fc_rows else None

    st.subheader("Veldinstellingen")
    cols = st.columns(4)
    with cols[0]:
        is_dropdown = st.checkbox("Dropdown", value=bool(existing_fc and existing_fc.get("is_dropdown")))
    with cols[1]:
        input_type = st.selectbox("Type", options=["text","int","float","date"],
                                  index=["text","int","float","date"].index(existing_fc.get("input_type","text")) if existing_fc else 0)
    with cols[2]:
        max_len = st.number_input("Max. lengte", value=int(existing_fc.get("max_len")) if (existing_fc and existing_fc.get("max_len") is not None) else 0, step=1)
    with cols[3]:
        required = st.checkbox("Verplicht", value=bool(existing_fc and existing_fc.get("required")))
else:
    st.info("Geen FieldConfig-tabel gedetecteerd. Je kunt wel de domeinwaarden beheren; de 'Dropdown' instelling wordt dan niet in GIS bewaard.")

# 3) Domeinwaarden voor gekozen veld
st.subheader(f"Domeinwaarden – {field_name}")
df_field = df[df["field_name"] == field_name].copy().reset_index(drop=True)
# Toon alleen "echte" waarden (sommige implementaties gebruiken meta-records; filter die eruit indien nodig)
if "domain_value" in df_field.columns:
    pass

edited = st.data_editor(
    df_field[["domain_value","domain_label","active","email"]].fillna(""),
    num_rows="dynamic",
    use_container_width=True,
    height=380
)

# 4) CSV upload (optioneel)
st.write("CSV upload (kolom 'waarde' en optioneel 'label', 'email')")
up = st.file_uploader("Upload CSV om lijst te vervangen/aan te vullen", type=["csv"])
if up is not None:
    csv_df = pd.read_csv(up)
    csv_df = csv_df.rename(columns=str.lower)
    if "waarde" not in csv_df.columns:
        st.error("CSV mist kolom 'waarde'.")
    else:
        # samenvoegen: vervang bestaande op 'waarde' (domain_value), voeg nieuwe toe
        csv_df["domain_value"] = csv_df["waarde"].astype(str)
        csv_df["domain_label"] = csv_df["label"] if "label" in csv_df.columns else csv_df["domain_value"]
        csv_df["email"] = csv_df["email"] if "email" in csv_df.columns else None
        csv_df["active"] = 1
        edited = csv_df[["domain_value","domain_label","active","email"]]

# 5) Opslaan
if st.button("Opslaan wijzigingen"):
    try:
        # Huidige set voor dit veld opnieuw ophalen (we hebben OBJECTIDs nodig)
        cur = agol.query(domain_url, where=f"field_name='{field_name}'", out_fields="*", return_geometry=False)
        cur_rows = [f["attributes"] for f in cur.get("features", [])]
        cur_by_value = {str(r.get("domain_value")): r for r in cur_rows if r.get("domain_value") is not None}

        new_values = set(edited["domain_value"].astype(str))
        cur_values = set(cur_by_value.keys())

        to_add = []
        to_upd = []
        to_del = []

        # add & update
        for _, r in edited.iterrows():
            dv = str(r.get("domain_value"))
            attrs = {
                "field_name": field_name,
                "domain_value": dv,
                "domain_label": r.get("domain_label"),
                "active": int(r.get("active") or 0),
                "email": r.get("email")
            }
            if dv in cur_by_value:
                # update - include OBJECTID
                attrs["OBJECTID"] = cur_by_value[dv].get("OBJECTID")
                to_upd.append({"attributes": attrs})
            else:
                to_add.append({"attributes": attrs})

        # delete
        to_delete_values = cur_values - new_values
        if to_delete_values:
            # verwijder per waarde
            where = " OR ".join([f"field_name='{field_name}' AND domain_value='{v.replace(\"'\",\"''\")}'" for v in to_delete_values])
            agol.delete_features(domain_url, where)

        if to_add:
            agol.add_features(domain_url, to_add)
        if to_upd:
            agol.update_features(domain_url, to_upd)

        # FieldConfig bijwerken (indien aanwezig)
        if fieldcfg_url:
            if existing_fc:
                upd_attrs = dict(existing_fc)
                upd_attrs["is_dropdown"] = 1 if is_dropdown else 0
                upd_attrs["input_type"] = input_type
                upd_attrs["max_len"] = int(max_len or 0)
                upd_attrs["required"] = 1 if required else 0
                to_upd_fc = [{"attributes": upd_attrs}]
                agol.update_features(fieldcfg_url, to_upd_fc)
            else:
                add_fc = [{
                    "attributes": {
                        "field_name": field_name,
                        "is_dropdown": 1 if is_dropdown else 0,
                        "input_type": input_type,
                        "max_len": int(max_len or 0),
                        "required": 1 if required else 0
                    }
                }]
                agol.add_features(fieldcfg_url, add_fc)

        st.success("Domeinen en instellingen opgeslagen.")
    except Exception as e:
        st.error(f"Opslaan mislukt: {e}")
