import streamlit as st
import pandas as pd
from utils_agol import AGOL

st.header("🧩 Domeinbeheer per veld")

cfg = st.secrets["arcgis"]
agol = AGOL(cfg["username"], cfg["password"], cfg.get("portal"))

domains_fs = cfg["domains_feature_server_url"]

# Service info
try:
    svc = agol.get(domains_fs)
except Exception as e:
    st.error(f"Fout bij ophalen service: {e}")
    st.stop()

# Detect domain layer
domain_layer_id = None
fieldcfg_table_id = None

if "layers" in svc and svc["layers"]:
    domain_layer_id = svc["layers"][0]["id"]

if domain_layer_id is None:
    st.error("Kon de domeinwaarden-laag niet vinden.")
    st.stop()

domain_url = domains_fs.rstrip("/") + f"/{domain_layer_id}"

# Detect FieldConfig table (optional)
if "tables" in svc and svc["tables"]:
    for t in svc["tables"]:
        tbl_url = domains_fs.rstrip("/") + f"/{t['id']}"
        try:
            meta = agol.get(tbl_url)
        except:
            continue
        flds = {f["name"].lower() for f in meta.get("fields", [])}
        if {"field_name", "is_dropdown", "input_type", "max_len", "required"}.issubset(flds):
            fieldcfg_table_id = t["id"]
            break

fieldcfg_url = domains_fs.rstrip("/") + f"/{fieldcfg_table_id}" if fieldcfg_table_id else None

# Load domain values
try:
    data = agol.query(
        domain_url,
        out_fields="field_name, domain_value, domain_label, active, email",
        return_geometry=False,
    )
except Exception as e:
    st.error(f"Fout bij ophalen domeinwaarden: {e}")
    st.stop()

rows = [f["attributes"] for f in data.get("features", [])]
df_all = pd.DataFrame(rows)

if df_all.empty:
    st.warning("Geen domeinrecords gevonden.")
    st.stop()

# Field selection
all_fields = sorted(df_all["field_name"].dropna().unique().tolist())
field_name = st.selectbox("Kies veld", all_fields)

df_field = df_all[df_all["field_name"] == field_name].copy().reset_index(drop=True)

# Ensure columns exist
for col in ["domain_value", "domain_label", "active", "email"]:
    if col not in df_field.columns:
        df_field[col] = ""

# Load field config
existing_fc = None
is_dropdown = False
input_type = "text"
max_len = 0
required = False

if fieldcfg_url:
    try:
        fc_data = agol.query(
            fieldcfg_url,
            where=f"field_name='{field_name}'",
            out_fields="*",
            return_geometry=False
        )
        fc_rows = [f["attributes"] for f in fc_data.get("features", [])]
        if fc_rows:
            existing_fc = fc_rows[0]
            is_dropdown = bool(existing_fc.get("is_dropdown"))
            input_type = existing_fc.get("input_type", "text")
            max_len = int(existing_fc.get("max_len") or 0)
            required = bool(existing_fc.get("required"))
    except:
        pass

# Field settings UI
if fieldcfg_url:
    st.subheader("Veldinstellingen")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        is_dropdown = st.checkbox("Dropdown", value=is_dropdown)
    with col2:
        input_type = st.selectbox(
            "Type", ["text", "int", "float", "date"],
            index=["text", "int", "float", "date"].index(input_type)
        )
    with col3:
        max_len = st.number_input("Max. lengte", min_value=0, step=1, value=max_len)
    with col4:
        required = st.checkbox("Verplicht", value=required)
else:
    st.info("Geen FieldConfig-tabel gedetecteerd - veldinstellingen worden niet opgeslagen.")

# Domain value editor
st.subheader(f"Domeinwaarden voor: {field_name}")

edited = st.data_editor(
    df_field[["domain_value", "domain_label", "active", "email"]].fillna(""),
    num_rows="dynamic",
    use_container_width=True,
    height=420
)

# CSV upload
st.write("CSV upload (kolommen: waarde, label*, email*)")
up = st.file_uploader("Upload CSV", type=["csv"])

if up:
    try:
        csv_df = pd.read_csv(up)
        csv_df = csv_df.rename(columns=str.lower)

        if "waarde" not in csv_df.columns:
            st.error("CSV mist kolom 'waarde'.")
        else:
            csv_df["domain_value"] = csv_df["waarde"].astype(str)
            csv_df["domain_label"] = csv_df["label"] if "label" in csv_df.columns else csv_df["domain_value"]
            csv_df["email"] = csv_df["email"] if "email" in csv_df.columns else None
            csv_df["active"] = 1
            edited = csv_df[["domain_value", "domain_label", "active", "email"]]
    except Exception as e:
        st.error(f"CSV fout: {e}")

# Save button
if st.button("Opslaan"):
    try:
        cur = agol.query(
            domain_url,
            where=f"field_name='{field_name}'",
            out_fields="*",
            return_geometry=False
        )
        cur_rows = [f["attributes"] for f in cur.get("features", [])]
        cur_by_val = {str(r["domain_value"]): r for r in cur_rows if r.get("domain_value")}

        new_values = set(edited["domain_value"].astype(str))
        old_values = set(cur_by_val.keys())

        to_add = []
        to_update = []

        # Add/update loop
        for _, r in edited.iterrows():
            dv = str(r["domain_value"])
            attrs = {
                "field_name": field_name,
                "domain_value": dv,
                "domain_label": r["domain_label"],
                "active": int(r["active"] or 0),
                "email": r["email"]
            }

            if dv in cur_by_val:
                attrs["OBJECTID"] = cur_by_val[dv]["OBJECTID"]
                to_update.append({"attributes": attrs})
            else:
                to_add.append({"attributes": attrs})

        # Delete removed
        to_delete = old_values - new_values
        if to_delete:
            where = " OR ".join([
                f"(field_name='{field_name}' AND domain_value='{v}')"
                for v in to_delete
            ])
            agol.delete_features(domain_url, where)

        if to_add:
            agol.add_features(domain_url, to_add)
        if to_update:
            agol.update_features(domain_url, to_update)

        # Save FieldConfig
        if fieldcfg_url:
            if existing_fc:
                upd = dict(existing_fc)
                upd.update({
                    "is_dropdown": int(is_dropdown),
                    "input_type": input_type,
                    "max_len": int(max_len),
                    "required": int(required)
                })
                agol.update_features(fieldcfg_url, [{"attributes": upd}])
            else:
                new_cfg = {
                    "field_name": field_name,
                    "is_dropdown": int(is_dropdown),
                    "input_type": input_type,
                    "max_len": int(max_len),
                    "required": int(required)
                }
                agol.add_features(fieldcfg_url, [{"attributes": new_cfg}])

        st.success("Wijzigingen opgeslagen.")

    except Exception as e:
        st.error(f"Opslaan mislukt: {e}")
