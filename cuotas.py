import streamlit as st
import pandas as pd
import numpy as np

def main():
# Cargar archivos
    archivo_excel = "data/representante.xlsx"
    df_preventa = pd.read_csv("descargas/preventa_por_cliente.csv", sep="|")
    df_venta = pd.read_csv("descargas/ventas_netas_por_periodo_cliente.csv", sep="|")

    # Calcular valor

    # Normalizamos nombres de columnas y sumamos
    ventas_pre = df_preventa.rename(columns={"Clie": "Cliente"})
    ventas_pre["valor"] = ventas_pre["Unidades"]
    df_venta["valor"] = df_venta["Venta Unid."] - df_venta["Unid. Bonif."]

    # Unificar ventas y calcular totales por cliente
    ventas_combinadas = pd.concat([
        ventas_pre[["Cliente", "valor"]],
        df_venta[["Cliente", "valor"]]
    ], ignore_index=True)

    ventas_totales_cliente = ventas_combinadas.groupby("Cliente")["valor"].sum().reset_index()
    ventas_totales_cliente.rename(columns={"valor": "Total Caviahue"}, inplace=True)

    # Lista de representantes esperados
    lista_representantes = [
        'Karina Macías', 'Karina Perfu y Supermercados', 'Esteban Piegari',
        'Maria Laura Lavanchy', 'Patricia Zacca', 'Marcela Rosselot', 'Lucio Colombo',
        'Yanina Cuezzo', 'Leonardo Paredes', 'Yamila Arreche', 'Emiliano Veiga',
        'Jessica Andermarch', 'Luciano Laguna'
    ]


    # Cargar hojas del Excel en un diccionario
    hojas_representantes = {
        nombre: pd.read_excel(archivo_excel, sheet_name=nombre)
        for nombre in lista_representantes
    }

    for nombre, df in hojas_representantes.items():
        df_actualizado = df.drop(columns=["Total Caviahue"], errors="ignore").merge(
            ventas_totales_cliente[["Cliente", "Total Caviahue"]],
            left_on="N° CLIENTE",
            right_on="Cliente",
            how="left"
        ).drop(columns=["Cliente"], errors="ignore")

        df_actualizado["Total Caviahue"] = df_actualizado["Total Caviahue"].fillna(0)

        # Move "Total Caviahue" to second position
        cols = df_actualizado.columns.tolist()
        if "Total Caviahue" in cols:
            cols.insert(3, cols.pop(cols.index("Total Caviahue")))
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

        hojas_representantes[nombre] = df

    def calcular_totales_por_bloques(df, columna_total="Total Caviahue"):
        df = df.copy()
        df[columna_total] = pd.to_numeric(df.get(columna_total), errors='coerce').fillna(0)

        start = 0
        for idx, row in df.iterrows():
            cliente = str(row.get("CLIENTE", "")).upper()
            ncliente = row.get("N° CLIENTE")

            if "TOTAL" in cliente or pd.isna(ncliente):
                bloque = df.iloc[start:idx]
                df.at[idx, columna_total] = bloque[columna_total].sum(skipna=True)
                start = idx + 1

        return df


    st.set_page_config(page_title="Control Cuota", layout="wide")
    st.title("Reporte de Representantes")
    st.write("Resumen de cuotas y totales por representante:")

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

if __name__ == "__main__":
    main()
