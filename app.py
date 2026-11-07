import streamlit as st
import pandas as pd
from core.optimizador import optimizar_cortes
from components.validaciones import validar_datos_entrada

st.set_page_config(page_title="Plan de Corte - Grupo 3", layout="wide")

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

st.title("✂️ Plan de Corte y Aprovechamiento de Retales")

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
            st.session_state.resultados = optimizar_cortes(
                st.session_state.inventario, st.session_state.pedidos, l_comercial, kerf, umbral, usar_orden_original=False
            )
            st.session_state.res_original = optimizar_cortes(
                st.session_state.inventario, st.session_state.pedidos, l_comercial, kerf, umbral, usar_orden_original=True
            )
            st.success("¡Cálculo exitoso! Ve a la pestaña Resultados.")
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

        df_comp = pd.DataFrame({
            "Métrica": ["Tubos Nuevos", "Descarte (mm)", "Pérdida (mm)", "Retal Generado (mm)"],
            "Optimizado": [res["tubos_comprados"], bal["descarte"], bal["perdida"], bal["nuevo_retal"]],
            "Orden Original": [res_orig["tubos_comprados"], res_orig["balance"]["descarte"], res_orig["balance"]["perdida"], res_orig["balance"]["nuevo_retal"]]
        })
        st.table(df_comp)

        st.subheader("Plan de Corte Detallado")
        df_plan = pd.DataFrame(res["detalle_csv"])
        st.dataframe(df_plan, use_container_width=True)

        st.subheader("Exportar Resultados")
        c1, c2, c3 = st.columns(3)
        c1.download_button("Descargar Plan", df_plan.to_csv(index=False).encode("utf-8"), "plan.csv", "text/csv")
        c2.download_button("Descargar Balance", pd.DataFrame([bal]).to_csv(index=False).encode("utf-8"), "balance.csv", "text/csv")

        if res["pendientes"]:
            st.warning("⚠️ Sin solución completa para las siguientes piezas:")
            st.dataframe(pd.DataFrame(res["pendientes"]))
            c3.download_button("Descargar Pendientes", pd.DataFrame(res["pendientes"]).to_csv(index=False).encode("utf-8"), "pendientes.csv", "text/csv")
    else:
        st.info("Ingrese sus datos en las pestañas anteriores y presione 'Calcular Optimización'.")