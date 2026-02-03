import streamlit as st
st.set_page_config(page_title='Ploegam Projecten', layout='wide')
st.title('📍 Ploegam Projecten – Dashboard & Formulier & Beheer')
st.write('Gebruik de navigatie in de linkerzijbalk om naar Dashboard / Nieuw project / Beheer domeinen te gaan.')
st.subheader('🔧 Vereiste configuratie (secrets)')
st.code('''[arcgis]
username = "<agol-gebruiker>"
password = "<agol-wachtwoord>"
portal = "https://www.arcgis.com"

# Data endpoints
projects_layer_url = "https://services-eu1.arcgis.com/dfv5dKtt4Crq9alU/arcgis/rest/services/Ploegam_Projecten_WFL1/FeatureServer/1"
workareas_layer_url = "https://services-eu1.arcgis.com/dfv5dKtt4Crq9alU/arcgis/rest/services/Ploegam_Projecten_WFL1/FeatureServer/2"
# Domeinenlijst FeatureServer (service), laag-id wordt automatisch gedetecteerd
domains_feature_server_url = "https://services-eu1.arcgis.com/dfv5dKtt4Crq9alU/arcgis/rest/services/Ploegam_Projecten_Domeinenlijst/FeatureServer"

# Relaties
relation_key_field = "Projectnr"

# PDOK geocoder
pdok_search_url = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/free"''', language='toml')
st.info('Als alles ingevuld is, ga dan naar Dashboard of Nieuw project in de zijbalk.')
