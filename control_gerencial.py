import pandas as pd
import streamlit as st
from datetime import datetime
from kits_config import KITS_ESTRUCTURA, KITS_SHOPIFY

def mult_farma(df, col_prod, col_unid):
    df = df.copy()
    df[col_prod] = pd.to_numeric(df[col_prod], errors="coerce")
    df = df[df[col_prod].notna()]
    df[col_prod] = df[col_prod].astype(int)
    df[col_unid] = pd.to_numeric(df[col_unid], errors="coerce").fillna(0)
    
    es_kit = df[col_prod].isin(KITS_ESTRUCTURA)
    df_kits = df[es_kit]
    df_prod = df[~es_kit]
    
    acumulado = 0
    for _, row in df_kits.iterrows():
        unidades = row[col_unid]
        kit = row[col_prod]
        acumulado += unidades * len(KITS_ESTRUCTURA[kit])
        
    total = df_prod[col_unid].sum() + acumulado
    return total

def mult_shopify(df, col_prod, col_unid):
    df = df.copy()
    df[col_prod] = df[col_prod].astype(str).str.strip().str.upper()
    df[col_unid] = pd.to_numeric(df[col_unid], errors="coerce").fillna(0)
    
    dict_shop = {k.upper(): v for k, v in KITS_SHOPIFY.items()}
    es_kit = df[col_prod].isin(dict_shop)
    df_kits = df[es_kit]
    df_prod = df[~es_kit]
    
    acumulado = 0
    for _, r in df_kits.iterrows():
        acumulado += r[col_unid] * len(dict_shop[r[col_prod]])
        
    return df_prod[col_unid].sum() + acumulado


def control_gerencial():
    mes_act = datetime.now().month

    # Códigos de filtro exclusivos para Cantabria
    CODIGOS_CANTABRIA = [
        22719, 22705, 22704, 22713, 22720, 22721, 22715, 22701, 22707, 
        22706, 22716, 22702, 22712, 22703, 22718, 22711, 22710, 22714, 
        22717, 22709, 22708
    ]

    # Estilos de las tablas HTML
    html_style = """
    <style>
        .report-container { font-family: 'Segoe UI', sans-serif; margin-top: 10px; margin-bottom: 30px; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; }
        table.gerencial { width: 100%; border-collapse: collapse; background-color: white; }
        .gerencial th { background-color: #262730; color: white; padding: 12px; text-align: right; font-size: 13px; }
        .gerencial th:first-child { text-align: left; }
        .gerencial td { padding: 10px; border-bottom: 1px solid #eee; text-align: right; font-size: 14px; color: #31333F; }
        .gerencial td:first-child { text-align: left; }
        .row-cat { background-color: #f0f2f6; font-weight: bold; }
        .row-sub td:first-child { padding-left: 30px; color: #666; font-style: italic; }
        .row-total { background-color: #e6f4ff; font-weight: bold; border-top: 2px solid #262730; }
        .perc { color: #0068c9; font-weight: bold; }
    </style>
    """

    def fmt_n(v): return f"{int(v):,}".replace(",", ".") if v != 0 else "-"
    def fmt_p(v): return f"{v:.1%}" if v != 0 else "-"

    # ==========================================
    # FUNCIONES DE CARGA AUXILIARES
    # ==========================================
    def cargar_csv(path, col_u, codigos_filtrar=None, col_cod=None):
        try:
            df = pd.read_csv(path, sep="|", decimal=',', thousands='.', encoding='latin1', quotechar='"')
            df.columns = [c.strip() for c in df.columns]
            df = df.iloc[:-1] 
            df = df[df["Importe Neto"] != 0] 
            
            # Filtrado estricto por la columna indicada si se requiere para Cantabria
            if codigos_filtrar is not None and col_cod in df.columns:
                df[col_cod] = pd.to_numeric(df[col_cod], errors='coerce').fillna(0).astype(int)
                df = df[df[col_cod].isin(codigos_filtrar)]
                
            u = pd.to_numeric(df[col_u], errors='coerce').fillna(0).sum()
            n = pd.to_numeric(df["Importe Neto"], errors='coerce').fillna(0).sum()
            return u, n
        except: return 0, 0

    def obtener_valor_excel(path, hoja, anio, mes, codigos_filtrar=None):
        try:
            df = pd.read_excel(path, sheet_name=hoja)
            
            if codigos_filtrar is not None:
                col_codigo_plan = df.columns[0]
                df[col_codigo_plan] = pd.to_numeric(df[col_codigo_plan], errors='coerce').fillna(0).astype(int)
                df = df[df[col_codigo_plan].isin(codigos_filtrar)]

            for col in df.columns:
                dt = pd.to_datetime(col, dayfirst=True, errors='coerce')
                if pd.notnull(dt):
                    a_real = dt.year + 2000 if dt.year < 100 else dt.year
                    if a_real == anio and dt.month == mes:
                        return pd.to_numeric(df[col], errors='coerce').fillna(0).sum()
            return 0
        except: return 0


    # =========================================================================
    # BLOQUE 1: CUADRO CAVIAHUE
    # =========================================================================
    st.markdown("### Cuadro de avance del mes - Caviahue")
    
    u_dis, n_dis = cargar_csv("descargas/venta_neta_por_periodo_producto_cliente.csv", "Venta Unid.")
    u_pre, n_pre = cargar_csv("descargas/preventa_por_producto.csv", "Un. Reserv.")

    try:
        df_t = pd.read_excel("data/TANGO.xlsx", sheet_name="Datos")
        df_t["Cód. Artículo"] = pd.to_numeric(df_t["Cód. Artículo"], errors='coerce').fillna(0).astype(int)
        df_t = df_t[~df_t['Cód. Artículo'].isin([4, 10, 3, 12, 21302, 21304, 21633, 19039])]
        u_tan = df_t.loc[df_t['Total'] != 0, 'Cantidad'].sum()
        n_tan = df_t.loc[df_t['Total'] != 0, 'Total'].sum()
    except: u_tan, n_tan = 0, 0
    
    try:
        df_s = pd.read_csv("descargas/ventas_caviahue_shopify.csv")
        u_shp = mult_shopify(df_s, col_prod="product_title", col_unid="unidades")
        n_shp = pd.to_numeric(df_s["neta_sin_impuestos"], errors="coerce").fillna(0).sum()
    except: u_shp, n_shp = 0, 0

    v_plan_online = obtener_valor_excel("data/Cuota_Productos.xlsx", "ONLINE", 2026, mes_act)
    v_plan_farma = obtener_valor_excel("data/Cuota_Productos.xlsx", "FARMA", 2026, mes_act)
    v_hist_online = obtener_valor_excel("data/Historico_Productos.xlsx", "ONLINE", 2025, mes_act)
    v_hist_farma = obtener_valor_excel("data/Historico_Productos.xlsx", "FARMA", 2025, mes_act)

    u_farma_total = u_dis + u_pre + u_tan
    n_farma_total = n_dis + n_pre + n_tan

    res_data_cav = [
        ["VENTA ONLINE", u_shp, n_shp, v_plan_online, (u_shp/v_plan_online if v_plan_online else 0), v_hist_online, (u_shp/v_hist_online if v_hist_online else 0)],
        ["Venta Shopify", u_shp, n_shp, 0, 0, 0, 0],
        ["FARMA Y PERFUMERÍA", u_farma_total, n_farma_total, v_plan_farma, (u_farma_total/v_plan_farma if v_plan_farma else 0), v_hist_farma, (u_farma_total/v_hist_farma if v_hist_farma else 0)],
        ["Tango (Directo)", u_tan, n_tan, 0, 0, 0, 0],
        ["Disprofarma", u_dis, n_dis, 0, 0, 0, 0],
        ["Preventa", u_pre, n_pre, 0, 0, 0, 0],
        ["TOTAL CAVIAHUE", (u_shp+u_farma_total), (n_shp+n_farma_total), (v_plan_online+v_plan_farma), 0, (v_hist_online+v_hist_farma), 0]
    ]
    
    if res_data_cav[-1][3] > 0: res_data_cav[-1][4] = res_data_cav[-1][1] / res_data_cav[-1][3]
    if res_data_cav[-1][5] > 0: res_data_cav[-1][6] = res_data_cav[-1][1] / res_data_cav[-1][5]

    table_html_cav = f"{html_style}<div class='report-container'><table class='gerencial'>"
    table_html_cav += "<thead><tr><th>Canal</th><th>Unidades</th><th>Neto ($)</th><th>Plan</th><th>% Plan</th><th>AA</th><th>% AA</th></tr></thead><tbody>"

    for i, row in enumerate(res_data_cav):
        row_class = "row-cat" if i in [0, 2] else ("row-total" if i == 6 else "row-sub")
        table_html_cav += f"<tr class='{row_class}'>"
        table_html_cav += f"<td>{row[0]}</td><td>{fmt_n(row[1])}</td><td>{fmt_n(row[2])}</td><td>{fmt_n(row[3])}</td><td class='perc'>{fmt_p(row[4])}</td><td>{fmt_n(row[5])}</td><td class='perc'>{fmt_p(row[6])}</td>"
        table_html_cav += "</tr>"
    table_html_cav += "</tbody></table></div>"
    st.write(table_html_cav, unsafe_allow_html=True)


    # =========================================================================
    # BLOQUE 2: CUADRO CANTABRIA
    # =========================================================================
    st.markdown("### Cuadro de avance del mes - Cantabria")

    # Filtros aplicados usando tus columnas exactas ("PRODU." en venta y "Producto" en preventa)
    u_dis_cant, n_dis_cant = cargar_csv("descargas/venta_neta_por_periodo_producto_cliente.csv", "Venta Unid.", CODIGOS_CANTABRIA, "PRODU.")
    u_pre_cant, n_pre_cant = cargar_csv("descargas/preventa_por_producto.csv", "Un. Reserv.", CODIGOS_CANTABRIA, "Producto")

    try:
        df_t_cant = pd.read_excel("data/TANGO.xlsx", sheet_name="Datos")
        df_t_cant["Cód. Artículo"] = pd.to_numeric(df_t_cant["Cód. Artículo"], errors='coerce').fillna(0).astype(int)
        df_t_cant = df_t_cant[df_t_cant['Cód. Artículo'].isin(CODIGOS_CANTABRIA)]
        u_tan_cant = df_t_cant.loc[df_t_cant['Total'] != 0, 'Cantidad'].sum()
        n_tan_cant = df_t_cant.loc[df_t_cant['Total'] != 0, 'Total'].sum()
    except: u_tan_cant, n_tan_cant = 0, 0

    v_plan_cantabria = obtener_valor_excel("data/Cuota_Productos.xlsx", "FARMA", 2026, mes_act, CODIGOS_CANTABRIA)

    u_cant_total = u_dis_cant + u_pre_cant + u_tan_cant
    n_cant_total = n_dis_cant + n_pre_cant + n_tan_cant

    res_data_cant = [
        ["FARMA Y PERFUMERÍA", u_cant_total, n_cant_total, v_plan_cantabria, (u_cant_total/v_plan_cantabria if v_plan_cantabria else 0)],
        ["Tango (Directo)", u_tan_cant, n_tan_cant, 0, 0],
        ["Disprofarma", u_dis_cant, n_dis_cant, 0, 0],
        ["Preventa", u_pre_cant, n_pre_cant, 0, 0],
        ["TOTAL CANTABRIA", u_cant_total, n_cant_total, v_plan_cantabria, (u_cant_total/v_plan_cantabria if v_plan_cantabria else 0)]
    ]

    table_html_cant = f"<div class='report-container'><table class='gerencial'>"
    table_html_cant += "<thead><tr><th>Canal</th><th>Unidades</th><th>Neto ($)</th><th>Plan</th><th>% Plan</th></tr></thead><tbody>"

    for i, row in enumerate(res_data_cant):
        row_class = "row-cat" if i == 0 else ("row-total" if i == 4 else "row-sub")
        table_html_cant += f"<tr class='{row_class}'>"
        table_html_cant += f"<td>{row[0]}</td><td>{fmt_n(row[1])}</td><td>{fmt_n(row[2])}</td><td>{fmt_n(row[3])}</td><td class='perc'>{fmt_p(row[4])}</td>"
        table_html_cant += "</tr>"
    table_html_cant += "</tbody></table></div>"
    
    st.write(table_html_cant, unsafe_allow_html=True)