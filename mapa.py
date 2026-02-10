import streamlit as st
import pandas as pd
import numpy as np

REPRESENTANTE_mapa= {
        
        "SROCCHI": "mapa_ventas_ZONA_NORTE.html",
        "PZACCA": "mapa_ventas_PATAGONIA.html",
        "MROSSELOT": "mapa_ventas_CORDOBA_+_NORESTE.html",
        "LCOLOMBO": "mapa_ventas_LITORAL.html",
        "YCUEZZO": "mapa_ventas_NORTE.html",
        "YARRECHE": "mapa_ventas_ZONA_SUR.html",
        "EVEIGA": "mapa_ventas_COSTA_ATLANTIDA.html",
        "JANDERMARCH": "mapa_ventas_CUYO.html",
        "NBRIDI" : "mapa_ventas_ZONA_CABA_1425"
       
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
