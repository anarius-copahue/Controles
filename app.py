import os
from datetime import datetime, timedelta
import streamlit as st

from cuotas import cuotas
from ventas import ventas
from recetas_medicas import recetas_medicas
from scraper import scrape_data
from productos_Caviahue import productos
from shopify import scrap_shopify
from control_gerencial import control_gerencial 
from cuadro_stock import app_ventas_stock
from api_dropbox import descargar_archivos_dropbox

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Caviahue Avance", layout="wide", page_icon="📦")

cols = st.columns([2, 3, 3, 3, 3, 3, 2, 2])
with cols[7]:
    if os.path.exists("logo.png"):
        st.image("logo.png")

# --- DEFINICIÓN DE PERFILES Y REPRESENTANTES ---
# Perfil A: Representantes Comerciales / Ventas
A_REPRESENTANTES = [
    'SROCCHI', 'PZACCA', 'MROSSELOT', 'AFLEBA', 
    'YCUEZZO', 'YARRECHE', 'NBRIDI', 'GERENCIA', 
    'MENDOZA', 'MPUTZOLU'
]

# Perfil M: Representantes Médicos
M_REPRESENTANTES = ["DCHANDLER", "RABBENANTE"]


# --- GESTIÓN DE SCRAPING / SINCRONIZACIÓN ---
def get_last_scrape_time():
    if os.path.exists("last_scrape.txt"):
        with open("last_scrape.txt", "r") as f:
            timestamp_str = f.read().strip()
            try:
                return datetime.fromisoformat(timestamp_str)
            except Exception:
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
        with st.spinner("Actualizando datos y ejecutando sincronización..."):
            try:
                scrape_data()
                descargar_archivos_dropbox()
                ventas_cav_shopify = scrap_shopify(
                    st.secrets["CAVIAHUE_SHOP_DOMAIN"],
                    st.secrets["CAVIAHUE_SHOP_TOKEN"]
                )
                ventas_cav_shopify.to_csv('descargas/ventas_caviahue_shopify.csv', index=False)
                scraped_correctly = True
            except Exception as e:
                st.error(f"Error en la actualización de datos: {e}")
                scraped_correctly = False

        if not scraped_correctly:
            st.stop()

        set_last_scrape_time(now)
    else:
        tiempo_restante = timedelta(hours=1) - (now - last_scrape)
        minutos_restantes = int(tiempo_restante.total_seconds() // 60)
        st.info(f"ℹ️ Última actualización hace menos de 1 hora. Próxima sincronización en {minutos_restantes} min.")

# Ejecutar proceso de scraping al inicio
run_scraping_if_needed()


# --- CONTROL DE ACCESO / LOGIN ---
def page_login():
    st.title("Tablero de Avance de Ventas")

    col_login, _ = st.columns([1, 1])
    with col_login:
        user_input = st.text_input("Ingresá tu usuario:").strip().upper()
        password_input = st.text_input("Ingresá la contraseña:", type="password").strip()

    if not user_input or not password_input:
        st.warning("Por favor, ingresá tu usuario y contraseña para continuar.")
        st.stop()

    try:
        password_correcta = st.secrets[user_input]
    except KeyError:
        st.error("Usuario no registrado o contraseña incorrecta.")
        st.stop()

    if password_input != password_correcta:
        st.error("Acceso denegado. Contraseña incorrecta.")
        st.stop()

    return user_input

# Inicio de sesión
user_logged = page_login()
st.success(f"Bienvenido/a, {user_logged}")


# --- VISTAS SEGÚN TIPO DE USUARIO ---

# 1. PERFIL ADMINISTRADOR
if user_logged == "ADMIN":
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Ventas", 
        "🩺 Recetas por Médico", 
        "🎯 Cuotas", 
        "📦 Productos", 
        "📈 Control Gerencial", 
        "🏭 Stock y Ventas"
    ])
    with tab1:
        ventas()
    with tab2:
        recetas_medicas()
    with tab3:
        cuotas()
    with tab4:
        productos()
    with tab5:
        control_gerencial()
    with tab6:
        app_ventas_stock()

# 2. PERFIL M (REPRESENTANTES MÉDICOS)
elif user_logged in M_REPRESENTANTES:
    st.markdown("### Recetas por médico")
    recetas_medicas(representantes=[user_logged], usuario_id=user_logged)

# 3. PERFIL A (REPRESENTANTES COMERCIALES / VENTAS)
else:
    tab_v, tab_c, tab_r = st.tabs([
        "Mis Ventas", 
        "Mis Cuotas", 
        "Recetas Médicas"
    ])
    with tab_v:
        ventas(representantes=[user_logged])
    with tab_c:
        cuotas(representantes=[user_logged])
    with tab_r:
        recetas_medicas(representantes=[user_logged], usuario_id=user_logged)