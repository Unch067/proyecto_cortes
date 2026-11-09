import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from core.optimizador import optimizar_cortes
from components.validaciones import validar_datos_entrada
from components.graficos import (
    crear_gemelo_digital_3d,
    crear_grafico_balance_dona,
    crear_grafico_comparativo_dual,
    crear_simulacion_paso_a_paso,
    generar_reporte_texto
)

st.set_page_config(page_title="OptiCorte 1D - Plan de Corte", layout="wide")

# ==========================================
# ESTILOS PERSONALIZADOS (Oculta menús y pinta botones)
# ==========================================
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stButton>button {
        background-color: #ff4b4b; 
        color: white; 
        border-radius: 10px; 
        font-weight: bold;
        padding: 10px 24px;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 1. INICIALIZACIÓN Y PERSISTENCIA DE ESTADO
# ==========================================
if "inventario" not in st.session_state:
    st.session_state.inventario = pd.DataFrame([{"ID_Retal": "R1", "Longitud_mm": 3000, "Cantidad": 1}])
if "pedidos" not in st.session_state:
    st.session_state.pedidos = pd.DataFrame([
        {"ID_Pieza": "P2900", "Longitud_mm": 2900, "Cantidad": 1},
        {"ID_Pieza": "P2000", "Longitud_mm": 2000, "Cantidad": 1},
        {"ID_Pieza": "P1900", "Longitud_mm": 1900, "Cantidad": 1},
        {"ID_Pieza": "P1800", "Longitud_mm": 1800, "Cantidad": 1}
    ])
if "resultados" not in st.session_state:
    st.session_state.resultados = None
if "res_original" not in st.session_state:
    st.session_state.res_original = None

st.title("📐 OptiCorte 1D | Optimización y Aprovechamiento de Retales")
st.caption("Herramienta de control de descarte, balance de masa y layout de taller · Grupo 3")

# ==========================================
# 2. SISTEMA DE PESTAÑAS
# ==========================================
tab_conf, tab_inv, tab_ped, tab_res = st.tabs(["⚙️ Configuración", "📦 Inventario", "📋 Pedidos", "📊 Resultados"])

with tab_conf:
    st.subheader("Parámetros del Proyecto")
    col1, col2, col3 = st.columns(3)
    l_comercial = col1.number_input("Tubo Nuevo (mm)", min_value=1000, value=6000, step=1, key="cfg_tubo")
    kerf = col2.number_input("Pérdida por corte (mm)", min_value=0, value=4, step=1, key="cfg_kerf")
    umbral = col3.number_input("Retal Mínimo (mm)", min_value=0, value=200, step=1, key="cfg_umbral")

with tab_inv:
    st.subheader("Retales Disponibles en Obra")
    st.session_state.inventario = st.data_editor(
        st.session_state.inventario,
        num_rows="dynamic",
        key="editor_inv",
        column_config={
            "ID_Retal": st.column_config.TextColumn("ID Retal", required=True),
            "Longitud_mm": st.column_config.NumberColumn("Longitud (mm)", min_value=1, step=1, required=True),
            "Cantidad": st.column_config.NumberColumn("Cantidad", min_value=0, step=1, required=True)
        }
    )

with tab_ped:
    st.subheader("Piezas Requeridas")
    st.session_state.pedidos = st.data_editor(
        st.session_state.pedidos,
        num_rows="dynamic",
        key="editor_ped",
        column_config={
            "ID_Pieza": st.column_config.TextColumn("ID Pieza", required=True),
            "Longitud_mm": st.column_config.NumberColumn("Longitud (mm)", min_value=1, step=1, required=True),
            "Cantidad": st.column_config.NumberColumn("Cantidad", min_value=0, step=1, required=True)
        }
    )

    if st.button("🚀 Calcular Optimización", type="primary", use_container_width=True):
        es_valido, msg = validar_datos_entrada(st.session_state.inventario, st.session_state.pedidos, l_comercial, kerf)
        
        if not es_valido:
            st.error(msg)
            st.stop()
            
        try:
            # 1. Animación de carga (Spinner)
            with st.spinner("Optimizando cortes y calculando balance de material..."):
                st.session_state.resultados = optimizar_cortes(
                    st.session_state.inventario, st.session_state.pedidos, l_comercial, kerf, umbral, usar_orden_original=False
                )
                st.session_state.res_original = optimizar_cortes(
                    st.session_state.inventario, st.session_state.pedidos, l_comercial, kerf, umbral, usar_orden_original=True
                )
            
            # 2. Mensajes de éxito flotantes
            st.success("¡Cálculo exitoso! Ve a la pestaña Resultados.")
            st.toast("Cortes optimizados correctamente 🎯")
            
        except Exception as e:
            st.error(f"⚠️ Ocurrió un error inesperado en el motor de optimización: {str(e)}")
            st.stop()

with tab_res:
    if st.session_state.resultados:
        
        res = st.session_state.resultados
        bal = res["balance"]
        res_orig = st.session_state.res_original
        
        st.subheader("Balance de Materiales")
        col0, col1, col2, col3, col4 = st.columns(5)
        col0.metric("Material Origen (Total)", f"{bal['material_total_origen']} mm")
        col1.metric("Tubos Nuevos a Comprar", res["tubos_comprados"])
        col2.metric("Material Incorporado", f"{bal['incorporado']} mm")
        col3.metric("Pérdida por Corte", f"{bal['perdida']} mm")
        col4.metric("Descarte Inútil", f"{bal['descarte']} mm")
        
        if not bal["cuadra_perfecto"]:
            st.error("⚠️ Alerta: El balance de masas no cuadra con el material de origen.")
            
        st.subheader("Comparativa de Eficiencia (Optimizado vs Orden Original)")
        diff_tubos = res_orig["tubos_comprados"] - res["tubos_comprados"]
        diff_descarte = res_orig["balance"]["descarte"] - bal["descarte"]
        
        if diff_tubos > 0 or diff_descarte > 0:
            st.info(f"✅ Cortar en el orden original requería **{res_orig['tubos_comprados']} tubos** y generaba **{res_orig['balance']['descarte']} mm** de descarte. La optimización ahorró **{diff_tubos} tubos** y **{diff_descarte} mm** de desperdicio.")
        elif diff_tubos == 0 and diff_descarte == 0:
            st.info("⚖️ El orden original ingresado ya era igual de eficiente que la optimización.")
        else:
            st.warning(f"⚠️ El orden original resultó mejor por **{-diff_tubos} tubos** y **{-diff_descarte} mm** (situación anómala del algoritmo Greedy).")
            
        # Tabla comparativa
        df_comp = pd.DataFrame({
            "Métrica": ["Tubos Nuevos", "Descarte (mm)", "Pérdida (mm)", "Retal Generado (mm)"],
            "Optimizado (IA)": [res["tubos_comprados"], bal["descarte"], bal["perdida"], bal["nuevo_retal"]],
            "Orden Original": [res_orig["tubos_comprados"], res_orig["balance"]["descarte"], res_orig["balance"]["perdida"], res_orig["balance"]["nuevo_retal"]]
        })
        st.table(df_comp)

        st.subheader("Plan de Corte Detallado")
        df_plan = pd.DataFrame(res["detalle_csv"])
        st.dataframe(df_plan, use_container_width=True)
        
        # Exportaciones CSV e Informe Técnico
        st.subheader("Exportar Resultados")
        c1, c2, c3, c4 = st.columns(4)
        c1.download_button("Descargar Plan (CSV)", df_plan.to_csv(index=False).encode('utf-8'), "plan.csv", "text/csv")
        c2.download_button("Descargar Balance (CSV)", pd.DataFrame([bal]).to_csv(index=False).encode('utf-8'), "balance.csv", "text/csv")
        
        texto_reporte = generar_reporte_texto(res, res_orig, l_comercial, kerf, umbral)
        c3.download_button("Descargar Informe Técnico", texto_reporte.encode('utf-8'), "informe_tecnico_corte.txt", "text/plain")

        if res["pendientes"]:
            st.warning("⚠️ Sin solución completa para las siguientes piezas:")
            st.dataframe(pd.DataFrame(res["pendientes"]))
            c4.download_button("Descargar Pendientes", pd.DataFrame(res["pendientes"]).to_csv(index=False).encode('utf-8'), "pendientes.csv", "text/csv")

        # ==========================================
        # 3. GEMELO DIGITAL 3D (LAYOUT DE TALLER)
        # ==========================================
        st.markdown("---")
        st.subheader("📐 Gemelo Digital 3D: Layout de Taller")
        st.write("Simulación volumétrica de los tubos y cortes. **Gira, rota o amplía** el modelo con el cursor:")

        fig_3d = crear_gemelo_digital_3d(res["detalle_csv"], kerf_nominal=kerf)
        st.plotly_chart(fig_3d, use_container_width=True)

        # ==========================================
        # 3.1 SIMULADOR DE CORTE PASO A PASO
        # ==========================================
        st.markdown("---")
        st.subheader("⚙️ Simulador de Taller: Avance de Corte")
        st.write("Selecciona una barra y desplaza el carro de la sierra para simular el proceso físico de seccionamiento:")

        lista_origenes = [f["Origen_ID"] for f in res["detalle_csv"]]
        col_sel_barra, col_slider = st.columns([1, 3])

        with col_sel_barra:
            barra_sel_id = st.selectbox("Barra a simular:", lista_origenes, key="sel_sim_barra")
            fila_sel = next(f for f in res["detalle_csv"] if f["Origen_ID"] == barra_sel_id)
            st.caption(f"**Longitud inicial:** {fila_sel['Longitud_Inicial']} mm")
            st.caption(f"**Piezas a extraer:** {fila_sel['Piezas_Asignadas']}")

        with col_slider:
            cota_disco = st.slider(
                "Posición del disco de corte (mm):",
                min_value=0,
                max_value=int(fila_sel["Longitud_Inicial"]),
                value=int(fila_sel["Longitud_Inicial"]),
                step=10,
                key=f"slider_{barra_sel_id}"
            )
            fig_sim = crear_simulacion_paso_a_paso(fila_sel, cota_disco, kerf_nominal=kerf)
            st.plotly_chart(fig_sim, use_container_width=True)

        # ==========================================
        # 4. ANÁLISIS COMPARATIVO VISUAL (DONA Y SUBPLOTS)
        # ==========================================
        st.markdown("---")
        st.subheader("📊 Análisis Visual Comparativo")
        
        col_graf_dona, col_graf_comp = st.columns(2)

        with col_graf_dona:
            fig_dona = crear_grafico_balance_dona(bal)
            st.plotly_chart(fig_dona, use_container_width=True)

        with col_graf_comp:
            fig_comp = crear_grafico_comparativo_dual(res, res_orig)
            st.plotly_chart(fig_comp, use_container_width=True)

    else:
        st.info("Ingrese sus datos en las pestañas anteriores y presione 'Calcular Optimización'.")