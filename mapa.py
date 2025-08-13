import streamlit as st
import pandas as pd
import numpy as np

REPRESENTANTE_mapa= {
        "KMACIAS": "mapa_ventas_KARINA.html",
        "EPIEGARI": "mapa_ventas_ESTEBAN.html",
        "PZACCA": "mapa_ventas_PATRICA.html",
        "MROSSELOT": "mapa_ventas_MARCELA.html",
        "LCOLOMBO": "mapa_ventas_LUCIO.html",
        "YCUEZZO": "mapa_ventas_YANINA.html",
        "YARRECHE": "mapa_ventas_YAMILA.html",
        "EVEIGA": "mapa_ventas_EMILIANO.html",
        "JANDERMARCH": "mapa_ventas_JESSICA.html",
        "LLAGUNA": "mapa_ventas_LUCIANO.html"
}

def mapa(representante):
    mapa_file = REPRESENTANTE_mapa.get(representante)

    if mapa_file:  # Solo si existe en el diccionario
        ruta_mapa = f"mapa por representante/{mapa_file}"
        with open(ruta_mapa, "r", encoding="utf-8") as f:
            mapa_html = f.read()

    # Mostrar el mapa en Streamlit
        st.components.v1.html(mapa_html, height=600, width=2000, scrolling=True)
    else:
        st.warning("No hay mapa disponible para este representante.")
