import pandas as pd
import streamlit as st
from datetime import datetime

def control_gerencial():
    st.markdown("### 📊 Tablero de Control Gerencial - Caviahue")
    mes_act = datetime.now().month

    # ==========================================
    # 1. FUNCIONES DE CARGA
    # ==========================================
    def cargar_csv(path, col_u):
        try:
            df = pd.read_csv(path, sep="|", decimal=',', thousands='.', encoding='latin1', quotechar='"')
            df.columns = [c.strip() for c in df.columns]
            df = df.iloc[:-1] # Eliminar última fila de totales
            df = df[df["Importe Neto"] != 0] # Eliminar filas con importe 0
            
            u = pd.to_numeric(df[col_u], errors='coerce').fillna(0).sum()
            n = pd.to_numeric(df["Importe Neto"], errors='coerce').fillna(0).sum()
            return u, n
        except Exception as e:
            st.error(f"Error en {path}: {e}")
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

    # ==========================================
    # 2. PROCESAMIENTO DE DATOS
    # ==========================================
    
    # Venta y Preventa
    u_dis, n_dis = cargar_csv("descargas/venta_neta_por_periodo_producto_cliente.csv", "Venta Unid.")
    u_pre, n_pre = cargar_csv("descargas/preventa_por_producto.csv", "Un. Reserv.")

    # Tango
    # --- TANGO (Ajustado según imagen) ---
    try:
        # Según la imagen, el archivo usa tabulaciones (\t) o es un Excel directo. 
        # Si es CSV, mantenemos sep="\t". Si es Excel, usar pd.read_excel.
        df_t = pd.read_csv("data/TANGO.csv")
        df_t.columns = [c.strip().upper() for c in df_t.columns]
        
        # 1. Filtro minimalista: eliminar códigos de servicio/descuento
        df_t = df_t[df_t['COD_ARTICU'] != 1]
        df_t = df_t[df_t['COD_ARTICU'] != 2]
        df_t = df_t[df_t['COD_ARTICU'] != 3]
        df_t = df_t[df_t['COD_ARTICU'] != 6]
        
        # 2. Conversión Numérica Limpia
        # Convertimos a string, quitamos puntos, cambiamos coma por punto y pasamos a float
        def limpiar_tango(col):
            return pd.to_numeric(
                col.astype(str)
                .str.replace(".", "", regex=False)
                .str.replace(",", ".", regex=False)
                .str.strip(), 
                errors='coerce'
            ).fillna(0)

        df_t['NETO_LIMPIO'] = limpiar_tango(df_t['TOT_S_IMP'])
        df_t['CANT_LIMPIA'] = limpiar_tango(df_t['CANTIDAD'])
        
        # 3. Solo sumamos si el neto es distinto de 0
        mask_t = df_t['NETO_LIMPIO'] != 0
        u_tan = df_t.loc[mask_t, 'CANT_LIMPIA'].sum()
        n_tan = df_t.loc[mask_t, 'NETO_LIMPIO'].sum()
        
    except Exception as e:
        st.error(f"Error procesando Tango: {e}")
        u_tan, n_tan = 0, 0

    # Shopify
    try:
        df_s = pd.read_csv("descargas/ventas_caviahue_shopify.csv")
        u_shp, n_shp = df_s['unidades'].sum(), df_s['neta_sin_impuestos'].sum()
    except: u_shp, n_shp = 0, 0

    # ==========================================
    # 3. PLANES E HISTÓRICOS (Hojas ONLINE y FARMA)
    # ==========================================
    # PLANES 2026
    v_plan_online = obtener_valor_excel("data/Cuota_Productos.xlsx", "ONLINE", 2026, mes_act)
    v_plan_farma = obtener_valor_excel("data/Cuota_Productos.xlsx", "FARMA", 2026, mes_act)
    
    # HISTÓRICOS 2025 (Año Anterior)
    v_hist_online = obtener_valor_excel("data/Historico_Productos.xlsx", "ONLINE", 2025, mes_act)
    v_hist_farma = obtener_valor_excel("data/Historico_Productos.xlsx", "FARMA", 2025, mes_act)

    # ==========================================
    # 4. CONSOLIDACIÓN ESTRUCTURADA
    # ==========================================
    u_farma_total = u_dis + u_pre + u_tan
    n_farma_total = n_dis + n_pre + n_tan

    res = [
        ["VENTA ONLINE", u_shp, n_shp, v_plan_online, (u_shp/v_plan_online if v_plan_online else 0), v_hist_online, (u_shp/v_hist_online if v_hist_online else 0)],
        ["   Venta Shopify", u_shp, n_shp, 0, 0, 0, 0],
        ["FARMA Y PERFUMERÍA", u_farma_total, n_farma_total, v_plan_farma, (u_farma_total/v_plan_farma if v_plan_farma else 0), v_hist_farma, (u_farma_total/v_hist_farma if v_hist_farma else 0)],
        ["   Tango (Directo)", u_tan, n_tan, 0, 0, 0, 0],
        ["   Disprofarma", u_dis, n_dis, 0, 0, 0, 0],
        ["   Preventa", u_pre, n_pre, 0, 0, 0, 0],
        ["TOTAL CAVIAHUE", (u_shp+u_farma_total), (n_shp+n_farma_total), (v_plan_online+v_plan_farma), 0, (v_hist_online+v_hist_farma), 0]
    ]
    
    # Porcentajes fila TOTAL
    res[-1][4] = res[-1][1] / res[-1][3] if res[-1][3] > 0 else 0
    res[-1][6] = res[-1][1] / res[-1][5] if res[-1][5] > 0 else 0

    df_res = pd.DataFrame(res, columns=["Canal", "Unidades", "Neto", "Plan", "% Plan", "AA", "% AA"])

    # ==========================================
    # 5. FORMATO Y RENDER
    # ==========================================
    def f_n(v): return f"{v:,.0f}".replace(",", ".") if v != 0 else "-"
    def f_p(v): return f"{v:.1%}" if v != 0 else "-"

    st.table(df_res.style.apply(lambda x: [
        'background-color: #F0F2F6; font-weight: bold' if x.name in [0, 2, 6] else '' for _ in x
    ], axis=1).format({
        "Unidades": f_n, "Neto": lambda x: f"$ {f_n(x)}" if x != 0 else "-",
        "Plan": f_n, "AA": f_n, "% Plan": f_p, "% AA": f_p
    }))