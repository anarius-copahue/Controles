import streamlit as st
from cuotas import cuotas
from ventas import ventas
from update_data import update_data
from mapa import mapa
from encrypt import decrypt_file
from productos import productos
from datetime import datetime
from control_gerencial import control_gerencial 
from cuadro_stock import app_ventas_stock
import os

st.set_page_config(page_title="Caviahue Avance", layout="wide", page_icon="📦")

cols = st.columns([2, 3, 3, 3, 3, 3, 2, 2])
with cols[7]:
    st.image("logo.png")

def decrypt_files():
    key = st.secrets["ENCRYPTION_KEY"]
    
    # 1. Desencriptar bases de datos fijas de la carpeta data/
    ARCHIVOS_DATA = [
        "data/diccionario.xlsx.encrypted", "data/representante.xlsx.encrypted", "data/db_SELL_IN_OUT.xlsx.encrypted",
        "data/Historico.xlsx.encrypted","data/Cuota_Productos.xlsx.encrypted", "data/Historico_Productos.xlsx.encrypted"
    ]
    for archivo in ARCHIVOS_DATA:
        if os.path.exists(archivo):
            decrypt_file(archivo, key.encode())
            
    tango_path = "data/TANGO.xlsx.encrypted"
    if os.path.exists(tango_path):
        decrypt_file(tango_path, key.encode())

    # 2. Desencriptar nuevos reportes generados automáticamente en la carpeta descargas/
    ARCHIVOS_DESCARGAS = [
        "descargas/preventa_por_cliente.csv.encrypted",
        "descargas/ventas_netas_por_periodo_cliente.csv.encrypted",
        "descargas/venta_neta_por_periodo_producto_cliente.csv.encrypted",
        "descargas/preventa_por_producto.csv.encrypted",
        "descargas/stock_por_productos.csv.encrypted",
        "descargas/ventas_caviahue_shopify.csv.encrypted"
    ]
    for archivo in ARCHIVOS_DESCARGAS:
        if os.path.exists(archivo):
            decrypt_file(archivo, key.encode())
        
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
                ventas_cav_shopify = scrap_shopify(st.secrets["CAVIAHUE_SHOP_DOMAIN"],st.secrets["CAVIAHUE_SHOP_TOKEN"])
                ventas_cav_shopify.to_csv('descargas/ventas_caviahue_shopify.csv', index=False)
                scraped_correctly = True
            except Exception as e:
                st.error("Error en el scraping, estamos trabajando para solucionarlo. Por favor, intentá nuevamente más tarde.")
                scraped_correctly = False
        if not scraped_correctly:
            st.stop()
        set_last_scrape_time(now)
        
    else:
        tiempo_restante = timedelta(hours=1) - (now - last_scrape)
        st.info(f"Último scraping fue hace menos de 1 hora. Próximo en {tiempo_restante}.")

# Desencriptar TODOS los archivos al iniciar la aplicación (Bases + Reportes)
decrypt_files()

# Password protection
def page_login():
    st.title("Tablero de avance de ventas")
    user_input = st.text_input("Ingresá tu usuario:")
    password_input = st.text_input("Ingresá la contraseña:", type="password")

    if not user_input or not password_input:
        st.warning("Por favor, ingresá tu usuario y contraseña.")
        st.stop()

    try:
        password = st.secrets[user_input.upper()]
    except KeyError:
        st.error("Usuario no encontrado.")
        st.stop()

    if password_input != password:
        st.warning("Acceso denegado. Ingresá la contraseña para continuar.")
        st.stop()

    return user_input

user_logged = page_login()
st.success("Acceso concedido")

if user_logged.upper() == "ADMIN":
    tab1, tab2, tab3, tab5, tab6 = st.tabs(["Ventas", "Cuota","Productos", "Cuadro de avance","Ventas y Stock"])
    with tab1:
        ventas()
    with tab2:
        cuotas()
    with tab3:
        productos()
    with tab5:
        control_gerencial()
    with tab6:
        app_ventas_stock()

elif user_logged.upper() == "ADMIN_DATA":
    tab1, tab2, tab3, tab5, tab4, tab6 = st.tabs(["Ventas", "Cuota", "Productos", "Cuadro de avance", "Actualizar Datos","Ventas y Stock"])
    with tab1:
        ventas()
    with tab2:
        cuotas()
    with tab3:
        productos()
    with tab5:
        control_gerencial()
    with tab4:
        update_data()
    with tab6:
        app_ventas_stock()

elif user_logged.upper() == "DISPROADMIN":
    cuotas()
    
else:
    ventas([user_logged.upper()])
    cuotas([user_logged.upper()])
    mapa(user_logged.upper())