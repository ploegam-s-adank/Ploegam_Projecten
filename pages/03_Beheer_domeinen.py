import streamlit as st
import pandas as pd
from utils_agol import AGOL

st.header("🧩 Domeinbeheer per veld")

cfg = st.secrets["arcgis"]
agol = AGOL(cfg["username"], cfg["password"], cfg.get("portal"))

domains_fs = cfg["domains_feature_server_url"]
svc = agol.get(domains_fs)

# Detecteer domain layer + optionele field-config tabel
domain_layer_id = None
fieldcfg_table_id = None

# 1) DomainValues laag
if "layers" in svc and svc["layers"]:
    # Verwacht dat layer 0 de domeinwaarden bevat
    domain_layer_id = svc["layers"][0]["id"]

# 2) FieldConfig tabel (optioneel)
if "tables" in svc and svc["tables"]:
    for t in svc["tables"]:
        t_url = domains_fs.rstrip("/") + f"/{t['id']}"
        meta = agol.get(t_url)
        # Vereiste kolommen
        flds = {f["name"].lower() for f in meta.get("fields", [])}
        needed = {"field_name", "is_dropdown", "input_type", "max_len", "required"}
        if needed.issubset(flds):
            fieldcfg_table_id = t["id"]
            break

if domain_layer_id is None:
    st.error("Kon de domeinwaarden-laag niet vinden in de FeatureServer.")
    st.stop()

domain_url = domains_fs.rstrip("/") + f"/{domain_layer_id}"
fieldcfg_url = (
    domains_fs.rstrip("/") + f"/{fieldcfg_table_id}"
    if fieldcfg_table_id is not None
    else None
)

# 3) Haal alle domeinwaarden op
try:
    D = agol.query(
        domain_url,
        out_fields="field_name, domain_value, domain_label, active, email",
        return_geometry=False,
    )
    rows = [f["attributes"] for f in D.get("features", [])]
except Exception as e:
    st.error(f"Fout bij ophalen domeinen: {e}")
    st.stop()

df_all = pd.DataFrame(rows)

if df_all.empty or "field_name" not in df_all.columns:
    st.warning("Geen domeingegevens gevonden.")
    st.stop()

# 4) Kies veld
all_fields = sorted(df_all["field_name"].dropna().unique().tolist())
field_name = st.selectbox("Kies veld", options=all_fields)

df_field = df_all[df_all["field_name"] == field_name].copy().reset_index(drop=True)

# 5) Lees bestaande FieldConfig (indien aanwezig)
existing_fc = None
is_dropdown = False
input_type = "text"
max_len = 0
required = False

if fieldcfg_url:
    FC = agol.query(
        fieldcfg_url,
        where=f"field_name='{field_name}'",
        out_fields="*",
        return_geometry=False,
    )
    fc_rows = [f["attributes"] for f in FC.get("features", [])]
    if fc_rows:
        existing_fc = fc_rows[0]
        is_dropdown = bool(existing_fc.get("is_dropdown"))
        input_type = existing_fc.get("input_type", "text")
        max_len = int(existing_fc.get("max_len") or 0)
        required = bool(existing_fc.get("required"))

# 6) UI – veldinstellingen
if fieldcfg_url:
    st.subheader("Veldinstellingen")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        is_dropdown = st.checkbox("Dropdown", value=is_dropdown)
    with c2:
        input_type = st.selectbox(
            "Type", ["text", "int", "float", "date"], index=["text", "int", "float", "date"].index(input_type)
        )
    with c3:
        max_len = st.number_input("Max. lengte", value=max_len, min_value=0, step=1)
    with c4:
        required = st.checkbox("Verplicht", value=required)
else:
    st.info("Geen FieldConfig-tabel gedetecteerd – alleen domeinwaarden worden beheerd.")

# 7) Domeinwaarden editor
st.subheader(f"Domeinwaarden – {field_name}")

for col in ["domain_value", "domain_label", "active", "email"]:
    if col not in df_field.columns:
        df_field[col] = ""

edited = st.data_editor(
    df_field[["domain_value", "domain_label", "active", "email"]],
    num_rows="dynamic",
    use_container_width=True,
    height=420,
)

# 8) CSV upload
st.write("CSV upload (kolommen: 'waarde', optioneel 'label', 'email')")
up = st.file_uploader("Upload CSV (optioneel)", type=["csv"])

if up is not None:
    try:
        csv_df = pd.read_csv(up)
        csv_df = csv_df.rename(columns=str.lower)

        if "waarde" not in csv_df.columns:
            st.error("CSV mist verplichte kolom 'waarde'.")
        else:
            csv_df["domain_value"] = csv_df["waarde"].astype(str)
            csv_df["domain_label"] = csv_df["label"] if "label" in csv_df.columns else csv_df["domain_value"]
            csv_df["email"] = csv_df["email"] if "email" in csv_df.columns else None
            csv_df["active"] = 1
            edited = csv_df[["domain_value", "domain_label", "active", "email"]]

    except Exception as e:
        st.error(f"CSV fout: {e}")

# 9) Opslaan
if st.button("Opslaan wijzigingen"):
    try:
        # Huidige domeinrecords ophalen (OBJECTIDs nodig)
        cur = agol.query(
            domain_url,
            where=f"field_name='{field_name}'",
            out_fields="*",
            return_geometry=False,
        )
        cur_rows = [f["attributes"] for f in cur.get("features", [])]
        cur_by_value = {
            str(r.get("domain_value")): r for r in cur_rows if "domain_value" in r
        }

        new_vals = set(edited["domain_value"].astype(str))
        cur_vals = set(cur_by_value.keys())

        to_add, to_upd = [], []

        # Add + Update
        for _, r in edited.iterrows():
            dv = str(r.get("domain_value"))
            attrs = {
                "field_name": field_name,
                "domain_value": dv,
                "domain_label": r.get("domain_label"),
                "active": int(r.get("active") or 0),
                "email": r.get("email"),
            }

            if dv in cur_by_value:
                attrs["OBJECTID"] = cur_by_value[dv]["OBJECTID"]
                to_upd.append({"attributes": attrs})
            else:
                to_add.append({"attributes": attrs})

        # Delete
        to_delete = cur_vals - new_vals
        if to_delete:
            where = " OR ".join(
                [
                    f"(field_name='{field_name.replace(\"'\", \"''\")}' AND domain_value='{v.replace(\"'\", \"''\")}')"
                    for v in to_delete
                ]
            )
            agol.delete_features(domain_url, where)

        if to_add:
            agol.add_features(domain_url, to_add)
        if to_upd:
            agol.update_features(domain_url, to_upd)

        # FieldConfig opslaan (indien beschikbaar)
        if fieldcfg_url:
            if existing_fc:
                upd = dict(existing_fc)
                upd.update(
                    {
                        "is_dropdown": 1 if is_dropdown else 0,
                        "input_type": input_type,
                        "max_len": int(max_len),
                        "required": 1 if required else 0,
                    }
                )
                agol.update_features(fieldcfg_url, [{"attributes": upd}])
            else:
                add_fc = {
                    "field_name": field_name,
                    "is_dropdown": 1 if is_dropdown else 0,
                    "input_type": input_type,
                    "max_len": int(max_len),
                    "required": 1 if required else 0,
                }
                agol.add_features(fieldcfg_url, [{"attributes": add_fc}])

        st.success("Wijzigingen opgeslagen.")

    except Exception as e:
        st.error(f"Opslaan mislukt: {e}")
