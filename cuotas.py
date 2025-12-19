import streamlit as st
import pandas as pd
import numpy as np
import io


REPRESENTANTE_POR_USUARIO = {
        
        "SROCCHI": ["Zona Norte"],
        "PZACCA": ["Patricia Zacca"],
        "MROSSELOT": ["Marcela Rosselot"],
        "LCOLOMBO": ["Lucio Colombo"],
        "YCUEZZO": ["Yanina Cuezzo"],
        "YARRECHE": ["Yamila Arreche"],
        "EVEIGA": ["Emiliano Veiga"],
        "JANDERMARCH": ["Jessica Andermarch"],
        "NBRIDI":["Natalia Bridi"],
        "OTROS" : [ "Gerencia" ],
}

def cuotas(representantes=[]):

    archivo_excel = "data/representante.xlsx"

    df_venta = pd.read_csv("descargas/preventa_por_cliente.csv", sep="|")
    
    # Calcular valor
    df_venta["Caviahue"] = df_venta["Unidades"]
    df_venta["Mizu"] = 0
    df_venta = df_venta.rename(columns={"Clie": "Cliente"})

    # Cargar archivo de preventa
    df_preventa = pd.read_csv("descargas/venta_neta_por_periodo_producto_cliente.csv", sep="|")

    # Limpieza de valores
    def limpiar_valor(valor):
        if pd.isna(valor):
            return 0
        valor = str(valor).replace('$', '').replace(' ', '')
        valor = valor.replace('.', '')
        valor = valor.replace(',', '.')
        return float(valor)
    
    df_preventa["Venta Bruta"] = df_preventa["Venta Bruta"].apply(limpiar_valor)
    df_preventa["Dtos. en Factura"] = df_preventa["Dtos. en Factura"].apply(limpiar_valor)

    # Bonificación
    df_preventa["venta_bonificada"] = np.isclose(
        df_preventa["Venta Bruta"],
        df_preventa["Dtos. en Factura"],
        atol=2
    )

    df_preventa["Venta Unid."] = np.where(
        df_preventa["venta_bonificada"],
        0,
        df_preventa["Venta Unid."]
    )

    # Clasificar productos PREVENTA
    df_preventa["Mizu"] = np.where(
        df_preventa['PRODU.'].isin([21304, 21302]),
        df_preventa["Venta Unid."],
        0
    )

    df_preventa["Caviahue"] = np.where(
        ~df_preventa['PRODU.'].isin([21304, 21302]),
        df_preventa["Venta Unid."],
        0
    )

    # Despaconar PREVENTA
    df_preventa["Caviahue"] = np.where(
        df_preventa['PRODU.'].isin([22005,21663,22251,21657,21655,21658]),
        df_preventa["Caviahue"] * 3,
        df_preventa["Caviahue"]
    )

    df_preventa["Caviahue"] = np.where(
        df_preventa['PRODU.'].isin([21653]),
        df_preventa["Caviahue"] * 2,
        df_preventa["Caviahue"]
    )

    df_preventa["Caviahue"] = np.where(
        df_preventa['PRODU.'].isin([21656]),
        df_preventa["Caviahue"] * 4,
        df_preventa["Caviahue"]
    )

    # ==========================================================
    # =====================   TANGO   ==========================
    # ==========================================================
    #SI EXISTE ARCHIVO TANGO CARGARLO Y PROCESARLO, SINO IGNORAR
try:
    df_tango = pd.read_excel("data/TANGO.xls", sheet_name="Datos")

    df_tango = df_tango.rename(columns={
        "COD_CLI": "Cliente",
        "COD_ARTICU": "PRODU.",
        "CANTIDAD": "Venta Unid."
    })

    df_tango["Mizu"] = np.where(
        df_tango["PRODU."].isin([21304, 21302]),
        df_tango["Venta Unid."],
        0
    )

    df_tango["Caviahue"] = np.where(
        ~df_tango["PRODU."].isin([21304, 21302]),
        df_tango["Venta Unid."],
        0
    )

    # Despaconar TANGO
    df_tango["Caviahue"] = np.where(
        df_tango['PRODU.'].isin([22005,21663,22251,21657,21655,21658]),
        df_tango["Caviahue"] * 3,
        df_tango["Caviahue"]
    )

    df_tango["Caviahue"] = np.where(
        df_tango['PRODU.'].isin([21653]),
        df_tango["Caviahue"] * 2,
        df_tango["Caviahue"]
    )

    df_tango["Caviahue"] = np.where(
        df_tango['PRODU.'].isin([21656]),
        df_tango["Caviahue"] * 4,
        df_tango["Caviahue"]
    )

    df_tango = df_tango[["Cliente", "Caviahue", "Mizu"]]

except FileNotFoundError:
    # DataFrame vacío PERO con columnas correctas
    df_tango = pd.DataFrame(columns=["Cliente", "Caviahue", "Mizu"])


    # ==========================================================
    # =============== UNIFICAR TODAS LAS FUENTES ===============
    # ==========================================================

    df_preventa = pd.concat([
        df_preventa[["Cliente", "Caviahue", "Mizu"]],
        df_venta[["Cliente", "Caviahue", "Mizu"]],
        df_tango[["Cliente", "Caviahue", "Mizu"]]
    ], ignore_index=True)

    # Agrupar totales por cliente
    totales_caviahue = df_preventa.groupby("Cliente")["Caviahue"].sum().reset_index()
    totales_caviahue.rename(columns={"Caviahue": "Total Caviahue"}, inplace=True)

    totales_mizu = df_preventa.groupby("Cliente")["Mizu"].sum().reset_index()
    totales_mizu.rename(columns={"Mizu": "Total Mizu"}, inplace=True)

    ventas_totales_cliente = pd.merge(totales_caviahue, totales_mizu, on="Cliente", how="outer")

    # ==========================================================
    # ============ EL RESTO DEL CÓDIGO ES IGUAL ===============
    # ==========================================================

    # Lista de hojas esperadas
    lista_representantes = []
    if not representantes:
        representantes = REPRESENTANTE_POR_USUARIO.keys()

    for usuario, nombres in REPRESENTANTE_POR_USUARIO.items():
        if usuario in representantes:
            lista_representantes.extend(nombres)
            
    hojas_representantes = {
        nombre: pd.read_excel(archivo_excel, sheet_name=nombre)
        for nombre in lista_representantes
    }

    # Incorporar totales en cada hoja
    for nombre, df in hojas_representantes.items():
        df_actualizado = df.drop(columns=["Total Caviahue", "Total Mizu"], errors="ignore").merge(
            ventas_totales_cliente[["Cliente", "Total Caviahue", "Total Mizu"]],
            left_on="N° CLIENTE",
            right_on="Cliente",
            how="left"
        ).drop(columns=["Cliente"], errors="ignore")

        df_actualizado[["Total Caviahue", "Total Mizu"]] = df_actualizado[["Total Caviahue", "Total Mizu"]].fillna(0)

        cols = df_actualizado.columns.tolist()
        for col in ["Total Caviahue", "Total Mizu"]:
            if col in cols:
                cols.insert(3, cols.pop(cols.index(col)))

        df_actualizado = df_actualizado[cols]
        hojas_representantes[nombre] = df_actualizado

    # Totales dentro de cada hoja
    for nombre, df in hojas_representantes.items():
        df = df.copy()
        
        total_rows = df["CLIENTE"].str.contains("TOTAL", case=False, na=False)
        group_id = total_rows.cumsum()

        for g in group_id[total_rows].unique():
            group_mask = group_id == g
            total_row_idx = df[group_mask & total_rows].index[0]
            children_mask = group_mask & (~total_rows)

            for col in ["Cuota Caviahue", "Total Caviahue", "Cuota Mizu", "Total Mizu"]:
                if col in df.columns:
                    df.loc[total_row_idx, col] = df.loc[children_mask, col].sum(skipna=True)

        hojas_representantes[nombre] = df

    # Porcentajes
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

        df["% Caviahue"] = df["% Caviahue"].replace([np.inf, -np.inf], 0).fillna(0).round(2)
        df["% Mizu"] = df["% Mizu"].replace([np.inf, -np.inf], 0).fillna(0).round(2)

        nuevo_orden = ["N° CLIENTE", "CLIENTE", "Cuota Caviahue", "Total Caviahue","% Caviahue",
                       "Cuota Mizu", "Total Mizu", "% Mizu"]

        df = df[nuevo_orden]

        hojas_representantes[nombre] = df

    st.set_page_config(page_title="Control Cuota", layout="wide")
    st.title("Reporte de Representantes")
    
    resumen = pd.DataFrame({
        "Representante": list(hojas_representantes.keys()),

        "Cuota Caviahue": [
            df[~df["CLIENTE"].str.contains("TOTAL", case=False, na=False)]["Cuota Caviahue"].sum(skipna=True)
            for df in hojas_representantes.values()
        ],

        "Total Caviahue": [
            df[df["N° CLIENTE"].notna()]["Total Caviahue"].sum(skipna=True)
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

    resumen["% Caviahue"] = ((resumen["Total Caviahue"] / resumen["Cuota Caviahue"]) * 100).fillna(0)
    resumen["% Mizu"] = ((resumen["Total Mizu"] / resumen["Cuota Mizu"]) * 100).fillna(0)

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

        cols[1].markdown(f"{fila['Representante']}")
        cols[2].markdown(f"{int(fila['Cuota Caviahue'])}")
        cols[3].markdown(f"{int(fila['Total Caviahue'])}")
        cols[4].markdown(f"{fila['% Caviahue']:.2f}%")
        cols[5].markdown(f"{int(fila['Cuota Mizu'])}")
        cols[6].markdown(f"{int(fila['Total Mizu'])}")
        cols[7].markdown(f"{fila['% Mizu']:.2f}%")

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

        def to_excel(df: pd.DataFrame) -> bytes:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Reporte")
            return output.getvalue()

        excel_file = to_excel(df)

        st.download_button(
            label="📥 Descargar Excel",
            data=excel_file,
            file_name=f"reporte_{fila['Representante']}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"download_{i}"
        )
