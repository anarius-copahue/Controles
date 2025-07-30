import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime       
import openpyxl

def main():
    st.set_page_config(page_title="Control SELL OUT/IN", layout="wide")
    st.title("Control SELL OUT/IN")

    # --- FILTROS EN LA PARTE SUPERIOR ---
    col1, col2 = st.columns(2)
    with col1:
        meses = st.radio("Seleccionar período móvil:", [3, 4, 6, 12], index=0, horizontal=True)
    with col2:
        tasa_crecimiento = (st.number_input("Tasa de crecimiento (%)", value=40) / 100)+1

    # --- CARGA DE DATOS ---
    df = pd.read_csv("data/SELL_IN_OUT.csv")
    df = df.rename(columns={"Unnamed: 0": "CADENA"})
    df["FECHA"] = pd.to_datetime(df["FECHA"], errors="coerce")
    df.dropna(subset=["FECHA", "CADENA"], inplace=True)
    df = df[df['CADENA'] != "PERFUMERÍAS PIGMENTO"]  # Excluir "PIGMENTO" de las cadenas
    df = df[df['CADENA'] != "FARMACIA DEL SIGLO"]  # Excluir "PIGMENTO" de las cadenas

    # --- DETERMINAR PERÍODOS ---
    fecha_ultima = df["FECHA"].max()
    fechas_actuales = pd.date_range(end=fecha_ultima, periods=meses, freq="MS")
    fechas_anio_ant = fechas_actuales - pd.DateOffset(years=1)
    mes_siguiente_fecha = fecha_ultima + pd.DateOffset(months=1)
    mes_siguiente_anio_anterior_fecha = mes_siguiente_fecha - pd.DateOffset(years=1)

    # --- FILTRAR POR PERÍODOS ---
    df["Periodo"] = df["FECHA"].dt.to_period("M")
    fechas_actuales_p = [f.to_period("M") for f in fechas_actuales]
    fechas_anio_ant_p = [f.to_period("M") for f in fechas_anio_ant]
    mes_siguiente_anio_anterior_p = mes_siguiente_anio_anterior_fecha.to_period("M")

    df_actual = df[df["Periodo"].isin(fechas_actuales_p)].copy()
    df_anterior = df[df["Periodo"].isin(fechas_anio_ant_p)].copy()
    df_siguiente_anio_anterior = df[df["Periodo"] == mes_siguiente_anio_anterior_p].copy()

    # --- AGREGAR ---
    def agg_periodo(df_, label):
        agg = df_.groupby("CADENA").agg({
            "SELL IN": ["sum", lambda x: x[x != 0].mean()],
            "SELL OUT": ["sum", lambda x: x[x != 0].mean()]
        })
        agg.columns = [
            f"SELL IN {label}",
            f"SELL IN promedio {label}",
            f"SELL OUT {label}",
            f"SELL OUT promedio {label}"
        ]
        return agg

    actual = agg_periodo(df_actual, f"{meses} últimos meses")
    anterior = agg_periodo(df_anterior, "mismo período año anterior")
    siguiente_sell_in = df_siguiente_anio_anterior.groupby("CADENA")["SELL IN"].sum().rename("SELL IN siguiente mes (año anterior)")

    resultado = actual.join(anterior, how="outer").join(siguiente_sell_in, how="outer").fillna(0)

    resultado["Variación vs año anterior (%)"] = np.where(
        resultado["SELL IN mismo período año anterior"] == 0,
        np.nan,
        ((resultado[f"SELL IN {meses} últimos meses"] / resultado["SELL IN mismo período año anterior"]) - 1) * 100
    )

    resultado["SELL OUT / SELL IN"] = np.where(
        resultado[f"SELL IN {meses} últimos meses"] == 0,
        np.nan,
        (resultado[f"SELL OUT {meses} últimos meses"] / resultado[f"SELL IN {meses} últimos meses"])*100
    )



    resultado["SELL IN estimado mes actual (crecimiento)"] = resultado[f"SELL IN promedio mismo período año anterior"] * (tasa_crecimiento)

    # --- UNIFICAR PREVENTAS Y VENTAS ---
    df_preventa = pd.read_csv("descargas/preventa_por_cliente.csv", sep="|")
    df_venta = pd.read_csv("descargas/ventas_netas_por_periodo_cliente.csv", sep="|")
    diccionario = pd.read_excel("data/diccionario.xlsx")
    mapa_cadenas = diccionario.set_index("N° CLIENTE")["CADENA"]

    df_preventa["CADENA"] = df_preventa["Clie"].map(mapa_cadenas)
    df_venta["CADENA"] = df_venta["Cliente"].map(mapa_cadenas)

    df_preventa["valor"] = df_preventa["Unidades"]
    df_venta["valor"] = df_venta["Venta Unid."] - df_venta["Unid. Bonif."]

    ventas_y_preventas = pd.concat([
        df_preventa[["CADENA", "valor"]],
        df_venta[["CADENA", "valor"]]
    ], ignore_index=True)

    ventas_totales = ventas_y_preventas.groupby("CADENA")["valor"].sum().reset_index()
    ventas_totales.rename(columns={"valor": "VENTA Y PREVENTA HASTA HOY"}, inplace=True)

    resultado = resultado.merge(ventas_totales, on="CADENA", how="left")
    resultado["FALTA"] = resultado["SELL IN estimado mes actual (crecimiento)"] - resultado["VENTA Y PREVENTA HASTA HOY"]



    st.subheader(f"Último mes disponible: {fecha_ultima.strftime('%B %Y')} | Período comparado: {fechas_actuales[0].strftime('%Y-%m')} a {fechas_actuales[-1].strftime('%Y-%m')}")

    # --- OPORTUNIDADES Y ALERTAS ---
    oportunidades = resultado[
        (resultado["Variación vs año anterior (%)"] > 40) &
        (resultado["FALTA"] > 50)
    ]

    alertas = resultado[
        (resultado["SELL OUT / SELL IN"] > 100)  &  (resultado["Variación vs año anterior (%)"] > 20)
    ]

    mensaje = ""
    if not oportunidades.empty:
        nombres_oportunidades = ", ".join(oportunidades["CADENA"].astype(str).tolist())
        mensaje += f"<span style='color:green; font-weight:bold;'>🟢 Oportunidades en: {nombres_oportunidades}</span><br>"

    if not alertas.empty:
        nombres_alertas = ", ".join(alertas["CADENA"].astype(str).tolist())
        mensaje += f"<span style='color:red; font-weight:bold;'>🔴 Alerta de quebrar stock en: {nombres_alertas}</span><br>"

    if mensaje == "":
        mensaje = "<span style='color:gray;'>Sin oportunidades ni alertas destacadas.</span>"

    st.markdown(mensaje, unsafe_allow_html=True)

    # --- COLOREO ---
    def highlight_variacion(val):
        if pd.isna(val): return ""
        elif val > 40: return "background-color: #66ff66"
        elif val > 20: return "background-color: #ccffcc"
        elif val > 0: return "background-color: #ffe0b3"
        elif val > -10: return "background-color: #ffcccc"
        else: return "background-color: #ff6666"

    # --- LIMPIEZA ---
    columnas_a_eliminar = [
        f"SELL IN {meses} últimos meses", f"SELL OUT {meses} últimos meses",
        'SELL IN mismo período año anterior', 'SELL OUT mismo período año anterior',
        "SELL IN siguiente mes (año anterior)","SELL OUT promedio mismo período año anterior",
    ]
    resultado.drop(columns=[col for col in columnas_a_eliminar if col in resultado.columns], inplace=True)

    # --- FORMATEO FINAL ---
    formato_columnas = {
        f"SELL IN {meses} últimos meses": lambda x: f"{int(x):,}".replace(",", ".") if pd.notnull(x) else "",
        f"SELL OUT {meses} últimos meses": lambda x: f"{int(x):,}".replace(",", ".") if pd.notnull(x) else "",
        f"SELL IN promedio {meses} últimos meses": lambda x: f"{int(x):,}".replace(",", ".") if pd.notnull(x) else "",

        f"SELL IN promedio mismo período año anterior": lambda x: f"{int(x):,}".replace(",", ".") if pd.notnull(x) else "",
        f"SELL OUT promedio {meses} últimos meses": lambda x: f"{int(x):,}".replace(",", ".") if pd.notnull(x) else "",
        "SELL IN estimado mes actual (crecimiento)": lambda x: f"{int(x):,}".replace(",", ".") if pd.notnull(x) else "",
        "VENTA Y PREVENTA HASTA HOY": lambda x: f"{int(x):,}".replace(",", ".") if pd.notnull(x) else "",
        "Variación vs año anterior (%)": lambda x: f"{int(x):,}%" if pd.notnull(x) else "",
        "SELL OUT / SELL IN": lambda x: f"{int(x):,}%" if pd.notnull(x) else "",
        "FALTA": lambda x: f"{int(x):,}".replace(",", ".") if pd.notnull(x) else ""
    }

    # --- MOSTRAR ---
    st.dataframe(
        resultado.style
            .format(formato_columnas)
            .applymap(highlight_variacion, subset=["Variación vs año anterior (%)"]),
        use_container_width=True
    )
