import math
try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
except ModuleNotFoundError:
    go = None
    make_subplots = None


def _crear_cilindro_hueco_malla(
    x0, x1, y_centro, radio_ext, radio_int, color, hover_text, opacity=1.0, segmentos=24
):
    """
    Construye un tubo cilíndrico hueco 3D paramétrico mediante triangulación (Mesh3d):
    pared cilíndrica exterior, perforación cilíndrica interior y tapas anulares en ambos extremos.
    """
    n = max(8, int(segmentos))
    vx, vy, vz = [], [], []

    # 4 anillos de n vértices:
    # 0: exterior x0 | 1: exterior x1 | 2: interior x0 | 3: interior x1
    for anillo_x, r in ((x0, radio_ext), (x1, radio_ext), (x0, radio_int), (x1, radio_int)):
        for s in range(n):
            theta = 2.0 * math.pi * s / n
            vx.append(anillo_x)
            vy.append(y_centro + r * math.cos(theta))
            vz.append(r * math.sin(theta))

    i_idx, j_idx, k_idx = [], [], []
    o0, o1, i0, i1 = 0, n, 2 * n, 3 * n

    for s in range(n):
        sn = (s + 1) % n

        # 1. Pared cilíndrica exterior
        i_idx.extend([o0 + s, o0 + s])
        j_idx.extend([o0 + sn, o1 + sn])
        k_idx.extend([o1 + sn, o1 + s])

        # 2. Perforación cilíndrica interior (orientación invertida)
        i_idx.extend([i0 + s, i0 + s])
        j_idx.extend([i1 + sn, i1 + s])
        k_idx.extend([i0 + sn, i1 + sn])

        # 3. Tapa anular en x0
        i_idx.extend([o0 + s, o0 + s])
        j_idx.extend([i0 + s, i0 + sn])
        k_idx.extend([i0 + sn, o0 + sn])

        # 4. Tapa anular en x1
        i_idx.extend([o1 + s, o1 + s])
        j_idx.extend([o1 + sn, i1 + sn])
        k_idx.extend([i1 + sn, i1 + s])

    return go.Mesh3d(
        x=vx, y=vy, z=vz,
        i=i_idx, j=j_idx, k=k_idx,
        color=color,
        opacity=opacity,
        lighting=dict(ambient=0.55, diffuse=0.85, roughness=0.45, specular=0.5),
        hoverinfo="text",
        text=hover_text,
        showlegend=False
    )


def crear_gemelo_digital_3d(detalle_csv, kerf_nominal=4, diametro_mm=114.3, diametro_etiqueta=None):
    """
    Genera el entorno 3D interactivo con tubos cilíndricos huecos escalados
    individualmente según el diámetro real de cada bancada ('Diametro_mm' si existe,
    o 'diametro_mm' por defecto) bajo la norma ANSI/ASME B36.10M.
    """
    fig = go.Figure()

    nombres_eje_y = []
    posiciones_eje_y = []

    y_actual = 0.0
    radio_anterior = None
    radio_max = 0.0

    for idx, fila in enumerate(detalle_csv):
        origen_id = fila["Origen_ID"]
        diam_fila = max(15.0, float(fila.get("Diametro_mm", diametro_mm)))
        etiqueta_fila = fila.get("Diametro") or diametro_etiqueta or f"{diam_fila:.1f} mm"
        diam_corto = etiqueta_fila.split(" (")[0]
        base_id = origen_id.split(" [")[0]
        etiqueta_y = f"{base_id} ({diam_corto})"

        radio_ext = diam_fila / 2.0
        radio_max = max(radio_max, radio_ext)
        radio_int = radio_ext * 0.72  # Espesor de pared visible (28% del radio)
        radio_ext_kerf = radio_ext * 1.18
        radio_int_kerf = radio_int * 0.92

        # Separación dinámica en Y proporcional a los radios adyacentes para evitar solapamientos
        if idx == 0:
            y_pos = 0.0
        else:
            margen_y = max(150.0, (radio_anterior + radio_ext) * 1.15)
            y_pos = y_actual + radio_anterior + radio_ext + margen_y
        y_actual = y_pos
        radio_anterior = radio_ext

        nombres_eje_y.append(etiqueta_y)
        posiciones_eje_y.append(y_pos)

        x_actual = 0
        piezas_str = fila["Piezas_Asignadas"].split(" | ") if fila["Piezas_Asignadas"] else []

        for p_idx, p in enumerate(piezas_str):
            if "(" in p:
                nombre, largo_str = p.rsplit("(", 1)
                largo = int(largo_str.replace(")", ""))

                # 1. Cilindro hueco 3D: Pieza Útil
                hover_pieza = (
                    f"<b>Bancada:</b> {origen_id}<br>"
                    f"<b>Pieza:</b> {nombre}<br>"
                    f"<b>Longitud:</b> {largo} mm<br>"
                    f"<b>Diámetro:</b> {etiqueta_fila}<br>"
                    f"<b>Tramo:</b> [{x_actual} - {x_actual + largo} mm]"
                )
                fig.add_trace(_crear_cilindro_hueco_malla(
                    x0=x_actual,
                    x1=x_actual + largo,
                    y_centro=y_pos,
                    radio_ext=radio_ext,
                    radio_int=radio_int,
                    color="#1E88E5",
                    hover_text=hover_pieza
                ))
                x_actual += largo

                # 2. Anillo 3D: Kerf (Corte de disco)
                es_ultimo = (p_idx == len(piezas_str) - 1) and (fila["Sobrante_mm"] == 0)
                if not es_ultimo and (x_actual < fila["Longitud_Inicial"]):
                    espesor = kerf_nominal if kerf_nominal > 0 else 4
                    hover_kerf = f"<b>Disco (Kerf):</b> {espesor} mm<br><b>Cota:</b> {x_actual} mm"
                    fig.add_trace(_crear_cilindro_hueco_malla(
                        x0=x_actual,
                        x1=x_actual + espesor,
                        y_centro=y_pos,
                        radio_ext=radio_ext_kerf,
                        radio_int=radio_int_kerf,
                        color="#E53935",
                        hover_text=hover_kerf
                    ))
                    x_actual += espesor

        # 3. Cilindro hueco 3D: Sobrante
        sobrante_mm = fila["Sobrante_mm"]
        if sobrante_mm > 0:
            clasif = fila["Clasificacion"]
            color_sob = "#FFB300" if clasif == "Retal Reutilizable" else "#78909C"
            hover_sob = (
                f"<b>Bancada:</b> {origen_id}<br>"
                f"<b>Estado:</b> {clasif}<br>"
                f"<b>Longitud:</b> {sobrante_mm} mm<br>"
                f"<b>Diámetro:</b> {etiqueta_fila}"
            )
            fig.add_trace(_crear_cilindro_hueco_malla(
                x0=x_actual,
                x1=fila["Longitud_Inicial"],
                y_centro=y_pos,
                radio_ext=radio_ext,
                radio_int=radio_int,
                color=color_sob,
                hover_text=hover_sob,
                opacity=0.9
            ))

    # Aspect ratio dinámico para mantener la sección circular real en Y-Z sin aplastar cilindros
    n_tubos = max(1, len(detalle_csv))
    span_y = max(radio_max * 2.4, y_actual + radio_max * 2.4)
    span_z = max(radio_max * 2.4, 1.0)
    aspect_z = 0.45
    aspect_y = max(0.45, min(2.4, aspect_z * (span_y / span_z)))
    aspect_x = max(3.4, min(4.6, 3.8 + 0.1 * (n_tubos - 1)))

    # Ajuste de escala visual (evita que 6000 mm deforme la ventana)
    fig.update_layout(
        scene=dict(
            xaxis=dict(
                title="Longitud (mm)",
                backgroundcolor="rgba(15, 23, 42, 0.6)",
                gridcolor="#334155",
                showbackground=True,
                zerolinecolor="#64748B",
                color="#F8FAFC"
            ),
            yaxis=dict(
                title="",
                tickvals=posiciones_eje_y,
                ticktext=nombres_eje_y,
                backgroundcolor="rgba(15, 23, 42, 0.6)",
                gridcolor="#334155",
                showbackground=True,
                color="#F8FAFC"
            ),
            zaxis=dict(
                title="",
                showticklabels=False,
                showgrid=False,
                backgroundcolor="rgba(15, 23, 42, 0.6)",
                showbackground=True
            ),
            camera=dict(
                eye=dict(x=-1.5, y=-1.5, z=1.4),
                up=dict(x=0, y=0, z=1)
            ),
            aspectmode="manual",
            aspectratio=dict(x=aspect_x, y=aspect_y, z=aspect_z)
        ),
        margin=dict(l=0, r=0, b=10, t=10),
        height=450,
        paper_bgcolor="rgba(0,0,0,0)"
    )
    return fig


def crear_grafico_balance_dona(bal):
    """
    Dona analítica con márgenes ampliados para evitar cortes de texto.
    """
    total_origen = bal.get("material_total_origen", 0)
    incorporado = bal.get("incorporado", 0)
    eficiencia = round((incorporado / total_origen * 100), 1) if total_origen > 0 else 0

    etiquetas_todas = ["Material Incorporado", "Pérdida por Corte", "Descarte Inútil", "Retal Reutilizable"]
    valores_todos = [incorporado, bal.get("perdida", 0), bal.get("descarte", 0), bal.get("nuevo_retal", 0)]
    colores_map = {
        "Material Incorporado": "#1E88E5",
        "Pérdida por Corte": "#E53935",
        "Descarte Inútil": "#78909C",
        "Retal Reutilizable": "#FFB300"
    }

    labels = []
    values = []
    colors = []
    pulls = []
    text_labels = []

    for l, v in zip(etiquetas_todas, valores_todos):
        if v > 0:
            labels.append(l)
            values.append(v)
            colors.append(colores_map[l])
            pulls.append(0.04 if l == "Material Incorporado" else 0.0)
            pct = (v / total_origen * 100.0) if total_origen > 0 else 0.0
            text_labels.append(f"{pct:.1f}%" if pct >= 2.0 else "")

    fig = go.Figure()
    fig.add_trace(go.Pie(
        labels=labels,
        values=values,
        hole=0.60,
        pull=pulls,
        marker=dict(colors=colors, line=dict(color="#0F172A", width=2)),
        text=text_labels,
        textinfo="text",
        textposition="inside",
        textfont=dict(color="#F8FAFC", size=12),
        hovertemplate="<b>%{label}</b><br>Longitud: %{value} mm<br>Proporción: %{percent}<extra></extra>"
    ))

    fig.update_layout(
        annotations=[
            dict(
                text=f"<span style='font-size:11px;color:#94A3B8;'>APROVECHAMIENTO</span><br><b style='font-size:26px;color:#38BDF8;'>{eficiencia}%</b>",
                x=0.5, y=0.5,
                font_size=14,
                showarrow=False
            )
        ],
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.22,
            xanchor="center",
            x=0.5,
            font=dict(color="#F8FAFC", size=11)
        ),
        height=380,
        margin=dict(l=20, r=20, b=70, t=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )
    return fig


def crear_grafico_comparativo_dual(res, res_orig):
    """
    Subplots desacoplados con espaciado horizontal ampliado y títulos concisos.
    """
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Tubos a Comprar (u)", "Descarte Total (mm)"),
        horizontal_spacing=0.25
    )

    # 1. Tubos Nuevos
    fig.add_trace(
        go.Bar(
            name="Optimizado",
            x=["Tubos"],
            y=[res["tubos_comprados"]],
            marker_color="#10B981",
            text=[f"{res['tubos_comprados']} u"],
            textposition="auto",
            hovertemplate="Optimizado: %{y} tubos<extra></extra>"
        ),
        row=1, col=1
    )
    fig.add_trace(
        go.Bar(
            name="Orden Original",
            x=["Tubos"],
            y=[res_orig["tubos_comprados"]],
            marker_color="#EF4444",
            text=[f"{res_orig['tubos_comprados']} u"],
            textposition="auto",
            hovertemplate="Original: %{y} tubos<extra></extra>"
        ),
        row=1, col=1
    )

    # 2. Descarte Inútil
    fig.add_trace(
        go.Bar(
            name="Optimizado",
            x=["Descarte"],
            y=[res["balance"]["descarte"]],
            marker_color="#10B981",
            text=[f"{res['balance']['descarte']} mm"],
            textposition="auto",
            showlegend=False,
            hovertemplate="Optimizado: %{y} mm<extra></extra>"
        ),
        row=1, col=2
    )
    fig.add_trace(
        go.Bar(
            name="Orden Original",
            x=["Descarte"],
            y=[res_orig["balance"]["descarte"]],
            marker_color="#EF4444",
            text=[f"{res_orig['balance']['descarte']} mm"],
            textposition="auto",
            showlegend=False,
            hovertemplate="Original: %{y} mm<extra></extra>"
        ),
        row=1, col=2
    )

    fig.update_layout(
        barmode="group",
        height=380,
        margin=dict(l=10, r=10, b=40, t=50),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.12,
            xanchor="center",
            x=0.5,
            font=dict(color="#F8FAFC", size=11)
        ),
        font=dict(color="#F8FAFC")
    )
    fig.update_xaxes(showgrid=False, color="#94A3B8")
    fig.update_yaxes(
        showgrid=True, 
        gridcolor="#334155", 
        color="#94A3B8",
        rangemode="nonnegative"  # Evita que el eje Y muestre números negativos en 0
    )
    return fig


def crear_simulacion_paso_a_paso(fila_detalle, cota_corte_actual, kerf_nominal=4):
    """
    Renderiza la simulación dinámica de una barra específica en función
    de la cota de avance de la sierra, escalando visualmente el grosor
    de la barra según su diámetro exterior real (Diametro_mm).
    """
    longitud_total = fila_detalle["Longitud_Inicial"]
    origen_id = fila_detalle["Origen_ID"]
    espesor_kerf = kerf_nominal if kerf_nominal > 0 else 0

    diametro_mm = float(fila_detalle.get("Diametro_mm", 114.3))
    diametro_etq = fila_detalle.get("Diametro") or f"{diametro_mm:.1f} mm"
    diam_corto = diametro_etq.split(" (")[0]
    etiqueta_y = origen_id if "[" in origen_id else f"{origen_id} [{diam_corto}]"

    # Mapeo lineal del rango comercial NPS (21.3 mm a 609.6 mm) al grosor visual [0.22, 0.85]
    factor_diam = max(0.0, min(1.0, (diametro_mm - 21.3) / (609.6 - 21.3)))
    grosor_barra = round(0.22 + factor_diam * (0.85 - 0.22), 3)
    mitad_disco = min(0.56, grosor_barra / 2.0 + 0.08)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=[etiqueta_y],
        x=[longitud_total],
        base=0,
        width=grosor_barra,
        orientation='h',
        marker_color='#334155',
        name='Material Pendiente',
        hoverinfo='skip',
        showlegend=False
    ))

    x_cursor = 0
    piezas_str = fila_detalle["Piezas_Asignadas"].split(" | ") if fila_detalle["Piezas_Asignadas"] else []

    for p_idx, p in enumerate(piezas_str):
        if "(" in p:
            nombre, largo_str = p.rsplit("(", 1)
            largo = int(largo_str.replace(")", ""))
            fin_pieza = x_cursor + largo

            if fin_pieza <= cota_corte_actual:
                fig.add_trace(go.Bar(
                    y=[etiqueta_y],
                    x=[largo],
                    base=x_cursor,
                    width=grosor_barra,
                    orientation='h',
                    marker_color='#0284C7',
                    text=f"✂️ {nombre} ({largo} mm)",
                    textposition='inside',
                    textfont=dict(color='white', size=11),
                    name='Pieza Cortada',
                    showlegend=False,
                    hovertemplate=(
                        f"<b>Pieza:</b> {nombre}<br>"
                        f"<b>Diámetro:</b> {diametro_etq}<br>"
                        f"<b>Longitud:</b> {largo} mm<extra></extra>"
                    )
                ))
            elif x_cursor < cota_corte_actual < fin_pieza:
                avance_parcial = cota_corte_actual - x_cursor
                fig.add_trace(go.Bar(
                    y=[etiqueta_y],
                    x=[avance_parcial],
                    base=x_cursor,
                    width=grosor_barra,
                    orientation='h',
                    marker_color='#38BDF8',
                    text=f"Cortando... {avance_parcial} mm",
                    textposition='inside',
                    textfont=dict(color='black', size=10),
                    name='En Corte',
                    showlegend=False,
                    hovertemplate=(
                        f"<b>Procesando:</b> {nombre}<br>"
                        f"<b>Diámetro:</b> {diametro_etq}<br>"
                        f"<b>Avance:</b> {avance_parcial}/{largo} mm<extra></extra>"
                    )
                ))

            x_cursor = fin_pieza

            if x_cursor < longitud_total and espesor_kerf > 0:
                if x_cursor + espesor_kerf <= cota_corte_actual:
                    fig.add_trace(go.Bar(
                        y=[etiqueta_y],
                        x=[espesor_kerf],
                        base=x_cursor,
                        width=grosor_barra,
                        orientation='h',
                        marker_color='#EF4444',
                        name='Kerf',
                        showlegend=False,
                        hoverinfo='skip'
                    ))
                x_cursor += espesor_kerf

    if cota_corte_actual >= longitud_total and fila_detalle["Sobrante_mm"] > 0:
        color_sob = '#EAB308' if fila_detalle["Clasificacion"] == "Retal Reutilizable" else '#64748B'
        sobrante_val = fila_detalle["Sobrante_mm"]
        texto_sob = (
            f"{sobrante_val} mm"
            if sobrante_val < 300
            else f"{fila_detalle['Clasificacion']} ({sobrante_val} mm)"
        )
        fig.add_trace(go.Bar(
            y=[etiqueta_y],
            x=[sobrante_val],
            base=longitud_total - sobrante_val,
            width=grosor_barra,
            orientation='h',
            marker_color=color_sob,
            text=texto_sob,
            textposition='inside',
            textfont=dict(color='black' if fila_detalle["Clasificacion"] == "Retal Reutilizable" else 'white', size=11),
            name='Sobrante',
            showlegend=False,
            hovertemplate=(
                f"<b>{fila_detalle['Clasificacion']}:</b> {sobrante_val} mm<br>"
                f"<b>Diámetro:</b> {diametro_etq}<extra></extra>"
            )
        ))

    fig.add_shape(
        type="line",
        x0=cota_corte_actual, x1=cota_corte_actual,
        y0=-mitad_disco, y1=mitad_disco,
        line=dict(color="#F43F5E", width=3, dash="dot")
    )

    fig.update_layout(
        barmode='overlay',
        xaxis=dict(
            title="Posición a lo largo del perfil (mm)",
            range=[0, longitud_total * 1.02],
            showgrid=True,
            gridcolor='#1E293B',
            color='#94A3B8'
        ),
        yaxis=dict(
            range=[-0.6, 0.6],
            showticklabels=True,
            showgrid=False,
            color='#F8FAFC'
        ),
        height=200,
        margin=dict(l=10, r=10, b=30, t=10),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig

def generar_reporte_texto(res, res_orig, l_comercial, kerf, umbral, diametro_mm=114.3, diametro_etiqueta=None):
    """
    Genera un informe técnico formal en formato texto estructurado (Markdown)
    para bitácora de obra y auditoría de materiales.
    """
    bal = res["balance"]
    lineas = []
    lineas.append("# INFORME TÉCNICO DE CORTE Y BALANCE DE MATERIAL")
    lineas.append("==================================================")
    lineas.append(f"- Longitud Comercial Estándar: {l_comercial} mm")
    if res.get("tubos_por_diametro"):
        diams_str = ", ".join(res["tubos_por_diametro"].keys())
        lineas.append(f"- Diámetros en Proyecto (NPS): {diams_str}")
    elif diametro_etiqueta:
        lineas.append(f"- Diámetro Comercial (NPS):    {diametro_etiqueta}")
    else:
        lineas.append(f"- Diámetro del Tubo:           {diametro_mm} mm ({diametro_mm / 25.4:.2f} in)")
    lineas.append(f"- Espesor de Disco (Kerf):      {kerf} mm")
    lineas.append(f"- Umbral Mínimo de Retal:       {umbral} mm")
    lineas.append("")
    lineas.append("## 1. BALANCE GLOBAL DE MASA")
    lineas.append("--------------------------------------------------")
    lineas.append(f"Material Origen Total:  {bal['material_total_origen']} mm")
    lineas.append(f"Tubos Nuevos a Comprar: {res['tubos_comprados']} unidades")
    if res.get("tubos_por_diametro"):
        for d_etq, cant_t in res["tubos_por_diametro"].items():
            lineas.append(f"  * {d_etq}: {cant_t} tubo(s)")
    lineas.append(f"Material Incorporado:   {bal['incorporado']} mm")
    lineas.append(f"Pérdida por Corte:      {bal['perdida']} mm")
    lineas.append(f"Descarte Inútil:        {bal['descarte']} mm")
    lineas.append(f"Retal Reutilizable:     {bal['nuevo_retal']} mm")
    lineas.append(f"Balance Cuadra 100%:    {'SÍ' if bal['cuadra_perfecto'] else 'NO (ALERTA)'}")
    lineas.append("")
    lineas.append("## 2. COMPARATIVA DE EFICIENCIA")
    lineas.append("--------------------------------------------------")
    diff_tubos = res_orig["tubos_comprados"] - res["tubos_comprados"]
    diff_desc = res_orig["balance"]["descarte"] - bal["descarte"]
    lineas.append(f"- Tubos: Original={res_orig['tubos_comprados']} | Optimizado={res['tubos_comprados']} (Ahorro: {diff_tubos} u)")
    lineas.append(f"- Descarte: Original={res_orig['balance']['descarte']} mm | Optimizado={bal['descarte']} mm (Ahorro: {diff_desc} mm)")
    lineas.append("")
    lineas.append("## 3. HOJA DE RUTA PARA OPERARIO DE TALLER")
    lineas.append("--------------------------------------------------")
    for f in res["detalle_csv"]:
        lineas.append(f"[{f['Origen_ID']}] Longitud: {f['Longitud_Inicial']} mm")
        lineas.append(f"  Piezas a cortar: {f['Piezas_Asignadas']}")
        lineas.append(f"  Pérdida en disco: {f['Kerf_Total']} mm")
        lineas.append(f"  Sobrante: {f['Sobrante_mm']} mm -> Clasificación: {f['Clasificacion']}")
        lineas.append("")
    
    if res.get("pendientes"):
        lineas.append("## 4. PIEZAS PENDIENTES SIN ATENDER")
        lineas.append("--------------------------------------------------")
        for p in res["pendientes"]:
            id_p = p.get("ID") if p.get("ID") is not None else p.get("ID_Pieza", "Sin_ID")
            largo_p = p.get("L") if p.get("L") is not None else p.get("Longitud_mm", 0)
            cant_str = f" (Cant: {p['Cantidad']})" if "Cantidad" in p else ""
            lineas.append(f"- Pieza {id_p}: {largo_p} mm{cant_str}")
        lineas.append("")

    return "\n".join(lineas)