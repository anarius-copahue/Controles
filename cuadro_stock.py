import streamlit as st
import pandas as pd
import numpy as np
import io
import datetime
from kits_config import PRODUCTOS_MAESTRO

# --- CONFIGURACIÓN DE PRODUCTOS ---
PRODUCTOS_IDS = [
    19653, 22287, 19415, 21420, 21422, 21670, 21360, 20195, 21314, 21316, 
    21315, 21411, 18547, 18548, 19060, 22012, 18921, 19749, 19676, 18550, 
    18544, 19515, 19074, 20224, 21991, 21992, 22285, 20035, 20037, 20036, 
    21660, 20093, 20170, 22622, 22559, 22151, 22560, 21421, 18921, 21657, 
    21658, 21656, 21653, 22251, 22005, 22441, 22618, 21655, 22619
]

def obtener_plan_df(path, hoja, anio, mes, nombre_col_plan):
    try:
        df = pd.read_excel(path, sheet_name=hoja)
        for col in df.columns:
            dt = pd.to_datetime(col, dayfirst=True, errors='coerce')
            if pd.notnull(dt) and dt.year == anio and dt.month == mes:
                res = df[["PRODU.", col]].copy()
                res.columns = ["PRODU.", nombre_col_plan]
                return res
        return pd.DataFrame(columns=["PRODU.", nombre_col_plan])
    except: return pd.DataFrame(columns=["PRODU.", nombre_col_plan])

def app_ventas_stock():
    st.set_page_config(layout="wide")
    st.title("Control de Stock y Ventas Consolidado")

    ahora = datetime.datetime.now()
    mes_act, anio_act = ahora.month, 2026 

    try:
        # 1. CARGA DISPRO
        df_s_dispro = pd.read_csv("descargas/stock_por_productos.csv", sep="|", decimal=",", encoding="latin1")
        stock_dispro = df_s_dispro[["Cod", "Descripcion", "Disp (31)"]].rename(
            columns={"Cod": "PRODU.", "Descripcion": "Producto", "Disp (31)": "Stock Dispro"}
        )

        df_v = pd.read_csv("descargas/venta_neta_por_periodo_producto_cliente.csv", sep="|", decimal=",", encoding="latin1")
        venta_dispro = df_v.groupby("PRODU.")["Venta Unid."].sum().reset_index().rename(columns={"Venta Unid.": "Venta Dispro"})
        
        df_p = pd.read_csv("descargas/preventa_por_producto.csv", sep="|", decimal=",", encoding="latin1")
        preventa_dispro = df_p.groupby("Producto")["Un. Reserv."].sum().reset_index().rename(columns={"Producto": "PRODU.", "Un. Reserv.": "Preventa Dispro"})

        # 2. TANGO (CON TRY/EXCEPT)
        try:
            df_t = pd.read_excel("data/TANGO.xlsx", sheet_name="Datos")
            tango_total = df_t.groupby("Cód. Artículo")["Cantidad"].sum().reset_index().rename(columns={"Cód. Artículo": "PRODU.", "Cantidad": "Venta Tango"})
        except Exception:
            st.warning("Archivo TANGO.xlsx no disponible. Se asumen ventas 0.")
            tango_total = pd.DataFrame(columns=["PRODU.", "Venta Tango"])

        # 3. CUOTAS Y SHOPIFY
        plan_farma = obtener_plan_df("data/Cuota_Productos.xlsx", "FARMA", anio_act, mes_act, "Plan Farma")
        plan_shopify = obtener_plan_df("data/Cuota_Productos.xlsx", "ONLINE", anio_act, mes_act, "Plan Shopify")

        df_shop_raw = pd.read_csv("descargas/ventas_caviahue_shopify.csv")
        shopify_resumen = df_shop_raw.groupby("product_title").agg({"unidades": "sum", "stock_total": "sum"}).reset_index()

    except Exception as e:
        st.error(f"Error en la carga de archivos base: {e}")
        return

    # --- PROCESAMIENTO ---
    df_final = stock_dispro[stock_dispro["PRODU."].isin(PRODUCTOS_IDS)].copy()
    df_final = df_final.merge(plan_farma, on="PRODU.", how="left")
    df_final = df_final.merge(plan_shopify, on="PRODU.", how="left")
    df_final = df_final.merge(venta_dispro, on="PRODU.", how="left")
    df_final = df_final.merge(preventa_dispro, on="PRODU.", how="left")
    df_final = df_final.merge(tango_total, on="PRODU.", how="left")

    df_final["Nombre_Shopify"] = df_final["PRODU."].map(PRODUCTOS_MAESTRO)
    df_final = df_final.merge(shopify_resumen, left_on="Nombre_Shopify", right_on="product_title", how="left")
    
    df_final = df_final.rename(columns={"unidades": "Venta Shopify", "stock_total": "Stock Shopify"})
    df_final = df_final.fillna(0)
    
    # Cálculos de diferencias (Auxiliares para el color)
    df_final["Total Farma"] = df_final["Venta Dispro"] + df_final["Preventa Dispro"] + df_final["Venta Tango"]
    df_final["Dif_Quiebre_Farma"] = df_final["Plan Farma"] - (df_final["Total Farma"] + df_final["Stock Dispro"])
    df_final["Dif_Quiebre_Shopify"] = df_final["Plan Shopify"] - (df_final["Venta Shopify"] + df_final["Stock Shopify"])
    df_final["Venta total"] = df_final["Total Farma"] + df_final["Venta Shopify"]
    df_final["Stock total"] = df_final["Stock Dispro"] + df_final["Stock Shopify"]
    df_final = df_final.sort_values("Plan Farma", ascending=False)

    #ordenar las columnas de df_final
    df_final = df_final[["PRODU.", "Producto", "Venta Dispro", "Preventa Dispro", "Venta Tango", 
                         "Total Farma", "Stock Dispro", "Plan Farma", 
                         "Venta Shopify", "Stock Shopify", "Plan Shopify","Venta total", "Stock total", "Dif_Quiebre_Farma",
                           "Dif_Quiebre_Shopify"
                         ]]

    # --- ALERTAS FARMA (ARRIBA) ---
    productos_alerta = df_final[df_final["Dif_Quiebre_Farma"] > 10].sort_values("Plan Farma", ascending=False)
    if not productos_alerta.empty:
        st.subheader("Alerta de Quiebre Farma (Acorde al Plan)")
        n_alertas = min(len(productos_alerta), 4)
        cols = st.columns(n_alertas)
        for i, (_, row) in enumerate(productos_alerta.head(4).iterrows()):
            with cols[i]:
                st.metric(label=row["Producto"], value=int(row["Stock Dispro"]), delta=f"{int(row['Dif_Quiebre_Farma'])} p/ Plan")
        st.divider()

    # --- ESTILOS DINÁMICOS ---
    def aplicar_estilos(row):
        estilos = [''] * len(row)
        idx_stock_dispro = row.index.get_loc("Stock Dispro")
        idx_stock_shop = row.index.get_loc("Stock Shopify")
        
        # LÓGICA DISPRO (FARMA)
        if row["Stock Dispro"] <= 0:
            estilos[idx_stock_dispro] = 'background-color: #ffcccc; color: red; font-weight: bold'
        elif row["Dif_Quiebre_Farma"] > 10:
            estilos[idx_stock_dispro] = 'background-color: #ffe5b4; color: #cc7a00; font-weight: bold'

        # LÓGICA SHOPIFY (ONLINE)
        if row["Stock Shopify"] <= 0:
            estilos[idx_stock_shop] = 'background-color: #ffcccc; color: red; font-weight: bold'
        elif row["Dif_Quiebre_Shopify"] > 10:
            estilos[idx_stock_shop] = 'background-color: #ffe5b4; color: #cc7a00; font-weight: bold'
            
        return estilos

    # --- TABLA FINAL ---
    st.dataframe(
        df_final.style.format(precision=0, thousands=".")
        .apply(aplicar_estilos, axis=1),
        use_container_width=True,
        height=700,
        hide_index=True,
        column_order=[
            "PRODU.", "Producto", "Venta Dispro", "Preventa Dispro", "Venta Tango", 
            "Total Farma", "Stock Dispro", "Plan Farma", 
            "Venta Shopify", "Stock Shopify", "Plan Shopify"
        ]
    )

    # Exportación
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_final.to_excel(writer, index=False)
    st.download_button("Descargar Reporte", output.getvalue(), "reporte_consolidado.xlsx")

if __name__ == "__main__":
    app_ventas_stock()