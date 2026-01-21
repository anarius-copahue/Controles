import streamlit as st
import pandas as pd
import numpy as np
import io
import datetime
import os

# Importamos tu función de encriptación
from encrypt import encrypt_file

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
    """Aplica color gris clarito a las filas que contienen 'TOTAL' en la columna CLIENTE"""
    # Usamos .get para evitar errores si la columna no existe en ese momento
    cliente_val = str(row.get('CLIENTE', '')).upper()
    if 'TOTAL' in cliente_val:
        return ['background-color: #f0f0f0'] * len(row)
    return [''] * len(row)

def cuotas(representantes=[], usuario_id="default"):
    archivo_excel = "data/representante.xlsx"
    archivo_historico = "data/Historico.xlsx"
    
    key_enc = st.secrets["ENCRYPTION_KEY"].encode() if "ENCRYPTION_KEY" in st.secrets else None

    # --- 0. PROCESAR HISTÓRICO ---
    try:
        df_hist = pd.read_excel(archivo_historico)
        df_hist = df_hist.dropna(subset=["N° CLIENTE"])
        df_hist["N° CLIENTE"] = df_hist["N° CLIENTE"].astype(int)
        
        ahora = datetime.datetime.now()
        mes_actual = ahora.month
        anio_actual = ahora.year
        anio_anterior = ahora.year - 1

        cols_fechas = {col: pd.to_datetime(col, dayfirst=True) for col in df_hist.columns if isinstance(col, (datetime.datetime, str)) and any(char.isdigit() for char in str(col))}

        cols_aa = [c for c, dt in cols_fechas.items() if dt.year == anio_anterior]
        df_hist["Venta Año Anterior"] = df_hist[cols_aa].sum(axis=1)

        cols_aa_ytd = [c for c, dt in cols_fechas.items() if dt.year == anio_anterior and dt.month <= mes_actual]
        df_hist["Venta AA YTD"] = df_hist[cols_aa_ytd].sum(axis=1)

        cols_act = [c for c, dt in cols_fechas.items() if dt.year == anio_actual]
        df_hist["Hist_Act"] = df_hist[cols_act].sum(axis=1)
        
        df_hist_resumen = df_hist[["N° CLIENTE", "Venta Año Anterior", "Venta AA YTD", "Hist_Act"]].groupby("N° CLIENTE").sum().reset_index()
    except Exception as e:
        df_hist_resumen = pd.DataFrame(columns=["N° CLIENTE", "Venta Año Anterior", "Venta AA YTD", "Hist_Act"])

    # --- 1. CARGA VENTAS ACTUALES ---
    try:
        df_venta = pd.read_csv("descargas/preventa_por_cliente.csv", sep="|").rename(columns={"Clie": "Cliente"})
        df_venta["Caviahue"] = df_venta["Unidades"]
        
        df_preventa = pd.read_csv("descargas/venta_neta_por_periodo_producto_cliente.csv", sep="|")
        def limpiar_v(v): return float(str(v).replace('$', '').replace(' ', '').replace('.', '').replace(',', '.')) if pd.notnull(v) else 0
        df_preventa["Venta Unid."] = np.where(np.isclose(df_preventa["Venta Bruta"].apply(limpiar_v), df_preventa["Dtos. en Factura"].apply(limpiar_v), atol=2), 0, df_preventa["Venta Unid."])
        df_preventa["Caviahue"] = np.where(~df_preventa['PRODU.'].isin([21304, 21302]), df_preventa["Venta Unid."], 0)

        def mult(df):
            for ids, m in [([22005,21663,22251,21657,21655,21658], 3), ([21653], 2), ([21656], 4)]:
                target = 'PRODU.' if 'PRODU.' in df.columns else 'COD_ARTICU'
                if target in df.columns: df["Caviahue"] = np.where(df[target].isin(ids), df["Caviahue"] * m, df["Caviahue"])
            return df
        df_preventa = mult(df_preventa)

        try:
            df_tango = pd.read_csv("data/TANGO.csv").rename(columns={"COD_CLI": "Cliente", "CANTIDAD": "Venta Unid."})
            df_tango["Caviahue"] = np.where(~df_tango["COD_ARTICU"].isin([21304, 21302]), df_tango["Venta Unid."], 0)
            df_tango = mult(df_tango)
        except: df_tango = pd.DataFrame(columns=["Cliente", "Caviahue"])

        ventas_mes = pd.concat([df_preventa[["Cliente", "Caviahue"]], df_venta[["Cliente", "Caviahue"]], df_tango[["Cliente", "Caviahue"]]])
        ventas_mes = ventas_mes.groupby("Cliente")["Caviahue"].sum().reset_index()
        ventas_mes.rename(columns={"Caviahue": "Venta Mes Actual"}, inplace=True)
        ventas_mes = ventas_mes.dropna(subset=["Cliente"])
        ventas_mes["Cliente"] = ventas_mes["Cliente"].astype(int)
    except:
        ventas_mes = pd.DataFrame(columns=["Cliente", "Venta Mes Actual"])

    # --- CIERRE DÍA 30 ---
    ahora = datetime.datetime.now()
    if ahora.day == 30:
        nueva_col = f"1/{ahora.month}/{ahora.year}"
        try:
            df_c = pd.read_excel(archivo_historico)
            if nueva_col not in df_c.columns:
                df_c = df_c.dropna(subset=["N° CLIENTE"])
                df_c["N° CLIENTE"] = df_c["N° CLIENTE"].astype(int)
                df_c[nueva_col] = df_c["N° CLIENTE"].map(ventas_mes.set_index("Cliente")["Venta Mes Actual"]).fillna(0).astype(int)
                df_c.to_excel(archivo_historico, index=False)
                if key_enc: encrypt_file(archivo_historico, key_enc)
        except: pass

    # --- 2. INTEGRACIÓN FINAL ---
    if not representantes: representantes = list(REPRESENTANTE_POR_USUARIO.keys())
    nombres_planillas = []
    for u in representantes:
        if u in REPRESENTANTE_POR_USUARIO: nombres_planillas.extend(REPRESENTANTE_POR_USUARIO[u])
            
    hojas_rep = {}
    for nombre in nombres_planillas:
        try:
            df_rep = pd.read_excel(archivo_excel, sheet_name=nombre)
            # Para los cálculos de merge, necesitamos N° CLIENTE temporal como int
            df_rep["N° CLIENTE_INT"] = pd.to_numeric(df_rep["N° CLIENTE"], errors='coerce')
            
            df_rep = df_rep.drop(columns=["Total Caviahue"], errors="ignore").merge(ventas_mes, left_on="N° CLIENTE_INT", right_on="Cliente", how="left").drop(columns=["Cliente"], errors="ignore")
            df_rep = df_rep.merge(df_hist_resumen, left_on="N° CLIENTE_INT", right_on="N° CLIENTE", how="left", suffixes=('', '_hist')).fillna(0)
            
            # Limpieza de columnas tras el merge
            if 'N° CLIENTE_hist' in df_rep.columns: df_rep = df_rep.drop(columns=['N° CLIENTE_hist'])
            
            df_rep["Acumulado año"] = df_rep["Hist_Act"] + df_rep["Venta Mes Actual"]
            
            # Lógica de Totales (sin filtrar las filas TOTAL)
            t_mask = df_rep["CLIENTE"].str.contains("TOTAL", case=False, na=False)
            gid = t_mask.cumsum()
            for g in gid[t_mask].unique():
                m = (gid == g); idx = df_rep[m & t_mask].index[0]; h = m & (~t_mask)
                for c in ["Cuota Caviahue", "Venta Mes Actual", "Venta Año Anterior", "Acumulado año", "Venta AA YTD"]:
                    df_rep.loc[idx, c] = df_rep.loc[h, c].sum()

            df_rep["Avance %"] = (df_rep["Venta Mes Actual"] / df_rep["Cuota Caviahue"] * 100).replace([np.inf, -np.inf], 0).fillna(0)
            df_rep["Crecimiento MMAA"] = np.where(df_rep["Venta AA YTD"] > 0, ((df_rep["Acumulado año"] / df_rep["Venta AA YTD"]) - 1) * 100, 0)
            
            orden = ["N° CLIENTE", "CLIENTE", "Cuota Caviahue", "Venta Mes Actual", "Avance %", "Venta Año Anterior", "Acumulado año", "Crecimiento MMAA", "Venta AA YTD"]
            hojas_rep[nombre] = df_rep[orden]
        except: pass

    # --- 3. UI ---
    st.title("Reporte Caviahue 2026")
    
    res_list = []
    for n, df in hojas_rep.items():
        # Para el resumen general, solo sumamos clientes reales (N° CLIENTE > 0)
        sc = df[pd.to_numeric(df["N° CLIENTE"], errors='coerce') > 0].copy()
        res_list.append({"Rep": n, "Cuota": sc["Cuota Caviahue"].sum(), "Venta": sc["Venta Mes Actual"].sum(), "VAA": sc["Venta Año Anterior"].sum(), "Acumulado año": sc["Acumulado año"].sum(), "VAA_YTD": sc["Venta AA YTD"].sum()})
    
    resumen = pd.DataFrame(res_list)
    if not resumen.empty:
        resumen["Avance"] = (resumen["Venta"] / resumen["Cuota"] * 100).fillna(0)
        resumen["Crecimiento MMAA"] = np.where(resumen["VAA_YTD"] > 0, ((resumen["Acumulado año"] / resumen["VAA_YTD"]) - 1) * 100, 0)

        # Renderizado de filas de representantes
        for i, r in resumen.iterrows():
            key = f"exp_{usuario_id}_{i}"
            if key not in st.session_state: st.session_state[key] = False
            
            cols = st.columns([0.5, 2, 1, 1, 1, 1, 1, 1])
            if cols[0].button("➕" if not st.session_state[key] else "➖", key=f"b_{usuario_id}_{i}"):
                st.session_state[key] = not st.session_state[key]
            
            cols[1].write(r["Rep"])
            cols[2].write(f"{int(r['Cuota']):,}".replace(",", "."))
            cols[3].write(f"{int(r['Venta']):,}".replace(",", "."))
            cols[4].write(f"{int(r['Avance'])}%")
            cols[5].write(f"{int(r['VAA']):,}".replace(",", "."))
            cols[6].write(f"{int(r['Acumulado año']):,}".replace(",", "."))
            color = "green" if r["Crecimiento MMAA"] >= 0 else "red"
            cols[7].markdown(f":{color}[{int(r['Crecimiento MMAA'])}%]")

            if st.session_state[key]:
                df_disp = hojas_rep[r["Rep"]].drop(columns=["Venta AA YTD"])
                
                # Formateo y Visualización de la tabla
                st.dataframe(
                    df_disp.style.apply(resaltar_totales, axis=1).format({
                        "Cuota Caviahue": "{:,.0f}", 
                        "Venta Mes Actual": "{:,.0f}",
                        "Avance %": "{:.0f}%", 
                        "Venta Año Anterior": "{:,.0f}",
                        "Acumulado año": "{:,.0f}", 
                        "Crecimiento MMAA": "{:.0f}%"
                    }), 
                    use_container_width=True, 
                    hide_index=True
                )
                
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    df_disp.to_excel(writer, index=False, sheet_name="Reporte")
                st.download_button("📥 Excel", output.getvalue(), f"{r['Rep']}_2026.xlsx", key=f"d_{usuario_id}_{i}")
            st.markdown("---")