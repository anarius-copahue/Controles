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
        mes_actual, anio_actual = ahora.month, ahora.year
        a2024, a2025 = 2024, 2025

        cols_fechas = {col: pd.to_datetime(col, dayfirst=True) for col in df_hist.columns 
                       if isinstance(col, (datetime.datetime, str)) and any(char.isdigit() for char in str(col))}
        
        df_hist["Venta 2024"] = df_hist[[c for c, dt in cols_fechas.items() if dt.year == a2024]].sum(axis=1)
        df_hist["Venta 2025"] = df_hist[[c for c, dt in cols_fechas.items() if dt.year == a2025]].sum(axis=1)
        df_hist["Venta 2025 YTD"] = df_hist[[c for c, dt in cols_fechas.items() if dt.year == a2025 and dt.month <= mes_actual]].sum(axis=1)
        df_hist["Hist_Act"] = df_hist[[c for c, dt in cols_fechas.items() if dt.year == anio_actual]].sum(axis=1)
        
        df_hist_resumen = df_hist[["N° CLIENTE", "Venta 2024", "Venta 2025", "Venta 2025 YTD", "Hist_Act"]].groupby("N° CLIENTE").sum().reset_index()
    except:
        df_hist_resumen = pd.DataFrame(columns=["N° CLIENTE", "Venta 2024", "Venta 2025", "Venta 2025 YTD", "Hist_Act"])

    # --- 1. CARGA VENTAS ACTUALES ---
    try:
        # (Misma lógica de carga que el anterior para no perder funcionalidad)
        df_venta = pd.read_csv("descargas/preventa_por_cliente.csv", sep="|").rename(columns={"Clie": "Cliente"})
        df_venta["Caviahue"] = df_venta["Unidades"]
        df_preventa = pd.read_csv("descargas/venta_neta_por_periodo_producto_cliente.csv", sep="|")
        df_preventa["Caviahue"] = np.where(~df_preventa['PRODU.'].isin([21304, 21302]), df_preventa["Venta Unid."], 0)

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
        except: df_tango = pd.DataFrame(columns=["Cliente", "Caviahue"])

        ventas_mes = pd.concat([df_preventa[["Cliente", "Caviahue"]], df_venta[["Cliente", "Caviahue"]], df_tango[["Cliente", "Caviahue"]]])
        ventas_mes = ventas_mes.groupby("Cliente")["Caviahue"].sum().reset_index().rename(columns={"Caviahue": "Venta Mes Actual"})
        ventas_mes["Cliente"] = pd.to_numeric(ventas_mes["Cliente"], errors='coerce').fillna(0).astype(int)
    except:
        ventas_mes = pd.DataFrame(columns=["Cliente", "Venta Mes Actual"])

    # --- 2. INTEGRACIÓN ---
    if not representantes: representantes = list(REPRESENTANTE_POR_USUARIO.keys())
    nombres_planillas = [nombre for u in representantes if u in REPRESENTANTE_POR_USUARIO for nombre in REPRESENTANTE_POR_USUARIO[u]]
            
    hojas_rep = {}
    for nombre in nombres_planillas:
        try:
            df_rep = pd.read_excel(archivo_excel, sheet_name=nombre)
            df_rep["N° CLIENTE_INT"] = pd.to_numeric(df_rep["N° CLIENTE"], errors='coerce').fillna(0).astype(int)
            df_rep = df_rep.drop(columns=["Total Caviahue"], errors="ignore").merge(ventas_mes, left_on="N° CLIENTE_INT", right_on="Cliente", how="left").drop(columns=["Cliente"], errors="ignore")
            df_rep = df_rep.merge(df_hist_resumen, left_on="N° CLIENTE_INT", right_on="N° CLIENTE", how="left", suffixes=('', '_hist')).fillna(0)
            df_rep["Acumulado año"] = df_rep["Hist_Act"] + df_rep["Venta Mes Actual"]
            
            t_mask = df_rep["CLIENTE"].astype(str).str.contains("TOTAL", case=False, na=False)
            gid = t_mask.cumsum()
            for g in gid[t_mask].unique():
                m = (gid == g); idx = df_rep[m & t_mask].index[0]; h = m & (~t_mask)
                for c in ["Cuota Caviahue", "Venta Mes Actual", "Venta 2024", "Venta 2025", "Acumulado año", "Venta 2025 YTD"]:
                    df_rep.loc[idx, c] = df_rep.loc[h, c].sum()

            df_rep["Avance %"] = (df_rep["Venta Mes Actual"] / df_rep["Cuota Caviahue"] * 100).replace([np.inf, -np.inf], 0).fillna(0)
            df_rep["growth 2025"] = np.where(df_rep["Venta 2024"] > 0, ((df_rep["Venta 2025"] / df_rep["Venta 2024"]) - 1) * 100, 0)
            df_rep["growth 2026"] = np.where(df_rep["Venta 2025 YTD"] > 0, ((df_rep["Acumulado año"] / df_rep["Venta 2025 YTD"]) - 1) * 100, 0)
            
            hojas_rep[nombre] = df_rep[["N° CLIENTE", "CLIENTE", "Cuota Caviahue", "Venta Mes Actual", "Avance %", "Venta 2024", "Venta 2025", "growth 2025", "Acumulado año", "growth 2026", "Venta 2025 YTD"]]
        except: pass

    # --- 3. UI ---
    st.title("📊 Control de Cuotas Caviahue")
    
    res_list = []
    for n, df in hojas_rep.items():
        mc = pd.to_numeric(df["N° CLIENTE"], errors='coerce') > 0
        res_list.append({
            "Rep": n, 
            "Cuota": float(df[mc]["Cuota Caviahue"].sum()), 
            "Venta": float(df[mc]["Venta Mes Actual"].sum()), 
            "V24": float(df[mc]["Venta 2024"].sum()), 
            "V25": float(df[mc]["Venta 2025"].sum()), 
            "Acum": float(df[mc]["Acumulado año"].sum()),
            "V25_YTD": float(df[mc]["Venta 2025 YTD"].sum())
        })
    
    resumen = pd.DataFrame(res_list)
    if not resumen.empty:
        # Definición de pesos de columnas (Única fuente de verdad para alineación)
        col_weights = [0.4, 1.8, 0.8, 0.8, 0.6, 0.8, 0.8, 0.6, 0.8, 0.6]

        # --- ENCABEZADO ALINEADO ---
        # Usamos un contenedor con fondo gris para simular la cabecera
        with st.container():
            st.markdown("""
                <style>
                [data-testid="column"] { text-align: center; }
                .header-text { font-weight: bold; font-size: 11px; color: #555; text-transform: uppercase; }
                </style>
            """, unsafe_allow_html=True)
            
            h_cols = st.columns(col_weights)
            headers = ["", "Representante", "Cuota", "Venta", "Av %", "V. 2024", "V. 2025", "G'25", "Acum'26", "G'26"]
            for col, text in zip(h_cols, headers):
                if text: col.markdown(f"<p class='header-text'>{text}</p>", unsafe_allow_html=True)
        
        st.markdown("<hr style='margin-top:0; margin-bottom:10px; border: 0.5px solid #ddd;'>", unsafe_allow_html=True)

        # --- FILAS DE DATOS ---
        for i, r in resumen.iterrows():
            key = f"exp_{usuario_id}_{i}"
            if key not in st.session_state: st.session_state[key] = False
            
            cols = st.columns(col_weights)
            
            # Botón
            if cols[0].button("➕" if not st.session_state[key] else "➖", key=f"b_{usuario_id}_{i}"):
                st.session_state[key] = not st.session_state[key]
                st.rerun()
            
            cols[1].write(f"**{r['Rep']}**")
            cols[2].write(f"{int(r['Cuota']):,}".replace(",", "."))
            cols[3].write(f"{int(r['Venta']):,}".replace(",", "."))
            cols[4].write(f"{int(r['Venta']/r['Cuota']*100 if r['Cuota']>0 else 0)}%")
            cols[5].write(f"{int(r['V24']):,}".replace(",", "."))
            cols[6].write(f"{int(r['V25']):,}".replace(",", "."))
            
            g25 = ((r['V25']/r['V24'])-1)*100 if r['V24']>0 else 0
            cols[7].markdown(f":{'green' if g25 >= 0 else 'red'}[{int(g25)}%]")
            
            cols[8].write(f"{int(r['Acum']):,}".replace(",", "."))
            
            g26 = ((r['Acum']/r['V25_YTD'])-1)*100 if r['V25_YTD']>0 else 0
            cols[9].markdown(f":{'green' if g26 >= 0 else 'red'}[{int(g26)}%]")

            # Expandible (Tabla Detalle)
            if st.session_state[key]:
                df_disp = hojas_rep[r["Rep"]].copy().drop(columns=["Venta 2025 YTD"], errors="ignore")
                df_disp["N° CLIENTE"] = pd.to_numeric(df_disp["N° CLIENTE"], errors='coerce').fillna(0).astype(int)
                
                styler = df_disp.style.apply(resaltar_totales, axis=1).format({
                    "N° CLIENTE": "{:d}", "Cuota Caviahue": "{:,.0f}", "Venta Mes Actual": "{:,.0f}",
                    "Avance %": "{:.1f}%", "Venta 2024": "{:,.0f}", "Venta 2025": "{:,.0f}",
                    "growth 2025": "{:.1f}%", "Acumulado año": "{:,.0f}", "growth 2026": "{:.1f}%"
                }).hide(axis="index")

                st.markdown(f'<div style="overflow-x:auto;">{styler.to_html()}</div>', unsafe_allow_html=True)
                
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    df_disp.to_excel(writer, index=False)
                st.download_button(f"📥 Excel {r['Rep']}", output.getvalue(), f"{r['Rep']}.xlsx", key=f"d_{usuario_id}_{i}")
            
            st.markdown("<hr style='margin:5px 0px; border: 0.2px solid #eee;'>", unsafe_allow_html=True)