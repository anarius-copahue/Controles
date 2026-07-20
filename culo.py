import os
from pathlib import Path
import dropbox
import streamlit as st

APP_KEY = st.secrets["APP_KEY"]
APP_SECRET = st.secrets["APP_SECRET"]

auth_flow = dropbox.DropboxOAuth2FlowNoRedirect(
    APP_KEY,
    APP_SECRET,
    token_access_type='offline'  # <--- Esto es la clave para que cree un token que NO expira
)

authorize_url = auth_flow.start()
print("1. Ve a esta dirección en tu navegador:")
print(authorize_url)
print("2. Haz clic en 'Permitir' (asegúrate de ingresar con la cuenta correcta).")
print("3. Copia el código de autorización que te da la página.")

auth_code = input("Pega el código de autorización aquí: ").strip()

try:
    oauth_result = auth_flow.finish(auth_code)
    print("\n✅ ¡ÉXITO! Guarda estos datos en tus secretos:")
    print(f"REFRESH_TOKEN = '{oauth_result.refresh_token}'")
except Exception as e:
    print(f"Error al autenticar: {e}")