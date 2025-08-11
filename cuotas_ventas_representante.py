import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime       
import openpyxl

FARMACIA_POR_USUARIO = {
"KMACIAS" : ["BELEN","DUTY PAID","CENTRAL OESTE","LA FRANCO","FARMACITY"],
"EPIEGARI" : ["SELMA","VASALLO","FARMATODO"],
"PZACCA" : ["SALVADO","FARMAQUEN GLOBAL (Farmaquen)","MEDIVEN","FARMACIAS PATAGONICAS (FARMA SRL)"],
"MROSSELOT" : ["RED PERSCE","FARMACIA GENERAL PAZ","FARMACIA LIDER","FARMAR","FARMALIFE"],
"LCOLOMBO" : ["FARMASHOP","FARMACIA DEL SIGLO","FARMACIA ZENTNER","FARMAVIP"],
"YCUEZZO" : ["BRADEL DEL PUEBLO","FARMACIA SAN FRANCISCO SALTA"],
"YARRECHE" : ["GRUPO ZORICH","SOY TU FARMACIA","PUNTO DE SALUD","FARMACIA MANES","VIDELA"],
"EVEIGA" : ["RADIGOS"],
"JANDERMARCH" : [ ],
"LLAGUNA" : [],
}

REPRESENTANTE_POR_USUARIO = {
        "KMACIAS": ["Karina Macías", "Karina Perfu y Supermercados"],
        "EPIEGARI": ["Esteban Piegari"],
        "PZACCA": ["Patricia Zacca"],
        "MROSSELOT": ["Marcela Rosselot"],
        "LCOLOMBO": ["Lucio Colombo"],
        "YCUEZZO": ["Yanina Cuezzo"],
        "YARRECHE": ["Yamila Arreche"],
        "EVEIGA": ["Emiliano Veiga"],
        "JANDERMARCH": ["Jessica Andermarch"],
        "LLAGUNA": ["Luciano Laguna"]
}

REPRESENTANTE_mapa= {
        "KMACIAS": "mapa_ventas_KARINA.html",
        "EPIEGARI": "mapa_ventas_ESTEBAN.html",
        "PZACCA": "mapa_ventas_PATRICA.html",
        "MROSSELOT": "mapa_ventas_MARCELA.html",
        "LCOLOMBO": "mapa_ventas_LUCIO.html",
        "YCUEZZO": "mapa_ventas_YANINA.html",
        "YARRECHE": "mapa_ventas_YAMILA.html",
        "EVEIGA": "mapa_ventas_EMILIANO.html",
        "JANDERMARCH": "mapa_ventas_JESSICA.html",
        "LLAGUNA": "mapa_ventas_LUCIANO.html"
}


def ventas(representante):
    st.set_page_config(page_title="Control SELL OUT/IN", layout="wide")
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
    lista = FARMACIA_POR_USUARIO.get(representante, [])
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
    ventas_totales.rename(columns={"valor": "VENTA Y PREVENTA A HOY"}, inplace=True)

    resultado = resultado.merge(ventas_totales, on="CADENA", how="left")
    resultado["FALTA"] = resultado["IN estimado mes actual (crecimiento)"] - resultado["VENTA Y PREVENTA A HOY"]



    st.subheader(f"mes disponible: {fecha_ultima.strftime('%B %Y')} | Período comparado: {fechas_actuales[0].strftime('%Y-%m')} a {fechas_actuales[-1].strftime('%Y-%m')}")

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
        f"IN {meses} meses", f"OUT {meses} meses",
        'IN MP AA', 'OUT MP AA',
        "IN siguiente mes (AA)","OUT promedio MP AA",
    ]
    resultado.drop(columns=[col for col in columnas_a_eliminar if col in resultado.columns], inplace=True)

    # --- FORMATEO FINAL ---
    formato_columnas = {
        f"IN {meses} meses": lambda x: f"{int(x):,}".replace(",", ".") if pd.notnull(x) else "",
        f"OUT {meses} meses": lambda x: f"{int(x):,}".replace(",", ".") if pd.notnull(x) else "",
        f"IN promedio {meses} meses": lambda x: f"{int(x):,}".replace(",", ".") if pd.notnull(x) else "",

        f"IN promedio MP AA": lambda x: f"{int(x):,}".replace(",", ".") if pd.notnull(x) else "",
        f"OUT promedio {meses} meses": lambda x: f"{int(x):,}".replace(",", ".") if pd.notnull(x) else "",
        "IN estimado mes actual (crecimiento)": lambda x: f"{int(x):,}".replace(",", ".") if pd.notnull(x) else "",
        "VENTA Y PREVENTA A HOY": lambda x: f"{int(x):,}".replace(",", ".") if pd.notnull(x) else "",
        "Variación vs AA": lambda x: f"{int(x):,}%" if pd.notnull(x) else "",
        "OUT / IN": lambda x: f"{int(x):,}%" if pd.notnull(x) else "",
        "FALTA": lambda x: f"{int(x):,}".replace(",", ".") if pd.notnull(x) else ""
    }

        # --- BUSCADOR DE CADENAS ---
    busqueda = st.text_input("🔍 Buscar cadena de farmacia:", "")

    if busqueda:
        resultado_filtrado = resultado[resultado["CADENA"].str.contains(busqueda, case=False, na=False)]
    else:
        resultado_filtrado = resultado

    st.markdown("""
        <style>
            table {
                width: 100%;
                table-layout: auto;
            }
            th {
                white-space: nowrap;
                text-align: center;
                font-size: 14px;
            }
            td {
                white-space: nowrap;
                font-size: 13px;
            }
        </style>
    """, unsafe_allow_html=True)


    # --- MOSTRAR ---
    styled_df = (
        resultado_filtrado.style
            .format(formato_columnas)
            .applymap(highlight_variacion, subset=["Variación vs AA"])
            .hide(axis="index")
    )

    st.markdown(styled_df.to_html(), unsafe_allow_html=True)

def cuotas(representante):
    archivo_excel = "data/representante.xlsx"

    df_venta = pd.read_csv("descargas/preventa_por_cliente.csv", sep="|")
    
        # Calcular valor
    df_venta["Caviahue"] = df_venta["Unidades"]
    df_venta["Mizu"] = 0
    df_venta = df_venta.rename(columns={"Clie": "Cliente"})

    # Cargar archivo de preventa
    df_preventa = pd.read_csv("descargas/venta_neta_por_periodo_producto_cliente.csv", sep="|")

    # Clasificar productos
    df_preventa["Mizu"] = np.where(
        df_preventa['Descripción'].isin([
            'MIZU COLAGENO PLUS LIMON',
            'F/L-COLAGENO HIDROLIZADO CLASICO - PIEL- MIZU',
            "MIZU ARTRO FLEX"
        ]),
        df_preventa["Venta Unid."],
        0
    )

    df_preventa["Caviahue"] = np.where(
        ~df_preventa['Descripción'].isin([
            'MIZU COLAGENO PLUS LIMON',
            'F/L-COLAGENO HIDROLIZADO CLASICO - PIEL- MIZU',
            "MIZU ARTRO FLEX"
        ]),
        df_preventa["Venta Unid."],
        0
    )

    #Despaconar
    df_preventa["Caviahue"] =  np.where(
        df_preventa['PRODU.'].isin(['22005','21663','22251','21657','21655','21658'
        ]),
        df_preventa["Caviahue"] *3,
        df_preventa["Caviahue"]
    )

    df_preventa["Caviahue"] =  np.where(
        df_preventa['PRODU.'].isin(['21653'    ]),    df_preventa["Caviahue"] *2,
        df_preventa["Caviahue"]
    )

    df_preventa["Caviahue"] =  np.where(
        df_preventa['PRODU.'].isin(['21656'   ]),    df_preventa["Caviahue"] *4,
        df_preventa["Caviahue"]
    )

    # Unificar ventas y calcular totales por cliente
    df_preventa = pd.concat([
            df_preventa[["Cliente", "Caviahue", "Mizu"]],
            df_venta[["Cliente", "Caviahue", "Mizu"]]
        ], ignore_index=True)

    # Agrupar totales por cliente
    totales_caviahue = df_preventa.groupby("Cliente")["Caviahue"].sum().reset_index()
    totales_caviahue.rename(columns={"Caviahue": "Total Caviahue"}, inplace=True)

    totales_mizu = df_preventa.groupby("Cliente")["Mizu"].sum().reset_index()
    totales_mizu.rename(columns={"Mizu": "Total Mizu"}, inplace=True)

    # Unir los totales en un solo DataFrame
    ventas_totales_cliente = pd.merge(totales_caviahue, totales_mizu, on="Cliente", how="outer")

    # Lista de hojas esperadas
    lista_representantes = REPRESENTANTE_POR_USUARIO.get(representante, [])

    # Cargar hojas del Excel
    hojas_representantes = {
        nombre: pd.read_excel(archivo_excel, sheet_name=nombre)
        for nombre in lista_representantes
    }

    # Incorporar los totales a cada hoja
    for nombre, df in hojas_representantes.items():
        df_actualizado = df.drop(columns=["Total Caviahue", "Total Mizu"], errors="ignore").merge(
            ventas_totales_cliente[["Cliente", "Total Caviahue", "Total Mizu"]],
            left_on="N° CLIENTE",
            right_on="Cliente",
            how="left"
        ).drop(columns=["Cliente"], errors="ignore")

        df_actualizado[["Total Caviahue", "Total Mizu"]] = df_actualizado[["Total Caviahue", "Total Mizu"]].fillna(0)

        # Reordenar columnas si es necesario (ejemplo: mover total_caviahue detrás de 'N° CLIENTE')
        cols = df_actualizado.columns.tolist()
        for col in ["Total Caviahue", "Total Mizu"]:
            if col in cols:
                cols.insert(3, cols.pop(cols.index(col)))
        df_actualizado = df_actualizado[cols]
    

        hojas_representantes[nombre] = df_actualizado


        # Calcular cuota para totales dentro de cada hoja
    for nombre, df in hojas_representantes.items():
        df = df.copy()
        
            # Search for clientes that have TOTAL in their name
        total_rows = df["CLIENTE"].str.contains("TOTAL", case=False, na=False)
        group_id = total_rows.cumsum()

        for g in group_id[total_rows].unique():
                # Get mask for this block
            group_mask = group_id == g
            total_row_idx = df[group_mask & total_rows].index[0]
            children_mask = group_mask & (~total_rows)

                # Sum numeric columns in children and assign to the total row
            for col in ["Cuota Caviahue", "Total Caviahue", "Cuota Mizu", "Total Mizu"]:
                if col in df.columns:
                    df.loc[total_row_idx, col] = df.loc[children_mask, col].sum(skipna=True)

            # Save updated version
        hojas_representantes[nombre] = df

        # Calcular porcentajes de Caviahue y Mizu
    for nombre, df in hojas_representantes.items():
        df = df.copy()

        df["% Caviahue"] = (
                pd.to_numeric(df.get("Total Caviahue"), errors="coerce") /
                pd.to_numeric(df.get("Cuota Caviahue"), errors="coerce") 
            ) * 100

        df["% Mizu"] = (
                pd.to_numeric(df.get("Total Mizu"), errors="coerce") /
                pd.to_numeric(df.get("Cuota Mizu"), errors="coerce")
            ) * 100

            # Limpiar y redondear
        df["% Caviahue"] = df["% Caviahue"].replace([np.inf, -np.inf], 0).fillna(0).round(2)
        df["% Mizu"] = df["% Mizu"].replace([np.inf, -np.inf], 0).fillna(0).round(2)

        nuevo_orden = ["N° CLIENTE", "CLIENTE", "Cuota Caviahue", "Total Caviahue","% Caviahue","Cuota Mizu", "Total Mizu", "% Mizu"]
        df = df[nuevo_orden]

        hojas_representantes[nombre] = df

    st.set_page_config(page_title="Control Cuota", layout="wide")
    st.title("Reporte de Representantes")
    
    resumen = pd.DataFrame({
            "Representante": list(hojas_representantes.keys()),

            "Cuota Caviahue": [
                df[df["N° CLIENTE"].notna()]["Cuota Caviahue"].sum(skipna=True)
                for df in hojas_representantes.values()
            ],

            "Total Caviahue": [
                df[df["N° CLIENTE"].notna()]["Total Caviahue"].sum(skipna=True)
                if "Total Caviahue" in df.columns else 0
                for df in hojas_representantes.values()
            ],

            "Cuota Mizu": [
                df[df["N° CLIENTE"].notna()]["Cuota Mizu"].sum(skipna=True)
                for df in hojas_representantes.values()
            ],

            "Total Mizu": [
                df[df["N° CLIENTE"].notna()]["Total Mizu"].sum(skipna=True)
                for df in hojas_representantes.values()
            ],
        })

        # Calculate percentages manually from the two columns
    resumen["% Caviahue"] = (
            (resumen["Total Caviahue"] / resumen["Cuota Caviahue"]) * 100
        ).fillna(0)


    resumen["% Mizu"] = (
            (resumen["Total Mizu"] / resumen["Cuota Mizu"]) * 100
        ).fillna(0)

        # Actualizar valores de totales por cada representante
    total_general_caviahue = resumen["Total Caviahue"].sum(skipna=True)
    st.markdown(f"<h2 style='color: #3A7CA5;'>Total Caviahue General: {int(total_general_caviahue)}</h2>", unsafe_allow_html=True)

    st.write("Resumen de cuotas y totales por representante:")
    header_cols = st.columns([2, 3, 3, 3, 3, 3, 2, 2])
    header_cols[0].write("")
    header_cols[1].markdown("### Representante")
    header_cols[2].markdown("### Cuota Caviahue")
    header_cols[3].markdown("### Total Caviahue")
    header_cols[4].markdown("### % Caviahue")
    header_cols[5].markdown("### Cuota Mizu")
    header_cols[6].markdown("### Total Mizu")
    header_cols[7].markdown("### % Mizu")

    for i, fila in resumen.iterrows():
        key_expand = f"expandir_{i}"
        if key_expand not in st.session_state:
            st.session_state[key_expand] = False

        cols = st.columns([2, 3, 3, 3, 3, 3, 2, 2])

        with cols[0]:
            if st.button("➖" if st.session_state[key_expand] else "➕", key=f"boton_{i}"):
                st.session_state[key_expand] = not st.session_state[key_expand]

            # Asegurate que TODAS las celdas usen el mismo fondo condicional
        cols[1].markdown(f"{fila['Representante']}</div>", unsafe_allow_html=True)
        cols[2].markdown(f"{int(fila['Cuota Caviahue'])}</div>", unsafe_allow_html=True)
        cols[3].markdown(f"{int(fila['Total Caviahue'])}</div>", unsafe_allow_html=True)
        cols[4].markdown(f"{fila['% Caviahue']:.2f}%</div>", unsafe_allow_html=True)
        cols[5].markdown(f"{int(fila['Cuota Mizu'])}</div>", unsafe_allow_html=True)
        cols[6].markdown(f"{int(fila['Total Mizu'])}</div>", unsafe_allow_html=True)
        cols[7].markdown(f"{fila['% Mizu']:.2f}%</div>", unsafe_allow_html=True)

        if st.session_state[key_expand]:
            st.markdown(f"#### Detalle de {fila['Representante']}")
            df = hojas_representantes[fila["Representante"]].copy()
                
            def resaltar_total(row):
                if str(row["CLIENTE"]).strip().upper().startswith("TOTAL"):
                    return ["background-color: #f0f0f0"] * len(row)
                else:
                    return [""] * len(row)
        
            st.dataframe(df.style.apply(resaltar_total, axis=1).format(precision=0), use_container_width=True)
                
        st.markdown("---")

        import streamlit as st

    # Cargar el archivo HTML
    mapa_html = REPRESENTANTE_mapa.get(representante)
    with open(f"mapa por representante/{mapa_html}", "r", encoding="utf-8") as f:
        mapa_html = f.read()

    # Mostrar el mapa en Streamlit
    st.components.v1.html(mapa_html, height=600, scrolling=True)


def main(representante):
    ventas(representante)
    cuotas(representante)