import pandas as pd
import streamlit as st
from datetime import datetime

def control_gerencial():
    st.markdown("### Tablero de Control Gerencial - Caviahue")
    mes_act = datetime.now().month

    # ==========================================
    # 1. FUNCIONES DE CARGA (Sin cambios en tu lógica)
    # ==========================================
    def cargar_csv(path, col_u):
        try:
            df = pd.read_csv(path, sep="|", decimal=',', thousands='.', encoding='latin1', quotechar='"')
            df.columns = [c.strip() for c in df.columns]
            df = df.iloc[:-1] 
            df = df[df["Importe Neto"] != 0] 
            u = pd.to_numeric(df[col_u], errors='coerce').fillna(0).sum()
            n = pd.to_numeric(df["Importe Neto"], errors='coerce').fillna(0).sum()
            return u, n
        except: return 0, 0

    def obtener_valor_excel(path, hoja, anio, mes):
        try:
            df = pd.read_excel(path, sheet_name=hoja)
            for col in df.columns:
                dt = pd.to_datetime(col, dayfirst=True, errors='coerce')
                if pd.notnull(dt):
                    a_real = dt.year + 2000 if dt.year < 100 else dt.year
                    if a_real == anio and dt.month == mes:
                        return pd.to_numeric(df[col], errors='coerce').fillna(0).sum()
            return 0
        except: return 0

    # ==========================================
    # 2. PROCESAMIENTO (Tu lógica original)
    # ==========================================
    u_dis, n_dis = cargar_csv("descargas/venta_neta_por_periodo_producto_cliente.csv", "Venta Unid.")
    u_pre, n_pre = cargar_csv("descargas/preventa_por_producto.csv", "Un. Reserv.")

    try:
        df_t = pd.read_csv("data/TANGO.csv")
        df_t.columns = [c.strip().upper() for c in df_t.columns]
        df_t = df_t[~df_t['COD_ARTICU'].isin([4, 10, 3, 12])]
        
        def limpiar_tango(col):
            return pd.to_numeric(col.astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False).str.strip(), errors='coerce').fillna(0)

        df_t['NETO_LIMPIO'] = limpiar_tango(df_t['TOT_S_IMP'])
        df_t['CANT_LIMPIA'] = limpiar_tango(df_t['CANTIDAD'])
        u_tan = df_t.loc[df_t['NETO_LIMPIO'] != 0, 'CANT_LIMPIA'].sum()
        n_tan = df_t.loc[df_t['NETO_LIMPIO'] != 0, 'NETO_LIMPIO'].sum()
    except: u_tan, n_tan = 0, 0

    try:
        df_s = pd.read_csv("descargas/ventas_caviahue_shopify.csv")
        u_shp, n_shp = df_s['unidades'].sum(), df_s['neta_sin_impuestos'].sum()
    except: u_shp, n_shp = 0, 0

    v_plan_online = obtener_valor_excel("data/Cuota_Productos.xlsx", "ONLINE", 2026, mes_act)
    v_plan_farma = obtener_valor_excel("data/Cuota_Productos.xlsx", "FARMA", 2026, mes_act)
    v_hist_online = obtener_valor_excel("data/Historico_Productos.xlsx", "ONLINE", 2025, mes_act)
    v_hist_farma = obtener_valor_excel("data/Historico_Productos.xlsx", "FARMA", 2025, mes_act)

    u_farma_total = u_dis + u_pre + u_tan
    n_farma_total = n_dis + n_pre + n_tan

    res_data = [
        ["VENTA ONLINE", u_shp, n_shp, v_plan_online, (u_shp/v_plan_online if v_plan_online else 0), v_hist_online, (u_shp/v_hist_online if v_hist_online else 0)],
        ["Venta Shopify", u_shp, n_shp, 0, 0, 0, 0],
        ["FARMA Y PERFUMERÍA", u_farma_total, n_farma_total, v_plan_farma, (u_farma_total/v_plan_farma if v_plan_farma else 0), v_hist_farma, (u_farma_total/v_hist_farma if v_hist_farma else 0)],
        ["Tango (Directo)", u_tan, n_tan, 0, 0, 0, 0],
        ["Disprofarma", u_dis, n_dis, 0, 0, 0, 0],
        ["Preventa", u_pre, n_pre, 0, 0, 0, 0],
        ["TOTAL CAVIAHUE", (u_shp+u_farma_total), (n_shp+n_farma_total), (v_plan_online+v_plan_farma), 0, (v_hist_online+v_hist_farma), 0]
    ]
    
    # Cálculos finales de la fila TOTAL
    if res_data[-1][3] > 0: res_data[-1][4] = res_data[-1][1] / res_data[-1][3]
    if res_data[-1][5] > 0: res_data[-1][6] = res_data[-1][1] / res_data[-1][5]

    # ==========================================
    # 3. CONSTRUCCIÓN DE LA TABLA HTML
    # ==========================================
    
    html_style = """
    <style>
        .report-container { font-family: 'Segoe UI', sans-serif; margin-top: 20px; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; }
        table.gerencial { width: 100%; border-collapse: collapse; background-color: white; }
        .gerencial th { background-color: #262730; color: white; padding: 12px; text-align: right; font-size: 13px; }
        .gerencial th:first-child { text-align: left; }
        .gerencial td { padding: 10px; border-bottom: 1px solid #eee; text-align: right; font-size: 14px; color: #31333F; }
        .gerencial td:first-child { text-align: left; }
        
        /* Estilos de Fila */
        .row-cat { background-color: #f0f2f6; font-weight: bold; }
        .row-sub td:first-child { padding-left: 30px; color: #666; font-style: italic; }
        .row-total { background-color: #e6f4ff; font-weight: bold; border-top: 2px solid #262730; }
        
        .perc { color: #0068c9; font-weight: bold; }
    </style>
    """

    table_html = f"{html_style}<div class='report-container'><table class='gerencial'>"
    table_html += "<thead><tr><th>Canal</th><th>Unidades</th><th>Neto ($)</th><th>Plan</th><th>% Plan</th><th>AA</th><th>% AA</th></tr></thead><tbody>"

    for i, row in enumerate(res_data):
        # Determinar clase de fila
        if i in [0, 2]: row_class = "row-cat"
        elif i == 6: row_class = "row-total"
        else: row_class = "row-sub"

        # Formateo de celdas
        def fmt_n(v): return f"{int(v):,}".replace(",", ".") if v != 0 else "-"
        def fmt_p(v): return f"{v:.1%}" if v != 0 else "-"

        table_html += f"<tr class='{row_class}'>"
        table_html += f"<td>{row[0]}</td>"
        table_html += f"<td>{fmt_n(row[1])}</td>"
        table_html += f"<td>{fmt_n(row[2])}</td>"
        table_html += f"<td>{fmt_n(row[3])}</td>"
        table_html += f"<td class='perc'>{fmt_p(row[4])}</td>"
        table_html += f"<td>{fmt_n(row[5])}</td>"
        table_html += f"<td class='perc'>{fmt_p(row[6])}</td>"
        table_html += "</tr>"

    table_html += "</tbody></table></div>"

    # Renderizado final
    st.write(table_html, unsafe_allow_html=True)

