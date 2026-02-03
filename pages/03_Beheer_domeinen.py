import streamlit as st
import pandas as pd
from utils_agol import AGOL

# ───────────────────────────────────────────────
# TITEL
# ───────────────────────────────────────────────

st.header("🧩 Domeinbeheer per veld")

cfg = st.secrets["arcgis"]
agol = AGOL(cfg["username"], cfg["password"], cfg.get("portal"))

domains_fs = cfg["domains_feature_server_url"]

# Laad service info
try:
    svc = agol.get(domains_fs)
except Exception as e:
    st.error(f"Fout bij ophalen service: {e}")
    st.stop()

# ───────────────────────────────────────────────
# DOMAIN VALUES LAYER DETECTIE
# ───────────────────────────────────────────────

domain_layer_id = None
fieldcfg_table_id = None

# DomainValues laag
if "layers" in svc and svc["layers"]:
    domain_layer_id = svc["layers"][0]["id"]

if domain_layer_id is None:
    st.error("Kon de domeinwaarden-laag niet vinden in de FeatureServer.")
    st.stop()

domain_url = domains_fs.rstrip("/") + f"/{domain_layer_id}"

# ───────────────────────────────────────────────
# FIELD CONFIG TABEL DETECTIE (OPTIONEEL)
# ───────────────────────────────────────────────

if "tables" in svc and svc["tables"]:
    for t in svc["tables"]:
        tbl_id = t["id"]
        tbl_url = domains_fs.rstrip("/") + f"/{tbl_id}"
        try:
            meta = agol.get(tbl_url)
        except:
            continue

        fields_lower = {f["name"].lower() for f in meta.get("fields", [])}
        required_fields = {"field_name", "is_dropdown", "input_type", "max_len", "required"}

        if required_fields.issubset(fields_lower):
            fieldcfg_table_id = tbl_id
            break

fieldcfg_url = (
    domains_fs.rstrip("/") + f"/{fieldcfg_table_id}"
    if fieldcfg_table_id is not None else None
)

# ───────────────────────────────────────────────
# HAAL ALLE DOMAIN VALUES OP
# ───────────────────────────────────────────────

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
    st.warning("Er zijn geen domeinrecords gevonden.")
    st.stop()

# ───────────────────────────────────────────────
# VELD SELECTIE
# ───────────────────────────────────────────────

all_fields = sorted(df_all["field_name"].dropna().unique().tolist())

field_name = st.selectbox("Kies veld", all_fields)

df_field = df_all[df_all["field_name"] == field_name].copy().reset_index(drop=True)

# Vul missende kolommen
for col in ["domain_value", "domain_label", "active", "email"]:
    if col not in df_field.columns:
        df_field[col] = ""

# ───────────────────────────────────────────────
# FIELD CONFIG LADEN (ALS BESTAANDE TABEL IS)
# ───────────────────────────────────────────────

existing_fc = None
is_dropdown = False
input_type = "text"
max_len = 0
required = False

if fieldcfg_url:
    try:
        res = agol.query(
            fieldcfg_url,
            where=f"field_name='{field_name}'",
            out_fields="*",
            return_geometry=False
        )
        rows_fc = [f["attributes"] for f in res.get("features", [])]
        if rows_fc:
            existing_fc = rows_fc[0]
            is_dropdown = bool(existing_fc.get("is_dropdown"))
            input_type = existing_fc.get("input_type", "text")
            max_len = int(existing_fc.get("max_len") or 0)
            required = bool(existing_fc.get("required"))
    except:
        pass

# ───────────────────────────────────────────────
# VELDINSTELLINGEN UI
# ───────────────────────────────────────────────

if fieldcfg_url:
    st.subheader("Veldinstellingen")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        is_dropdown = st.checkbox("Dropdown", value=is_dropdown)
    with c2:
        input_type = st.selectbox("Type", ["text", "int", "float", "date"], index=["text","int","float","date"].index(input_type))
    with c3:
        max_len = st.number_input("Max. lengte", min_value=0, step=1, value=max_len)
    with c4:
        required = st.checkbox("Verplicht veld", value=required)
else:
    st.info("Geen FieldConfig‑tabel gedetecteerd — veldinstellingen kunnen niet worden opgeslagen.")

# ───────────────────────────────────────────────
# DOMEINWAARDEN EDITOR
# ───────────────────────────────────────────────

st.subheader(f"Domeinwaarden voor: **{field_name}**")

edited = st.data_editor(
    df_field[["domain_value", "domain_label", "active", "email"]].fillna(""),
    num_rows="dynamic",
    use_container_width=True,
    height=420
)

# ───────────────────────────────────────────────
# CSV UPLOAD (OPTIONEEL)
# ───────────────────────────────────────────────

st.write("CSV upload (kolom: 'waarde', optioneel 'label', 'email'): ")
up = st.file_uploader("Upload CSV (optioneel)", type=["csv"])

if up:
    try:
        csv_df = pd.read_csv(up)
        csv_df = csv_df.rename(columns=str.lower)

        if "waarde" not in csv_df.columns:
            st.error("CSV mist de kolom 'waarde'.")
        else:
            csv_df["domain_value"] = csv_df["waarde"].astype(str)
            csv_df["domain_label"] = csv_df["label"] if "label" in csv_df.columns else csv_df["domain_value"]
            csv_df["email"] = csv_df["email"] if "email" in csv_df.columns else None
            csv_df["active"] = 1
            edited = csv_df[["domain_value", "domain_label", "active", "email"]]
    except Exception as e:
        st.error(f"CSV fout: {e}")

# ───────────────────────────────────────────────
# OPSLAAN
# ───────────────────────────────────────────────

if st.button("Opslaan wijzigingen"):
    try:
        # Haal bestaande records op (voor OBJECTID)
        cur = agol.query(
            domain_url,
            where=f"field_name='{field_name}'",
            out_fields="*",
            return_geometry=False
        )
        cur_rows = [f["attributes"] for f in cur.get("features", [])]

        cur_by_val = {
            str(r.get("domain_value")): r
            for r in cur_rows
            if r.get("domain_value") is not None
        }

        new_vals = set(edited["domain_value"].astype(str))
        old_vals = set(cur_by_val.keys())

        to_add = []
        to_upd = []

        # ADD + UPDATE
        for _, r in edited.iterrows():
            dv = str(r["domain_value"])
            attrs = {
                "field_name": field_name,
                "domain_value": dv,
                "domain_label": r.get("domain_label"),
                "active": int(r.get("active") or 0),
                "email": r.get("email")
            }

            # Update
            if dv in cur_by_val:
                attrs["OBJECTID"] = cur_by_val[dv]["OBJECTID"]
                to_upd.append({"attributes": attrs})
            else:
                to_add.append({"attributes": attrs})

        # DELETE
        to_delete = old_vals - new_vals
        if to_delete:
            clause_list = [
                f"(field_name='{field_name.replace(\"'\",\"''\")}' AND domain_value='{v.replace(\"'\",\"''\")}')"
                for v in to_delete
            ]
            where = " OR ".join(clause_list)
            agol.delete_features(domain_url, where)

        # Apply add & update
        if to_add:
            agol.add_features(domain_url, to_add)
        if to_upd:
            agol.update_features(domain_url, to_upd)

        # Opslaan FIELD CONFIG (indien aanwezig)
        if fieldcfg_url:
            if existing_fc:
                # Update
                upd = dict(existing_fc)
                upd.update({
                    "is_dropdown": int(is_dropdown),
                    "input_type": input_type,
                    "max_len": int(max_len),
                    "required": int(required)
                })
                agol.update_features(fieldcfg_url, [{"attributes": upd}])

            else:
                # Add new config
                add_cfg = [{
                    "attributes": {
                        "field_name": field_name,
                        "is_dropdown": int(is_dropdown),
                        "input_type": input_type,
                        "max_len": int(max_len),
                        "required": int(required)
                    }
                }]
                agol.add_features(fieldcfg_url, add_cfg)

        st.success("Wijzigingen opgeslagen.")

    except Exception as e:
        st.error(f"Opslaan mislukt: {e}")
