import pandas as pd


def optimizar_cortes(df_retales, df_pedidos, l_comercial, kerf, umbral, usar_orden_original=False):
    # PASO 1: Expansión de piezas
    piezas_expandidas = []
    if not df_pedidos.empty:
        for _, fila in df_pedidos[df_pedidos["Cantidad"] > 0].iterrows():
            for i in range(int(fila["Cantidad"])):
                piezas_expandidas.append({
                    "ID": f"{fila['ID_Pieza']}_{i+1}" if fila["Cantidad"] > 1 else str(fila["ID_Pieza"]),
                    "L": int(fila["Longitud_mm"])
                })

    fuentes_disponibles = []
    if not df_retales.empty:
        for _, fila in df_retales[df_retales["Cantidad"] > 0].iterrows():
            for i in range(int(fila["Cantidad"])):
                fuentes_disponibles.append({
                    "Origen_ID": f"Retal_{fila['ID_Retal']}_{i+1}",
                    "Longitud_Inicial": int(fila["Longitud_mm"]),
                    "Longitud_Actual": int(fila["Longitud_mm"]),
                    "Es_Nuevo": False,
                    "Piezas_Asignadas": [],
                    "Kerf_Total": 0
                })

    # PASO 2: Ordenamiento
    if usar_orden_original:
        piezas_ordenadas = piezas_expandidas
    else:
        piezas_ordenadas = sorted(piezas_expandidas, key=lambda x: x["L"], reverse=True)

    tubos_nuevos_usados = 0
    piezas_pendientes = []
    contador_tubos_nuevos = 1

    # PASO 3: Asignación Best-Fit Decreasing
    for pieza in piezas_ordenadas:
        L_pieza = pieza["L"]
        candidatos = []

        for fuente in fuentes_disponibles:
            L_disp = fuente["Longitud_Actual"]
            if L_disp == L_pieza:
                candidatos.append((0, fuente["Longitud_Inicial"], fuente["Origen_ID"], fuente))
            elif L_disp >= L_pieza + kerf:
                candidatos.append((L_disp - (L_pieza + kerf), fuente["Longitud_Inicial"], fuente["Origen_ID"], fuente))

        if l_comercial == L_pieza:
            candidatos.append((0, l_comercial, f"Tubo_Nuevo_{contador_tubos_nuevos}", None))
        elif l_comercial >= L_pieza + kerf:
            candidatos.append((l_comercial - (L_pieza + kerf), l_comercial, f"Tubo_Nuevo_{contador_tubos_nuevos}", None))

        if not candidatos:
            piezas_pendientes.append(pieza)
            continue

        # Desempate: 1) menor remanente, 2) menor longitud original, 3) ID alfabético
        candidatos.sort(key=lambda x: (x[0], x[1], x[2]))
        mejor = candidatos[0]
        remanente = mejor[0]
        fuente_seleccionada = mejor[3]

        if fuente_seleccionada is None:
            nueva_fuente = {
                "Origen_ID": f"Tubo_Nuevo_{contador_tubos_nuevos}",
                "Longitud_Inicial": l_comercial,
                "Longitud_Actual": l_comercial,
                "Es_Nuevo": True,
                "Piezas_Asignadas": [],
                "Kerf_Total": 0
            }
            fuentes_disponibles.append(nueva_fuente)
            fuente_seleccionada = nueva_fuente
            tubos_nuevos_usados += 1
            contador_tubos_nuevos += 1

        kerf_aplicado = 0 if fuente_seleccionada["Longitud_Actual"] == L_pieza else kerf
        fuente_seleccionada["Piezas_Asignadas"].append(pieza)
        fuente_seleccionada["Kerf_Total"] += kerf_aplicado
        fuente_seleccionada["Longitud_Actual"] = remanente

    # PASO 4: Balance de masas
    balance = {"material_total_origen": 0, "incorporado": 0, "perdida": 0, "descarte": 0, "nuevo_retal": 0}
    plan_csv = []

    for fuente in fuentes_disponibles:
        if not fuente["Piezas_Asignadas"]:
            continue

        balance["material_total_origen"] += fuente["Longitud_Inicial"]
        balance["perdida"] += fuente["Kerf_Total"]
        balance["incorporado"] += sum(p["L"] for p in fuente["Piezas_Asignadas"])

        sobrante = fuente["Longitud_Actual"]
        if sobrante >= umbral:
            balance["nuevo_retal"] += sobrante
            clase_sobrante = "Retal Reutilizable"
        elif sobrante > 0:
            balance["descarte"] += sobrante
            clase_sobrante = "Descarte"
        else:
            clase_sobrante = "Exacto"

        plan_csv.append({
            "Origen_ID": fuente["Origen_ID"],
            "Tipo": "Tubo Nuevo" if fuente["Es_Nuevo"] else "Retal Inventario",
            "Longitud_Inicial": fuente["Longitud_Inicial"],
            "Piezas_Asignadas": " | ".join([f"{p['ID']}({p['L']})" for p in fuente["Piezas_Asignadas"]]),
            "Kerf_Total": fuente["Kerf_Total"],
            "Sobrante_mm": sobrante,
            "Clasificacion": clase_sobrante
        })

    total_calculado = balance["incorporado"] + balance["perdida"] + balance["descarte"] + balance["nuevo_retal"]
    balance["cuadra_perfecto"] = (balance["material_total_origen"] == total_calculado)

    return {
        "tubos_comprados": tubos_nuevos_usados,
        "balance": balance,
        "detalle_csv": plan_csv,
        "pendientes": piezas_pendientes
    }