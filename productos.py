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

def estilo_html(df):
    """
    Genera una tabla HTML con encabezado fijo y colores condicionales.
    """
    # Definir estilos condicionales
    def aplicar_colores(row):
        styles = [''] * len(row)
        # Índice de columnas: Stock está en la pos 6, Avance en la 5
        # Pero es más seguro usar nombres si el styler lo permite
        return styles

    # Formateo inicial
    styler = df.style.format({
        "Venta mes": "{:,.0f}", "Preventa mes": "{:,.0f}", "Total Mes": "{:,.0f}", 
        "Plan": "{:,.0f}", "Avance": "{:.1f}%", "Stock": "{:,.0f}", 
        "Venta 25": "{:,.0f}", "Growth 25": "{:.1f}%",
        "Acumulado 26": "{:,.0f}", "Growth 26": "{:.1f}%"
    })

    # Color Rojo para Stock <= 0
    styler = styler.map(lambda v: 'color: red; font-weight: bold;' if v <= 0 else '', subset=['Stock'])
    
    # Color Verde para Avance >= 100
    styler = styler.map(lambda v: 'color: green; font-weight: bold;' if v >= 100 else '', subset=['Avance'])

    # CSS para encabezado fijo y diseño
    # 'sticky' hace que el th se quede arriba al hacer scroll en el div padre
    estilos_css = [
        {'selector': 'table', 'props': [('width', '100%'), ('border-collapse', 'collapse')]},
        {'selector': 'th', 'props': [
            ('position', 'sticky'), 
            ('top', '0'), 
            ('background-color', '#f0f2f6'), 
            ('color', '#31333F'), 
            ('z-index', '1'), 
            ('padding', '12px'),
            ('border-bottom', '2px solid #dcdfe4')
        ]},
        {'selector': 'td', 'props': [('padding', '10px'), ('text-align', 'center'), ('border-bottom', '1px solid #eee')]}
    ]

    styler = styler.set_table_styles(estilos_css).hide(axis="index")

    # Envolvemos la tabla en un DIV con scroll
    html = f"""
    <div style="height: 600px; overflow-y: auto; border: 1px solid #ddd; border-radius: 8px;">
        {styler.to_html()}
    </div>
    """
    return html

# --- En tu función productos(), reemplaza la sección de renderizado por esto: ---



def productos(usuario_id="default"):
    # --- Configuración de Archivos ---
    archivo_historico = "data/Historico_Productos.xlsx" 
    archivo_ventas = "descargas/venta_neta_por_periodo_producto_cliente.csv"
    archivo_cuotas = "data/Cuota_Productos.xlsx"
    archivo_preventa = "descargas/preventa_por_producto.csv"
    archivo_stock = "descargas/stock_por_productos.csv"

    st.title("Venta por producto")

    ahora = datetime.datetime.now()
    mes_act, anio_act = ahora.month, ahora.year 

    # --- 0. PROCESAR HISTÓRICO ---
    try:
        df_hist = pd.read_excel(archivo_historico)
        id_orig = next((c for c in df_hist.columns if "PRODU" in str(c).upper()), df_hist.columns[0])
        df_hist[id_orig] = pd.to_numeric(df_hist[id_orig], errors='coerce').fillna(0).astype(int)
        
        cols_24, cols_25, cols_25_ytd, cols_26 = [], [], [], []
        for col in df_hist.columns:
            dt = pd.to_datetime(col, dayfirst=True, errors='coerce')
            if pd.notnull(dt):
                anio = dt.year + 2000 if dt.year < 100 else dt.year
                if anio == 2024: cols_24.append(col)
                elif anio == 2025:
                    cols_25.append(col)
                    if dt.month <= mes_act: cols_25_ytd.append(col)
                elif anio == 2026: cols_26.append(col)

        for c in (cols_24 + cols_25 + cols_26):
            df_hist[c] = pd.to_numeric(df_hist[c], errors='coerce').fillna(0)

        df_hist["Venta 2024"] = df_hist[cols_24].sum(axis=1) if cols_24 else 0
        df_hist["Venta 25"] = df_hist[cols_25].sum(axis=1) if cols_25 else 0
        df_hist["Venta 25 YTD"] = df_hist[cols_25_ytd].sum(axis=1) if cols_25_ytd else 0
        df_hist["Hist_Act"] = df_hist[cols_26].sum(axis=1) if cols_26 else 0
        
        rename_map = {id_orig: "PRODU."}
        for col in df_hist.columns:
            if "producto" in str(col).lower(): rename_map[col] = "Producto"
        df_hist = df_hist.rename(columns=rename_map)
        
        df_hist_resumen = df_hist.groupby(["PRODU.", "Producto"]).agg({
            "Venta 2024": "sum", "Venta 25": "sum", "Venta 25 YTD": "sum", "Hist_Act": "sum"
        }).reset_index()
    except Exception as e:
        st.error(f"Error Histórico: {e}")
        df_hist_resumen = pd.DataFrame(columns=["PRODU.", "Producto", "Venta 2024", "Venta 25", "Venta 25 YTD", "Hist_Act"])

    # --- 1. CARGA DE OTROS DATOS (Ventas, Preventa, Stock, Plan) ---
    # (Lógica simplificada para brevedad, mantenemos la de tu script anterior)
    try:
        df_v = pd.read_csv(archivo_ventas, sep="|", decimal=',', thousands='.', encoding='latin1')
        df_v["Caviahue"] = pd.to_numeric(df_v["Venta Unid."], errors='coerce').fillna(0)
        
        df_v["Importe Neto"] = pd.to_numeric(df_v["Importe Neto"], errors='coerce').fillna(0)
        df_v = df_v[df_v["Importe Neto"] != 0].copy()
        ventas_mes = mult(df_v).groupby("PRODU.")["Caviahue"].sum().reset_index().rename(columns={"Caviahue": "Venta mes"})
    except: ventas_mes = pd.DataFrame(columns=["PRODU.", "Venta mes"])

    try:
        df_p = pd.read_csv(archivo_preventa, sep="|", decimal=',', thousands='.', encoding='latin1').rename(columns={"Producto": "PRODU."})
        df_p["Caviahue"] = pd.to_numeric(df_p["Un. Reserv."], errors='coerce').fillna(0)
        df_p["Importe Neto"] = pd.to_numeric(df_p["Importe Neto"], errors='coerce').fillna(0)
       
        preventa_total = mult(df_p).groupby("PRODU.")["Caviahue"].sum().reset_index().rename(columns={"Caviahue": "Preventa mes"})
    except: preventa_total = pd.DataFrame(columns=["PRODU.", "Preventa mes"])

    try:
        df_s = pd.read_csv(archivo_stock, sep="|", decimal=',', thousands='.', encoding='latin1')
        df_s["PRODU."] = pd.to_numeric(df_s["Cod"], errors='coerce').fillna(0).astype(int)
        df_s["Caviahue"] = pd.to_numeric(df_s["Disp (31)"], errors='coerce').fillna(0)
        stock_final = mult(df_s).groupby("PRODU.")["Caviahue"].sum().reset_index().rename(columns={"Caviahue": "Stock"})
    except: stock_final = pd.DataFrame(columns=["PRODU.", "Stock"])

    try:
        df_c = pd.read_excel(archivo_cuotas)
        col_plan = next((c for c in df_c.columns if pd.to_datetime(c, errors='coerce').month == mes_act and pd.to_datetime(c, errors='coerce').year == anio_act), None)
        df_plan = df_c[["PRODU.", col_plan]].rename(columns={col_plan: "Plan"}) if col_plan else pd.DataFrame(columns=["PRODU.", "Plan"])
        df_plan["PRODU."] = pd.to_numeric(df_plan["PRODU."], errors='coerce').fillna(0).astype(int)
    except: df_plan = pd.DataFrame(columns=["PRODU.", "Plan"])

    # --- 2. INTEGRACIÓN Y CÁLCULOS ---
    df_final = pd.merge(df_hist_resumen, ventas_mes, on="PRODU.", how="left")
    df_final = pd.merge(df_final, preventa_total, on="PRODU.", how="left")
    df_final = pd.merge(df_final, stock_final, on="PRODU.", how="left")
    df_final = pd.merge(df_final, df_plan, on="PRODU.", how="left").fillna(0)

    df_final["Total Mes"] = df_final["Venta mes"] + df_final["Preventa mes"]
    df_final["Avance"] = np.where(df_final["Plan"] > 0, (df_final["Total Mes"] / df_final["Plan"]) * 100, 0)
    df_final["Growth 25"] = np.where(df_final["Venta 2024"] > 0, ((df_final["Venta 25"] / df_final["Venta 2024"]) - 1) * 100, 0)
    df_final["Acumulado 26"] = df_final["Hist_Act"] + df_final["Total Mes"]
    df_final["Growth 26"] = np.where(df_final["Venta 25 YTD"] > 0, ((df_final["Acumulado 26"] / df_final["Venta 25 YTD"]) - 1) * 100, 0)

    # --- 3. MÉTRICAS (KPIs) ---
    m = st.columns(5)
    m[0].metric("Venta", f"{int(df_final['Venta mes'].sum()):,}")
    m[1].metric("Preventa", f"{int(df_final['Preventa mes'].sum()):,}")
    m[2].metric("Total Mes", f"{int(df_final['Total Mes'].sum()):,}")
    m[3].metric("Plan", f"{int(df_final['Plan'].sum()):,}")
    m[4].metric("Avance", f"{(df_final['Total Mes'].sum()/df_final['Plan'].sum()*100 if df_final['Plan'].sum()>0 else 0):.1f}%")

    # --- 4. RENDERIZADO HTML ---
    st.write("### Detalle por Producto")
    cols_orden = ["Producto", "Venta mes", "Preventa mes", "Total Mes", "Plan", "Avance", "Stock", "Venta 25", "Growth 25", "Acumulado 26", "Growth 26"]
    df_html = df_final[cols_orden].sort_values("Total Mes", ascending=False)

    # Renderizar la tabla con encabezado fijo
    st.markdown(estilo_html(df_html), unsafe_allow_html=True)

    # --- 5. EXPORTAR ---
    st.divider()
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_final.to_excel(writer, index=False)
    st.download_button("📥 Descargar Excel", output.getvalue(), "reporte.xlsx")

if __name__ == "__main__":
    productos()