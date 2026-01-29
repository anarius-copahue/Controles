import pandas as pd
import streamlit as st
from datetime import datetime

def control_gerencial():
    st.markdown("### Tablero de Control Gerencial - Caviahue")
    
    # Configuración de fecha (Año actual según sistema)
    anio_actual = 2026 
    mes_act = datetime.now().month

    # ==========================================
    # 1. FUNCIONES DE CARGA Y PROCESAMIENTO
    # ==========================================
    def cargar_csv(path, col_u):
        try:
            df = pd.read_csv(path, sep="|", decimal=',', thousands='.', encoding='latin1', quotechar='"')
            df.columns = [c.strip() for c in df.columns]
            df = df.iloc[:-1] # Eliminar última fila de totales
            df = df[df["Importe Neto"] != 0]
            
            u = pd.to_numeric(df[col_u], errors='coerce').fillna(0).sum()
            n = pd.to_numeric(df["Importe Neto"], errors='coerce').fillna(0).sum()
            return u, n
        except:
            return 0, 0

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

    # --- Procesamiento de Datos ---
    u_dis, n_dis = cargar_csv("descargas/venta_neta_por_periodo_producto_cliente.csv", "Venta Unid.")
    u_pre, n_pre = cargar_csv("descargas/preventa_por_producto.csv", "Un. Reserv.")

    # Tango
    try:
        df_t = pd.read_csv("data/TANGO.csv")
        df_t.columns = [c.strip().upper() for c in df_t.columns]
        df_t = df_t[~df_t['COD_ARTICU'].isin([1, 2, 3, 6])]
        
        def limpiar_tango(col):
            return pd.to_numeric(col.astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False).str.strip(), errors='coerce').fillna(0)

        df_t['NETO_LIMPIO'] = limpiar_tango(df_t['TOT_S_IMP'])
        df_t['CANT_LIMPIA'] = limpiar_tango(df_t['CANTIDAD'])
        
        u_tan = df_t.loc[df_t['NETO_LIMPIO'] != 0, 'CANT_LIMPIA'].sum()
        n_tan = df_t.loc[df_t['NETO_LIMPIO'] != 0, 'NETO_LIMPIO'].sum()
    except:
        u_tan, n_tan = 0, 0

    # Shopify
    try:
        df_s = pd.read_csv("descargas/ventas_caviahue_shopify.csv")
        u_shp, n_shp = df_s['unidades'].sum(), df_s['neta_sin_impuestos'].sum()
    except: u_shp, n_shp = 0, 0

    # Planes e Históricos
    v_plan_online = obtener_valor_excel("data/Cuota_Productos.xlsx", "ONLINE", anio_actual, mes_act)
    v_plan_farma = obtener_valor_excel("data/Cuota_Productos.xlsx", "FARMA", anio_actual, mes_act)
    v_hist_online = obtener_valor_excel("data/Historico_Productos.xlsx", "ONLINE", anio_actual - 1, mes_act)
    v_hist_farma = obtener_valor_excel("data/Historico_Productos.xlsx", "FARMA", anio_actual - 1, mes_act)

    # Consolidación
    u_farma_total = u_dis + u_pre + u_tan
    n_farma_total = n_dis + n_pre + n_tan

    data_res = [
        ["VENTA ONLINE", u_shp, n_shp, v_plan_online, (u_shp/v_plan_online if v_plan_online else 0), v_hist_online, (u_shp/v_hist_online if v_hist_online else 0)],
        ["&nbsp;&nbsp;&nbsp;Venta Shopify", u_shp, n_shp, 0, 0, 0, 0],
        ["FARMA Y PERFUMERÍA", u_farma_total, n_farma_total, v_plan_farma, (u_farma_total/v_plan_farma if v_plan_farma else 0), v_hist_farma, (u_farma_total/v_hist_farma if v_hist_farma else 0)],
        ["&nbsp;&nbsp;&nbsp;Tango (Directo)", u_tan, n_tan, 0, 0, 0, 0],
        ["&nbsp;&nbsp;&nbsp;Disprofarma", u_dis, n_dis, 0, 0, 0, 0],
        ["&nbsp;&nbsp;&nbsp;Preventa", u_pre, n_pre, 0, 0, 0, 0],
        ["TOTAL CAVIAHUE", (u_shp+u_farma_total), (n_shp+n_farma_total), (v_plan_online+v_plan_farma), 0, (v_hist_online+v_hist_farma), 0]
    ]
    
    # Totales finales
    if data_res[-1][3] > 0: data_res[-1][4] = data_res[-1][1] / data_res[-1][3]
    if data_res[-1][5] > 0: data_res[-1][6] = data_res[-1][1] / data_res[-1][5]

    df_res = pd.DataFrame(data_res, columns=["Canal", "Unidades", "Neto", "Plan", "% Plan", "AA", "% AA"])

    # ==========================================
    # 2. GENERADOR DE TABLA HTML
    # ==========================================
    def render_html_table(df):
        styles = """
        <style>
            .container { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin-top: 20px; }
            .main-table { width: 100%; border-collapse: collapse; border-radius: 8px; overflow: hidden; box-shadow: 0 0 10px rgba(0,0,0,0.05); }
            .main-table th { background-color: #2c3e50; color: white; padding: 12px; text-align: left; font-size: 13px; }
            .main-table td { padding: 10px; border-bottom: 1px solid #eee; font-size: 13px; color: #444; }
            .row-cat { background-color: #f8f9fa; font-weight: bold; color: #2c3e50 !important; }
            .row-total { background-color: #e9ecef; font-weight: 800; border-top: 2px solid #333 !important; }
            .text-right { text-align: right; }
            .text-center { text-align: center; }
            .perc { font-weight: bold; color: #2980b9; }
        </style>
        """
        
        html = f"{styles}<div class='container'><table class='main-table'><thead><tr>"
        for col in df.columns:
            html += f"<th class='{'text-right' if col != 'Canal' else ''}'>{col}</th>"
        html += "</tr></thead><tbody>"

        for i, row in df.iterrows():
            # Clases especiales
            tr_class = ""
            if i in [0, 2]: tr_class = 'class="row-cat"'
            elif i == 6: tr_class = 'class="row-total"'

            # Formateo
            def fn(v): return f"{int(v):,}".replace(",", ".") if v != 0 else "-"
            def fp(v): return f"{v:.1%}" if v != 0 else "-"
            
            html += f"""
            <tr {tr_class}>
                <td>{row['Canal']}</td>
                <td class="text-right">{fn(row['Unidades'])}</td>
                <td class="text-right">$ {fn(row['Neto'])}</td>
                <td class="text-right">{fn(row['Plan'])}</td>
                <td class="text-center perc">{fp(row['% Plan'])}</td>
                <td class="text-right">{fn(row['AA'])}</td>
                <td class="text-center perc">{fp(row['% AA'])}</td>
            </tr>
            """
        html += "</tbody></table></div>"
        return html

    # Renderizar en Streamlit
    st.markdown(render_html_table(df_res), unsafe_allow_html=True)

if __name__ == "__main__":
    control_gerencial()