from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
# from webdriver_manager.chrome import ChromeDriverManager
# from webdriver_manager.core.os_manager import ChromeType
import os
import time
import streamlit as st

#DISPRO_USER = st.secrets["DISPRO_USER"]
#DISPRO_PASSWORD = st.secrets["DISPRO_PASSWORD"]

# MERCADOLIBRE_USER = st.secrets["MERCADOLIBRE_USER"]
# MERCADOLIBRE_PASSWORD = st.secrets["MERCADOLIBRE_PASSWORD"]

MERCADOLIBRE_USER = "ana.rius@labcopahue.com"
MERCADOLIBRE_PASSWORD = "Lasheras12"

DOWNLOAD_DIR = os.path.join(os.getcwd(), "descargas")

PREVENTA_REPORT_FILE_NAME = "preventa_por_cliente.csv"
VENTA_REPORT_FILE_NAME = "ventas_netas_por_periodo_cliente.csv"
VENTAS_PRODUCTO_REPORT_FILE_NAME = "venta_neta_por_periodo_producto_cliente.csv"

DISPRO_LOGIN_URL = "https://dispro360.disprofarma.com.ar/Dispro360/inicio/Login.aspx"
PREVENTA_URL = "https://dispro360.disprofarma.com.ar/Dispro360/estadisticas/PreventaPorCliente.aspx"
VENTAS_URL = "https://dispro360.disprofarma.com.ar/Dispro360/estadisticas/VentasNetasPeriodoCliente.aspx"
VENTAS_PRODUCTO_URL = "https://dispro360.disprofarma.com.ar/Dispro360/inicio/ConsultaDinamica.aspx?param=Y29kaWdvTWVudSUzRDExMDk%3D"

MERCADOLIBRE_LOGIN_URL = "https://www.mercadolibre.com/jms/mla/lgz/msl/login/"
VENTAS_URL = "https://www.mercadolibre.com.ar/ventas/omni/listado?filters=&subFilters=&search=&limit=50&offset=0&startPeriod=WITH_DATE_CLOSED_1M_OLD"

MERCADOLIBRE_REPORT_FILE_NAME = "Ventas_AR_Mercado_Libre.xlsx"

def setup_driver():
    options = Options()
    # options.add_argument("--headless")  # Run in headless mode
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # Set the path to the ChromeDriver executable
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    # Set Chrome options for downloading files
    options.add_experimental_option("prefs", {
    "download.default_directory": DOWNLOAD_DIR,
    "download.prompt_for_download": False,
    "directory_upgrade": True,
    "safebrowsing.enabled": True
    })
    
    driver = webdriver.Chrome(options=options)
    
    return driver

def login_to_dispro(driver):
    driver.get(DISPRO_LOGIN_URL)
    driver.wait = WebDriverWait(driver, 10)

    # Wait for the login form to be present and fill in the credentials
    driver.wait.until(EC.presence_of_element_located((By.ID, "txtLogin"))).send_keys(DISPRO_USER)
    driver.wait.until(EC.presence_of_element_located((By.ID, "txtPassword"))).send_keys(DISPRO_PASSWORD)
    driver.find_element(By.XPATH, '//button[contains(text(), "Ingresar")]').click()

    # Wait for the login to complete and the page to load
    current_url = driver.current_url
    driver.wait.until(EC.url_changes(current_url))

def download_preventa_report(driver):
    delete_previous_file(PREVENTA_REPORT_FILE_NAME)

    driver.get(PREVENTA_URL)
    driver.wait = WebDriverWait(driver, 10)

    driver.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="cmb_ventas"]/option[4]')))
    Select(driver.wait.until(EC.presence_of_element_located((By.ID, "cmb_ventas")))).select_by_visible_text("Ambos")
    time.sleep(0.5) # Wait for the dropdown to update before clicking
    driver.wait.until(EC.presence_of_element_located((By.ID, "btnFiltrar"))).click()

    # Download report as a csv file
    driver.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="tbPreventaPorCliente_wrapper"]/div[1]/div/a[2]'))).click()

    wait_for_report_download(PREVENTA_REPORT_FILE_NAME)

def download_venta_report(driver):
    delete_previous_file(VENTA_REPORT_FILE_NAME)

    driver.get(VENTAS_URL)
    driver.wait = WebDriverWait(driver, 10)

    driver.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="cmb_ventas"]/option[4]')))
    Select(driver.wait.until(EC.presence_of_element_located((By.ID, "cmb_fecha")))).select_by_visible_text("Procesado")
    Select(driver.wait.until(EC.presence_of_element_located((By.ID, "cmb_ventas")))).select_by_visible_text("Ambas")
    time.sleep(0.5) # Wait for the dropdown to update before clicking
    driver.wait.until(EC.presence_of_element_located((By.ID, "btnFiltrar"))).click()

    # Download report as a csv file
    driver.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="tbVentasNetasPeriodoCliente_wrapper"]/div[1]/div/a[2]'))).click()

    wait_for_report_download(VENTA_REPORT_FILE_NAME)

def download_producto_report(driver):
    delete_previous_file(VENTAS_PRODUCTO_REPORT_FILE_NAME)

    driver.get(VENTAS_PRODUCTO_URL)
    driver.wait = WebDriverWait(driver, 10)

    driver.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="tbinVtaporPeriodoProduClie_codigoVenta"]/option[3]')))
    Select(driver.wait.until(EC.presence_of_element_located((By.ID, "tbinVtaporPeriodoProduClie_codigoVenta")))).select_by_visible_text("Ambas")
    time.sleep(0.5) # Wait for the dropdown to update before clicking
    driver.wait.until(EC.presence_of_element_located((By.ID, "btnFiltrar"))).click()

    # Download report as a csv file
    driver.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="tbinVtaporPeriodoProduClie_wrapper"]/div[1]/div/a[2]'))).click()

    wait_for_report_download(VENTAS_PRODUCTO_REPORT_FILE_NAME)

def login_to_mercadolibre(driver):
    driver.get(MERCADOLIBRE_LOGIN_URL)
    driver.wait = WebDriverWait(driver, 10)

    # Wait for the login form to be present and fill in the credentials
    driver.wait.until(EC.presence_of_element_located((By.NAME, "user_id"))).send_keys(MERCADOLIBRE_USER)
    driver.find_element(By.XPATH, '//*[@id=":Rijhh:"]').click()

    driver.wait.until(EC.presence_of_element_located((By.NAME, "password"))).send_keys(MERCADOLIBRE_PASSWORD)
    driver.find_element(By.XPATH, '//*[@id="action-complete"]').click()

    # Wait for the login to complete and the page to load
    current_url = driver.current_url
    driver.wait.until(EC.url_changes(current_url))

def download_mercadolibre_report(driver):
    delete_previous_file(VENTAS_PRODUCTO_REPORT_FILE_NAME)

    driver.get(VENTAS_URL)
    driver.wait = WebDriverWait(driver, 10)

    # Wait for the report to load and download it
    driver.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id=":re:"]'))).click()

    # Wait for the download button to be present
    driver.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="desktop"]/div[2]/div/div[3]/div[2]/div/div/div[2]/div/div/a'))).click()

    # Wait for the download to complete
    wait_for_report_download(MERCADOLIBRE_REPORT_FILE_NAME)

def delete_previous_file(file_name):
    name, ext = file_name.rsplit('.', 1)

    # Search for a file that contains the name and ends with the same extension
    for file in os.listdir(DOWNLOAD_DIR):
        if name in file and file.endswith('.' + ext):
            file_path = os.path.join(DOWNLOAD_DIR, file)
            if os.path.exists(file_path):
                os.remove(file_path)
                break

def wait_for_report_download(file_name):
    name, ext = file_name.rsplit('.', 1)

    timeout_seconds = 60
    start_time = time.time()

    # Wait until the file that contains the name and extension is created
    while not any(name in file and file.endswith('.' + ext) for file in os.listdir(DOWNLOAD_DIR)):
        if time.time() - start_time > timeout_seconds:
            raise TimeoutError(f"Timeout waiting for {file_name} to download.")
        time.sleep(1)

def scrape_data():
    driver = setup_driver()

    try:
        # login_to_dispro(driver)
        # download_preventa_report(driver)
        # download_venta_report(driver)
        # download_producto_report(driver)

        login_to_mercadolibre(driver)
        download_mercadolibre_report(driver)
    finally:
        driver.quit()
    return

if __name__ == "__main__":
    scrape_data()
