import streamlit as st
import pandas as pd
import numpy as np
import io
import datetime
import os

FARMACIA_POR_USUARIO = {
    "KMACIAS" : ["FARMACIA BELEN","DUTY PAID","CENTRAL OESTE","LA FRANCO","FARMACITY","FARMAPLUS"],
    "SROCCHI" :  ["SELMA","VASALLO","FARMATODO","FARMANOI"],
    "PZACCA" : ["SALVADO","FARMAQUEN (Global)","MEDIVEN","FARMACIAS PATAGONICAS (FARMA SRL)"],
    "MROSSELOT" : ["RED PERSCE","FARMACIA GENERAL PAZ","FARMACIA LÍDER","MAR JUFEC","FARMALIFE"],
    "AFLEBA" : ["FARMASHOP","FARMACIA ZENTNER","FARMAVIP"],
    "YCUEZZO" : ["BRADEL DEL PUEBLO","SAN FRANCISCO SALTA"],
    "YARRECHE" : ["ZORICH","SOY TU FARMACIA","PUNTO DE SALUD","FARMACIA MANES","VIDELA"],
    "EVEIGA" : ["RIADIGOS"],
    "JANDERMARCH" : [ ],
    "NBRIDI": ["TKL"]
}

def ventas(representantes=[]):

    st.title("Control SELL OUT/IN")

    # --- FILTROS EN LA PARTE SUPERIOR ---
    col1, col2 = st.columns(2)
    with col1:
        meses = st.radio("Seleccionar período móvil:", [1, 3, 4, 6, 12], index=0, horizontal=True)
    with col2:
        tasa_crecimiento = (st.number_input("Tasa de crecimiento (%)", value=40) / 100)+1

    # --- CARGA DE DATOS ---
    df = pd.read_csv("data/SELL_IN_OUT.csv")
    df = df.rename(columns={"Unnamed: 0": "CADENA"})
    df["FECHA"] = pd.to_datetime(df["FECHA"], errors="coerce")
    df.dropna(subset=["FECHA", "CADENA"], inplace=True)

    # Lista de farmacias según el representante
    lista = []
    if not representantes:
        representantes = FARMACIA_POR_USUARIO.keys()

    for usuario, farmacias in FARMACIA_POR_USUARIO.items():
        if usuario in representantes:
            lista.extend(farmacias)

    df = df[df['CADENA'].isin(lista)]  # Filtrar por representante
    df = df.rename(columns={
        "SELL IN": "IN",
        "SELL OUT": "OUT"
    })
    
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
            "IN": ["sum", lambda x: x[x != 0].mean()],
            "OUT": ["sum", lambda x: x[x != 0].mean()]
        })
        agg.columns = [
            f"IN {label}",
            f"IN promedio {label}",
            f"OUT {label}",
            f"OUT promedio {label}"
        ]
        return agg

    actual = agg_periodo(df_actual, f"{meses} meses")
    anterior = agg_periodo(df_anterior, "MP AA")
    siguiente_sell_in = df_siguiente_anio_anterior.groupby("CADENA")["IN"].sum().rename("IN siguiente mes (AA)")

    resultado = actual.join(anterior, how="outer").join(siguiente_sell_in, how="outer").fillna(0)

    resultado["Variación vs AA"] = np.where(
        resultado["IN MP AA"] == 0,
        np.nan,
        ((resultado[f"IN {meses} meses"] / resultado["IN MP AA"]) - 1) * 100
    )

    resultado["OUT / IN"] = np.where(
        resultado[f"IN {meses} meses"] == 0,
        np.nan,
        (resultado[f"OUT {meses} meses"] / resultado[f"IN {meses} meses"])*100
    )

    resultado["IN estimado mes actual (crecimiento)"] = resultado[f"IN promedio MP AA"] * (tasa_crecimiento)

    # --- UNIFICAR PREVENTAS Y VENTAS ---
    df_preventa = pd.read_csv("descargas/preventa_por_cliente.csv", sep="|")
    df_venta = pd.read_csv("descargas/venta_neta_por_periodo_producto_cliente.csv", sep="|")
    diccionario = pd.read_excel("data/diccionario.xlsx")
    diccionario = diccionario.drop_duplicates(subset=["N° CLIENTE"])
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
    ventas_totales.rename(columns={"valor": "VENTA Y PREVENTA A HOY"}, inplace=True)

    resultado = resultado.merge(ventas_totales, on="CADENA", how="left").fillna(0)
    resultado["FALTA"] = resultado["IN estimado mes actual (crecimiento)"] - resultado["VENTA Y PREVENTA A HOY"]

    st.subheader(f"Mes disponible: {fecha_ultima.strftime('%B %Y')} | Período: {fechas_actuales[0].strftime('%Y-%m')} a {fechas_actuales[-1].strftime('%Y-%m')}")

    # --- OPORTUNIDADES Y ALERTAS ---
    oportunidades = resultado[
        (resultado["Variación vs AA"] > 40) &
        (resultado["FALTA"] > 50)
    ]

    alertas = resultado[
        (resultado["OUT / IN"] > 100)  &  (resultado["Variación vs AA"] > 20)
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

    # --- LIMPIEZA ---
    columnas_a_eliminar = [
        f"IN {meses} meses", f"OUT {meses} meses",
        'IN MP AA', 'OUT MP AA',
        "IN siguiente mes (AA)","OUT promedio MP AA",
    ]
    resultado.drop(columns=[col for col in columnas_a_eliminar if col in resultado.columns], inplace=True)

    # --- BUSCADOR Y ORDENAMIENTO ---
    busqueda = st.text_input("🔍 Buscar cadena de farmacia:", "")
    
    if busqueda:
        resultado_filtrado = resultado[resultado["CADENA"].str.contains(busqueda, case=False, na=False)].copy()
    else:
        resultado_filtrado = resultado.copy()

    # >>> AJUSTE SOLICITADO: Ordenar por mayor Sell In promedio <<<
    col_orden = f"IN promedio {meses} meses"
    if col_orden in resultado_filtrado.columns:
        resultado_filtrado = resultado_filtrado.sort_values(by=col_orden, ascending=False)

    # --- AGREGAR FILA DE TOTALES ---
    totales = resultado_filtrado.drop(columns=["CADENA"], errors="ignore").sum(numeric_only=True)
    totales["CADENA"] = "TOTAL"
    resultado_con_totales = pd.concat([resultado_filtrado, pd.DataFrame([totales])], ignore_index=True)

    # --- FORMATEO Y ESTILOS ---
    formato_columnas = {
        f"IN promedio {meses} meses": lambda x: f"{int(x):,}".replace(",", ".") if pd.notnull(x) and x != "" else "",
        f"IN promedio MP AA": lambda x: f"{int(x):,}".replace(",", ".") if pd.notnull(x) and x != "" else "",
        f"OUT promedio {meses} meses": lambda x: f"{int(x):,}".replace(",", ".") if pd.notnull(x) and x != "" else "",
        "IN estimado mes actual (crecimiento)": lambda x: f"{int(x):,}".replace(",", ".") if pd.notnull(x) and x != "" else "",
        "VENTA Y PREVENTA A HOY": lambda x: f"{int(x):,}".replace(",", ".") if pd.notnull(x) and x != "" else "",
        "Variación vs AA": lambda x: f"{int(x):,}%" if pd.notnull(x) and x != "" else "",
        "OUT / IN": lambda x: f"{int(x):,}%" if pd.notnull(x) and x != "" else "",
        "FALTA": lambda x: f"{int(x):,}".replace(",", ".") if pd.notnull(x) and x != "" else ""
    }

    def highlight_variacion(val):
        if pd.isna(val) or val == "": return ""
        elif val > 40: return "background-color: #66ff66"
        elif val > 20: return "background-color: #ccffcc"
        elif val > 0: return "background-color: #ffe0b3"
        elif val > -10: return "background-color: #ffcccc"
        else: return "background-color: #ff6666"

    st.markdown("""
    <style>
        table { width: 100%; table-layout: auto; }
        th { white-space: nowrap; text-align: center; font-size: 14px; }
        td { white-space: nowrap; font-size: 13px; }
    </style>
    """, unsafe_allow_html=True)

    styled_df = (
        resultado_con_totales.style
        .format(formato_columnas)
        .map(highlight_variacion, subset=["Variación vs AA"])
        .hide(axis="index")
        .apply(
            lambda row: ["font-weight: bold;" if row["CADENA"] == "TOTAL" else "" for _ in row],
            axis=1
        )
    )

    st.markdown(styled_df.to_html(), unsafe_allow_html=True)

    # --- EXCEL ---
    def to_excel(df_ex: pd.DataFrame):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df_ex.to_excel(writer, index=False, sheet_name="Reporte")
        output.seek(0)
        return output

    excel_file = to_excel(resultado_con_totales)
    st.download_button(
        label="📥 Descargar Excel",
        data=excel_file,
        file_name="reporte_sell_in_out.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )