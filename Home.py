import streamlit as st
from pathlib import Path

st.set_page_config(
    page_title="Ploegam Projecten",
    layout="wide"
)

# --- Custom CSS (zelfde stijl als erkenningen-app) ---
st.markdown("""
<style>
/* Algemene layout */
.main {
    padding: 0rem 3rem;
}

/* Header afbeelding */
.header-img {
    width: 100%;
    border-radius: 6px;
    margin-bottom: 1.5rem;
}

/* Titelstijl */
.app-title {
    font-size: 2.5rem;
    font-weight: 700;
    color: #003366;
    margin-top: 1rem;
    margin-bottom: 0.7rem;
}

/* Subtekst */
.app-sub {
    font-size: 1.2rem;
    color: #444;
}

/* Kaarten / info blokken */
.info-block {
    background: white;
    padding: 1.5rem;
    border-radius: 8px;
    margin-top: 1.5rem;
    box-shadow: 0 0 4px rgba(0,0,0,0.15);
}

</style>
""", unsafe_allow_html=True)


# --- Logo ---
logo = Path("assets/ploegam_logo.png")
if logo.exists():
    st.image(str(logo), width=240)

# --- Header afbeelding ---
header = Path("assets/header.jpg")
if header.exists():
    st.markdown(f"{header.as_posix()}", unsafe_allow_html=True)

# --- Titel ---
st.markdown("<div class='app-title'>Ploegam Projecten</div>", unsafe_allow_html=True)
st.markdown("<div class='app-sub'>Projectbeheer • Registratie • Domeinbeheer</div>", unsafe_allow_html=True)

# --- Welkomstblok ---
with st.container():
    st.markdown("""
    <div class='info-block'>
    <h3>📘 Over deze toepassing</h3>
    <p>
    Deze applicatie biedt één centrale omgeving voor:
    </p>
    <ul>
        <li><b>Project dashboard</b> – kaartweergave & tabeloverzicht</li>
        <li><b>Nieuwe projecten invoeren</b> – inclusief geometrie tekenen</li>
        <li><b>Domeinbeheer</b> – waardelijsten & dropdown-instellingen beheren</li>
    </ul>
    <p>
    Gebruik het menu links om een pagina te openen.
    </p>
    </div>
    """, unsafe_allow_html=True)
