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
PREVENTA_PRODUCTO_REPORT_FILE_NAME = "preventa_por_producto.csv"
STOCK_REPORT_FILE_NAME = "stock_por_productos.csv"

LOGIN_URL = "https://dispro360.disprofarma.com.ar/Dispro360/inicio/Login.aspx"
PREVENTA_URL = "https://dispro360.disprofarma.com.ar/Dispro360/estadisticas/PreventaPorCliente.aspx"
VENTAS_URL = "https://dispro360.disprofarma.com.ar/Dispro360/estadisticas/VentasNetasPeriodoCliente.aspx"
VENTAS_PRODUCTO_URL = "https://dispro360.disprofarma.com.ar/Dispro360/inicio/ConsultaDinamica.aspx?param=Y29kaWdvTWVudSUzRDExMDk%3D"
PREVENTA_PRODUCTO_URL = "https://dispro360.disprofarma.com.ar/Dispro360/estadisticas/PreventaPorProducto.aspx"
STOCK_URL = "https://dispro360.disprofarma.com.ar/Dispro360/stock/StockProductoV2.aspx"

import os
import shutil
import subprocess
import streamlit as st

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service


def setup_driver():

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    # -------------------------
    # Diagnóstico
    # -------------------------

    st.write("## Diagnóstico Chrome")

    for exe in [
        "chromium",
        "chromedriver",
        "/usr/bin/chromium",
        "/usr/bin/chromedriver",
    ]:

        if exe.startswith("/"):
            exists = os.path.exists(exe)
            st.write(f"{exe}: {exists}")

            if exists:
                try:
                    r = subprocess.run(
                        [exe, "--version"],
                        capture_output=True,
                        text=True,
                    )
                    st.write(r.stdout)
                    st.write(r.stderr)
                except Exception as e:
                    st.write(e)

        else:

            path = shutil.which(exe)

            st.write(f"{exe}: {path}")

            if path:
                try:
                    r = subprocess.run(
                        [path, "--version"],
                        capture_output=True,
                        text=True,
                    )
                    st.write(r.stdout)
                    st.write(r.stderr)
                except Exception as e:
                    st.write(e)

    # -------------------------
    # Chrome Options
    # -------------------------

    options = Options()

    options.binary_location = "/usr/bin/chromium"

    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-setuid-sandbox")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-sync")
    options.add_argument("--disable-default-apps")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-features=VizDisplayCompositor")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--window-size=1920,1080")

    prefs = {
        "download.default_directory": DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    }

    options.add_experimental_option("prefs", prefs)

    # -------------------------
    # Crear Driver
    # -------------------------

    try:

        service = Service(
            executable_path="/usr/bin/chromedriver",
            log_output="chromedriver.log"
        )

        driver = webdriver.Chrome(
            service=service,
            options=options,
        )

        st.success("Chrome iniciado correctamente")

        return driver

    except Exception as e:

        st.error(e)

        if os.path.exists("chromedriver.log"):

            st.write("## ChromeDriver log")

            with open("chromedriver.log", "r") as f:
                st.code(f.read())

        raise

def login_to_dispro(driver):
    driver.get(LOGIN_URL)
    driver.wait = WebDriverWait(driver, 10)

    # Wait for the login form to be present and fill in the credentials
    driver.wait.until(EC.presence_of_element_located((By.ID, "txtLogin"))).send_keys(USER)
    driver.wait.until(EC.presence_of_element_located((By.ID, "txtPassword"))).send_keys(PASSWORD)
    driver.find_element(By.XPATH, '//*[@id="formLogin"]/button').click()

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

def download_preventa_producto_report(driver):
  
    delete_previous_file(PREVENTA_PRODUCTO_REPORT_FILE_NAME)

    driver.get(PREVENTA_PRODUCTO_URL)
    driver.wait = WebDriverWait(driver, 10)

    driver.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="cmb_ventas"]')))
    
    Select(driver.wait.until(EC.presence_of_element_located((By.ID, "cmb_ventas")))).select_by_visible_text("Ambos")
    # Obtain current date from the element by id tbinVtaporPeriodoProduClie_fechaDesde
        
    time.sleep(0.5) # Wait for the dropdown to update before clicking
    driver.wait.until(EC.presence_of_element_located((By.ID, "btnFiltrar"))).click()

    # Download report as a csv file
    driver.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="tbPreventaPorProducto_wrapper"]/div[1]/div/a[2]/span'))).click()

    wait_for_report_download(PREVENTA_PRODUCTO_REPORT_FILE_NAME)

def download_stock_report(driver):
    delete_previous_file(STOCK_REPORT_FILE_NAME)

    driver.get(STOCK_URL)
    driver.wait = WebDriverWait(driver, 10)
    
    # Select the second option in the dropdown which is the last day
    driver.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="cmb_periodos"]/option[2]'))).click()
    
    time.sleep(0.5) # Wait for the dropdown to update before clicking
    driver.wait.until(EC.presence_of_element_located((By.ID, "btnFiltrar"))).click()

    # Download report as a csv file
    driver.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="tbStockProductoV2_wrapper"]/div[1]/div/a[2]/span/i'))).click()

    wait_for_report_download(STOCK_REPORT_FILE_NAME)


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
        #download_venta_report(driver)
        download_producto_report(driver)
        download_preventa_producto_report(driver)
        download_stock_report(driver)
    finally:
        driver.quit()
    return

if __name__ == "__main__":
    scrape_data()