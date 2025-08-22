from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import os
import time
import streamlit as st

USER = st.secrets["DISPRO_USER"]
PASSWORD = st.secrets["DISPRO_PASSWORD"]

DOWNLOAD_DIR = os.path.join(os.getcwd(), "descargas")
PREVENTA_REPORT_FILE_NAME = "preventa_por_cliente.csv"
VENTA_REPORT_FILE_NAME = "ventas_netas_por_periodo_cliente.csv"
VENTAS_PRODUCTO_REPORT_FILE_NAME = "venta_neta_por_periodo_producto_cliente.csv"

LOGIN_URL = "https://dispro360.disprofarma.com.ar/Dispro360/inicio/Login.aspx"
PREVENTA_URL = "https://dispro360.disprofarma.com.ar/Dispro360/estadisticas/PreventaPorCliente.aspx"
VENTAS_URL = "https://dispro360.disprofarma.com.ar/Dispro360/estadisticas/VentasNetasPeriodoCliente.aspx"
VENTAS_PRODUCTO_URL = "https://dispro360.disprofarma.com.ar/Dispro360/inicio/ConsultaDinamica.aspx?param=Y29kaWdvTWVudSUzRDExMDk%3D"

def setup_driver():
    options = Options()
    if st.secrets["LOCAL"] == "FALSE":
        options.add_argument("--headless")  # Run in headless mode
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

    if st.secrets["LOCAL"] == "FALSE":
        from webdriver_manager.chrome import ChromeDriverManager
        from webdriver_manager.core.os_manager import ChromeType
        driver = webdriver.Chrome(service=Service(
                    ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()
                ), options=options)
    else:
        driver = webdriver.Chrome(options=options)
    
    return driver

def login_to_dispro(driver):
    driver.get(LOGIN_URL)
    driver.wait = WebDriverWait(driver, 10)

    # Wait for the login form to be present and fill in the credentials
    driver.wait.until(EC.presence_of_element_located((By.ID, "txtLogin"))).send_keys(USER)
    driver.wait.until(EC.presence_of_element_located((By.ID, "txtPassword"))).send_keys(PASSWORD)
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
    time.sleep(1) # Wait for the dropdown to update before clicking
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
    # Obtain current date from the element by id tbinVtaporPeriodoProduClie_fechaDesde
    current_date = driver.wait.until(EC.presence_of_element_located((By.ID, "tbinVtaporPeriodoProduClie_fechaDesde"))).get_attribute("value")
    new_date = current_date.split("/")
    new_date[0] = "01"  # Change the day to the first of the month
    current_date = "/".join(new_date)
    # Change the date to the first day of the month
    driver.find_element(By.ID, "tbinVtaporPeriodoProduClie_fechaDesde").clear()
    driver.find_element(By.ID, "tbinVtaporPeriodoProduClie_fechaDesde").send_keys(new_date)

    
    time.sleep(0.5) # Wait for the dropdown to update before clicking
    driver.wait.until(EC.presence_of_element_located((By.ID, "btnFiltrar"))).click()

    # Download report as a csv file
    driver.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="tbinVtaporPeriodoProduClie_wrapper"]/div[1]/div/a[2]'))).click()

    wait_for_report_download(VENTAS_PRODUCTO_REPORT_FILE_NAME)


def delete_previous_file(file_name):
    file_path = os.path.join(DOWNLOAD_DIR, file_name)
    if os.path.exists(file_path):
        os.remove(file_path)

def wait_for_report_download(file_name):
    # Wait for the download to complete
    file_path = os.path.join(DOWNLOAD_DIR, file_name)
    timeout_seconds = 60
    start_time = time.time()

    while not os.path.exists(file_path) and (time.time() - start_time) < timeout_seconds:
        time.sleep(1)

def scrape_data():

    driver = setup_driver()

    try:
        login_to_dispro(driver)
        download_preventa_report(driver)
        download_venta_report(driver)
        download_producto_report(driver)
    finally:
        driver.quit()
    return

if __name__ == "__main__":
    scrape_data()