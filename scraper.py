from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import os
import time
from datetime import datetime

# 🔒 Librerías de tu ecosistema actual
from shopify import scrap_shopify  
from encrypt import encrypt_file

# --- 1. CONTROL DUAL DE CREDENCIALES (LOCAL VS ACTIONS) ---
try:
    import streamlit as st
    # Si estamos en local con Streamlit configurado, prioriza st.secrets
    USER = st.secrets["DISPRO_USER"]
    PASSWORD = st.secrets["DISPRO_PASSWORD"]
    SHOPIFY_DOMAIN = st.secrets["CAVIAHUE_SHOP_DOMAIN"]
    SHOPIFY_TOKEN = st.secrets["CAVIAHUE_SHOP_TOKEN"]
    ENCRYPTION_KEY = st.secrets["ENCRYPTION_KEY"]
    IS_LOCAL = st.secrets.get("LOCAL", "TRUE")
except Exception:
    # Si falla st.secrets (como pasa en GitHub Actions), lee las variables de entorno de GitHub
    USER = os.environ.get("DISPRO_USER")
    PASSWORD = os.environ.get("DISPRO_PASSWORD")
    SHOPIFY_DOMAIN = os.environ.get("CAVIAHUE_SHOP_DOMAIN")
    SHOPIFY_TOKEN = os.environ.get("CAVIAHUE_SHOP_TOKEN")
    ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY")
    IS_LOCAL = "FALSE" if os.environ.get("GITHUB_ACTIONS") == "true" else "TRUE"

# --- 2. CONFIGURACIÓN DE RUTAS Y NOMBRES DE ARCHIVOS ---
DOWNLOAD_DIR = os.path.join(os.getcwd(), "descargas")

PREVENTA_REPORT_FILE_NAME = "preventa_por_cliente.csv"
VENTA_REPORT_FILE_NAME = "ventas_netas_por_periodo_cliente.csv"
VENTAS_PRODUCTO_REPORT_FILE_NAME = "venta_neta_por_periodo_producto_cliente.csv"
PREVENTA_PRODUCTO_REPORT_FILE_NAME = "preventa_por_producto.csv"
STOCK_REPORT_FILE_NAME = "stock_por_productos.csv"

LOGIN_URL = "https://dispro360.disprofarma.com.ar/Dispro360/inicio/Login.aspx"
PREVENTA_URL = "https://dispro360.disprofarma.com.ar/Dispro360/estadisticas/PreventaPorCliente.aspx"
VENTAS_URL = "https://dispro360.disprofarma.com.ar/Dispro360/estadisticas/VentasNetasPeriodoCliente.aspx"
VENTAS_PRODUCTO_URL = "https://dispro360.disprofarma.com.ar/Dispro360/inicio/ConsultaDinamica.aspx?param=Y29kaWdvTWVudSUzRDExMDk%3D"
PREVENTA_PRODUCTO_URL = "https://dispro360.disprofarma.com.ar/Dispro360/estadisticas/PreventaPorProducto.aspx"
STOCK_URL = "https://dispro360.disprofarma.com.ar/Dispro360/stock/StockProductoV2.aspx"

# --- 3. CONFIGURACIÓN ROBUSTA DEL DRIVER ---
def setup_driver():
    options = Options()
    if IS_LOCAL == "FALSE":
        options.add_argument("--headless=new")  # Headless moderno para Linux
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    options.add_experimental_option("prefs", {
        "download.default_directory": DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "directory_upgrade": True,
        "safebrowsing.enabled": True
    })

    if IS_LOCAL == "FALSE":
        # Mantiene la inicialización nativa limpia para entornos automatizados de Linux
        driver = webdriver.Chrome(options=options)
    else:
        driver = webdriver.Chrome(options=options)
        
    return driver

# --- 4. TU LÓGICA DE NAVEGACIÓN EXACTA (SIN TOCAR COMPORTAMIENTOS) ---

def login_to_dispro(driver):
    driver.get(LOGIN_URL)
    driver.wait = WebDriverWait(driver, 15)

    driver.wait.until(EC.presence_of_element_located((By.ID, "txtLogin"))).send_keys(USER)
    driver.wait.until(EC.presence_of_element_located((By.ID, "txtPassword"))).send_keys(PASSWORD)
    
    # 💥 CAMBIO SEGURO PARA EL ENTORNO CLOUD:
    # Seleccionamos el botón igual que antes, pero lo clickeamos con JavaScript.
    # Esto asegura que el formulario se envíe en GitHub Actions sin importar el tamaño de la pantalla.
    boton_login = driver.find_element(By.XPATH, '//*[@id="formLogin"]/button')
    driver.execute_script("arguments[0].click();", boton_login)

    # 🚀 REEMPLAZO DE LA LÍNEA 87:
    # Quitamos 'url_changes' que rompía el flujo en la nube.
    # Le damos 5 segundos físicos para que el servidor procese la sesión.
    # Como inmediatamente después tu función 'download_preventa_report' hace un 'driver.get(PREVENTA_URL)',
    # la espera de URL era redundante; el script igual forzará la redirección al reporte.
    time.sleep(5)

def download_preventa_report(driver):
    delete_previous_file(PREVENTA_REPORT_FILE_NAME)
    driver.get(PREVENTA_URL)
    driver.wait = WebDriverWait(driver, 15)
    driver.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="cmb_ventas"]/option[4]')))
    Select(driver.wait.until(EC.presence_of_element_located((By.ID, "cmb_ventas")))).select_by_visible_text("Ambos")
    time.sleep(1) 
    driver.wait.until(EC.presence_of_element_located((By.ID, "btnFiltrar"))).click()

    driver.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="tbPreventaPorCliente_wrapper"]/div[1]/div/a[2]'))).click()
    wait_for_report_download(PREVENTA_REPORT_FILE_NAME)

def download_venta_report(driver):
    delete_previous_file(VENTA_REPORT_FILE_NAME)
    driver.get(VENTAS_URL)
    driver.wait = WebDriverWait(driver, 15)
    driver.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="cmb_ventas"]/option[4]')))
    Select(driver.wait.until(EC.presence_of_element_located((By.ID, "cmb_fecha")))).select_by_visible_text("Procesado")
    Select(driver.wait.until(EC.presence_of_element_located((By.ID, "cmb_ventas")))).select_by_visible_text("Ambas")
    time.sleep(0.5) 
    driver.wait.until(EC.presence_of_element_located((By.ID, "btnFiltrar"))).click()

    driver.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="tbVentasNetasPeriodoCliente_wrapper"]/div[1]/div/a[2]'))).click()
    wait_for_report_download(VENTA_REPORT_FILE_NAME)

def download_producto_report(driver):
    delete_previous_file(VENTAS_PRODUCTO_REPORT_FILE_NAME)
    driver.get(VENTAS_PRODUCTO_URL)
    driver.wait = WebDriverWait(driver, 15)
    driver.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="tbinVtaporPeriodoProduClie_codigoVenta"]/option[3]')))
    Select(driver.wait.until(EC.presence_of_element_located((By.ID, "tbinVtaporPeriodoProduClie_codigoVenta")))).select_by_visible_text("Ambas")
    
    current_date = driver.wait.until(EC.presence_of_element_located((By.ID, "tbinVtaporPeriodoProduClie_fechaDesde"))).get_attribute("value")
    new_date = current_date.split("/")
    new_date[0] = "01"  
    current_date = "/".join(new_date)
    
    driver.find_element(By.ID, "tbinVtaporPeriodoProduClie_fechaDesde").clear()
    driver.find_element(By.ID, "tbinVtaporPeriodoProduClie_fechaDesde").send_keys(current_date)

    time.sleep(0.5) 
    driver.wait.until(EC.presence_of_element_located((By.ID, "btnFiltrar"))).click()

    driver.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="tbinVtaporPeriodoProduClie_wrapper"]/div[1]/div/a[2]'))).click()
    wait_for_report_download(VENTAS_PRODUCTO_REPORT_FILE_NAME)

def download_preventa_producto_report(driver):
    delete_previous_file(PREVENTA_PRODUCTO_REPORT_FILE_NAME)
    driver.get(PREVENTA_PRODUCTO_URL)
    driver.wait = WebDriverWait(driver, 15)
    driver.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="cmb_ventas"]')))
    Select(driver.wait.until(EC.presence_of_element_located((By.ID, "cmb_ventas")))).select_by_visible_text("Ambos")
    
    time.sleep(0.5) 
    driver.wait.until(EC.presence_of_element_located((By.ID, "btnFiltrar"))).click()

    driver.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="tbPreventaPorProducto_wrapper"]/div[1]/div/a[2]/span'))).click()
    wait_for_report_download(PREVENTA_PRODUCTO_REPORT_FILE_NAME)

def download_stock_report(driver):
    delete_previous_file(STOCK_REPORT_FILE_NAME)
    driver.get(STOCK_URL)
    driver.wait = WebDriverWait(driver, 15)
    driver.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="cmb_periodos"]/option[2]'))).click()
    
    time.sleep(0.5) 
    driver.wait.until(EC.presence_of_element_located((By.ID, "btnFiltrar"))).click()

    driver.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="tbStockProductoV2_wrapper"]/div[1]/div/a[2]/span/i'))).click()
    wait_for_report_download(STOCK_REPORT_FILE_NAME)

# --- 5. FUNCIONES AUXILIARES DE ARCHIVOS ---
def delete_previous_file(file_name):
    file_path = os.path.join(DOWNLOAD_DIR, file_name)
    if os.path.exists(file_path):
        os.remove(file_path)
    enc_path = os.path.join(DOWNLOAD_DIR, file_name + ".encrypted")
    if os.path.exists(enc_path):
        os.remove(enc_path)

def wait_for_report_download(file_name):
    file_path = os.path.join(DOWNLOAD_DIR, file_name)
    timeout_seconds = 90
    start_time = time.time()
    while not os.path.exists(file_path) and (time.time() - start_time) < timeout_seconds:
        time.sleep(1)

# --- 6. ORQUESTADOR CENTRAL ---
def scrape_data():
    if not ENCRYPTION_KEY:
        print("Error: No se detectó ninguna ENCRYPTION_KEY cargada en el entorno.")
        return

    print("Iniciando el driver de Chrome...")
    driver = setup_driver()
    
    try:
        print("Descargando reportes de Disprofarma...")
        login_to_dispro(driver)
        
        # Ejecuta tus descargas exactamente en tu orden previo
        download_preventa_report(driver)
        # download_venta_report(driver) # Se mantiene comentado como lo tenías
        download_producto_report(driver)
        download_preventa_producto_report(driver)
        download_stock_report(driver)

        # 🔒 PROCESAMIENTO DE ENCRIPTACIÓN POST-DESCARGA
        print("Encriptando archivos descargados de Disprofarma...")
        lista_reportes = [
            PREVENTA_REPORT_FILE_NAME,
            VENTAS_PRODUCTO_REPORT_FILE_NAME,
            PREVENTA_PRODUCTO_REPORT_FILE_NAME,
            STOCK_REPORT_FILE_NAME
        ]
        
        for csv_nombre in lista_reportes:
            ruta_csv_plano = os.path.join(DOWNLOAD_DIR, csv_nombre)
            if os.path.exists(ruta_csv_plano):
                encrypt_file(ruta_csv_plano, ENCRYPTION_KEY.encode())
                os.remove(ruta_csv_plano) 

        # 🛒 DESCARGA Y ENCRIPTACIÓN DE SHOPIFY
        print("Iniciando Scraping de Shopify...")
        ventas_cav_shopify = scrap_shopify(SHOPIFY_DOMAIN, SHOPIFY_TOKEN)
        
        os.makedirs(DOWNLOAD_DIR, exist_ok=True) 
        ruta_plana_shopify = os.path.join(DOWNLOAD_DIR, 'ventas_caviahue_shopify.csv')
        ventas_cav_shopify.to_csv(ruta_plana_shopify, index=False)

        print("Encriptando archivo de Shopify...")
        encrypt_file(ruta_plana_shopify, ENCRYPTION_KEY.encode())
        os.remove(ruta_plana_shopify) 

        print("Guardando marca de tiempo de actualización...")
        with open("last_scrape.txt", "w") as f:
            f.write(datetime.now().isoformat())

        print("¡Proceso de Scraping y Encriptación completo con éxito!")
        
    except Exception as e:
        print(f"Error crítico en el proceso: {e}")
        raise e
    finally:
        driver.quit()

if __name__ == "__main__":
    scrape_data()