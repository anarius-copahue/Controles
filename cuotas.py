import streamlit as st
import pandas as pd
import numpy as np
import io
import datetime
import kits_config as KITS_ESTRUCTURA

# --- CONFIGURACIÓN DE REPRESENTANTES ---
REPRESENTANTE_POR_USUARIO = {
    "MROSSELOT": ["Marcela Rosselot"],
    "PZACCA": ["Patricia Zacca"],
    "YARRECHE": ["Yamila Arreche"],
    "AFLEBA": ["Agustin Fleba"],
    "YCUEZZO": ["Yanina Cuezzo"],
    "SROCCHI": ["Santiago Rocchi"],
    "NBRIDI":["Natalia Bridi"],
    "OTROS" : [ "Gerencia","Mendoza","Mar del Plata" ],
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

        cols_fechas = {}
        for col in df_hist.columns:
            try:
                dt = pd.to_datetime(col, dayfirst=True, errors="coerce")
                if pd.notna(dt):
                    cols_fechas[col] = dt
            except:
                pass
        
        df_hist["Venta 2024"] = df_hist[[c for c, dt in cols_fechas.items() if dt.year == a2024]].sum(axis=1)
        df_hist["Venta 2025"] = df_hist[[c for c, dt in cols_fechas.items() if dt.year == a2025]].sum(axis=1)
        df_hist["Venta 2025 YTD"] = df_hist[[c for c, dt in cols_fechas.items() if dt.year == a2025 and dt.month <= mes_actual]].sum(axis=1)
        df_hist["Hist_Act"] = df_hist[[c for c, dt in cols_fechas.items() if dt.year == anio_actual]].sum(axis=1)
        
        df_hist_resumen = df_hist[["N° CLIENTE", "Venta 2024", "Venta 2025", "Venta 2025 YTD", "Hist_Act"]].groupby("N° CLIENTE").sum().reset_index()
    except Exception as e:
        df_hist_resumen = pd.DataFrame(columns=["N° CLIENTE", "Venta 2024", "Venta 2025", "Venta 2025 YTD", "Hist_Act"])

    # --- 1. CARGA VENTAS ACTUALES ---
    try:
        df_venta = pd.read_csv("descargas/preventa_por_cliente.csv", sep="|", decimal=',', thousands='.', quotechar='"', encoding='latin1').rename(columns={"Clie": "Cliente"})
        df_venta["Caviahue"] = df_venta["Unidades"]
        
        df_preventa = pd.read_csv("descargas/venta_neta_por_periodo_producto_cliente.csv", sep="|", decimal=',', thousands='.', quotechar='"', encoding='latin1').rename(columns={"Cliente": "Cliente"})
        df_preventa["Importe Neto"] = pd.to_numeric(df_preventa["Importe Neto"], errors='coerce').fillna(0)
        df_preventa = df_preventa[df_preventa["Importe Neto"] != 0].copy()
        df_preventa["Caviahue"] = df_preventa["Venta Unid."]

        def mult(df):
            target = 'PRODU.' if 'PRODU.' in df.columns else 'COD_ARTICU'
            if target in df.columns:
                ids_df = pd.to_numeric(df[target], errors='coerce')
                try:
                    dict_real = KITS_ESTRUCTURA if isinstance(KITS_ESTRUCTURA, dict) else KITS_ESTRUCTURA.KITS_ESTRUCTURA
                    map_mult = {int(k): len(v) for k, v in dict_real.items()}
                except:
                    st.error("Error: No se pudo acceder al diccionario KITS_ESTRUCTURA")
                    return df

                multiplicadores = ids_df.map(map_mult).fillna(1)
                df["Caviahue"] = pd.to_numeric(df["Caviahue"], errors='coerce').fillna(0)
                df["Caviahue"] = df["Caviahue"] * multiplicadores
            return df
        
        df_preventa = mult(df_preventa)
        try:
            df_tango = pd.read_excel("data/TANGO.xlsx", sheet_name="Datos").rename(columns={"Cód. cliente": "Cliente", "Cantidad": "Venta Unid."})
            df_tango["Caviahue"] = np.where(~df_tango["Cód. Artículo"].isin([21304, 21302]), df_tango["Venta Unid."], 0)
            df_tango = mult(df_tango)
        except: 
            df_tango = pd.DataFrame(columns=["Cliente", "Caviahue"])

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
            df_rep = df_rep.reset_index(drop=True)
            
            df_rep["CLIENTE"] = df_rep["CLIENTE"].astype(str).str.strip().str.upper()
            df_rep["CLIENTE"] = df_rep["CLIENTE"].str.replace("Ó", "O").str.replace("Á", "A")
            
            df_rep["N° CLIENTE_INT"] = pd.to_numeric(df_rep["N° CLIENTE"], errors='coerce').fillna(-9999).astype(int)
            
            df_rep = df_rep.drop(columns=["Total Caviahue"], errors="ignore").merge(ventas_mes, left_on="N° CLIENTE_INT", right_on="Cliente", how="left").drop(columns=["Cliente"], errors="ignore")
            df_rep = df_rep.merge(df_hist_resumen, left_on="N° CLIENTE_INT", right_on="N° CLIENTE", how="left", suffixes=('', '_hist')).fillna(0)
            
            df_rep["Acumulado año"] = df_rep["Hist_Act"] + df_rep["Venta Mes Actual"]
            
            t_mask = df_rep["CLIENTE"].str.contains("TOTAL", case=False, na=False)
            gid = t_mask.cumsum()
            for g in gid[t_mask].unique():
                m = (gid == g); idx = df_rep[m & t_mask].index[0]; h = m & (~t_mask)
                for c in ["Cuota Caviahue", "Venta Mes Actual", "Venta 2024", "Venta 2025", "Acumulado año", "Venta 2025 YTD"]:
                    df_rep.loc[idx, c] = df_rep.loc[h, c].sum()
            
            df_rep["Avance %"] = (df_rep["Venta Mes Actual"] / df_rep["Cuota Caviahue"].replace(0, np.nan)) * 100
            df_rep["Avance %"] = df_rep["Avance %"].fillna(0)
            df_rep["growth 2025"] = (df_rep["Venta 2025"] / df_rep["Venta 2024"].replace(0, np.nan) - 1) * 100
            df_rep["growth 2025"] = df_rep["growth 2025"].fillna(0)
            df_rep["growth 2026"] = (df_rep["Acumulado año"] / df_rep["Venta 2025 YTD"].replace(0, np.nan) - 1) * 100
            df_rep["growth 2026"] = df_rep["growth 2026"].fillna(0)

            hojas_rep[nombre] = df_rep[["N° CLIENTE", "CLIENTE", "Cuota Caviahue", "Venta Mes Actual", "Avance %", "Venta 2024", "Venta 2025", "growth 2025", "Acumulado año", "growth 2026", "Venta 2025 YTD"]]
        except Exception as e:
            st.error(f"Error en hoja {nombre}: {e}")

    # --- 3. UI ---
    st.title("Control de Avance - Caviahue")
    
    res_list = []
    for n, df in hojas_rep.items():
        mc = pd.to_numeric(df["N° CLIENTE"], errors='coerce') > 0
        res_list.append({
            "Rep": n, 
            "Cuota": float(df[mc]["Cuota Caviahue"].sum()), 
            "Venta": float(df[mc]["Venta Mes Actual"].sum()), 
            "V24": float(df[mc]["Venta 2024"].sum()), 
            "V25": float(df[mc]["Venta 2025"].sum()), 
            "G25": float(df[mc]["growth 2025"].mean()), 
            "Acum": float(df[mc]["Acumulado año"].sum()),
            "V25_YTD": float(df[mc]["Venta 2025 YTD"].sum())
        })
    
    resumen = pd.DataFrame(res_list)
    if not resumen.empty:
        tc, tv, ta, ty = resumen["Cuota"].sum(), resumen["Venta"].sum(), resumen["Acum"].sum(), resumen["V25_YTD"].sum()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Venta Mes", f"{int(tv):,}".replace(",", "."), f"{int(tv/tc*100 if tc>0 else 0)}% Avance")
        m2.metric("Cuota Total", f"{int(tc):,}".replace(",", "."))
        m3.metric("Acumulado Año", f"{int(ta):,}".replace(",", "."))
        m4.metric("growth 2026", f"{int((ta/ty-1)*100 if ty>0 else 0)}%", delta_color="normal")
        
        st.markdown("""
        <div style='background-color: #f1f3f6; padding: 5px; border-radius: 5px; margin-bottom: 10px; font-weight: bold; font-size: 12px;'>
            <div style='display: flex; text-align: center;'>
                <div style='flex: 0.5;'></div>
                <div style='flex: 1; text-align: left;'>REPRESENTANTE</div>
                <div style='flex: 0.8;'>CUOTA</div>
                <div style='flex: 0.8;'>VENTA</div>
                <div style='flex: 0.7;'>AVANCE %</div>
                <div style='flex: 0.7;'>VENTA 24</div>
                <div style='flex: 0.7;'>VENTA 25</div>
                <div style='flex: 0.7;'>GROWTH 25</div>
                <div style='flex: 0.7;'>ACUMULADO 26</div>
                <div style='flex: 0.7;'>GROWTH 26</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        for i, r in resumen.iterrows():
            rep_key_clean = str(r['Rep']).replace(" ", "_")
            key = f"exp_{usuario_id}_{rep_key_clean}"
            if key not in st.session_state: st.session_state[key] = False
            
            cols = st.columns([0.5, 1.5, 0.8, 0.8, 0.6, 0.8, 0.8, 0.6, 0.8, 0.6])
            
            if cols[0].button("➕" if not st.session_state[key] else "➖", key=f"b_{usuario_id}_{rep_key_clean}"):
                st.session_state[key] = not st.session_state[key]
                st.rerun()
            
            cols[1].write(f"**{r['Rep']}**")
            cols[2].write(f"{int(r['Cuota']):,}".replace(",", "."))
            cols[3].write(f"{int(r['Venta']):,}".replace(",", "."))
            cols[4].write(f"{int(r['Venta']/r['Cuota']*100 if r['Cuota']>0 else 0)}%")
            cols[5].write(f"{int(r['V24']):,}".replace(",", "."))
            cols[6].write(f"{int(r['V25']):,}".replace(",", "."))
            
            g25_total = ((r['V25']/r['V24'])-1)*100 if r['V24']>0 else 0
            cols[7].markdown(f":{'green' if g25_total >= 0 else 'red'}[{int(g25_total)}%]")
            cols[8].write(f"{int(r['Acum']):,}".replace(",", "."))
            
            g26_total = ((r['Acum']/r['V25_YTD'])-1)*100 if r['V25_YTD']>0 else 0
            cols[9].markdown(f":{'green' if g26_total >= 0 else 'red'}[{int(g26_total)}%]")

            if st.session_state[key]:
                df_disp = hojas_rep[r["Rep"]].copy()
                df_disp["es_total"] = df_disp["CLIENTE"].astype(str).str.contains("TOTAL", case=False, na=False)
                
                # --- NUEVA LÓGICA DE CONTROL COMPLETO SOBRE VALORES DE ENTRADA ---
                if df_disp["es_total"].any():
                    # CASO A: La hoja tiene totales estructurados (Comportamiento Estándar)
                    df_disp["grupo_total_idx"] = np.where(df_disp["es_total"], df_disp.index, np.nan)
                    df_disp["grupo_total_idx"] = df_disp["grupo_total_idx"].bfill().ffill()
                    indices_totales = df_disp.index[df_disp["es_total"]].tolist()

                    for idx_tot, idx_total in enumerate(indices_totales):
                        total_row = df_disp.loc[idx_total]
                        total_key = f"total_{usuario_id}_{rep_key_clean}_{idx_total}"

                        if total_key not in st.session_state: st.session_state[total_key] = False

                        cols_tot = st.columns([0.5, 1.5, 0.8, 0.8, 0.6, 0.8, 0.8, 0.6, 0.8, 0.6])
                        if cols_tot[0].button("➕" if not st.session_state[total_key] else "➖", key=f"btn_{total_key}_{idx_tot}"):
                            st.session_state[total_key] = not st.session_state[total_key]
                            st.rerun()

                        cuota = total_row.get("Cuota Caviahue", 0)
                        venta_mes = total_row.get("Venta Mes Actual", 0)
                        venta_24 = total_row.get("Venta 2024", 0)
                        venta_25 = total_row.get("Venta 2025", 0)
                        acum = total_row.get("Acumulado año", 0)
                        g26 = total_row.get("growth 2026", 0)

                        avance = (venta_mes / cuota * 100) if cuota > 0 else 0
                        g25 = ((venta_25 / venta_24) - 1) * 100 if venta_24 > 0 else 0

                        cols_tot[1].markdown(f"**{total_row['CLIENTE']}**")
                        cols_tot[2].write(f"{int(cuota):,}".replace(",", "."))
                        cols_tot[3].write(f"{int(venta_mes):,}".replace(",", "."))
                        cols_tot[4].write(f"{int(avance)}%")
                        cols_tot[5].write(f"{int(venta_24):,}".replace(",", "."))
                        cols_tot[6].write(f"{int(venta_25):,}".replace(",", "."))
                        cols_tot[7].markdown(f":{'green' if g25 >= 0 else 'red'}[{int(g25)}%]")
                        cols_tot[8].write(f"{int(acum):,}".replace(",", "."))
                        cols_tot[9].markdown(f":{'green' if g26 >= 0 else 'red'}[{int(g26)}%]")

                        clientes_del_total = df_disp[
                            (df_disp["grupo_total_idx"] == idx_total) & 
                            (~df_disp["es_total"]) &
                            (df_disp["CLIENTE"].notna()) & 
                            (~df_disp["CLIENTE"].isin(["NAN", "NONE", ""]))
                        ]

                        if st.session_state[total_key] and not clientes_del_total.empty:
                            for _, row_cli in clientes_del_total.iterrows():
                                c_cuota = row_cli.get("Cuota Caviahue", 0)
                                c_venta_mes = row_cli.get("Venta Mes Actual", 0)
                                c_venta_24 = row_cli.get("Venta 2024", 0)
                                c_venta_25 = row_cli.get("Venta 2025", 0)
                                c_acum = row_cli.get("Acumulado año", 0)
                                c_g26 = row_cli.get("growth 2026", 0)

                                c_avance = (c_venta_mes / c_cuota * 100) if c_cuota > 0 else 0
                                c_g25 = ((c_venta_25 / c_venta_24) - 1) * 100 if c_venta_24 > 0 else 0

                                cols_cli = st.columns([0.5, 1.5, 0.8, 0.8, 0.6, 0.8, 0.8, 0.6, 0.8, 0.6])
                                cols_cli[0].write("")
                                cols_cli[1].write("  " + str(row_cli["CLIENTE"]))  
                                cols_cli[2].write(f"{int(c_cuota):,}".replace(",", "."))
                                cols_cli[3].write(f"{int(c_venta_mes):,}".replace(",", "."))
                                cols_cli[4].write(f"{int(c_avance)}%")
                                cols_cli[5].write(f"{int(c_venta_24):,}".replace(",", "."))
                                cols_cli[6].write(f"{int(c_venta_25):,}".replace(",", "."))
                                cols_cli[7].markdown(f":{'green' if c_g25 >= 0 else 'red'}[{int(c_g25)}%]")
                                cols_cli[8].write(f"{int(c_acum):,}".replace(",", "."))
                                cols_cli[9].markdown(f":{'green' if c_g26 >= 0 else 'red'}[{int(c_g26)}%]")
                else:
                    # CASO B: La hoja NO tiene totales (Mendoza y Natalia Bridi) - Renderizado Directo Seguro
                    total_key = f"total_directo_{usuario_id}_{rep_key_clean}"
                    if total_key not in st.session_state: st.session_state[total_key] = False

                    cols_tot = st.columns([0.5, 1.5, 0.8, 0.8, 0.6, 0.8, 0.8, 0.6, 0.8, 0.6])
                    if cols_tot[0].button("➕" if not st.session_state[total_key] else "➖", key=f"btn_{total_key}_dir"):
                        st.session_state[total_key] = not st.session_state[total_key]
                        st.rerun()

                    # Renderiza un agrupador sumando dinámicamente todo el listado de clientes
                    cols_tot[1].markdown("**VER LISTADO DE CLIENTES**")
                    cols_tot[2].write(f"{int(df_disp['Cuota Caviahue'].sum()):,}".replace(",", "."))
                    cols_tot[3].write(f"{int(df_disp['Venta Mes Actual'].sum()):,}".replace(",", "."))
                    av_dir = (df_disp['Venta Mes Actual'].sum() / df_disp['Cuota Caviahue'].sum() * 100) if df_disp['Cuota Caviahue'].sum() > 0 else 0
                    cols_tot[4].write(f"{int(av_dir)}%")
                    cols_tot[5].write(f"{int(df_disp['Venta 2024'].sum()):,}".replace(",", "."))
                    cols_tot[6].write(f"{int(df_disp['Venta 2025'].sum()):,}".replace(",", "."))
                    g25_dir = ((df_disp['Venta 2025'].sum() / df_disp['Venta 2024'].sum()) - 1) * 100 if df_disp['Venta 2024'].sum() > 0 else 0
                    cols_tot[7].markdown(f":{'green' if g25_dir >= 0 else 'red'}[{int(g25_dir)}%]")
                    cols_tot[8].write(f"{int(df_disp['Acumulado año'].sum()):,}".replace(",", "."))
                    g26_dir = ((df_disp['Acumulado año'].sum() / df_disp['Venta 2025 YTD'].sum()) - 1) * 100 if df_disp['Venta 2025 YTD'].sum() > 0 else 0
                    cols_tot[9].markdown(f":{'green' if g26_dir >= 0 else 'red'}[{int(g26_dir)}%]")

                    # Si el usuario despliega el botón dinámico, mostramos los clientes directo de la lista plana
                    if st.session_state[total_key]:
                        df_clientes_validos = df_disp[
                            (df_disp["CLIENTE"].notna()) & 
                            (~df_disp["CLIENTE"].isin(["NAN", "NONE", ""]))
                        ]
                        for _, row_cli in df_clientes_validos.iterrows():
                            c_cuota = row_cli.get("Cuota Caviahue", 0)
                            c_venta_mes = row_cli.get("Venta Mes Actual", 0)
                            c_venta_24 = row_cli.get("Venta 2024", 0)
                            c_venta_25 = row_cli.get("Venta 2025", 0)
                            c_acum = row_cli.get("Acumulado año", 0)

                            c_avance = (c_venta_mes / c_cuota * 100) if c_cuota > 0 else 0
                            c_g25 = ((c_venta_25 / c_venta_24) - 1) * 100 if c_venta_24 > 0 else 0
                            c_g26 = row_cli.get("growth 2026", 0)

                            cols_cli = st.columns([0.5, 1.5, 0.8, 0.8, 0.6, 0.8, 0.8, 0.6, 0.8, 0.6])
                            cols_cli[0].write("")
                            cols_cli[1].write("  " + str(row_cli["CLIENTE"]))  
                            cols_cli[2].write(f"{int(c_cuota):,}".replace(",", "."))
                            cols_cli[3].write(f"{int(c_venta_mes):,}".replace(",", "."))
                            cols_cli[4].write(f"{int(c_avance)}%")
                            cols_cli[5].write(f"{int(c_venta_24):,}".replace(",", "."))
                            cols_cli[6].write(f"{int(c_venta_25):,}".replace(",", "."))
                            cols_cli[7].markdown(f":{'green' if c_g25 >= 0 else 'red'}[{int(c_g25)}%]")
                            cols_cli[8].write(f"{int(c_acum):,}".replace(",", "."))
                            cols_cli[9].markdown(f":{'green' if c_g26 >= 0 else 'red'}[{int(c_g26)}%]")

                # ===== BOTÓN DE DESCARGA PERFECTO =====
                st.write("")  
                output = io.BytesIO()
                df_excel = df_disp.drop(columns=["es_total", "grupo_total_idx"], errors="ignore")
                
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    df_excel.to_excel(writer, index=False)
                
                output.seek(0)  
                st.download_button(
                    label=f"📥 Descargar Excel {r['Rep']}", 
                    data=output.getvalue(), 
                    file_name=f"Avance_Caviahue_{rep_key_clean}.xlsx", 
                    key=f"dl_final_{usuario_id}_{rep_key_clean}_{i}"  
                )

            st.markdown("<hr style='margin:5px 0px'>", unsafe_allow_html=True)