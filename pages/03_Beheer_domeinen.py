# ───────────────────────────────────────────────
# DOMAIN VALUES LAYER OR TABLE DETECTIE
# ───────────────────────────────────────────────

domain_layer_id = None
fieldcfg_table_id = None

# 1) Kijk eerst naar layers (voor de zekerheid)
if "layers" in svc and svc["layers"]:
    domain_layer_id = svc["layers"][0]["id"]

# 2) Als er geen layers zijn → gebruik de eerste TABLE als domeinwaarden
if domain_layer_id is None:
    if "tables" in svc and svc["tables"]:
        domain_layer_id = svc["tables"][0]["id"]
    else:
        st.error("Geen layers of tables gevonden in deze FeatureServer.")
        st.stop()

# Bepaal domein-URL
domain_url = domains_fs.rstrip("/") + f"/{domain_layer_id}"

# 3) FIELD CONFIG detectie (tabel 2 indien aanwezig)
if "tables" in svc and len(svc["tables"]) > 1:
    # tweede table = FieldConfig
    fieldcfg_table_id = svc["tables"][1]["id"]

fieldcfg_url = (
    domains_fs.rstrip("/") + f"/{fieldcfg_table_id}"
    if fieldcfg_table_id is not None else None
)
