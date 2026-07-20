import streamlit as st
from cuotas import cuotas
from ventas import ventas
from recetas_medicas import recetas_medicas
from scraper import scrape_data
from productos_Caviahue import productos
from datetime import datetime, timedelta
from shopify import scrap_shopify
from control_gerencial import control_gerencial 
from shopify import scrap_shopify
from cuadro_stock import app_ventas_stock
from api_dropbox import descargar_archivos_dropbox
import os

st.set_page_config(page_title="Caviahue Avance", layout="wide", page_icon="📦")

cols = st.columns([2, 3, 3, 3, 3, 3, 2, 2])
with cols[7]:
        st.image("logo.png")

a_representantes = [
        'Santiago Rocchi',
        'Gerencia', 'Patricia Zacca', 'Marcela Rosselot', 'Agustin Fleba',
        'Yanina Cuezzo',  'Yamila Arreche', 'Mar del Plata',
        'Mendoza'
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
        scraped_correctly = False
        with st.spinner("Ejecutando scraping..."):
            #Shopify api
            try:
                scrape_data()  # Ejecuta tu función de scraping
                descargar_archivos_dropbox()
                ventas_cav_shopify = scrap_shopify(st.secrets["CAVIAHUE_SHOP_DOMAIN"],st.secrets["CAVIAHUE_SHOP_TOKEN"])
                ventas_cav_shopify.to_csv('descargas/ventas_caviahue_shopify.csv', index=False)
                scraped_correctly = True
            except Exception as e:
                st.error(f"Error en el scraping, estamos trabajando para solucionarlo. Por favor, intentá nuevamente más tarde. \n Error: {e}")
                scraped_correctly = False
        if not scraped_correctly:
            st.stop()
        set_last_scrape_time(now)
        
    else:
        tiempo_restante = timedelta(hours=1) - (now - last_scrape)
        st.info(f"Último scraping fue hace menos de 1 hora. Próximo en {tiempo_restante}.")

# Llamamos a la función para controlar el scraping
run_scraping_if_needed()


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
    tab1, tab6, tab2, tab3, tab4, tab5 = st.tabs(["Ventas", "Recetas por médico", "Cuota", "Venta por productos", "Cuadro de avance", "Stock y ventas totales"])
    with tab1:
        ventas()
    with tab6:
        recetas_medicas()
    with tab2:
        productos()
    with tab4:
        control_gerencial()
    with tab5:
        app_ventas_stock()


else:
    ventas([user_logged.upper()])
    cuotas([user_logged.upper()])
    recetas_medicas([user_logged.upper()], user_logged)
