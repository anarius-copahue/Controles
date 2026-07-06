from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import os
import time
from datetime import datetime
from shopify import scrap_shopify  
from encrypt import encrypt_file

# --- CONTROL DUAL DE CREDENCIALES (LOCAL VS ACTIONS) ---
try:
    import streamlit as st
    # Si estamos en local con Streamlit configurado, prioriza st.secrets
    USER = st.secrets["DISPRO_USER"]
    PASSWORD = st.secrets["DISPRO_PASSWORD"]
    SHOPIFY_DOMAIN = st.secrets["CAVIAHUE_SHOP_DOMAIN"]
    SHOPIFY_TOKEN = st.secrets["CAVIAHUE_SHOP_TOKEN"]
    ENCRYPTION_KEY = st.secrets["ENCRYPTION_KEY"]
except Exception:
    # Si falla st.secrets (como pasa en GitHub Actions), lee las variables del sistema
    USER = os.environ.get("DISPRO_USER")
    PASSWORD = os.environ.get("DISPRO_PASSWORD")
    SHOPIFY_DOMAIN = os.environ.get("CAVIAHUE_SHOP_DOMAIN")
    SHOPIFY_TOKEN = os.environ.get("CAVIAHUE_SHOP_TOKEN")
    ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY")

DOWNLOAD_DIR = os.path.join(os.getcwd(), "descargas")

REPORTES_DISPRO = {
    "preventa_por_cliente.csv": "descargas/preventa_por_cliente.csv.encrypted",
    "ventas_netas_por_periodo_cliente.csv": "descargas/ventas_netas_por_periodo_cliente.csv.encrypted",
    "venta_neta_por_periodo_producto_cliente.csv": "descargas/venta_neta_por_periodo_producto_cliente.csv.encrypted",
    "preventa_por_producto.csv": "descargas/preventa_por_producto.csv.encrypted",
    "stock_por_productos.csv": "descargas/stock_por_productos.csv.encrypted"
}

LOGIN_URL = "https://dispro360.disprofarma.com.ar/Dispro360/inicio/Login.aspx"
PREVENTA_URL = "https://dispro360.disprofarma.com.ar/Dispro360/estadisticas/PreventaPorCliente.aspx"
VENTAS_URL = "https://dispro360.disprofarma.com.ar/Dispro360/estadisticas/VentasNetasPeriodoCliente.aspx"
VENTAS_PRODUCTO_URL = "https://dispro360.disprofarma.com.ar/Dispro360/inicio/ConsultaDinamica.aspx?param=Y29kaWdvTWVudSUzRDExMDk%3D"
PREVENTA_PRODUCTO_URL = "https://dispro360.disprofarma.com.ar/Dispro360/estadisticas/PreventaPorProducto.aspx"
STOCK_URL = "https://dispro360.disprofarma.com.ar/Dispro360/stock/StockProductoV2.aspx"

def setup_driver():
    options = Options()
    # Si detecta que corre en GitHub Actions (entorno Linux), fuerza modo Headless estricto
    if os.environ.get("GITHUB_ACTIONS") == "true":
        options.add_argument("--headless=new")  
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
    else:
        # En local podés elegir ver el navegador comentando la línea de abajo si querés depurar
        options.add_argument("--headless=new") 
        
    options.add_argument("--window-size=1920,1080")
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    options.add_experimental_option("prefs", {
        "download.default_directory": DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "directory_upgrade": True,
        "safebrowsing.enabled": True
    })

    driver = webdriver.Chrome(options=options)
    return driver

def login_to_dispro(driver):
    driver.get(LOGIN_URL)
    # Subimos el tiempo de espera a 25 segundos por si el servidor de Dispro está lento
    driver.wait = WebDriverWait(driver, 25) 
    
    # Completar usuario y contraseña
    driver.wait.until(EC.presence_of_element_located((By.ID, "txtLogin"))).send_keys(USER)
    driver.wait.until(EC.presence_of_element_located((By.ID, "txtPassword"))).send_keys(PASSWORD)
    
    # Forzar el clic mediante JavaScript para asegurar que impacte en el servidor
    boton_login = driver.find_element(By.XPATH, '//*[@id="formLogin"]/button')
    driver.execute_script("arguments[0].click();", boton_login)
    
    print("Clic de login enviado, esperando redirección...")
    time.sleep(3) # Le damos un pequeño respiro físico a la carga

def download_preventa_report(driver):
    nombre_csv = "preventa_por_cliente.csv"
    delete_previous_file(nombre_csv)
    driver.get(PREVENTA_URL)
    driver.wait = WebDriverWait(driver, 15)
    driver.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="cmb_ventas"]/option[4]')))
    Select(driver.wait.until(EC.presence_of_element_located((By.ID, "cmb_ventas")))).select_by_visible_text("Ambos")
    time.sleep(1) 
    driver.wait.until(EC.presence_of_element_located((By.ID, "btnFiltrar"))).click()
    driver.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="tbPreventaPorCliente_wrapper"]/div[1]/div/a[2]'))).click()
    wait_for_report_download(nombre_csv)

def download_venta_report(driver):
    nombre_csv = "ventas_netas_por_periodo_cliente.csv"
    delete_previous_file(nombre_csv)
    driver.get(VENTAS_URL)
    driver.wait = WebDriverWait(driver, 15)
    driver.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="cmb_ventas"]/option[4]')))
    Select(driver.wait.until(EC.presence_of_element_located((By.ID, "cmb_fecha")))).select_by_visible_text("Procesado")
    Select(driver.wait.until(EC.presence_of_element_located((By.ID, "cmb_ventas")))).select_by_visible_text("Ambas")
    time.sleep(0.5) 
    driver.wait.until(EC.presence_of_element_located((By.ID, "btnFiltrar"))).click()
    driver.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="tbVentasNetasPeriodoCliente_wrapper"]/div[1]/div/a[2]'))).click()
    wait_for_report_download(nombre_csv)

def download_producto_report(driver):
    nombre_csv = "venta_neta_por_periodo_producto_cliente.csv"
    delete_previous_file(nombre_csv)
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
    wait_for_report_download(nombre_csv)

def download_preventa_producto_report(driver):
    nombre_csv = "preventa_por_producto.csv"
    delete_previous_file(nombre_csv)
    driver.get(PREVENTA_PRODUCTO_URL)
    driver.wait = WebDriverWait(driver, 15)
    driver.wait.until(EC.presence_of_element_located((By.ID, "cmb_ventas")))
    Select(driver.wait.until(EC.presence_of_element_located((By.ID, "cmb_ventas")))).select_by_visible_text("Ambos")
    time.sleep(0.5) 
    driver.wait.until(EC.presence_of_element_located((By.ID, "btnFiltrar"))).click()
    driver.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="tbPreventaPorProducto_wrapper"]/div[1]/div/a[2]/span'))).click()
    wait_for_report_download(nombre_csv)

def download_stock_report(driver):
    nombre_csv = "stock_por_productos.csv"
    delete_previous_file(nombre_csv)
    driver.get(STOCK_URL)
    driver.wait = WebDriverWait(driver, 15)
    driver.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="cmb_periodos"]/option[2]'))).click()
    time.sleep(0.5) 
    driver.wait.until(EC.presence_of_element_located((By.ID, "btnFiltrar"))).click()
    driver.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="tbStockProductoV2_wrapper"]/div[1]/div/a[2]/span/i'))).click()
    wait_for_report_download(nombre_csv)

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

def scrape_data():
    if not ENCRYPTION_KEY:
        print("Error: No se detectó ninguna ENCRYPTION_KEY cargada en el entorno.")
        return

    print("Iniciando el driver de Chrome...")
    driver = setup_driver()
    try:
        print("Descargando reportes de Disprofarma...")
        login_to_dispro(driver)
        download_preventa_report(driver)
        download_venta_report(driver)
        download_producto_report(driver)
        download_preventa_producto_report(driver)
        download_stock_report(driver)
        
        # 🔒 ENCRIPTACIÓN DE REPORTES DISPROFARMA
        print("Encriptando archivos descargados de Disprofarma...")
        for csv_nombre, _ in REPORTES_DISPRO.items():
            ruta_csv_plano = os.path.join(DOWNLOAD_DIR, csv_nombre)
            if os.path.exists(ruta_csv_plano):
                encrypt_file(ruta_csv_plano, ENCRYPTION_KEY.encode())
                os.remove(ruta_csv_plano) 

        # 🛒 DESCARGA Y ENCRIPTACIÓN DE SHOPIFY
        print("Iniciando Scraping de Shopify...")
        ventas_cav_shopify = scrap_shopify(SHOPIFY_DOMAIN, SHOPIFY_TOKEN)
        
        # 🔥 AGREGA ESTA LÍNEA AQUÍ ABAJO:
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