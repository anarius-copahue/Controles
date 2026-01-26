import streamlit as st
import pandas as pd
import numpy as np
import io
import datetime

def productos(usuario_id="default"):
    archivo_historico = "data/Historico_Productos.xlsx" 
    archivo_ventas = "descargas/venta_neta_por_periodo_producto_cliente.csv"
    archivo_cuotas = "data/Cuota_productos.xlsx"

    st.title("Ventas por Producto (Sin preventa)")

    ahora = datetime.datetime.now()
    mes_actual, anio_actual = ahora.month, ahora.year

    # --- 0. PROCESAR HISTÓRICO ---
    try:
        df_hist = pd.read_excel(archivo_historico)
        df_hist = df_hist.dropna(subset=["PRODU."])
        df_hist["PRODU."] = pd.to_numeric(df_hist["PRODU."], errors='coerce').fillna(0).astype(int)
        df_hist = df_hist[df_hist["PRODU."] > 0]

        cols_fechas = {col: pd.to_datetime(col, dayfirst=True) for col in df_hist.columns 
                       if isinstance(col, (datetime.datetime, str)) and any(char.isdigit() for char in str(col))}
        
        df_hist["Venta 2024"] = df_hist[[c for c, dt in cols_fechas.items() if dt.year == 2024]].apply(pd.to_numeric, errors='coerce').sum(axis=1)
        df_hist["Venta 2025"] = df_hist[[c for c, dt in cols_fechas.items() if dt.year == 2025]].apply(pd.to_numeric, errors='coerce').sum(axis=1)
        df_hist["Venta 2025 YTD"] = df_hist[[c for c, dt in cols_fechas.items() if dt.year == 2025 and dt.month <= mes_actual]].apply(pd.to_numeric, errors='coerce').sum(axis=1)
        df_hist["Hist_Act"] = df_hist[[c for c, dt in cols_fechas.items() if dt.year == anio_actual]].apply(pd.to_numeric, errors='coerce').sum(axis=1)
        
        df_hist_resumen = df_hist.groupby(["PRODU.", "Producto", "Descripción"]).agg({
            "Venta 2024": "sum", 
            "Venta 2025": "sum", 
            "Venta 2025 YTD": "sum", 
            "Hist_Act": "sum"
        }).reset_index()

    except Exception as e:
        st.error(f"Error en histórico: {e}")
        df_hist_resumen = pd.DataFrame(columns=["PRODU.", "Producto", "Descripción", "Venta 2024", "Venta 2025", "Venta 2025 YTD", "Hist_Act"])

    # --- 1. CARGA VENTAS ACTUALES ---
    try:
        df_venta_actual = pd.read_csv(archivo_ventas, sep="|")
        df_venta_actual.columns = df_venta_actual.columns.str.strip()
        df_venta_actual["Caviahue"] = df_venta_actual["Venta Unid."]

        for ids, m in [([22005,21663,22251,21657,21655,21658], 3), ([21653], 2), ([21656], 4)]:
            df_venta_actual["Caviahue"] = np.where(df_venta_actual["PRODU."].isin(ids), df_venta_actual["Caviahue"] * m, df_venta_actual["Caviahue"])
        
        ventas_mes = df_venta_actual.groupby("PRODU.")["Caviahue"].sum().reset_index().rename(columns={"Caviahue": "Venta Mes Actual"})
        ventas_mes["PRODU."] = pd.to_numeric(ventas_mes["PRODU."], errors='coerce').fillna(0).astype(int)
    except:
        ventas_mes = pd.DataFrame(columns=["PRODU.", "Venta Mes Actual"])

    # --- 2. CARGA CUOTAS ---
    try:
        df_cuotas_raw = pd.read_excel(archivo_cuotas)
        df_cuotas_raw["PRODU."] = pd.to_numeric(df_cuotas_raw["PRODU."], errors='coerce').fillna(0).astype(int)
        
        # Identificar columna del mes actual en las cuotas
        cols_cuotas = {col: pd.to_datetime(col, dayfirst=True) for col in df_cuotas_raw.columns 
                       if isinstance(col, (datetime.datetime, str)) and any(char.isdigit() for char in str(col))}
        
        col_cuota_mes = [c for c, dt in cols_cuotas.items() if dt.year == anio_actual and dt.month == mes_actual]
        
        if col_cuota_mes:
            df_cuotas = df_cuotas_raw[["PRODU.", col_cuota_mes[0]]].rename(columns={col_cuota_mes[0]: "Cuota"})
        else:
            df_cuotas = pd.DataFrame(columns=["PRODU.", "Cuota"])
    except Exception as e:
        st.warning(f"No se pudo cargar el archivo de cuotas: {e}")
        df_cuotas = pd.DataFrame(columns=["PRODU.", "Cuota"])

    # --- 3. INTEGRACIÓN FINAL ---
    df_final = pd.merge(df_hist_resumen, ventas_mes, on="PRODU.", how="left")
    df_final = pd.merge(df_final, df_cuotas, on="PRODU.", how="left").fillna(0)
    
    # Cálculos adicionales
    df_final["Acumulado 2026"] = df_final["Hist_Act"] + df_final["Venta Mes Actual"]
    df_final["Avance"] = np.where(df_final["Cuota"] > 0, (df_final["Venta Mes Actual"] / df_final["Cuota"]) * 100, 0)
    df_final["growth 2025"] = np.where(df_final["Venta 2024"] > 0, ((df_final["Venta 2025"] / df_final["Venta 2024"]) - 1) * 100, 0)
    df_final["growth 2026"] = np.where(df_final["Venta 2025 YTD"] > 0, ((df_final["Acumulado 2026"] / df_final["Venta 2025 YTD"]) - 1) * 100, 0)

    # --- 4. UI ---
    tv = df_final["Venta Mes Actual"].sum()
    ta = df_final["Acumulado 2026"].sum()
    ty = df_final["Venta 2025 YTD"].sum()
    tc = df_final["Cuota"].sum()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Venta Mes", f"{int(tv):,}".replace(",", "."))
    m2.metric("Cuota Mes", f"{int(tc):,}".replace(",", "."))
    m3.metric("Avance", f"{int((tv/tc)*100 if tc>0 else 0)}%")
    m4.metric("Growth 2026", f"{int((ta/ty-1)*100 if ty>0 else 0)}%")

    # Formateo
    fmt_entero = lambda x: f"{int(x):,}".replace(",", ".")
    fmt_porcentaje = lambda x: f"{x:.1f}%"

    df_disp = df_final.sort_values("Venta Mes Actual", ascending=False).copy()
    
    # Reordenar columnas para que Cuota y Avance estén cerca de Venta Mes Actual
    columnas_orden = ["PRODU.", "Producto", "Descripción", "Venta Mes Actual", "Cuota", "Avance",
                       "Venta 2024", "Venta 2025", "growth 2025" , "Acumulado 2026", "growth 2026"]
    df_disp = df_disp[columnas_orden]

    styler = df_disp.style.format({
        "PRODU.": "{:d}",
        "Venta Mes Actual": fmt_entero,
        "Cuota": fmt_entero,
        "Avance": fmt_porcentaje,          
         "Venta 2024": fmt_entero,
        "Venta 2025": fmt_entero,
          "growth 2025": fmt_porcentaje,
         "Acumulado 2026": fmt_entero,
        "growth 2026": fmt_porcentaje,
    }).applymap(
        lambda v: 'color: green;' if isinstance(v, (int, float)) and v > 0 else ('color: red;' if isinstance(v, (int, float)) and v < 0 else ''),
        subset=["growth 2025", "growth 2026"]
    ).applymap(
        lambda v: 'font-weight: bold; color: blue;' if isinstance(v, (int, float)) and v >= 100 else '',
        subset=["Avance"]
    ).hide(axis="index")

    st.markdown(f'<div style="overflow-x:auto;">{styler.to_html()}</div>', unsafe_allow_html=True)

    # Descarga
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_final.to_excel(writer, index=False)
    st.download_button("📥 Descargar Excel", output.getvalue(), "control_productos_completo.xlsx")