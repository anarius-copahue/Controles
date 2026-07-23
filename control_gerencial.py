import pandas as pd
import streamlit as st
from datetime import datetime
from kits_config import KITS_ESTRUCTURA, KITS_SHOPIFY

def limpiar_numero(serie):
    """ Convierte una serie a numérico manejando formatos con comas, puntos y símbolos. """
    if serie is None:
        return pd.Series(dtype=float)
    
    s = serie.astype(str).str.strip()
    s = s.str.replace("$", "", regex=False).str.replace(" ", "", regex=False)
    
    # Manejo de separadores decimales/miles
    if s.str.contains(",").any() and s.str.contains(r"\.").any():
        s = s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    elif s.str.contains(",").any():
        s = s.str.replace(",", ".", regex=False)
        
    return pd.to_numeric(s, errors="coerce").fillna(0)

def mult_farma(df, col_prod, col_unid):
    if df.empty or col_prod not in df.columns or col_unid not in df.columns:
        return 0
        
    df = df.copy()
    df[col_prod] = pd.to_numeric(df[col_prod], errors="coerce")
    df = df[df[col_prod].notna()]
    df[col_prod] = df[col_prod].astype(int)
    df[col_unid] = limpiar_numero(df[col_unid])
    
    es_kit = df[col_prod].isin(KITS_ESTRUCTURA)
    df_kits = df[es_kit]
    df_prod = df[~es_kit]
    
    acumulado = 0
    for _, row in df_kits.iterrows():
        unidades = row[col_unid]
        kit = row[col_prod]
        if kit in KITS_ESTRUCTURA:
            acumulado += unidades * len(KITS_ESTRUCTURA[kit])
        
    total = df_prod[col_unid].sum() + acumulado
    return total

def mult_shopify(df, col_prod, col_unid):
    if df.empty or col_prod not in df.columns or col_unid not in df.columns:
        return 0
        
    df = df.copy()
    df[col_prod] = df[col_prod].astype(str).str.strip().str.upper()
    df[col_unid] = limpiar_numero(df[col_unid])
    
    dict_shop = {k.upper(): v for k, v in KITS_SHOPIFY.items()}
    es_kit = df[col_prod].isin(dict_shop)
    df_kits = df[es_kit]
    df_prod = df[~es_kit]
    
    acumulado = 0
    for _, r in df_kits.iterrows():
        prod_key = r[col_prod]
        if prod_key in dict_shop:
            acumulado += r[col_unid] * len(dict_shop[prod_key])
        
    return df_prod[col_unid].sum() + acumulado


def control_gerencial():
    mes_act = datetime.now().month

    # Códigos de filtro exclusivos para Cantabria
    CODIGOS_CANTABRIA = [
        22719, 22705, 22704, 22713, 22720, 22721, 22715, 22701, 22707, 
        22706, 22716, 22702, 22712, 22703, 22718, 22711, 22710, 22714, 
        22717, 22709, 22708
    ]

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

    def fmt_n(v): return f"{int(round(v)):,}".replace(",", ".") if v != 0 else "-"
    def fmt_p(v): return f"{v:.1%}" if v != 0 else "-"

    # ==========================================
    # FUNCIONES DE CARGA AUXILIARES
    # ==========================================
    def cargar_csv(path, col_u, codigos_filtrar=None, col_cod=None):
        try:
            df = pd.read_csv(path, sep="|", encoding='latin1', quotechar='"', dtype=str)
            df.columns = [c.strip() for c in df.columns]
            
            df = df.dropna(how='all')
            if len(df) > 0:
                df = df.iloc[:-1] 

            if "Importe Neto" in df.columns:
                df["Importe Neto"] = limpiar_numero(df["Importe Neto"])
                df = df[df["Importe Neto"] != 0]

            if codigos_filtrar is not None and col_cod in df.columns:
                df[col_cod] = pd.to_numeric(df[col_cod], errors='coerce').fillna(0).astype(int)
                df = df[df[col_cod].isin(codigos_filtrar)]

            if col_cod in df.columns and col_u in df.columns:
                u = mult_farma(df, col_prod=col_cod, col_unid=col_u)
            elif col_u in df.columns:
                u = limpiar_numero(df[col_u]).sum()
            else:
                u = 0

            n = df["Importe Neto"].sum() if "Importe Neto" in df.columns else 0
            return u, n
        except Exception as e:
            st.warning(f"Aviso al cargar {path}: {e}")
            return 0, 0

    def obtener_valor_excel(path, hoja, anio, mes, codigos_filtrar=None):
        try:
            df = pd.read_excel(path, sheet_name=hoja)
            if df.empty:
                return 0

            # Si se solicita filtrar por códigos de producto (para Cantabria)
            if codigos_filtrar is not None:
                col_codigo = df.columns[0] # Se asume la primera columna como código
                df_cods = pd.to_numeric(df[col_codigo], errors='coerce').fillna(-1).astype(int)
                df = df[df_cods.isin(codigos_filtrar)]

            for col in df.columns:
                col_str = str(col).strip()
                dt = pd.to_datetime(col, dayfirst=True, errors='coerce')
                
                # Coincidencia 1: Cuando la columna es parseable como Timestamp de Pandas
                if pd.notnull(dt):
                    a_real = dt.year + 2000 if dt.year < 100 else dt.year
                    if a_real == anio and dt.month == mes:
                        return limpiar_numero(df[col]).sum()
                
                # Coincidencia 2: Cuando la columna viene formateada como texto (ej: "2026-07", "07/2026", etc.)
                if str(anio) in col_str and (f"/{mes:02d}/" in col_str or f"-{mes:02d}-" in col_str or f"_{mes:02d}" in col_str or col_str.endswith(f"-{mes}") or col_str.endswith(f"/{mes}")):
                    return limpiar_numero(df[col]).sum()

            return 0
        except Exception as e:
            st.warning(f"Aviso leyendo Excel ({hoja} en {path}): {e}")
            return 0


    # =========================================================================
    # BLOQUE 1: CUADRO CAVIAHUE
    # =========================================================================
    st.markdown("### Cuadro de avance del mes - Caviahue")
    
    u_dis, n_dis = cargar_csv("descargas/venta_neta_por_periodo_producto_cliente.csv", "Venta Unid.", col_cod="PRODU.")
    u_pre, n_pre = cargar_csv("descargas/preventa_por_producto.csv", "Un. Reserv.", col_cod="Producto")

    try:
        df_t = pd.read_excel("data/TANGO.xlsx", sheet_name="Datos")
        df_t.columns = [c.strip() for c in df_t.columns]
        df_t["Cód. Artículo"] = pd.to_numeric(df_t["Cód. Artículo"], errors='coerce').fillna(0).astype(int)
        df_t = df_t[~df_t['Cód. Artículo'].isin([4, 10, 3, 12, 21302, 21304, 21633, 19039])]
        
        df_t["Total"] = limpiar_numero(df_t["Total"])
        df_t_act = df_t[df_t['Total'] != 0]
        
        u_tan = mult_farma(df_t_act, col_prod="Cód. Artículo", col_unid="Cantidad")
        n_tan = df_t_act['Total'].sum()
    except Exception as e: 
        st.warning(f"Aviso en Tango Caviahue: {e}")
        u_tan, n_tan = 0, 0
    
    try:
        df_s = pd.read_csv("descargas/ventas_caviahue_shopify.csv")
        df_s.columns = [c.strip() for c in df_s.columns]
        u_shp = mult_shopify(df_s, col_prod="product_title", col_unid="unidades")
        n_shp = limpiar_numero(df_s["neta_sin_impuestos"]).sum() if "neta_sin_impuestos" in df_s.columns else 0
    except Exception as e: 
        st.warning(f"Aviso en Shopify Caviahue: {e}")
        u_shp, n_shp = 0, 0

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

    u_dis_cant, n_dis_cant = cargar_csv("descargas/venta_neta_por_periodo_producto_cliente.csv", "Venta Unid.", CODIGOS_CANTABRIA, "PRODU.")
    u_pre_cant, n_pre_cant = cargar_csv("descargas/preventa_por_producto.csv", "Un. Reserv.", CODIGOS_CANTABRIA, "Producto")

    try:
        df_t_cant = pd.read_excel("data/TANGO.xlsx", sheet_name="Datos")
        df_t_cant.columns = [c.strip() for c in df_t_cant.columns]
        df_t_cant["Cód. Artículo"] = pd.to_numeric(df_t_cant["Cód. Artículo"], errors='coerce').fillna(0).astype(int)
        df_t_cant = df_t_cant[df_t_cant['Cód. Artículo'].isin(CODIGOS_CANTABRIA)]
        
        df_t_cant["Total"] = limpiar_numero(df_t_cant["Total"])
        df_t_cant_act = df_t_cant[df_t_cant['Total'] != 0]
        
        u_tan_cant = mult_farma(df_t_cant_act, col_prod="Cód. Artículo", col_unid="Cantidad")
        n_tan_cant = df_t_cant_act['Total'].sum()
    except Exception as e: 
        st.warning(f"Aviso en Tango Cantabria: {e}")
        u_tan_cant, n_tan_cant = 0, 0

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