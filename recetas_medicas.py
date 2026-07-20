import streamlit as st
import pandas as pd
import numpy as np
import io
import datetime
import unicodedata

# --- CONFIGURACIÓN DE REPRESENTANTES ---
REPRESENTANTE_POR_USUARIO = {
    "MROSSELOT": ["Marcela Rosselot"],
    "PZACCA": ["Patricia Zacca"],
    "YARRECHE": ["YAMILA ARRECHE"],
    "AFLEBA": ["LUCIO COLOMBO","AGUSTIN FLEBA"],
    "YCUEZZO": ["YANINA CUEZO"],
    "SROCCHI": ["Santiago Rocchi"],
    "NBRIDI": ["Natalia Bridi"],
    "DCHANDLER": ["DAIANA CHANDLER"],
    "MPUTZOLU": ["MARIANELA PUTZULO","EMILIANO VEIGA"],
    "RABBENANTE" : ["ROMINA ABBENANTE"],
    "OTROS": ["JESSICCA ANDERMARCH", "LEONARDO PAREDES"],
}

def normalizar_texto(texto):
    """Elimina tildes, espacios extra y convierte a mayúsculas para emparejamientos seguros."""
    if pd.isna(texto):
        return ""
    texto = str(texto).strip().upper()
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    return texto

def recetas_medicas(representantes=[], usuario_id="default"):
    """
    Control de Recetas Emitidas con métricas generales y Top 3 productos.
    """
    archivo_recetas = "data/Recetas_por_médico.xlsx"

    # --- 1. FILTRADO DE APMs PERMITIDOS SEGÚN USUARIO ---
    if not representantes:
        representantes = list(REPRESENTANTE_POR_USUARIO.keys())

    nombres_permitidos = [
        nombre
        for u in representantes
        if u in REPRESENTANTE_POR_USUARIO
        for nombre in REPRESENTANTE_POR_USUARIO[u]
    ]
    
    nombres_permitidos_norm = [normalizar_texto(n) for n in nombres_permitidos]

    # --- 2. CARGA Y PROCESAMIENTO DE DATOS ---
    try:
        try:
            df_recetas = pd.read_csv(archivo_recetas, sep=None, engine='python', encoding='latin1')
        except Exception:
            df_recetas = pd.read_excel("data/Recetas_por_médico.xlsx")

        df = df_recetas.copy()

        df['fechaReceta'] = pd.to_datetime(df['fechaReceta'], dayfirst=True, errors='coerce')
        anio_actual = datetime.datetime.now().year
        
        if not df['fechaReceta'].dropna().empty:
            anio_max = df['fechaReceta'].dt.year.max()
            anio_actual = anio_max if pd.notna(anio_max) else anio_actual
            
        df = df[df['fechaReceta'].dt.year == anio_actual].copy()

        df['APM_NORM'] = df['APM'].apply(normalizar_texto)
        df['Nombre_Display'] = df['Nombre'].fillna('MÉDICO NO INFORMADO').astype(str).str.strip().str.upper()
        df['Producto_Display'] = df['Producto'].fillna('PRODUCTO NO INFORMADO').astype(str).str.strip()

        if nombres_permitidos_norm:
            df = df[df['APM_NORM'].isin(nombres_permitidos_norm)].copy()

        if df.empty:
            st.warning("⚠️ No se encontraron registros de recetas para el usuario o representantes seleccionados.")
            return

        df['Mes_Num'] = df['fechaReceta'].dt.month
        meses_presentes = sorted(df['Mes_Num'].dropna().unique())
        
        meses_nombres = {
            1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun',
            7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'
        }
        cols_meses = [meses_nombres[int(m)] for m in meses_presentes]

        df_grouped = df.groupby(['APM', 'Nombre_Display', 'Producto_Display', 'Mes_Num']).size().reset_index(name='Cantidad')
        df_grouped['Mes_Nombre'] = df_grouped['Mes_Num'].map(meses_nombres)

        pivot_prod = df_grouped.pivot_table(
            index=['APM', 'Nombre_Display', 'Producto_Display'],
            columns='Mes_Nombre',
            values='Cantidad',
            aggfunc='sum',
            fill_value=0
        ).reset_index()

        for m in cols_meses:
            if m not in pivot_prod.columns:
                pivot_prod[m] = 0

        pivot_prod['Total Recetas'] = pivot_prod[cols_meses].sum(axis=1)

    except Exception as e:
        st.error(f"Error al procesar la base de datos de recetas: {e}")
        return

    # --- 3. UI: ENCABEZADO Y MÉTRICAS PRINCIPALES ---
    st.title("Recetas Emitidas")

    total_recetas = pivot_prod['Total Recetas'].sum()
    cant_meses = len(cols_meses) if len(cols_meses) > 0 else 1
    promedio_mensual = total_recetas / cant_meses
    medicos_unicos = pivot_prod['Nombre_Display'].nunique()

    m1, m2, m3 = st.columns(3)
    m1.metric("N° de Recetas", f"{int(total_recetas):,}".replace(",", "."))
    m2.metric("Prom. Recetas / Mes", f"{int(promedio_mensual):,}".replace(",", "."))
    m3.metric("Médicos Únicos", medicos_unicos)

    # --- TOP 3 PRODUCTOS MÁS RECETADOS ---
    st.write("")
    st.markdown("##### 🏆 Top 3 Productos Más Recetados")
    
    top_productos = (
        pivot_prod.groupby('Producto_Display')['Total Recetas']
        .sum()
        .sort_values(ascending=False)
        .head(3)
    )

    cols_top = st.columns(3)
    medallas = ["🥇 1°", "🥈 2°", "🥉 3°"]

    for idx, (prod_nombre, prod_cant) in enumerate(top_productos.items()):
        porcentaje = (prod_cant / total_recetas * 100) if total_recetas > 0 else 0
        cols_top[idx].metric(
            label=f"{medallas[idx]} {prod_nombre}",
            value=f"{int(prod_cant):,}".replace(",", "."),
            delta=f"{porcentaje:.1f}% del total",
            delta_color="normal"
        )

    st.markdown("---")

    # --- 4. TABLA JERÁRQUICA CON DESPLIEGUE ---
    ancho_columnas = [0.4, 2.2] + [0.7] * len(cols_meses) + [0.8]

    headers_html = "".join([f"<div style='flex: 0.7; text-align: center;'>{m}</div>" for m in cols_meses])
    st.markdown(f"""
        <div style='background-color: #f1f3f6; padding: 6px; border-radius: 5px; margin-bottom: 8px; font-weight: bold; font-size: 11px;'>
            <div style='display: flex; align-items: center;'>
                <div style='flex: 0.4;'></div>
                <div style='flex: 2.2; text-align: left;'>APM / MÉDICO / PRODUCTO</div>
                {headers_html}
                <div style='flex: 0.8; text-align: center;'>TOTAL</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Ordenar APMs por total descendente
    apms_totales = pivot_prod.groupby('APM')['Total Recetas'].sum().sort_values(ascending=False)
    apms_ordenados = apms_totales.index.tolist()

    for apm in apms_ordenados:
        apm_clean = str(apm).replace(" ", "_")
        df_apm = pivot_prod[pivot_prod['APM'] == apm]
        key_apm = f"exp_rec_{usuario_id}_{apm_clean}"

        if key_apm not in st.session_state:
            st.session_state[key_apm] = False

        totales_apm_mes = [df_apm[m].sum() for m in cols_meses]
        total_apm_general = df_apm['Total Recetas'].sum()

        cols = st.columns(ancho_columnas)
        if cols[0].button("➕" if not st.session_state[key_apm] else "➖", key=f"btn_{key_apm}"):
            st.session_state[key_apm] = not st.session_state[key_apm]
            st.rerun()

        cols[1].markdown(f"**👤 {apm}**")
        for i, m_val in enumerate(totales_apm_mes):
            cols[2 + i].write(f"{int(m_val):,}".replace(",", "."))
        cols[-1].markdown(f"**{int(total_apm_general):,}**".replace(",", "."))

        # --- NIVEL 2: MÉDICOS (DESCENTENTE) ---
        if st.session_state[key_apm]:
            medicos_totales = df_apm.groupby('Nombre_Display')['Total Recetas'].sum().sort_values(ascending=False)
            medicos_ordenados = medicos_totales.index.tolist()

            for med in medicos_ordenados:
                med_clean = str(med).replace(" ", "_")
                df_med = df_apm[df_apm['Nombre_Display'] == med]
                key_med = f"exp_rec_{usuario_id}_{apm_clean}_{med_clean}"

                if key_med not in st.session_state:
                    st.session_state[key_med] = False

                totales_med_mes = [df_med[m].sum() for m in cols_meses]
                total_med_general = df_med['Total Recetas'].sum()

                cols_med = st.columns(ancho_columnas)
                if cols_med[0].button("➕" if not st.session_state[key_med] else "➖", key=f"btn_{key_med}"):
                    st.session_state[key_med] = not st.session_state[key_med]
                    st.rerun()

                cols_med[1].write(f" └─ 🩺 **Dr. {med}**")
                for i, m_val in enumerate(totales_med_mes):
                    cols_med[2 + i].write(f"{int(m_val):,}".replace(",", "."))
                cols_med[-1].write(f"{int(total_med_general):,}".replace(",", "."))

                # --- NIVEL 3: PRODUCTOS (DESCENDENTE) ---
                if st.session_state[key_med]:
                    df_med_prods_ordenados = df_med.sort_values(by='Total Recetas', ascending=False)
                    
                    for _, row_prod in df_med_prods_ordenados.iterrows():
                        cols_prod = st.columns(ancho_columnas)
                        cols_prod[0].write("")
                        cols_prod[1].caption(f"     └── 💊 {row_prod['Producto_Display']}")

                        for i, m in enumerate(cols_meses):
                            val = row_prod[m]
                            cols_prod[2 + i].caption(f"{int(val):,}".replace(",", "."))
                        cols_prod[-1].caption(f"{int(row_prod['Total Recetas']):,}".replace(",", "."))

        st.markdown("<hr style='margin: 4px 0px; border-top: 1px solid #e0e0e0;'>", unsafe_allow_html=True)