import streamlit as st
from pathlib import Path

st.set_page_config(
    page_title="Ploegam Projecten",
    layout="wide"
)

# --- Custom CSS stijl (zoals Erkenningen-app) ---
st.markdown("""
<style>
.main { padding: 0rem 3rem; }
.header-img {
    width: 100%;
    border-radius: 6px;
    margin-bottom: 1.5rem;
}
.app-title {
    font-size: 2.5rem;
    font-weight: 700;
    color: #003366;
    margin-top: 1rem;
    margin-bottom: 0.7rem;
}
.app-sub {
    font-size: 1.2rem;
    color: #444;
}
.info-block {
    background: #ffffff;
    padding: 1.5rem;
    border-radius: 8px;
    margin-top: 1.5rem;
    box-shadow: 0 0 4px rgba(0,0,0,0.15);
}
</style>
""", unsafe_allow_html=True)

# Logo
logo = Path("assets/ploegam_logo.png")
if logo.exists():
    st.image(str(logo), width=240)

# Header afbeelding
header = Path("assets/ploegam_hero.webp")
if header.exists():
    st.markdown(f"{header.as_posix()}", unsafe_allow_html=True)

st.markdown("<div class='app-title'>Ploegam Projecten</div>", unsafe_allow_html=True)
st.markdown("<div class='app-sub'>Projectbeheer • Registratie • Domeinbeheer</div>", unsafe_allow_html=True)

st.markdown("""
<div class='info-block'>
  <h3>📘 Over deze toepassing</h3>
  <ul>
    <li><b>Dashboard</b> – native kaart + tabel</li>
    <li><b>Nieuw project</b> – formulier + geometrie tekenen</li>
    <li><b>Domeinbeheer</b> – dropdowns, waardenlijsten, CSV upload</li>
  </ul>
</div>
""", unsafe_allow_html=True)
