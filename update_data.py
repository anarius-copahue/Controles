import streamlit as st
import pandas as pd
import numpy as np
import io
from encrypt import encrypt_file
import os
from datetime import datetime, timedelta

#es una ventana para actualizar desde la pagina el archivo sell_in_out.csv.
# hacer una verificacion de formato compatible con el archivo original.
# encryptar con el modulo encrypt despues de subir el archivo.




def update_data():
    st.title("Actualizar Datos de Ventas (Sell In/Out)")

    uploaded_file = st.file_uploader("Sube el archivo SELL_IN_OUT.csv", type=["csv"])

    if uploaded_file is not None:
        try:
            # Leer el archivo CSV subido
            df = pd.read_csv(uploaded_file)

            # Validar que el DataFrame no esté vacío
            if df.empty:

                st.error("El archivo CSV está vacío. Por favor, sube un archivo válido.")
                return
            # Validar que las columnas esperadas estén presentes
            expected_columns = ["Unnamed: 0", "MES", "AÑO", "FECHA", "SELL OUT", "SELL IN", "Fecha_ingles"]

            # Verificar si las columnas coinciden
            if not all(col in df.columns for col in expected_columns):
                st.error("El archivo no tiene las columnas esperadas. Por favor, sube un archivo con el formato correcto.")
                return
            
            # encriptar el archivo usando el modulo encrypt
            
            # Guardar el archivo temporalmente antes de encriptar
            temp_path = "data/SELL_IN_OUT.csv"
            df.to_csv(temp_path, index=False)
            # Encriptar el archivo
            encrypt_file(temp_path, st.secrets["ENCRYPTION_KEY"])

            st.success("Archivo encriptado y guardado correctamente")
           
        except Exception as e:
            st.error(f"Ocurrió un error al procesar el archivo: {e}")
        
    #tambien subir analogamente el archivo representante.xlsx
    st.title("Actualizar Cuota por representante")
    uploaded_rep_file = st.file_uploader("Sube el archivo representante.xlsx", type=["xlsx"])
    if uploaded_rep_file is not None:
        try:
            # Leer el archivo CSV subido
            df = pd.read_csv(uploaded_rep_file)

            # Validar que el DataFrame no esté vacío
            if df.empty:

                st.error("El archivo CSV está vacío. Por favor, sube un archivo válido.")
                return
            # Validar que las columnas esperadas estén presentes en cada pestaña
            expected_columns = ["N° CLIENTE", "CLIENTE", "Cuota Caviahue", "Total Caviahue", "% Caviahue", "Cuota Mizu", "Total Mizu", "% Mizu"]

            # Verificar si las columnas coinciden
            if not all(col in df.columns for col in expected_columns):
                st.error("El archivo no tiene las columnas esperadas. Por favor, sube un archivo con el formato correcto.")
                return
            
            # encriptar el archivo usando el modulo encrypt
            
            # Guardar el archivo temporalmente antes de encriptar
            temp_path = "data/temp_representante.csv"
            df.to_csv(temp_path, index=False)
            # Encriptar el archivo
            encrypt_file(temp_path, st.secrets["ENCRYPTION_KEY"])

            st.success("Archivo encriptado y guardado correctamente como representante_encrypted.csv")
           
        except Exception as e:
            st.error(f"Ocurrió un error al procesar el archivo: {e}")
            return
        
        #tambien subir analogamente el archivo "TANGO.xls". 
        # Revisar que la hoja datos exista y tenga las columnas esperadas
 
    st.title("Actualizar Datos de Tango")
    uploaded_tango_file = st.file_uploader("Sube el archivo TANGO.xls", type=["xls", "xlsx"])
    if uploaded_tango_file is not None:
        try:
            # Leer el archivo Excel subido
            xls = pd.ExcelFile(uploaded_tango_file)
            if "Datos" not in xls.sheet_names:
                st.error("El archivo no contiene una hoja llamada 'Datos'. Por favor, sube un archivo con el formato correcto.")
                return
            df = pd.read_excel(xls, sheet_name="Datos")

            # Validar que el DataFrame no esté vacío
            if df.empty:
                st.error("La hoja 'Datos' está vacía. Por favor, sube un archivo válido.")
                return

            # Validar que las columnas esperadas estén presentes
            expected_columns = ["COD_CLI","COD_ARTICU", "CANTIDAD"]

            # Verificar si las columnas coinciden
            if not all(col in df.columns for col in expected_columns):
                st.error("La hoja 'Datos' no tiene las columnas esperadas. Por favor, sube un archivo con el formato correcto.")
                return
            
            # encriptar el archivo usando el modulo encrypt
            
            # Guardar el archivo temporalmente antes de encriptar como csv
            temp_path = "data/TANGO.csv"
            df.to_csv(temp_path, index=False)
            # Encriptar el archivo
            encrypt_file(temp_path, st.secrets["ENCRYPTION_KEY"])

            st.success("Archivo encriptado y guardado correctamente como TANGO.csv")

           
        except Exception as e:
            st.error(f"Ocurrió un error al procesar el archivo: {e}")
            return
        
    # Este archivo dura una semana y luego se vacia automaticamente

    st.info("Nota: El archivo TANGO.csv se mantiene por una semana antes de ser eliminado automáticamente.")
      
    def remove_old_tango_file():
        tango_path = "data/TANGO.csv"
        if os.path.exists(tango_path):
            file_mod_time = datetime.fromtimestamp(os.path.getmtime(tango_path))
            if datetime.now() - file_mod_time > timedelta(weeks=1):
                os.remove(tango_path)
                st.info("El archivo TANGO.csv ha sido eliminado automáticamente después de una semana.")
    remove_old_tango_file()
        
