import streamlit as st
from cuotas import main as main_cuota
from ventas import main as main_ventas
from scrap import scrape_data
from encrypt import decrypt_file
from datetime import datetime, timedelta
import os
logo = Image.open("logo.png")  # Ruta local de tu logo
st.image(logo, width=200)
st.set_page_config(page_title="Panel SELL", layout="wide")

def decrypt_files():
    ARCHIVOS = ["data/diccionario.xlsx.encrypted", "data/representante.xlsx.encrypted", "data/SELL_IN_OUT.csv.encrypted"]
    key = st.secrets["ENCRYPTION_KEY"]

    for archivo in ARCHIVOS:
        decrypt_file(archivo, key.encode())

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

# Show all files in the "data" and "descargas" directories
data_files = os.listdir("data")
descargas_files = os.listdir("descargas")
st.subheader("Archivos en 'data':")
st.write(data_files)
st.subheader("Archivos en 'descargas':")
st.write(descargas_files)
# Password protection

# Define la contraseña correcta
PASSWORD = st.secrets["PASSWORD"]

# Campo para ingresar contraseña
st.title("Acceso restringido")
password_input = st.text_input("Ingresá la contraseña:", type="password")

# Verificación
if password_input != PASSWORD:
    st.warning("Acceso denegado. Ingresá la contraseña para continuar.")
    st.stop()

# Si la contraseña es correcta, muestra el contenido
st.success("Acceso concedido")

# Tabs
tab1, tab2 = st.tabs(["Ventas", "Cuota"])

with tab1:
    main_ventas()

with tab2:
    main_cuota()