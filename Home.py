import streamlit as st
from pathlib import Path

st.set_page_config(
    page_title="Ploegam Projecten",
    layout="wide"
)

# Logo
logo_path = Path("assets/ploegam_logo.png")
if logo_path.exists():
    st.image(str(logo_path), width=220)

header_path = Path("assets/header_image.jpg")
if header_path.exists():
    st.image(str(header_path), use_column_width=True)

st.title("📍 Ploegam Projecten")

st.markdown("""
Welkom bij de Ploegam Projecten applicatie.  
Gebruik het menu links om naar de volgende onderdelen te gaan:

### 📊 Dashboard
Kaartweergave + tabel van alle lopende projecten.

### ➕ Nieuw project / Project bewerken
Voer een nieuw project in en teken de projectgrenzen.

### 🧩 Beheer Domeinen
Beheer de codetabellen, labels en gekoppelde e-mails.
""")