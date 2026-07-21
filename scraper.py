import os
import csv
import json
import requests
import streamlit as st
from datetime import datetime, timedelta
from login_dispro import get_auth_token

# =====================================================================
# 1. HERRAMIENTAS / FUNCIONES REUTILIZABLES (Para cualquier reporte)
# =====================================================================

# 1. Obtener la fecha de hoy
hoy = datetime.now()

# 2. Calcular 'ayer' dependiendo de si hoy es lunes
if hoy.weekday() == 0:
    # Si hoy es lunes (0), restamos 3 días para ir al viernes
    ayer = hoy - timedelta(days=3)
else:
    # Si es cualquier otro día, restamos 1 día
    ayer = hoy - timedelta(days=1)

# 3. Formatear la fecha en el formato ISO que necesitas
ayer_iso_stock = ayer.strftime("%Y-%m-%dT00:00:00")

# --- Tus otras variables se mantienen igual ---
fecha_hoy = hoy.strftime("%d/%m/%Y")
fecha_primero_mes = (hoy - timedelta(days=hoy.day-1)).strftime("%d/%m/%Y")


print(f"Fecha de hoy: {fecha_hoy}, Fecha primero del mes: {fecha_primero_mes}")
print(f"Fecha ISO de hoy: {ayer_iso_stock}")

def consultar_api(url, headers, cookies, payload):
    """Realiza la petición POST de forma segura y maneja errores de conexión."""
    try:
        response = requests.post(url, headers=headers, cookies=cookies, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error crítico al conectar con el endpoint ({url.split('/')[-1]}): {e}")
        raise e

def formatear_numero(val, con_signo=False):
    """Formatea números flotantes/enteros al sistema regional (1.234.567,89)."""
    if val is None or val == "":
        return "0,00" if not con_signo else "$ 0,00"
    try:
        formateado = f"{float(val):,.2f}"
        formateado = formateado.replace(',', 'X').replace('.', ',').replace('X', '.')
        return f"$ {formateado}" if con_signo else formateado
    except (ValueError, TypeError):
        return str(val)

def guardar_a_csv(nombre_archivo, headers, filas):
    """Genera el CSV con delimitador pipe (|) y comillas obligatorias."""
    carpeta = "descargas"
    os.makedirs(carpeta, exist_ok=True)
    filepath = os.path.join(carpeta, nombre_archivo)
    
    with open(filepath, mode='w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, delimiter='|', quoting=csv.QUOTE_ALL)
        writer.writerow(headers)
        writer.writerows(filas)
    
    print(f"¡Archivo '{nombre_archivo}' generado con éxito en /{carpeta}!")
    return filepath


# =====================================================================
# 2. PROCESADORES ESPECÍFICOS (Uno por cada tipo de reporte)
# =====================================================================

def procesar_preventa_por_cliente(token, fecha_desde=fecha_primero_mes, fecha_hasta=fecha_hoy):
    """Lógica y mapeo para el reporte 'ConsultarPreventaPorCliente'."""
    url = 'https://dispro360.disprofarma.com.ar/WcfDispronet2/DispronetConsultas.svc/ConsultarPreventaPorCliente'
    headers = {'content-type': 'application/json; charset=UTF-8', 'tokenautenticacion': token}
    cookies = {'ASP.NET_SessionId': 'n3e4k2d5b0d2qslxellxeyqn', 'tokenAutenticacion': token}
    payload = {
        "parametros": {
            "codigoNeg": "062", "codigoVenta": "1", "codigoLaboratorio": "99",
            "fechaDesde": fecha_desde, "fechaHasta": fecha_hasta
        }
    }
    
    response_data = consultar_api(url, headers, cookies, payload)
        
    datos_json = json.loads(response_data.get('datos', '{}'))
    items = datos_json.get('listadoPreventaPorCliente', [])

    csv_headers = [
        "Neg", "Lab", "Pedido", "Clie", "Razón Social", "Fec Pedido", 
        "Fec. Estimada Despacho", "Fec.Estimada Entrega", "Items", "Unidades", 
        "Importe", "Imp. Neto", "Sellado"
    ]
    
    rows = []
    for item in items:
        rows.append([
            str(item.get("NEG", "")), str(item.get("LAB", "")), str(item.get("PEDI", "")),
            str(item.get("CLIE", "")), item.get("DESCLI", ""), item.get("FECCTE", ""),
            item.get("FECESTDESP", ""), item.get("FECESTENTR", ""), str(item.get("ITEMS", "")),
            str(item.get("UNIDAD", "")), 
            formatear_numero(item.get("IMPORTE"), con_signo=True),
            formatear_numero(item.get("IMPORTENETO"), con_signo=True),
            "" if item.get("SELLADO") is None else str(item["SELLADO"])
        ])
        
    guardar_a_csv("preventa_por_cliente.csv", csv_headers, rows)
    return True


def procesar_ventas_netas_periodo(token, fecha_desde=fecha_primero_mes, fecha_hasta=fecha_hoy):
    """Lógica, request y mapeo para el endpoint ConsultaGenericaGrillaDinamica."""
    # 1. Nueva URL extraída del cURL
    url = 'https://dispro360.disprofarma.com.ar/WcfDispronet2/DispronetServiciosDinamicos.svc/ConsultaGenericaGrillaDinamica'
    
    # 2. Headers actualizados según el cURL
    headers = {
        'accept': 'application/json, text/javascript, */*; q=0.01',
        'content-type': 'application/json; charset=UTF-8',
        'tokenautenticacion': token,
        'x-requested-with': 'XMLHttpRequest'
    }
    
    # 3. Cookies requeridas
    cookies = {
        'ASP.NET_SessionId': 'n3e4k2d5b0d2qslxellxeyqn', 
        'tokenAutenticacion': token
    }
    
    # 4. Estructura de Payload corregida con la lista dinámica de parámetros
    payload = {
        "parametros": {
            "idGrillaEjecucion": 25,
            "listado": [
                {"nombre": "codigoLaboratorio", "valor": "62"},
                {"nombre": "fechaDesde", "valor": fecha_desde},
                {"nombre": "fechaHasta", "valor": fecha_hasta},
                {"nombre": "Venta", "valor": "2"}
            ]
        }
    }
    

    # Realiza la petición usando tu función base
    response_data = consultar_api(url, headers, cookies, payload)
        
    datos_json = json.loads(response_data.get('datos', '{}'))
    # Procesa el "listado" interno de la respuesta provista
    items = datos_json.get('listado', [])
        
    # Encabezados del CSV (Se mantienen intactos)
    csv_headers = [
        "Div", "Familia", "PRODU.", "Descripción", "Cliente",
        "Alias", "GRUPO", "GRUPO_AMPLIADO", "Venta Unid.", "Unid. Bonif.", 
        "Venta Bruta", "Dtos. en Factura", "Dtos. (Vol.)", "Dtos. Por Transfer",
        "Dto. Obra Social", "Dto. AP", "Dto. x Prod", "Importe Neto", "Log"
    ]
    
    rows = []
    for item in items:
        # Extraer y limpiar cantidades para que queden como enteros ("6" en vez de "6.0")
        venta_unid = str(int(float(item.get("CANTA", 0)))) if item.get("CANTA") is not None else "0"
        unid_bonif = str(int(float(item.get("CANTB", 0)))) if item.get("CANTB") is not None else "0"

        rows.append([
            item.get("LABORAT", "").strip() if item.get("LABORAT") else "",                       # "Div"
            item.get("FAMILIA", "").strip() if item.get("FAMILIA") else "",                       # "Familia"
            str(item.get("PRODU", "")),                                                           # "PRODU."
            item.get("DESLA", "").strip() if item.get("DESLA") else "",                           # "Descripción"
            str(item.get("CLIE", "")),                                                            # "Cliente"
            item.get("ALIAS", "").strip() if item.get("ALIAS") else "",                           # "Alias"
            item.get("GRUPO", "").strip() if item.get("GRUPO") else "",                           # "GRUPO"
            item.get("GRUPO_AMPLIADO", "").strip() if item.get("GRUPO_AMPLIADO") else "",         # "GRUPO_AMPLIADO"
            venta_unid,                                                                           # "Venta Unid."
            unid_bonif,                                                                           # "Unid. Bonif."
            formatear_numero(item.get("BRUTO"), con_signo=False),                                 # "Venta Bruta" (SIN $)
            formatear_numero(item.get("DTO"), con_signo=False),                                   # "Dtos. en Factura" (SIN $)
            formatear_numero(item.get("DTOVOL"), con_signo=False),                                # "Dtos. (Vol.)" (SIN $)
            formatear_numero(item.get("DTOTRAN"), con_signo=False),                               # "Dtos. Por Transfer" (SIN $)
            formatear_numero(item.get("DTOOOSS"), con_signo=False),                               # "Dto. Obra Social" (SIN $)
            formatear_numero(item.get("DTOAP"), con_signo=False),                                 # "Dto. AP" (SIN $)
            formatear_numero(item.get("DTOPP"), con_signo=False),                                 # "Dto. x Prod" (SIN $)
            formatear_numero(item.get("IMPNETO"), con_signo=False),                               # "Importe Neto" (SIN $)
            item.get("ESP", "").strip() if item.get("ESP") else ""                                # "Log"
        ])
    # Guardar el resultado en el CSV
    guardar_a_csv("venta_neta_por_periodo_producto_cliente.csv", csv_headers, rows)
    return True


def procesar_preventa_por_producto(token, fecha_desde=fecha_primero_mes, fecha_hasta=fecha_hoy):
    """Lógica, request y mapeo para el endpoint ConsultarPreventaPorProducto."""
    # 1. Nueva URL extraída del cURL
    url = 'https://dispro360.disprofarma.com.ar/WcfDispronet2/DispronetConsultas.svc/ConsultarPreventaPorProducto'
    
    # 2. Headers requeridos
    headers = {
        'accept': 'application/json, text/javascript, */*; q=0.01',
        'content-type': 'application/json; charset=UTF-8',
        'tokenautenticacion': token,
        'x-requested-with': 'XMLHttpRequest'
    }
    
    # 3. Cookies de sesión
    cookies = {
        'ASP.NET_SessionId': 'n3e4k2d5b0d2qslxellxeyqn', 
        'tokenAutenticacion': token
    }
    
    # 4. Estructura de Payload plana dentro de "parametros"
    # NOTA: Recuerda que 'fecha_desde' y 'fecha_hasta' deben tener formato "DD/MM/YYYY"
    payload = {
        "parametros": {
            "codigoNeg": "062",
            "codigoLaboratorio": "99",
            "fechaDesde": fecha_desde,
            "fechaHasta": fecha_hasta
        }
    }
    
    # Realiza la petición usando tu función base
    response_data = consultar_api(url, headers, cookies, payload)
        
    # El backend devuelve un JSON serializado como string dentro de la propiedad 'datos'
    datos_json = json.loads(response_data.get('datos', '{}'))
    items = datos_json.get('listadoPreventaPorProducto', [])

    # Encabezados del CSV idénticos a los de tu archivo original
    csv_headers = [
        "Div", "Familia", "Neg", "Lab", "Producto", 
        "Descripción", "Items", "Un. Reserv.", "Importe", 
        "Importe Neto", "TUnidades"
    ]
    
    rows = []
    for item in items:
        rows.append([
            item.get("LABORAT", "").strip() if item.get("LABORAT") else "",
            item.get("FAMILIA", "").strip() if item.get("FAMILIA") else "",
            str(item.get("NEG", "0")),
            str(item.get("LAB", "")),
            str(item.get("PRODU", "")),
            item.get("DESLA", "").strip() if item.get("DESLA") else "",
            str(item.get("ITEMS", "0")),
            str(item.get("UNIDAD", "0")),
            formatear_numero(item.get("IMPORTE"), con_signo=True),
            formatear_numero(item.get("IMPORTENETO"), con_signo=True),
            str(item.get("TUNIDADES", "0"))
        ])
        
    # Guarda los datos en el nuevo archivo CSV designado
    guardar_a_csv("preventa_por_producto.csv", csv_headers, rows)
    return True


def procesar_stock_productos(token, periodo=ayer_iso_stock):
    """Lógica, request y mapeo para el endpoint ConsultarStockProductoV2."""
    # 1. Nueva URL extraída del cURL
    url = 'https://dispro360.disprofarma.com.ar/WcfDispronet2/DispronetConsultas.svc/ConsultarStockProductoV2'
    
    # 2. Headers requeridos
    headers = {
        'accept': 'application/json, text/javascript, */*; q=0.01',
        'content-type': 'application/json; charset=UTF-8',
        'tokenautenticacion': token,
        'x-requested-with': 'XMLHttpRequest'
    }
    
    # 3. Cookies de sesión
    cookies = {
        'ASP.NET_SessionId': 'n3e4k2d5b0d2qslxellxeyqn', 
        'tokenAutenticacion': token
    }
    
    # 4. Estructura de Payload según el cURL recibido
    # NOTA: 'periodo' debe venir formateado en formato ISO (ej: "2026-07-06T00:00:00")
    payload = {
        "parametros": {
            "codigoLaboratorio": "062",
            "periodo": periodo,
            "tipoProd": "",
            "diasStock": "0",
            "producto": "-1",
            "descripcion": ""
        }
    }
    
    # Realiza la petición usando tu función base
    response_data = consultar_api(url, headers, cookies, payload)
        
    # El backend devuelve un JSON serializado como string dentro de 'datos'
    datos_json = json.loads(response_data.get('datos', '{}'))
    items = datos_json.get('listadoStockProducto', [])

    # Encabezados del CSV ordenados exactamente como en 'stock_por_productos.csv'
    csv_headers = [
        "Des Div", "Cod", "GTIN", "Descripcion", "L", "Disp (31)", 
        "Res (32, 36)", "Cua (33)", "Otros (34, 35, 39)", "Otros (3,21)", 
        "Total", "Presup", "Vta Dis", "Vta Ins", "Pre Vta Dis", 
        "Pre Vta Ins", "Precio", "Ing", "Días Stk", "Div", "Almacenamiento"
    ]
    
    rows = []
    for item in items:
        rows.append([
            item.get("DESDIV", "").strip() if item.get("DESDIV") else "",
            str(item.get("PRODU", "")),
            str(item.get("EAM13", "")),
            item.get("DESCRIP", "").strip() if item.get("DESCRIP") else "",
            str(item.get("LINPRO", "")),
            str(item.get("STOCKDISP", "0")),
            str(item.get("STOCKNODISP", "0")),
            str(item.get("STOCKCUA", "0")),
            str(item.get("STOCKOTDIS", "0")),
            str(item.get("CONTABLE", "0")),
            str(item.get("TOTAL", "0")),
            str(item.get("PRESU", "0")),
            str(item.get("VTADISP", "0")),
            str(item.get("VTAINST", "0")),
            str(item.get("PREVENTADIS", "0")),
            str(item.get("PREVENTAINST", "0")),
            formatear_numero(item.get("PRECIO"), con_signo=True),
            str(item.get("INGRESO", "0")),
            str(item.get("DIASSTK", "0")),
            item.get("DIVISION", "").strip() if item.get("DIVISION") else "",
            item.get("ALMACENAMIENTO", "").strip() if item.get("ALMACENAMIENTO") else ""
        ])
        
    # Guarda los datos en el archivo CSV correspondiente
    guardar_a_csv("stock_por_productos.csv", csv_headers, rows)
    return True


# =====================================================================
# 3. ORQUESTADOR CENTRAL MODIFICADO (Soporta ejecución pura en consola)
# =====================================================================
def scrape_data():

    token_dispro = get_auth_token()
   
    print("Iniciando la descarga en lote...")
    
    procesar_preventa_por_cliente(token_dispro)
    procesar_ventas_netas_periodo(token_dispro)
    procesar_preventa_por_producto(token_dispro)
    procesar_stock_productos(token_dispro)
    
    print("¡Proceso finalizado por completo!")

