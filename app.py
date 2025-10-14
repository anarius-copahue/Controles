import streamlit as st
from cuotas import cuotas
from ventas import ventas
from mapa import mapa
from scrap import scrape_data
from encrypt import decrypt_file
from datetime import datetime, timedelta
import os

st.set_page_config(page_title="Panel SELL", layout="wide")

cols = st.columns([2, 3, 3, 3, 3, 3, 2, 2])
with cols[7]:
        st.image("logo.png")

def decrypt_files():
    ARCHIVOS = ["data/diccionario.xlsx.encrypted", "data/representante.xlsx.encrypted", "data/SELL_IN_OUT.csv.encrypted"]
    key = st.secrets["ENCRYPTION_KEY"]

    for archivo in ARCHIVOS:
        decrypt_file(archivo, key.encode())
a_representantes = [
        'Karina Macías', 'Karina Perfu y Supermercados', 'Zona Norte',
        'Gerencia', 'Patricia Zacca', 'Marcela Rosselot', 'Lucio Colombo',
        'Yanina Cuezzo',  'Yamila Arreche', 'Emiliano Veiga',
        'Jessica Andermarch', 'Vacante'
    ]

def get_last_scrape_time():
    if os.path.exists("last_scrape.txt"):
        with open("last_scrape.txt", "r") as f:
            timestamp_str = f.read().strip()
            try:
                return datetime.fromisoformat(timestamp_str)
            except:
                return None
    return None

def set_last_scrape_time(ts):
    with open("last_scrape.txt", "w") as f:
        f.write(ts.isoformat())

def run_scraping_if_needed():
    now = datetime.now()
    last_scrape = get_last_scrape_time()

    if (last_scrape is None) or (now - last_scrape > timedelta(hours=1)):
        with st.spinner("Ejecutando scraping..."):
            scrape_data()  # Ejecuta tu función de scraping
        set_last_scrape_time(now)
        st.success("Scraping ejecutado correctamente.")
    else:
        tiempo_restante = timedelta(hours=1) - (now - last_scrape)
        st.info(f"Último scraping fue hace menos de 1 hora. Próximo en {tiempo_restante}.")

# Llamamos a la función para controlar el scraping
run_scraping_if_needed()

# Desencriptar archivos al iniciar la aplicación
decrypt_files()

# Password protection
def page_login():
    # Campo para ingresar contraseña
    st.title("Tablero de avance de ventas")

    user_input = st.text_input("Ingresá tu usuario:")
    password_input = st.text_input("Ingresá la contraseña:", type="password")

    # Esperar a que el usuario ingrese ambos campos
    if not user_input or not password_input:
        st.warning("Por favor, ingresá tu usuario y contraseña.")
        st.stop()

    # Define la contraseña correcta
    password = st.secrets[user_input.upper()]

    # Verificación
    if password_input != password:
        st.warning("Acceso denegado. Ingresá la contraseña para continuar.")
        st.stop()

    return user_input

user_logged = page_login()

# Si la contraseña es correcta, muestra el contenido
st.success("Acceso concedido")

if user_logged.upper() == "ADMIN":
    # Tabs
    tab1, tab2 = st.tabs(["Ventas", "Cuota"])
    with tab1:
        ventas()
    with tab2:
        cuotas()

else:
    ventas([user_logged.upper()])
    cuotas([user_logged.upper()])
    mapa(user_logged.upper())
