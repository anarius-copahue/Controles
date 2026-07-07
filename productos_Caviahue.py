import streamlit as st
import pandas as pd
import numpy as np
import io
import datetime
import os
from kits_config import KITS_ESTRUCTURA 

def normalizar_producto(df, col="PRODU."):
    df = df.copy()
    df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df[df[col].notna()]
    df[col] = df[col].astype(int)
    return df


def aplicar_kits(df, col_prod="PRODU.", col_unid="Caviahue"):
    df = df.copy()

    df = normalizar_producto(df, col_prod)
    df[col_unid] = pd.to_numeric(df[col_unid], errors="coerce").fillna(0)

    es_kit = df[col_prod].isin(KITS_ESTRUCTURA)

    df_kits = df[es_kit]
    df_prod = df[~es_kit]

    acumulado = {}

    for _, row in df_kits.iterrows():
        kit = row[col_prod]
        unidades = row[col_unid]

        for prod in KITS_ESTRUCTURA[kit]:
            acumulado[prod] = acumulado.get(prod, 0) + unidades

    if acumulado:
        df_kits_prod = pd.DataFrame(
            acumulado.items(),
            columns=[col_prod, col_unid]
        )
        df_final = pd.concat([df_prod[[col_prod, col_unid]], df_kits_prod])
    else:
        df_final = df_prod[[col_prod, col_unid]]

    return (
        df_final
        .groupby(col_prod, as_index=False)[col_unid]
        .sum()
    )


def formato_miles(valor):
    if pd.isna(valor):
        return "0"
    return "{:,.0f}".format(valor).replace(",", ".")


def estilo_html(df):
    formato_dict = {col: formato_miles for col in df.select_dtypes(include=[np.number]).columns}
    
    cols_pct = ["Avance", "Growth 25", "Growth 26"]
    for c in cols_pct:
        if c in df.columns:
            formato_dict[c] = lambda v: f"{formato_miles(v)}%"

    styler = df.style.format(formato_dict)

    # --- COLORES CONDICIONALES ---
    styler = styler.map(lambda v: 'color: red; font-weight: bold;' if v <= 0 else '', subset=['Stock'])
    styler = styler.map(lambda v: 'color: green; font-weight: bold;' if v >= 100 else '', subset=['Avance'])

    # CSS para encabezado fijo
    estilos_css = [
        {'selector': 'table', 'props': [('width', '100%'), ('border-collapse', 'collapse')]},
        {'selector': 'th', 'props': [
            ('position', 'sticky'), ('top', '0'), ('background-color', '#f0f2f6'),
            ('color', '#31333F'), ('z-index', '1'), ('padding', '12px'),
            ('border-bottom', '2px solid #dcdfe4')
        ]},
        {'selector': 'td', 'props': [('padding', '10px'), ('text-align', 'center'), ('border-bottom', '1px solid #eee')]}
    ]

    styler = styler.set_table_styles(estilos_css).hide(axis="index")

    html = f"""
    <div style="height: 600px; overflow-y: auto; border: 1px solid #ddd; border-radius: 8px;">
        {styler.to_html()}
    </div>
    """
    return html


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

    # --- 0. CARGA DE PLAN / CUOTAS (EJE PRINCIPAL DEL REPORTE) ---
    try:
        df_c = pd.read_excel(archivo_cuotas, sheet_name="FARMA")
        
        # Buscar columna de Nombre/Producto dentro de las cuotas
        col_nom_cuota = next((c for c in df_c.columns if "PRODUCTO" in str(c).upper() or "NOMBRE" in str(c).upper()), None)
        
        # Buscar la columna del mes actual para la cuota
        col_plan = next((c for c in df_c.columns if pd.to_datetime(c, errors='coerce').month == mes_act and pd.to_datetime(c, errors='coerce').year == anio_act), None)
        
        cols_a_cargar = ["PRODU."]
        if col_nom_cuota: cols_a_cargar.append(col_nom_cuota)
        if col_plan: cols_a_cargar.append(col_plan)
            
        df_plan = df_c[cols_a_cargar].copy()
        df_plan["PRODU."] = pd.to_numeric(df_plan["PRODU."], errors='coerce').fillna(0).astype(int)
        
        rename_cuotas = {}
        if col_plan: rename_cuotas[col_plan] = "Plan"
        if col_nom_cuota: rename_cuotas[col_nom_cuota] = "Producto"
        df_plan = df_plan.rename(columns=rename_cuotas)
        
        if "Producto" not in df_plan.columns:
            df_plan["Producto"] = "Sin Nombre (Ver Cuotas)"
            
    except Exception as e:
        st.error(f"Error crítico al cargar Cuota_Productos: {e}")
        df_plan = pd.DataFrame(columns=["PRODU.", "Producto", "Plan"])

    # --- 1. PROCESAR HISTÓRICO ---
    try:
        df_hist = pd.read_excel(archivo_historico, sheet_name="FARMA")
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
        
        df_hist_resumen = df_hist.groupby(id_orig).agg({
            "Venta 2024": "sum", "Venta 25": "sum", "Venta 25 YTD": "sum", "Hist_Act": "sum"
        }).reset_index().rename(columns={id_orig: "PRODU."})
    except Exception as e:
        st.error(f"Error Histórico: {e}")
        df_hist_resumen = pd.DataFrame(columns=["PRODU.", "Venta 2024", "Venta 25", "Venta 25 YTD", "Hist_Act"])

    # --- 2. CARGA DE OTROS DATOS (Ventas, Preventa, Stock, Tango) ---
    try:
        df_v = pd.read_csv(archivo_ventas, sep="|", decimal=",", thousands=".", encoding="latin1")
        df_v = normalizar_producto(df_v, "PRODU.")
        df_v["Caviahue"] = pd.to_numeric(df_v["Venta Unid."], errors="coerce").fillna(0)
        df_v["Importe Neto"] = pd.to_numeric(df_v["Importe Neto"], errors="coerce").fillna(0)
        df_v = df_v[df_v["Importe Neto"] != 0]
        ventas_mes = aplicar_kits(df_v).rename(columns={"Caviahue": "Venta"})
    except Exception as e:
        st.error(f"Error Ventas: {e}")
        ventas_mes = pd.DataFrame(columns=["PRODU.", "Venta"])

    try:
        df_p = pd.read_csv(archivo_preventa, sep="|", decimal=",", thousands=".", encoding="latin1")
        df_p = df_p.rename(columns={"Producto": "PRODU."})
        df_p = normalizar_producto(df_p, "PRODU.")
        df_p["Caviahue"] = pd.to_numeric(df_p["Un. Reserv."], errors="coerce").fillna(0)
        preventa_total = aplicar_kits(df_p).rename(columns={"Caviahue": "Preventa"})
    except: 
        preventa_total = pd.DataFrame(columns=["PRODU.", "Preventa"])

    try:
        df_s = pd.read_csv(archivo_stock, sep="|", decimal=',', thousands='.', encoding='latin1')
        df_s["PRODU."] = pd.to_numeric(df_s["Cod"], errors='coerce').fillna(0).astype(int)
        df_s["Caviahue"] = pd.to_numeric(df_s["Disp (31)"], errors='coerce').fillna(0)
        stock_final = aplicar_kits(df_s).rename(columns={"Caviahue": "Stock"})
    except: 
        stock_final = pd.DataFrame(columns=["PRODU.", "Stock"])

    try:
        df_t = pd.read_excel("data/TANGO.xlsx", sheet_name="Datos").rename(columns={"Cód. Artículo": "PRODU.", "Cantidad": "Caviahue"})
        df_t = df_t[~df_t['PRODU.'].isin([4, 10, 3, 12, 21302, 21304])].copy()
        tango_total = aplicar_kits(df_t).rename(columns={"Caviahue": "Tango"})
    except: 
        tango_total = pd.DataFrame(columns=["PRODU.", "Tango"])

    # --- 3. INTEGRACIÓN Y CÁLCULOS (LEFT JOIN CON DF_PLAN COMO BASE) ---
    df_final = (
        df_plan
        .merge(ventas_mes, on="PRODU.", how="left")
        .merge(preventa_total, on="PRODU.", how="left")
        .merge(tango_total, on="PRODU.", how="left")
        .merge(stock_final, on="PRODU.", how="left")
        .merge(df_hist_resumen, on="PRODU.", how="left")
        .fillna(0)
    )

    # Cálculos operacionales
    df_final["Total Mes"] = (df_final["Venta"] + df_final["Preventa"] + df_final["Tango"]).astype(int)

    # === AVANCE % ===
    df_final["Avance"] = (df_final["Total Mes"] / df_final["Plan"].replace(0, np.nan)) * 100
    df_final["Avance"] = df_final["Avance"].fillna(0)

    # === GROWTH 25 % ===
    df_final["Growth 25"] = (df_final["Venta 25"] / df_final["Venta 2024"].replace(0, np.nan) - 1) * 100
    df_final["Growth 25"] = df_final["Growth 25"].fillna(0)

    # === ACUMULADO 26 ===
    df_final["Acumulado 26"] = (df_final["Hist_Act"] + df_final["Total Mes"]).astype(int)

    # === GROWTH 26 % ===
    df_final["Growth 26"] = (df_final["Acumulado 26"] / df_final["Venta 25 YTD"].replace(0, np.nan) - 1) * 100
    df_final["Growth 26"] = df_final["Growth 26"].fillna(0)

    # --- 4. RENDERIZAR MÉTRICAS ---
    m = st.columns(6)
    f_m = lambda x: "{:,.0f}".format(x).replace(",", ".")

    m[0].metric("Venta", f_m(df_final['Venta'].sum()))
    m[1].metric("Preventa", f_m(df_final['Preventa'].sum()))
    m[2].metric("Tango", f_m(df_final['Tango'].sum()))
    m[3].metric("Total Mes", f_m(df_final['Total Mes'].sum()))
    m[4].metric("Plan", f_m(df_final['Plan'].sum()))
    
    avance_total = (df_final['Total Mes'].sum() / df_final['Plan'].sum() * 100 
                    if df_final['Plan'].sum() > 0 else 0)
    m[5].metric("Avance", f"{f_m(avance_total)}%")
    
    # --- 5. RENDERIZAR TABLA ---
    st.write("### Detalle por Producto")
    cols_orden = ["Producto", "Venta", "Preventa", "Tango", "Total Mes", "Plan", "Avance", "Stock", "Venta 25", "Growth 25", "Acumulado 26", "Growth 26"]
    
    # Asegurar que todas las columnas requeridas existan antes de filtrar el orden
    for col in cols_orden:
        if col not in df_final.columns:
            df_final[col] = 0
            
    df_html = df_final[cols_orden].sort_values("Total Mes", ascending=False)
    st.markdown(estilo_html(df_html), unsafe_allow_html=True)

    # --- 6. EXPORTAR ---
    st.markdown("---")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_final.to_excel(writer, index=False)
    st.download_button("📥 Descargar Excel", output.getvalue(), "reporte_completo.xlsx")


if __name__ == "__main__":
    productos()