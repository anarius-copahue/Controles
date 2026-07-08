import requests
import streamlit as st

USER = st.secrets["DISPRO_USER"]  # Ya vi que tu login es este en el JWT :)
PASSWORD = st.secrets["DISPRO_PASSWORD"]

URL_LOGIN_PAGE = 'https://dispro360.disprofarma.com.ar/Dispro360/inicio/Login.aspx'
URL_AUTH_ENDPOINT = 'https://dispro360.disprofarma.com.ar/WcfDispronet2/DispronetLogin.svc/AutenticarUsuario'

def get_auth_token():
    headers = {
    'accept': 'application/json, text/javascript, */*; q=0.01',
    'accept-language': 'es-ES,es;q=0.9',
    'content-type': 'application/json; charset=UTF-8',
    'origin': 'https://dispro360.disprofarma.com.ar',
    'referer': URL_LOGIN_PAGE,
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36',
    'x-requested-with': 'XMLHttpRequest'
    }
    payload = {"login": USER, "password": PASSWORD}
    session = requests.Session()

    try:
        # 1. Obtener cookies base (ASP.NET_SessionId)
        session.get(URL_LOGIN_PAGE, headers=headers)
        
        # 2. Hacer el login
        response = session.post(URL_AUTH_ENDPOINT, json=payload, headers=headers)
        
        if response.status_code == 200:
            # Transformamos la respuesta de texto a un diccionario de Python
            respuesta_json = response.json()
            
            # Validamos si el resultado fue exitoso
            if respuesta_json.get("resultado") == True:
                token = respuesta_json.get("token")
                return token
                
            else:
                raise ValueError("Error en la autenticación: " + respuesta_json.get("mensaje", "Sin mensaje de error."))
        else:
            raise ValueError(f"Error HTTP {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Error: {e}")