import plotly.graph_objects as go
from plotly.subplots import make_subplots

def _crear_cubo_malla(x0, x1, y_centro, ancho_y, alto_z, color, hover_text, opacity=1.0):
    """
    Construye un prisma rectangular 3D paramétrico mediante triangulación estándar (Mesh3d).
    8 vértices y 12 triángulos orientados.
    """
    y0 = y_centro - ancho_y / 2
    y1 = y_centro + ancho_y / 2
    z0 = -alto_z / 2
    z1 = alto_z / 2

    # 8 Vértices del prisma
    vx = [x0, x1, x1, x0, x0, x1, x1, x0]
    vy = [y0, y0, y1, y1, y0, y0, y1, y1]
    vz = [z0, z0, z0, z0, z1, z1, z1, z1]

    # 12 Triángulos que forman las 6 caras del paralelepípedo
    i = [7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2]
    j = [3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3]
    k = [0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6]

    return go.Mesh3d(
        x=vx, y=vy, z=vz,
        i=i, j=j, k=k,
        color=color,
        opacity=opacity,
        lighting=dict(ambient=0.6, diffuse=0.8, roughness=0.5, specular=0.4),
        hoverinfo="text",
        text=hover_text,
        showlegend=False
    )


def crear_gemelo_digital_3d(detalle_csv, kerf_nominal=4):
    """
    Genera el entorno 3D interactivo (Gemelo Digital) representando todas
    las barras, cortes y retales clasificados en sus bancadas de taller.
    Adaptado para tema oscuro y contraste industrial.
    """
    fig = go.Figure()
    
    ancho_tubo = 80.0
    alto_tubo = 80.0
    paso_y = 200.0

    nombres_eje_y = []
    posiciones_eje_y = []

    for idx, fila in enumerate(detalle_csv):
        origen_id = fila["Origen_ID"]
        y_pos = idx * paso_y
        nombres_eje_y.append(origen_id)
        posiciones_eje_y.append(y_pos)

        x_actual = 0
        piezas_str = fila["Piezas_Asignadas"].split(" | ") if fila["Piezas_Asignadas"] else []

        for p_idx, p in enumerate(piezas_str):
            if "(" in p:
                nombre = p.split("(")[0]
                largo = int(p.split("(")[1].replace(")", ""))

                # 1. Prisma 3D: Pieza Útil
                hover_pieza = (
                    f"<b>Bancada:</b> {origen_id}<br>"
                    f"<b>Pieza:</b> {nombre}<br>"
                    f"<b>Longitud:</b> {largo} mm<br>"
                    f"<b>Tramo:</b> [{x_actual} mm - {x_actual + largo} mm]"
                )
                fig.add_trace(_crear_cubo_malla(
                    x0=x_actual,
                    x1=x_actual + largo,
                    y_centro=y_pos,
                    ancho_y=ancho_tubo,
                    alto_z=alto_tubo,
                    color="#1E88E5",  # Azul ingeniería
                    hover_text=hover_pieza
                ))
                x_actual += largo

                # 2. Prisma 3D: Disco de Corte (Kerf)
                es_ultimo_corte = (p_idx == len(piezas_str) - 1) and (fila["Sobrante_mm"] == 0)
                if not es_ultimo_corte and (x_actual < fila["Longitud_Inicial"]):
                    espesor_kerf = kerf_nominal if kerf_nominal > 0 else 4
                    hover_kerf = (
                        f"<b>Pérdida por Corte (Kerf):</b> {espesor_kerf} mm<br>"
                        f"<b>Cota de corte:</b> {x_actual} mm"
                    )
                    fig.add_trace(_crear_cubo_malla(
                        x0=x_actual,
                        x1=x_actual + espesor_kerf,
                        y_centro=y_pos,
                        ancho_y=ancho_tubo * 1.15,
                        alto_z=alto_tubo * 1.15,
                        color="#E53935",  # Rojo advertencia
                        hover_text=hover_kerf
                    ))
                    x_actual += espesor_kerf

        # 3. Prisma 3D: Sobrante / Descarte
        sobrante_mm = fila["Sobrante_mm"]
        if sobrante_mm > 0:
            clasif = fila["Clasificacion"]
            color_sob = "#FFB300" if clasif == "Retal Reutilizable" else "#78909C"
            hover_sob = (
                f"<b>Bancada:</b> {origen_id}<br>"
                f"<b>Estado:</b> {clasif}<br>"
                f"<b>Longitud:</b> {sobrante_mm} mm<br>"
                f"<b>Tramo final:</b> [{x_actual} mm - {fila['Longitud_Inicial']} mm]"
            )
            fig.add_trace(_crear_cubo_malla(
                x0=x_actual,
                x1=fila["Longitud_Inicial"],
                y_centro=y_pos,
                ancho_y=ancho_tubo,
                alto_z=alto_tubo,
                color=color_sob,
                hover_text=hover_sob,
                opacity=0.9
            ))

    # Optimización para visualización y tema oscuro de Streamlit
    fig.update_layout(
        scene=dict(
            xaxis=dict(
                title="Longitud del Material (mm)",
                backgroundcolor="rgba(15, 23, 42, 0.6)",
                gridcolor="#334155",
                showbackground=True,
                zerolinecolor="#64748B",
                color="#F8FAFC"
            ),
            yaxis=dict(
                title="Bancada / Tubo",
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
                eye=dict(x=-1.3, y=-1.6, z=1.2),
                up=dict(x=0, y=0, z=1)
            ),
            aspectmode="data"
        ),
        margin=dict(l=0, r=0, b=10, t=10),
        height=500,
        paper_bgcolor="rgba(0,0,0,0)"
    )
    
    return fig

from plotly.subplots import make_subplots

def crear_grafico_balance_dona(bal):
    """
    Dona analítica con visualización de balance de masa y KPI central
    de aprovechamiento útil en modo oscuro.
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

    for l, v in zip(etiquetas_todas, valores_todos):
        if v > 0:
            labels.append(l)
            values.append(v)
            colors.append(colores_map[l])
            pulls.append(0.04 if l == "Material Incorporado" else 0.0)

    fig = go.Figure()
    fig.add_trace(go.Pie(
        labels=labels,
        values=values,
        hole=0.62,
        pull=pulls,
        marker=dict(colors=colors, line=dict(color="#0F172A", width=2)),
        textinfo="percent+label",
        textposition="outside",
        textfont=dict(color="#F8FAFC", size=11),
        hovertemplate="<b>%{label}</b><br>Longitud: %{value} mm<br>Proporción: %{percent}<extra></extra>"
    ))

    # Anotación central con el KPI de aprovechamiento
    fig.update_layout(
        annotations=[
            dict(
                text=f"<span style='font-size:11px;color:#94A3B8;'>APROVECHAMIENTO</span><br><b style='font-size:24px;color:#38BDF8;'>{eficiencia}%</b>",
                x=0.5, y=0.5,
                font_size=14,
                showarrow=False
            )
        ],
        showlegend=False,
        height=360,
        margin=dict(l=20, r=20, b=20, t=30),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )
    return fig


def crear_grafico_comparativo_dual(res, res_orig):
    """
    Subplots desacoplados para comparar Tubos Nuevos y Descarte en mm
    evitando distorsión de escala dimensional.
    """
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Tubos Comerciales Necesarios", "Descarte Inútil (mm)"),
        horizontal_spacing=0.18
    )

    # 1. Subplot: Tubos Nuevos
    fig.add_trace(
        go.Bar(
            name="Optimizado (IA)",
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

    # 2. Subplot: Descarte Inútil (mm)
    fig.add_trace(
        go.Bar(
            name="Optimizado (IA)",
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
        height=360,
        margin=dict(l=10, r=10, b=20, t=50),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.12,
            xanchor="center",
            x=0.5,
            font=dict(color="#F8FAFC")
        ),
        font=dict(color="#F8FAFC")
    )
    fig.update_xaxes(showgrid=False, color="#94A3B8")
    fig.update_yaxes(showgrid=True, gridcolor="#334155", color="#94A3B8")
    return fig