import streamlit as st
import pandas as pd
import numpy as np
import io


REPRESENTANTE_POR_USUARIO = {
        "KMACIAS": ["Karina Macías", "Karina Perfu y Supermercados"],
        "SROCCHI": ["Zona Norte"],
        "PZACCA": ["Patricia Zacca"],
        "MROSSELOT": ["Marcela Rosselot"],
        "LCOLOMBO": ["Lucio Colombo"],
        "YCUEZZO": ["Yanina Cuezzo"],
        "YARRECHE": ["Yamila Arreche"],
        "EVEIGA": ["Emiliano Veiga"],
        "JANDERMARCH": ["Jessica Andermarch"],
        "NBRIDI":["Natalia Bridi"],
        "OTROS" : ["Vacante", "Gerencia" ],
}

def cuotas(representantes=[]):
    """
    args:
        representantes: Lista de representantes a incluir en el reporte. Si es None, se incluyen todos los representantes.
    """
    archivo_excel = "data/representante.xlsx"

    df_venta = pd.read_csv("descargas/preventa_por_cliente.csv", sep="|")
    
        # Calcular valor
    df_venta["Caviahue"] = df_venta["Unidades"]
    df_venta["Mizu"] = 0
    df_venta = df_venta.rename(columns={"Clie": "Cliente"})

    # Cargar archivo de preventa
    df_preventa = pd.read_csv("descargas/venta_neta_por_periodo_producto_cliente.csv", sep="|")

    #Que las unidades bonificadas resten. Si venta bruta es igual a dtos. en farmacia mas menos 2, es una venta bonificada
    def limpiar_valor(valor):
        if pd.isna(valor):
            return 0
        valor = str(valor).replace('$', '').replace(' ', '')  # quitar $ y espacios
        valor = valor.replace('.', '')  # quitar puntos de miles
        valor = valor.replace(',', '.')  # reemplazar coma decimal por punto
        return float(valor)
    
    df_preventa["Venta Bruta"] = df_preventa["Venta Bruta"].apply(limpiar_valor)
    df_preventa["Dtos. en Factura"] = df_preventa["Dtos. en Factura"].apply(limpiar_valor)


    df_preventa["venta_bonificada"] = np.isclose(    df_preventa["Venta Bruta"],    df_preventa["Dtos. en Factura"],   atol=2    )
    #si la venta es bonificada, las unidades se toman como negativas
    df_preventa["Venta Unid."] = np.where(    df_preventa["venta_bonificada"],   0,   df_preventa["Venta Unid."]    )


    # Clasificar productos
    df_preventa["Mizu"] = np.where(
        df_preventa['PRODU.'].isin([ 21304 , 21302 ]),df_preventa["Venta Unid."], 0 )

    df_preventa["Caviahue"] = np.where(
        ~df_preventa['PRODU.'].isin([ 21304 , 21302 ]),  df_preventa["Venta Unid."],   0  )

    #Despaconar
    df_preventa["Caviahue"] =  np.where(
        df_preventa['PRODU.'].isin([22005,21663,22251,21657,21655,21658]),
        df_preventa["Caviahue"] *3,
        df_preventa["Caviahue"]
    )

    df_preventa["Caviahue"] =  np.where(
        df_preventa['PRODU.'].isin([21653    ]),    df_preventa["Caviahue"] *2,
        df_preventa["Caviahue"]
    )

    df_preventa["Caviahue"] =  np.where(
        df_preventa['PRODU.'].isin([21656   ]),    df_preventa["Caviahue"] *4,
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
    lista_representantes = []
    if not representantes:
        representantes = REPRESENTANTE_POR_USUARIO.keys()

    # Lista de representantes según el usuario
    for usuario, nombres in REPRESENTANTE_POR_USUARIO.items():
        if usuario in representantes:
            lista_representantes.extend(nombres)
            
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
                df[~df["CLIENTE"].str.contains("TOTAL", case=False, na=False)]["Cuota Caviahue"].sum(skipna=True)
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

        def to_excel(df: pd.DataFrame) -> bytes:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Reporte")
            return output.getvalue()

    
        # Generar el Excel del DataFrame actual
        excel_file = to_excel(df)

        st.download_button(
        label="📥 Descargar Excel",
        data=excel_file,
        file_name=f"reporte_{fila['Representante']}.xlsx",  # nombre único
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"download_{i}"  # clave única para cada botón
        )
