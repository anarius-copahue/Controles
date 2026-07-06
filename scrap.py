from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import os
import time
from datetime import datetime
from shopify import scrap_shopify  # Importamos tu función de shopify.py

# Leer credenciales desde las variables de entorno de GitHub Actions
USER = os.environ.get("DISPRO_USER")
PASSWORD = os.environ.get("DISPRO_PASSWORD")
SHOPIFY_DOMAIN = os.environ.get("CAVIAHUE_SHOP_DOMAIN")
SHOPIFY_TOKEN = os.environ.get("CAVIAHUE_SHOP_TOKEN")

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

def setup_driver():
    options = Options()
    options.add_argument("--headless=new")  
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
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
    driver.wait = WebDriverWait(driver, 15)
    driver.wait.until(EC.presence_of_element_located((By.ID, "txtLogin"))).send_keys(USER)
    driver.wait.until(EC.presence_of_element_located((By.ID, "txtPassword"))).send_keys(PASSWORD)
    driver.find_element(By.XPATH, '//*[@id="formLogin"]/button').click()
    current_url = driver.current_url
    driver.wait.until(EC.url_changes(current_url))

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
    driver.wait.until(EC.presence_of_element_located((By.ID, "cmb_ventas")))
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

def delete_previous_file(file_name):
    file_path = os.path.join(DOWNLOAD_DIR, file_name)
    if os.path.exists(file_path):
        os.remove(file_path)

def wait_for_report_download(file_name):
    file_path = os.path.join(DOWNLOAD_DIR, file_name)
    timeout_seconds = 90
    start_time = time.time()
    while not os.path.exists(file_path) and (time.time() - start_time) < timeout_seconds:
        time.sleep(1)

def scrape_data():
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
        
        print("Iniciando Scraping de Shopify...")
        ventas_cav_shopify = scrap_shopify(SHOPIFY_DOMAIN, SHOPIFY_TOKEN)
        ventas_cav_shopify.to_csv('descargas/ventas_caviahue_shopify.csv', index=False)
        
        print("Guardando marca de tiempo...")
        with open("last_scrape.txt", "w") as f:
            f.write(datetime.now().isoformat())
            
        print("¡Proceso de Scraping Completo Exitoso!")
    except Exception as e:
        print(f"Error: {e}")
        raise e
    finally:
        driver.quit()

if __name__ == "__main__":
    scrape_data()