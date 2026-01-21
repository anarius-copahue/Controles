import streamlit as st
import pandas as pd
import numpy as np
import io
import datetime

# --- CONFIGURACIÓN DE REPRESENTANTES ---
REPRESENTANTE_POR_USUARIO = {
    "KMACIAS": ["Karina Macías", "Karina Perfu y Supermercados"],
    "SROCCHI": ["Zona Norte"],
    "PZACCA": ["Patricia Zacca"],
    "MROSSELOT": ["Marcela Rosselot"],
    "LCOLOMBO": ["Lucio Colombo"],
    "YCUEZZO": ["Yanina Cuezzo"],
    "YARRECHE": ["Yamila Arreche"],
    "EVEIGA": ["Emiliano Veiga"],
    "JANDERMARCH": ["Jessica Andermarch"],
    "NBRIDI":["Natalia Bridi"],
    "OTROS" : [ "Gerencia" ],
}

def resaltar_totales(row):
    """Lógica de color para las filas de TOTAL"""
    cliente_val = str(row.get('CLIENTE', '')).upper()
    if 'TOTAL' in cliente_val:
        return ['background-color: #f0f0f0; font-weight: bold'] * len(row)
    return [''] * len(row)

def cuotas(representantes=[], usuario_id="default"):
    archivo_excel = "data/representante.xlsx"
    archivo_historico = "data/Historico.xlsx"
    
    # --- 0. PROCESAR HISTÓRICO ---
    try:
        df_hist = pd.read_excel(archivo_historico)
        df_hist = df_hist.dropna(subset=["N° CLIENTE"])
        df_hist["N° CLIENTE"] = pd.to_numeric(df_hist["N° CLIENTE"], errors='coerce').fillna(0).astype(int)
        
        ahora = datetime.datetime.now()
        mes_actual, anio_actual, anio_anterior = ahora.month, ahora.year, ahora.year - 1

        cols_fechas = {col: pd.to_datetime(col, dayfirst=True) for col in df_hist.columns 
                       if isinstance(col, (datetime.datetime, str)) and any(char.isdigit() for char in str(col))}
        
        # Sumamos columnas por año
        df_hist["Venta Año Anterior"] = df_hist[[c for c, dt in cols_fechas.items() if dt.year == anio_anterior]].sum(axis=1)
        df_hist["Venta AA YTD"] = df_hist[[c for c, dt in cols_fechas.items() if dt.year == anio_anterior and dt.month <= mes_actual]].sum(axis=1)
        df_hist["Hist_Act"] = df_hist[[c for c, dt in cols_fechas.items() if dt.year == anio_actual]].sum(axis=1)
        
        df_hist_resumen = df_hist[["N° CLIENTE", "Venta Año Anterior", "Venta AA YTD", "Hist_Act"]].groupby("N° CLIENTE").sum().reset_index()
    except:
        df_hist_resumen = pd.DataFrame(columns=["N° CLIENTE", "Venta Año Anterior", "Venta AA YTD", "Hist_Act"])

    # --- 1. CARGA VENTAS ACTUALES (TANGO + PREVENTA) ---
    try:
        df_venta = pd.read_csv("descargas/preventa_por_cliente.csv", sep="|").rename(columns={"Clie": "Cliente"})
        df_venta["Caviahue"] = df_venta["Unidades"]
        
        df_preventa = pd.read_csv("descargas/venta_neta_por_periodo_producto_cliente.csv", sep="|")
        df_preventa["Caviahue"] = np.where(~df_preventa['PRODU.'].isin([21304, 21302]), df_preventa["Venta Unid."], 0)

        # Lógica de Multiplicadores (Despaconado)
        def mult(df):
            for ids, m in [([22005,21663,22251,21657,21655,21658], 3), ([21653], 2), ([21656], 4)]:
                target = 'PRODU.' if 'PRODU.' in df.columns else 'COD_ARTICU'
                if target in df.columns: 
                    df["Caviahue"] = np.where(df[target].isin(ids), df["Caviahue"] * m, df["Caviahue"])
            return df
        
        df_preventa = mult(df_preventa)

        try:
            df_tango = pd.read_csv("data/TANGO.csv").rename(columns={"COD_CLI": "Cliente", "CANTIDAD": "Venta Unid."})
            df_tango["Caviahue"] = np.where(~df_tango["COD_ARTICU"].isin([21304, 21302]), df_tango["Venta Unid."], 0)
            df_tango = mult(df_tango)
        except: 
            df_tango = pd.DataFrame(columns=["Cliente", "Caviahue"])

        ventas_mes = pd.concat([df_preventa[["Cliente", "Caviahue"]], df_venta[["Cliente", "Caviahue"]], df_tango[["Cliente", "Caviahue"]]])
        ventas_mes = ventas_mes.groupby("Cliente")["Caviahue"].sum().reset_index().rename(columns={"Caviahue": "Venta Mes Actual"})
        ventas_mes["Cliente"] = pd.to_numeric(ventas_mes["Cliente"], errors='coerce').fillna(0).astype(int)
    except:
        ventas_mes = pd.DataFrame(columns=["Cliente", "Venta Mes Actual"])

    # --- 2. INTEGRACIÓN Y CÁLCULOS POR REPRESENTANTE ---
    if not representantes: representantes = list(REPRESENTANTE_POR_USUARIO.keys())
    nombres_planillas = [nombre for u in representantes if u in REPRESENTANTE_POR_USUARIO for nombre in REPRESENTANTE_POR_USUARIO[u]]
            
    hojas_rep = {}
    for nombre in nombres_planillas:
        try:
            df_rep = pd.read_excel(archivo_excel, sheet_name=nombre)
            df_rep["N° CLIENTE_INT"] = pd.to_numeric(df_rep["N° CLIENTE"], errors='coerce').fillna(0).astype(int)
            
            # Merges
            df_rep = df_rep.drop(columns=["Total Caviahue"], errors="ignore").merge(ventas_mes, left_on="N° CLIENTE_INT", right_on="Cliente", how="left").drop(columns=["Cliente"], errors="ignore")
            df_rep = df_rep.merge(df_hist_resumen, left_on="N° CLIENTE_INT", right_on="N° CLIENTE", how="left", suffixes=('', '_hist')).fillna(0)
            
            df_rep["Acumulado año"] = df_rep["Hist_Act"] + df_rep["Venta Mes Actual"]
            
            # Recalcular filas de TOTAL
            t_mask = df_rep["CLIENTE"].astype(str).str.contains("TOTAL", case=False, na=False)
            gid = t_mask.cumsum()
            for g in gid[t_mask].unique():
                m = (gid == g); idx = df_rep[m & t_mask].index[0]; h = m & (~t_mask)
                for c in ["Cuota Caviahue", "Venta Mes Actual", "Venta Año Anterior", "Acumulado año", "Venta AA YTD"]:
                    if c in df_rep.columns:
                        df_rep.loc[idx, c] = df_rep.loc[h, c].sum()

            df_rep["Avance %"] = (df_rep["Venta Mes Actual"] / df_rep["Cuota Caviahue"] * 100).replace([np.inf, -np.inf], 0).fillna(0)
            df_rep["Crecimiento MMAA"] = np.where(df_rep["Venta AA YTD"] > 0, ((df_rep["Acumulado año"] / df_rep["Venta AA YTD"]) - 1) * 100, 0)
            
            hojas_rep[nombre] = df_rep[["N° CLIENTE", "CLIENTE", "Cuota Caviahue", "Venta Mes Actual", "Avance %", "Venta Año Anterior", "Acumulado año", "Crecimiento MMAA", "Venta AA YTD"]]
        except: pass

    # --- 3. UI Y RENDERIZADO ---
    st.markdown("""<style>
        [data-testid="stMetricValue"] { font-size: 24px; }
        .rep-header { background-color: #f8f9fa; padding: 10px; border-radius: 5px; margin: 5px 0; border: 1px solid #eee; }
    </style>""", unsafe_allow_html=True)

    res_list = []
    for n, df in hojas_rep.items():
        mc = pd.to_numeric(df["N° CLIENTE"], errors='coerce') > 0
        res_list.append({
            "Rep": n, "Cuota": float(df[mc]["Cuota Caviahue"].sum()), 
            "Venta": float(df[mc]["Venta Mes Actual"].sum()), 
            "VAA_YTD": float(df[mc]["Venta AA YTD"].sum()), 
            "Acum": float(df[mc]["Acumulado año"].sum()), 
            "VAA": float(df[mc]["Venta Año Anterior"].sum())
        })
    
    resumen = pd.DataFrame(res_list)
    if not resumen.empty:
        tc, tv, ta, ty = resumen["Cuota"].sum(), resumen["Venta"].sum(), resumen["Acum"].sum(), resumen["VAA_YTD"].sum()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Venta Mes", f"{int(tv):,}".replace(",", "."), f"{int(tv/tc*100 if tc>0 else 0)}% Avance")
        m2.metric("Cuota Total", f"{int(tc):,}".replace(",", "."))
        m3.metric("Acumulado Año", f"{int(ta):,}".replace(",", "."))
        m4.metric("Crecimiento YTD", f"{int((ta/ty-1)*100 if ty>0 else 0)}%", delta_color="normal")
        st.markdown("---")

        for i, r in resumen.iterrows():
            key = f"exp_{usuario_id}_{i}"
            if key not in st.session_state: st.session_state[key] = False
            
            cols = st.columns([0.5, 2, 1, 1, 1, 1, 1, 1])
            if cols[0].button("➕" if not st.session_state[key] else "➖", key=f"b_{usuario_id}_{i}"):
                st.session_state[key] = not st.session_state[key]
            
            cols[1].write(f"**{r['Rep']}**")
            cols[2].write(f"{int(r['Cuota']):,}".replace(",", "."))
            cols[3].write(f"{int(r['Venta']):,}".replace(",", "."))
            cols[4].write(f"{int(r['Venta']/r['Cuota']*100 if r['Cuota']>0 else 0)}%")
            cols[5].write(f"{int(r['VAA']):,}".replace(",", "."))
            cols[6].write(f"{int(r['Acum']):,}".replace(",", "."))
            crec_val = (r['Acum']/r['VAA_YTD']-1)*100 if r['VAA_YTD']>0 else 0
            cols[7].markdown(f":{'green' if crec_val >= 0 else 'red'}[{int(crec_val)}%]")

            if st.session_state[key]:
                df_disp = hojas_rep[r["Rep"]].copy().drop(columns=["Venta AA YTD"], errors="ignore")
                
                # Renderizado HTML para evitar error LargeUtf8
                styler = df_disp.style.apply(resaltar_totales, axis=1).format({
                    "Cuota Caviahue": "{:,.0f}", "Venta Mes Actual": "{:,.0f}",
                    "Avance %": "{:.1f}%", "Venta Año Anterior": "{:,.0f}",
                    "Acumulado año": "{:,.0f}", "Crecimiento MMAA": "{:.1f}%"
                }).hide(axis="index")

                custom_css = """<style>
                    .table-container { width: 100%; overflow-x: auto; margin: 10px 0; }
                    table { width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 13px; }
                    th { background-color: #f1f3f6; color: #333; padding: 10px; text-align: left; border: 1px solid #dee2e6; }
                    td { padding: 8px; border: 1px solid #dee2e6; }
                </style>"""
                
                st.markdown(custom_css + f'<div class="table-container">{styler.to_html()}</div>', unsafe_allow_html=True)
                
                # Descarga Excel
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    df_disp.to_excel(writer, index=False)
                st.download_button("📥 Descargar Excel", output.getvalue(), f"{r['Rep']}.xlsx", key=f"d_{usuario_id}_{i}")
            st.markdown("---")