import streamlit as st
import pandas as pd
import numpy as np
import io
import datetime
import os
from kits_config import KITS_ESTRUCTURA 

def mult(df):
    target = 'PRODU.' if 'PRODU.' in df.columns else 'COD_ARTICU'
    if target in df.columns:
        df[target] = pd.to_numeric(df[target], errors='coerce').fillna(0).astype(int)
        map_mult = {int(k): len(v) for k, v in KITS_ESTRUCTURA.items()}
        multiplicadores = df[target].map(map_mult).fillna(1)
        if "Caviahue" not in df.columns: df["Caviahue"] = 0
        df["Caviahue"] = pd.to_numeric(df["Caviahue"], errors='coerce').fillna(0)
        df["Caviahue"] = df["Caviahue"] * multiplicadores
    return df

def productos(usuario_id="default"):
    archivo_historico = "data/Historico_Productos.xlsx" 
    archivo_ventas = "descargas/venta_neta_por_periodo_producto_cliente.csv"
    archivo_cuotas = "data/Cuota_Productos.xlsx"
    archivo_preventa = "descargas/preventa_por_producto.csv"
    archivo_stock = "descargas/stock_por_productos.csv"

    st.title("Ventas, Preventa y Stock por Producto")

    ahora = datetime.datetime.now()
    mes_act, anio_act = ahora.month, ahora.year 

    # --- 0. PROCESAR HISTÓRICO ---
   
        # --- 0. PROCESAR HISTÓRICO (CORRECCIÓN PARA FECHAS REALES) ---
    try:
        df_hist = pd.read_excel(archivo_historico)
        
        # Identificar la columna de ID (PRODU.)
        # Buscamos 'PRODU.' sin importar mayúsculas/minúsculas
        id_orig = next((c for c in df_hist.columns if str(c).strip().upper() == "PRODU."), df_hist.columns[0])
        df_hist[id_orig] = pd.to_numeric(df_hist[id_orig], errors='coerce').fillna(0).astype(int)
        
        cols_2024, cols_25, cols_25_ytd, cols_26 = [], [], [], []
        
        for col in df_hist.columns:
            # Intentamos convertir el encabezado a fecha (si ya es fecha, lo toma directo)
            dt = pd.to_datetime(col, errors='coerce')
            
            if pd.notnull(dt):
                if dt.year == 2024:
                    cols_2024.append(col)
                elif dt.year == 25:
                    cols_25.append(col)
                    # YTD: Meses anteriores o igual al mes actual de 26 (pero del año pasado)
                    if dt.month <= mes_act:
                        cols_25_ytd.append(col)
                elif dt.year == 26:
                    cols_26.append(col)

        # Aseguramos que las columnas detectadas sean numéricas antes de sumar
        todas_las_columnas_datos = cols_2024 + cols_25 + cols_26
        for c in todas_las_columnas_datos:
            df_hist[c] = pd.to_numeric(df_hist[c], errors='coerce').fillna(0)

        # Creamos los totales por año
        df_hist["Venta 2024"] = df_hist[cols_2024].sum(axis=1) if cols_2024 else 0
        df_hist["Venta 25"] = df_hist[cols_25].sum(axis=1) if cols_25 else 0
        df_hist["Venta 25 YTD"] = df_hist[cols_25_ytd].sum(axis=1) if cols_25_ytd else 0
        df_hist["Hist_Act"] = df_hist[cols_26].sum(axis=1) if cols_26 else 0
        
        # Limpieza de nombres de columnas para el resto del reporte
        df_hist = df_hist.rename(columns={
            id_orig: "PRODU.",
            "Producto": "Producto",
            "Descripción": "Descripción"
        })
        
        # Agrupamos por si hay filas duplicadas
        df_hist_resumen = df_hist.groupby(["PRODU.", "Producto", "Descripción"]).agg({
            "Venta 2024": "sum", 
            "Venta 25": "sum", 
            "Venta 25 YTD": "sum", 
            "Hist_Act": "sum"
        }).reset_index()

    except Exception as e:
        st.error(f"Error procesando fechas del histórico: {e}")
        df_hist_resumen = pd.DataFrame(columns=["PRODU.", "Producto", "Descripción", "Venta 2024", "Venta 25", "Venta 25 YTD", "Hist_Act"])

        # Creamos las columnas de resumen
        df_hist["Venta 2024"] = df_hist[cols_2024].apply(pd.to_numeric, errors='coerce').fillna(0).sum(axis=1) if cols_2024 else 0
        df_hist["Venta 25"] = df_hist[cols_25].apply(pd.to_numeric, errors='coerce').fillna(0).sum(axis=1) if cols_25 else 0
        df_hist["Venta 25 YTD"] = df_hist[cols_25_ytd].apply(pd.to_numeric, errors='coerce').fillna(0).sum(axis=1) if cols_25_ytd else 0
        df_hist["Hist_Act"] = df_hist[cols_26].apply(pd.to_numeric, errors='coerce').fillna(0).sum(axis=1) if cols_26 else 0
        
        # Renombrar para asegurar compatibilidad con el resto del script
        rename_dict = {id_orig: "PRODU."}
        if "producto" in df_hist.columns: rename_dict["producto"] = "Producto"
        if "descripción" in df_hist.columns: rename_dict["descripción"] = "Descripción"
        
        df_hist = df_hist.rename(columns=rename_dict)
        
        df_hist_resumen = df_hist.groupby(["PRODU.", "Producto", "Descripción"]).agg({
            "Venta 2024": "sum", "Venta 25": "sum", "Venta 25 YTD": "sum", "Hist_Act": "sum"
        }).reset_index()
    except Exception as e:
        st.error(f"Error crítico en histórico: {e}")
        # Estructura de emergencia para que el merge no falle
        df_hist_resumen = pd.DataFrame(columns=["PRODU.", "Producto", "Descripción", "Venta 2024", "Venta 25", "Venta 25 YTD", "Hist_Act"])

    # --- 1. CARGA VENTAS ACTUALES ---
    try:
        df_v = pd.read_csv(archivo_ventas, sep="|", decimal=',', thousands='.', encoding='latin1')
        df_v.columns = df_v.columns.str.strip()
        df_v["Caviahue"] = pd.to_numeric(df_v["Venta Unid."], errors='coerce').fillna(0)
        df_v = mult(df_v)
        ventas_mes = df_v.groupby("PRODU.")["Caviahue"].sum().reset_index().rename(columns={"Caviahue": "Venta mes"})
    except: ventas_mes = pd.DataFrame(columns=["PRODU.", "Venta mes"])

    # --- 2. CARGA PREVENTA ---
    try:
        df_p = pd.read_csv(archivo_preventa, sep="|", decimal=',', thousands='.', encoding='latin1')
        df_p.columns = df_p.columns.str.strip()
        df_p = df_p.rename(columns={"Producto": "PRODU."})
        df_p["Caviahue"] = pd.to_numeric(df_p["Un. Reserv."], errors='coerce').fillna(0)
        df_p = mult(df_p)
        preventa_total = df_p.groupby("PRODU.")["Caviahue"].sum().reset_index().rename(columns={"Caviahue": "Preventa mes"})
    except: preventa_total = pd.DataFrame(columns=["PRODU.", "Preventa mes"])

    # --- 3. CARGA STOCK ---
    try:
        df_s = pd.read_csv(archivo_stock, sep="|", decimal=',', thousands='.', encoding='latin1')
        df_s.columns = df_s.columns.str.strip()
        df_s["PRODU."] = pd.to_numeric(df_s["Cod"], errors='coerce').fillna(0).astype(int)
        df_s["Caviahue"] = pd.to_numeric(df_s["Disp (31)"], errors='coerce').fillna(0)
        df_s = mult(df_s)
        stock_final = df_s.groupby("PRODU.")["Caviahue"].sum().reset_index().rename(columns={"Caviahue": "Stock"})
    except: stock_final = pd.DataFrame(columns=["PRODU.", "Stock"])

    # --- 4. CARGA PLAN ---
    try:
        df_c = pd.read_excel(archivo_cuotas)
        df_c.columns = [str(c).strip() for c in df_c.columns]
        col_plan = None
        for col in df_c.columns:
            dt_c = pd.to_datetime(col, dayfirst=True, errors='coerce')
            if dt_c and dt_c.year == anio_act and dt_c.month == mes_act:
                col_plan = col
                break
        df_plan = df_c[["PRODU.", col_plan]].rename(columns={col_plan: "Plan"}) if col_plan else pd.DataFrame(columns=["PRODU.", "Plan"])
        df_plan["PRODU."] = pd.to_numeric(df_plan["PRODU."], errors='coerce').fillna(0).astype(int)
    except: df_plan = pd.DataFrame(columns=["PRODU.", "Plan"])

    # --- 5. INTEGRACIÓN TOTAL ---
    df_final = pd.merge(df_hist_resumen, ventas_mes, on="PRODU.", how="left")
    df_final = pd.merge(df_final, preventa_total, on="PRODU.", how="left")
    df_final = pd.merge(df_final, stock_final, on="PRODU.", how="left")
    df_final = pd.merge(df_final, df_plan, on="PRODU.", how="left").fillna(0)

    # --- CÁLCULOS ---
    df_final["Total Mes"] = df_final["Venta mes"] + df_final["Preventa mes"]
    df_final["Avance"] = np.where(df_final["Plan"] > 0, (df_final["Total Mes"] / df_final["Plan"]) * 100, 0)
    df_final["Growth 25"] = np.where(df_final["Venta 2024"] > 0, ((df_final["Venta 25"] / df_final["Venta 2024"]) - 1) * 100, 0)
    df_final["Acumulado 26"] = df_final["Hist_Act"] + df_final["Total Mes"]
    df_final["Growth 26"] = np.where(df_final["Venta 25 YTD"] > 0, ((df_final["Acumulado 26"] / df_final["Venta 25 YTD"]) - 1) * 100, 0)

    # --- 6. MÉTRICAS ---
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Venta", f"{int(df_final['Venta mes'].sum()):,}".replace(",", "."))
    m2.metric("Preventa", f"{int(df_final['Preventa mes'].sum()):,}".replace(",", "."))
    m3.metric("Total Mes", f"{int(df_final['Total Mes'].sum()):,}".replace(",", "."))
    m4.metric("Plan", f"{int(df_final['Plan'].sum()):,}".replace(",", "."))
    tot_plan = df_final['Plan'].sum()
    m5.metric("Avance", f"{(df_final['Total Mes'].sum()/tot_plan*100 if tot_plan>0 else 0):.1f}%")

    # --- 7. TABLA ---
    cols_orden = [
        "Producto", "Venta mes", "Preventa mes", "Total Mes", "Plan", 
        "Avance", "Stock", "Venta 25", "Growth 25", "Acumulado 26", "Growth 26"
    ]
    
    st.dataframe(df_final[cols_orden].sort_values("Total Mes", ascending=False).style.format({
        "Venta mes": "{:,.0f}", "Preventa mes": "{:,.0f}", "Total Mes": "{:,.0f}", "Plan": "{:,.0f}",
        "Avance": "{:.1f}%", "Stock": "{:,.0f}", "Venta 25": "{:,.0f}", "Growth 25": "{:.1f}%",
        "Acumulado 26": "{:,.0f}", "Growth 26": "{:.1f}%"
    }), use_container_width=True)

    # --- 8. EXPORTAR ---
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_final.to_excel(writer, index=False)
    st.download_button("📥 Exportar Reporte", output.getvalue(), "reporte_consolidado.xlsx")