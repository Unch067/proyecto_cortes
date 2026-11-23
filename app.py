import streamlit as st
import pandas as pd
from core.optimizador import optimizar_multi_diametro
from components.validaciones import (
    DIAMETROS_COMERCIALES_NPS,
    DEFAULT_DIAMETRO_ETIQUETA,
    validar_inventario,
    validar_pedidos,
    cargar_csv_datos,
    normalizar_ids_inventario
)
from components.graficos import (
    crear_gemelo_digital_3d,
    crear_grafico_balance_dona,
    crear_grafico_comparativo_dual,
    crear_simulacion_paso_a_paso,
    generar_reporte_texto
)

# ==========================================
# PARÁMETROS BASE CENTRALIZADOS
# ==========================================
DEFAULT_L_COMERCIAL = 6000
DEFAULT_KERF = 4
DEFAULT_UMBRAL = 200

st.set_page_config(page_title="OptiCorte 1D - Plan de Corte", layout="wide")

# ==========================================
# ESTILOS PERSONALIZADOS (Oculta menús y elementos de Streamlit Cloud)
# ==========================================
st.markdown("""
    <style>
    /* Ocultar menú principal, barra superior, decoración y pie de página */
    #MainMenu {visibility: hidden !important; display: none !important;}
    header, [data-testid="stHeader"] {visibility: hidden !important; display: none !important; height: 0px !important;}
    [data-testid="stDecoration"] {visibility: hidden !important; display: none !important;}
    footer {visibility: hidden !important; display: none !important;}

    /* Ocultar barra de herramientas, botón Deploy y widget de estado */
    [data-testid="stToolbar"] {visibility: hidden !important; display: none !important;}
    [data-testid="stStatusWidget"] {visibility: hidden !important; display: none !important;}
    .stDeployButton, [data-testid="stDeployButton"] {visibility: hidden !important; display: none !important;}

    /* Ocultar insignias y botones flotantes de Streamlit Cloud (esquina inferior derecha) */
    [class^="viewerBadge"],
    [class*="_viewerBadge_"],
    [class^="stAppViewBlockContainer"] a[href*="streamlit.io"],
    a[href*="streamlit.io"],
    [class*="_profileContainer_"],
    [class*="_profilePreview_"],
    [data-testid="manage-app-button"] {
        visibility: hidden !important;
        display: none !important;
    }

    /* Estilo de botones principales */
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
if "inventario_base" not in st.session_state:
    st.session_state.inventario_base = pd.DataFrame([{
        "ID_Retal": "R1",
        "Diametro": DEFAULT_DIAMETRO_ETIQUETA,
        "Longitud_mm": 3000,
        "Cantidad": 1
    }])
if "inventario" not in st.session_state:
    st.session_state.inventario = st.session_state.inventario_base.copy()
if "info_diametro_inv" not in st.session_state:
    st.session_state.info_diametro_inv = None
if "pedidos_base" not in st.session_state:
    st.session_state.pedidos_base = pd.DataFrame([
        {"ID_Pieza": "P2900", "Diametro": DEFAULT_DIAMETRO_ETIQUETA, "Longitud_mm": 2900, "Cantidad": 1},
        {"ID_Pieza": "P2000", "Diametro": DEFAULT_DIAMETRO_ETIQUETA, "Longitud_mm": 2000, "Cantidad": 1},
        {"ID_Pieza": "P1900", "Diametro": DEFAULT_DIAMETRO_ETIQUETA, "Longitud_mm": 1900, "Cantidad": 1},
        {"ID_Pieza": "P1800", "Diametro": DEFAULT_DIAMETRO_ETIQUETA, "Longitud_mm": 1800, "Cantidad": 1}
    ])
if "pedidos" not in st.session_state:
    st.session_state.pedidos = st.session_state.pedidos_base.copy()
if "resultados" not in st.session_state:
    st.session_state.resultados = None
if "res_original" not in st.session_state:
    st.session_state.res_original = None
if "csv_inv_firma" not in st.session_state:
    st.session_state.csv_inv_firma = None
if "csv_ped_firma" not in st.session_state:
    st.session_state.csv_ped_firma = None
if "ver_editor_inv" not in st.session_state:
    st.session_state.ver_editor_inv = 0
if "ver_editor_ped" not in st.session_state:
    st.session_state.ver_editor_ped = 0

# Estado del flujo secuencial guiado por pasos
if "paso_conf_ok" not in st.session_state:
    st.session_state.paso_conf_ok = False
if "conf_confirmada" not in st.session_state:
    st.session_state.conf_confirmada = None
if "paso_inv_ok" not in st.session_state:
    st.session_state.paso_inv_ok = False
if "inv_confirmado_df" not in st.session_state:
    st.session_state.inv_confirmado_df = None
if "paso_ped_ok" not in st.session_state:
    st.session_state.paso_ped_ok = False
if "ped_confirmado_df" not in st.session_state:
    st.session_state.ped_confirmado_df = None

st.title("📐 OptiCorte 1D | Optimización y Aprovechamiento de Retales")
st.caption("Herramienta de control de descarte, balance de masa y layout de taller · Grupo 3")

# ==========================================
# TUTORIAL INICIAL PARA OPERARIOS
# ==========================================
with st.expander("📘 Guía Rápida de Uso (4 pasos sencillos)", expanded=True):
    st.markdown("""
    Bienvenido a **OptiCorte 1D**. Ahora puedes **mezclar múltiples diámetros comerciales NPS** (norma ANSI/ASME B36.10M) tanto en tu inventario como en tus pedidos dentro de un mismo proyecto. Sigue estos **4 pasos en orden**:
    1. **⚙️ Configuración:** Elige la longitud del tubo nuevo comercial (`6000 mm` o `9000 mm`). La pérdida por corte (`4 mm`) y el retal mínimo (`200 mm`) son parámetros fijos estándar. Luego pulsa **Confirmar Configuración**.
    2. **📦 Inventario:** Registra tus sobrantes (**retales**) indicando su **Diámetro (NPS)**, longitud y cantidad (o cárgalos desde CSV). Los códigos `R1..Rn` se generan automáticamente. Pulsa **Validar y Confirmar Inventario**.
    3. **📋 Pedidos:** Escribe las piezas requeridas indicando su **Diámetro (NPS)**, longitud y cantidad (o cárgalas desde CSV) y pulsa **Validar y Calcular Optimización**. El motor agrupará cada diámetro por separado sin mezclar medidas distintas.
    4. **📊 Resultados:** Consulta los tubos nuevos por diámetro, el balance de masa global, los retales reservados en almacén, el **Gemelo Digital 3D multi-diámetro** y el simulador paso a paso.
    """)

# ==========================================
# BARRA DE PROGRESO SECUENCIAL
# ==========================================
progreso = 0.0
texto_progreso = "Paso 1 de 4 · Confirma los parámetros en '1. ⚙️ Configuración'"
if st.session_state.paso_ped_ok and st.session_state.resultados:
    progreso = 1.0
    texto_progreso = "✅ ¡Plan de corte listo! Revisa la pestaña '4. 📊 Resultados'"
elif st.session_state.paso_inv_ok:
    progreso = 0.66
    texto_progreso = "Paso 3 de 4 · Ingresa las piezas y calcula en '3. 📋 Pedidos'"
elif st.session_state.paso_conf_ok:
    progreso = 0.33
    texto_progreso = "Paso 2 de 4 · Registra y confirma los retales en '2. 📦 Inventario'"

st.progress(progreso, text=texto_progreso)

# ==========================================
# 2. SISTEMA DE PESTAÑAS SECUENCIALES
# ==========================================
tab_conf, tab_inv, tab_ped, tab_res = st.tabs([
    "1. ⚙️ Configuración",
    "2. 📦 Inventario",
    "3. 📋 Pedidos",
    "4. 📊 Resultados"
])

with tab_conf:
    st.subheader("Paso 1: Parámetros Globales del Proyecto")
    col1, col2, col3 = st.columns(3)
    l_comercial = int(col1.selectbox(
        "Tubo Nuevo Comercial (mm)",
        options=[6000, 9000],
        index=0,
        key="cfg_tubo"
    ))
    kerf = int(col2.number_input(
        "Pérdida por corte (mm)",
        min_value=0,
        value=DEFAULT_KERF,
        step=1,
        disabled=True,
        key="cfg_kerf"
    ))
    umbral = int(col3.number_input(
        "Retal Mínimo (mm)",
        min_value=0,
        value=DEFAULT_UMBRAL,
        step=1,
        disabled=True,
        key="cfg_umbral"
    ))

    conf_actual = (l_comercial, kerf, umbral)
    if st.session_state.paso_conf_ok and st.session_state.conf_confirmada != conf_actual:
        st.session_state.paso_conf_ok = False
        st.session_state.paso_inv_ok = False
        st.session_state.paso_ped_ok = False
        st.session_state.resultados = None
        st.session_state.res_original = None
        st.info("🔄 Modificaste un parámetro de configuración. Vuelve a confirmar este paso para continuar.")

    if st.button("✅ Confirmar Configuración y Desbloquear Inventario", type="primary", use_container_width=True):
        st.session_state.conf_confirmada = conf_actual
        st.session_state.paso_conf_ok = True
        st.rerun()

    if st.session_state.paso_conf_ok:
        st.success("✅ Configuración confirmada. Ya puedes avanzar a la pestaña **2. 📦 Inventario**.")

with tab_inv:
    if not st.session_state.paso_conf_ok:
        st.warning("🔒 Paso bloqueado: primero debes confirmar los parámetros en la pestaña **1. ⚙️ Configuración**.")
        with tab_ped:
            st.warning("🔒 Paso bloqueado: primero debes completar **1. ⚙️ Configuración** y **2. 📦 Inventario**.")
        with tab_res:
            st.warning("🔒 Paso bloqueado: completa y confirma los pasos 1, 2 y 3 para ver los resultados.")
        st.stop()

    st.subheader("Paso 2: Retales Disponibles en Obra")
    archivo_inv = st.file_uploader(
        "📂 Cargar retales desde CSV (columnas: Diametro, Longitud_mm, Cantidad · ID_Retal se genera automáticamente · delimitador ',' o ';')",
        type=["csv"],
        key="uploader_inv"
    )
    if archivo_inv is not None:
        firma_inv = (archivo_inv.name, archivo_inv.size)
        if firma_inv != st.session_state.csv_inv_firma:
            df_csv_inv, err_inv = cargar_csv_datos(
                archivo_inv,
                tipo="inventario",
                diametro_por_defecto=DEFAULT_DIAMETRO_ETIQUETA
            )
            if err_inv:
                st.error(err_inv)
            else:
                st.session_state.inventario_base = df_csv_inv
                st.session_state.inventario = df_csv_inv.copy()
                st.session_state.csv_inv_firma = firma_inv
                st.session_state.ver_editor_inv += 1
                st.session_state.paso_inv_ok = False
                st.session_state.paso_ped_ok = False
                st.session_state.resultados = None
                st.success("Inventario cargado correctamente desde CSV con códigos R1..Rn. Confirma este paso para continuar.")
                if df_csv_inv.attrs.get("aviso_diametro_defecto"):
                    st.info(f"ℹ️ El CSV no contenía columna 'Diametro'; se asignó **{DEFAULT_DIAMETRO_ETIQUETA}** por defecto.")
    else:
        st.session_state.csv_inv_firma = None

    df_inv_editado = st.data_editor(
        st.session_state.inventario_base,
        num_rows="dynamic",
        disabled=["ID_Retal"],
        key=f"editor_inv_{st.session_state.ver_editor_inv}",
        column_order=("ID_Retal", "Diametro", "Longitud_mm", "Cantidad"),
        column_config={
            "ID_Retal": st.column_config.TextColumn("ID Retal (Auto)", disabled=True),
            "Diametro": st.column_config.SelectboxColumn(
                "Diámetro (NPS)",
                options=list(DIAMETROS_COMERCIALES_NPS.keys()),
                default=DEFAULT_DIAMETRO_ETIQUETA,
                required=True
            ),
            "Longitud_mm": st.column_config.NumberColumn("Longitud (mm)", min_value=1, step=1),
            "Cantidad": st.column_config.NumberColumn("Cantidad", min_value=0, step=1)
        }
    )

    # Reasignar automáticamente R1..Rn y diámetro por defecto al agregar o eliminar filas (sin descartar None/NaN)
    df_inv_norm, requiere_rerun_inv = normalizar_ids_inventario(
        df_inv_editado,
        n_filas_base=len(st.session_state.inventario_base),
        diametro_por_defecto=DEFAULT_DIAMETRO_ETIQUETA
    )
    if requiere_rerun_inv:
        st.session_state.inventario_base = df_inv_norm
        st.session_state.inventario = df_inv_norm.copy()
        st.session_state.ver_editor_inv += 1
        st.session_state.paso_inv_ok = False
        st.session_state.paso_ped_ok = False
        st.session_state.resultados = None
        st.session_state.res_original = None
        st.rerun()

    st.session_state.inventario = df_inv_norm

    if st.session_state.paso_inv_ok and st.session_state.inv_confirmado_df is not None:
        if not df_inv_editado.reset_index(drop=True).equals(st.session_state.inv_confirmado_df.reset_index(drop=True)):
            st.session_state.paso_inv_ok = False
            st.session_state.paso_ped_ok = False
            st.session_state.resultados = None
            st.session_state.res_original = None
            st.info("🔄 Modificaste el inventario. Vuelve a validarlo y confirmarlo para desbloquear Pedidos.")

    if st.button("✅ Validar y Confirmar Inventario", type="primary", use_container_width=True):
        inv_ok, msg_inv = validar_inventario(st.session_state.inventario, l_comercial)
        if not inv_ok:
            st.session_state.paso_inv_ok = False
            st.error(msg_inv)
        else:
            st.session_state.inv_confirmado_df = st.session_state.inventario.copy()
            st.session_state.paso_inv_ok = True
            st.rerun()

    if st.session_state.paso_inv_ok:
        st.success("✅ Inventario validado y confirmado. Ya puedes avanzar a la pestaña **3. 📋 Pedidos**.")

with tab_ped:
    if not st.session_state.paso_inv_ok:
        st.warning("🔒 Paso bloqueado: primero debes validar y confirmar tus retales en la pestaña **2. 📦 Inventario**.")
        with tab_res:
            st.warning("🔒 Paso bloqueado: primero debes confirmar **2. 📦 Inventario** y calcular en **3. 📋 Pedidos**.")
        st.stop()

    st.subheader("Paso 3: Piezas Requeridas")
    archivo_ped = st.file_uploader(
        "📂 Cargar pedidos desde CSV (columnas: ID_Pieza, Diametro, Longitud_mm, Cantidad · delimitador ',' o ';')",
        type=["csv"],
        key="uploader_ped"
    )
    if archivo_ped is not None:
        firma_ped = (archivo_ped.name, archivo_ped.size)
        if firma_ped != st.session_state.csv_ped_firma:
            df_csv_ped, err_ped = cargar_csv_datos(
                archivo_ped,
                tipo="pedidos",
                diametro_por_defecto=DEFAULT_DIAMETRO_ETIQUETA
            )
            if err_ped:
                st.error(err_ped)
            else:
                st.session_state.pedidos_base = df_csv_ped
                st.session_state.pedidos = df_csv_ped.copy()
                st.session_state.csv_ped_firma = firma_ped
                st.session_state.ver_editor_ped += 1
                st.session_state.paso_ped_ok = False
                st.session_state.resultados = None
                st.success("Pedidos cargados correctamente desde CSV. Presiona Calcular Optimización.")
                if df_csv_ped.attrs.get("aviso_diametro_defecto"):
                    st.info(f"ℹ️ El CSV no contenía columna 'Diametro'; se asignó **{DEFAULT_DIAMETRO_ETIQUETA}** por defecto.")
    else:
        st.session_state.csv_ped_firma = None

    df_ped_editado = st.data_editor(
        st.session_state.pedidos_base,
        num_rows="dynamic",
        key=f"editor_ped_{st.session_state.ver_editor_ped}",
        column_order=("ID_Pieza", "Diametro", "Longitud_mm", "Cantidad"),
        column_config={
            "ID_Pieza": st.column_config.TextColumn("ID Pieza", required=True),
            "Diametro": st.column_config.SelectboxColumn(
                "Diámetro (NPS)",
                options=list(DIAMETROS_COMERCIALES_NPS.keys()),
                default=DEFAULT_DIAMETRO_ETIQUETA,
                required=True
            ),
            "Longitud_mm": st.column_config.NumberColumn("Longitud (mm)", min_value=1, step=1, required=True),
            "Cantidad": st.column_config.NumberColumn("Cantidad", min_value=0, step=1, required=True)
        }
    )
    st.session_state.pedidos = df_ped_editado

    if st.session_state.paso_ped_ok and st.session_state.ped_confirmado_df is not None:
        if not df_ped_editado.reset_index(drop=True).equals(st.session_state.ped_confirmado_df.reset_index(drop=True)):
            st.session_state.paso_ped_ok = False
            st.session_state.resultados = None
            st.session_state.res_original = None
            st.info("🔄 Modificaste la lista de pedidos. Pulsa nuevamente 'Calcular Optimización' para actualizar los resultados.")

    if st.button("🚀 Validar y Calcular Optimización", type="primary", use_container_width=True):
        ped_ok, msg_ped = validar_pedidos(st.session_state.pedidos, l_comercial, kerf)
        if not ped_ok:
            st.session_state.paso_ped_ok = False
            st.error(msg_ped)
        else:
            try:
                # Optimización agrupada por diámetro comercial NPS (dos pasadas: Optimizado BFD vs Orden Original).
                # Cada diámetro usa únicamente los retales de inventario que coinciden exactamente con ese diámetro.
                with st.spinner("Optimizando cortes por diámetro y calculando balance global de material..."):
                    st.session_state.resultados = optimizar_multi_diametro(
                        st.session_state.inventario,
                        st.session_state.pedidos,
                        l_comercial,
                        kerf,
                        umbral,
                        DIAMETROS_COMERCIALES_NPS,
                        diametro_defecto=DEFAULT_DIAMETRO_ETIQUETA,
                        usar_orden_original=False
                    )
                    st.session_state.res_original = optimizar_multi_diametro(
                        st.session_state.inventario,
                        st.session_state.pedidos,
                        l_comercial,
                        kerf,
                        umbral,
                        DIAMETROS_COMERCIALES_NPS,
                        diametro_defecto=DEFAULT_DIAMETRO_ETIQUETA,
                        usar_orden_original=True
                    )
                st.session_state.ped_confirmado_df = st.session_state.pedidos.copy()
                st.session_state.paso_ped_ok = True
                st.rerun()
            except Exception as e:
                st.error(f"⚠️ Ocurrió un error inesperado en el motor de optimización: {str(e)}")

    if st.session_state.paso_ped_ok and st.session_state.resultados:
        st.success("✅ ¡Cálculo exitoso! Ve a la pestaña **4. 📊 Resultados** para ver el plan de corte y el Gemelo Digital 3D.")

with tab_res:
    if not st.session_state.paso_ped_ok or not st.session_state.resultados:
        st.warning("🔒 Paso bloqueado: primero debes validar y calcular tus piezas en la pestaña **3. 📋 Pedidos**.")
        st.stop()

    res = st.session_state.resultados
    bal = res["balance"]
    res_orig = st.session_state.res_original

    st.subheader("Balance Global de Materiales")
    col0, col1, col2, col3, col4 = st.columns(5)
    col0.metric("Material Origen (Total)", f"{bal['material_total_origen']} mm")
    col1.metric("Tubos Nuevos (Total)", res["tubos_comprados"])
    col2.metric("Material Incorporado", f"{bal['incorporado']} mm")
    col3.metric("Pérdida por Corte", f"{bal['perdida']} mm")
    col4.metric("Descarte Inútil", f"{bal['descarte']} mm")

    if res.get("tubos_por_diametro"):
        st.caption("**Desglose de Tubos Nuevos a Comprar por Diámetro (NPS):**")
        df_tubos_diam = pd.DataFrame([
            {"Diámetro (NPS)": d, "Tubos Nuevos": c}
            for d, c in res["tubos_por_diametro"].items()
        ])
        st.dataframe(df_tubos_diam, use_container_width=True, hide_index=True)

    if res.get("retales_reservados"):
        with st.expander(
            f"📦 Retales de otros diámetros reservados en almacén ({len(res['retales_reservados'])} registro(s) no consumidos)",
            expanded=False
        ):
            st.write("Estos retales pertenecen a diámetros que no fueron solicitados en los pedidos de esta orden y permanecen intactos en almacén:")
            st.dataframe(pd.DataFrame(res["retales_reservados"]), use_container_width=True, hide_index=True)

    if not bal["cuadra_perfecto"]:
        st.error("⚠️ Alerta: El balance de masas no cuadra con el material de origen.")

    # Cálculo de ahorros comparando el escenario base (Orden Original) contra el Optimizado (BFD):
    # - diff_tubos > 0    -> Tubos comerciales que se evitaron comprar gracias al ordenamiento.
    # - diff_descarte > 0 -> Milímetros de chatarra/descarte reducidos frente al corte sin ordenar.
    st.subheader("Comparativa de Eficiencia (Optimizado vs Orden Original)")
    diff_tubos = res_orig["tubos_comprados"] - res["tubos_comprados"]
    diff_descarte = res_orig["balance"]["descarte"] - bal["descarte"]

    if diff_tubos > 0 or diff_descarte > 0:
        msg_tubos = f"ahorró **{diff_tubos} tubo{'s' if diff_tubos > 1 else ''}** comercial{'es' if diff_tubos > 1 else ''}" if diff_tubos > 0 else ""
        if diff_descarte > 0:
            msg_desc = f"redujo **{diff_descarte} mm** de descarte"
        elif diff_descarte < 0:
            msg_desc = f"generó **{-diff_descarte} mm** de descarte (asumible al evitar compras)"
        else:
            msg_desc = "mantuvo el mismo descarte"

        conector = " y " if (msg_tubos and msg_desc) else ""
        st.info(f"✅ Cortar en el orden original requería **{res_orig['tubos_comprados']} tubos**. La optimización {msg_tubos}{conector}{msg_desc}.")
    elif diff_tubos == 0 and diff_descarte == 0:
        st.info("⚖️ El orden original ingresado ya era igual de eficiente que la optimización.")
    else:
        st.warning(f"⚠️ El orden original resultó mejor por **{-diff_tubos} tubos** y **{-diff_descarte} mm** (situación anómala del algoritmo Greedy).")

    # Tabla comparativa
    df_comp = pd.DataFrame({
        "Métrica": ["Tubos Nuevos", "Descarte (mm)", "Pérdida (mm)", "Retal Generado (mm)"],
        "Optimizado": [res["tubos_comprados"], bal["descarte"], bal["perdida"], bal["nuevo_retal"]],
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
    # 3. GEMELO DIGITAL 3D (LAYOUT DE TALLER MULTI-DIÁMETRO)
    # ==========================================
    if res["detalle_csv"]:
        st.markdown("---")
        st.subheader("📐 Gemelo Digital 3D: Layout de Taller")

        diametros_en_plan = list(dict.fromkeys(
            f.get("Diametro", DEFAULT_DIAMETRO_ETIQUETA) for f in res["detalle_csv"]
        ))
        filtro_diam_3d = st.selectbox(
            "Filtrar vista 3D y simulador por diámetro:",
            options=["Todos los diámetros"] + diametros_en_plan,
            index=0,
            key="filtro_diam_resultados"
        )

        detalle_visible = (
            res["detalle_csv"]
            if filtro_diam_3d == "Todos los diámetros"
            else [f for f in res["detalle_csv"] if f.get("Diametro") == filtro_diam_3d]
        )

        st.write(
            "Simulación volumétrica de tubos cilíndricos huecos escalados a su diámetro exterior real (ANSI/ASME B36.10M). "
            "**Gira, rota o amplía** el modelo con el cursor:"
        )

        fig_3d = crear_gemelo_digital_3d(detalle_visible, kerf_nominal=kerf)
        st.plotly_chart(fig_3d, use_container_width=True)

        # ==========================================
        # 3.1 SIMULADOR DE CORTE PASO A PASO
        # ==========================================
        st.markdown("---")
        st.subheader("⚙️ Simulador de Taller: Avance de Corte")
        st.write("Selecciona una barra y desplaza el carro de la sierra para simular el proceso físico de seccionamiento:")

        lista_origenes = [f["Origen_ID"] for f in detalle_visible]
        col_sel_barra, col_slider = st.columns([1, 3])

        with col_sel_barra:
            barra_sel_id = st.selectbox("Barra a simular:", lista_origenes, key="sel_sim_barra")
            fila_sel = next((f for f in detalle_visible if f["Origen_ID"] == barra_sel_id), detalle_visible[0])
            st.caption(f"**Diámetro:** {fila_sel.get('Diametro', DEFAULT_DIAMETRO_ETIQUETA)}")
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
    else:
        st.info("No se registraron cortes activos en el plan actual.")

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