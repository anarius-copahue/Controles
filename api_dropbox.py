import os
import time
from pathlib import Path
import dropbox
import streamlit as st

def descargar_archivos_dropbox():
    # 1. Determinar el directorio de destino
    es_local = st.secrets.get("LOCAL", "FALSE").upper() == "TRUE"

    if es_local:
        carpeta_destino = Path(r"C:\Users\anari\Documents\GitHub\Controles\data")
    else:
        carpeta_destino = Path("data")

    carpeta_destino.mkdir(parents=True, exist_ok=True)

    # 2. Mapeo de archivos
    base_dropbox = "/Laboratorio Copahue/Ana/Actualización control de avance"
    
    archivos = {
        "TANGO.xlsx": f"{base_dropbox}/TANGO.xlsx",
        "Cuota_Productos.xlsx": f"{base_dropbox}/Cuota_Productos.xlsx",
        "Historico_Productos.xlsx": f"{base_dropbox}/Historico_Productos.xlsx",
        "diccionario.xlsx": f"{base_dropbox}/diccionario.xlsx",
        "db_SELL_IN_OUT.xlsx": f"{base_dropbox}/db_SELL_IN_OUT.xlsx",
        "representante.xlsx": f"{base_dropbox}/representante.xlsx",
        "Historico.xlsx": f"{base_dropbox}/Historico.xlsx"

    }


    # 4. Conexión usando solo ACCESS_TOKEN
    access_token =  st.secrets["ACCESS_TOKEN"]
    dbx_base = dropbox.Dropbox(access_token)

    # Configuración de Team Space para cuentas de equipo
    account = dbx_base.users_get_current_account()
    root_id = account.root_info.root_namespace_id
    dbx = dbx_base.with_path_root(dropbox.common.PathRoot.root(root_id))

    # 5. Descarga de archivos
    for nombre_archivo, ruta_remota in archivos.items():
        ruta_local = carpeta_destino / nombre_archivo
        try:
            dbx.files_download_to_file(str(ruta_local), ruta_remota)
            print(f" -> Descargado: {nombre_archivo}")
        except Exception as e:
            print(f" -> Error al descargar {nombre_archivo}: {e}")

    return str(carpeta_destino)
