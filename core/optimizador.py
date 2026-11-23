"""
Motor de optimización de corte unidimensional (1D Cutting Stock Problem) - OptiCorte 1D.
Implementa la heurística Best-Fit Decreasing (BFD) respetando la física real del corte
(pérdida por espesor de disco o kerf) y verifica la conservación exacta de masa en milímetros enteros.
"""
import pandas as pd


def optimizar_cortes(df_retales, df_pedidos, l_comercial, kerf, umbral, usar_orden_original=False):
    """
    Calcula el plan óptimo de corte priorizando el aprovechamiento de retales existentes
    antes de comprar tubos comerciales nuevos.

    Parámetros:
    - df_retales: DataFrame con retales disponibles en inventario (ID_Retal, Longitud_mm, Cantidad).
    - df_pedidos: DataFrame con piezas requeridas (ID_Pieza, Longitud_mm, Cantidad).
    - l_comercial (int): Longitud de cada tubo nuevo comercial en milímetros (ej. 6000 o 9000 mm).
    - kerf (int): Pérdida de material en milímetros causada por el espesor del disco de sierra en cada corte.
    - umbral (int): Longitud mínima en milímetros para que un sobrante sea retal reutilizable (ej. 200 mm).
    - usar_orden_original (bool):
        * False -> Ordena piezas de mayor a menor (Best-Fit Decreasing, optimizado).
        * True  -> Respeta exactamente el orden en que el usuario ingresó las piezas (referencia comparativa).

    Retorna:
    Diccionario con 'tubos_comprados', 'balance', 'detalle_csv' y 'pendientes'.
    """
    # =========================================================================
    # PASO 1: EXPANSIÓN DE PIEZAS Y RETALES A UNIDADES INDIVIDUALES (EN INT mm)
    # =========================================================================
    # Todas las longitudes se convierten explícitamente a enteros (int) en milímetros
    # para evitar errores de redondeo de punto flotante (float IEEE 754) en el balance de masa.
    piezas_expandidas = []
    if not df_pedidos.empty:
        # Se ignoran las filas con Cantidad == 0 (desactivadas por el usuario)
        for _, fila in df_pedidos[df_pedidos["Cantidad"] > 0].iterrows():
            # Si una fila pide Cantidad = 3, se crean 3 piezas individuales independientes (ID_1, ID_2, ID_3)
            for i in range(int(fila["Cantidad"])):
                piezas_expandidas.append({
                    "ID": f"{fila['ID_Pieza']}_{i+1}" if fila["Cantidad"] > 1 else str(fila["ID_Pieza"]),
                    "L": int(fila["Longitud_mm"])
                })

    # De la misma forma, cada retal del inventario con Cantidad > 0 se expande en barras físicas individuales
    fuentes_disponibles = []
    if not df_retales.empty:
        for _, fila in df_retales[df_retales["Cantidad"] > 0].iterrows():
            for i in range(int(fila["Cantidad"])):
                fuentes_disponibles.append({
                    "Origen_ID": f"Retal_{fila['ID_Retal']}_{i+1}",
                    "Longitud_Inicial": int(fila["Longitud_mm"]),  # Medida original antes de cualquier corte
                    "Longitud_Actual": int(fila["Longitud_mm"]),   # Saldo disponible que irá disminuyendo
                    "Es_Nuevo": False,                             # False = proviene del inventario en almacén
                    "Piezas_Asignadas": [],                        # Lista de piezas que se cortarán de esta barra
                    "Kerf_Total": 0                                # Acumulador de pérdida por disco en esta barra
                })

    # =========================================================================
    # PASO 2: ORDENAMIENTO (BEST-FIT DECREASING vs ORDEN ORIGINAL DE LLEGADA)
    # =========================================================================
    # - Si usar_orden_original=True: se procesan las piezas exactamente como las escribió el usuario.
    #   Riesgo: piezas pequeñas pueden ocupar retales grandes e impedir luego ubicar piezas largas.
    # - Si usar_orden_original=False (Optimizado): se ordenan de MAYOR a MENOR longitud (reverse=True).
    #   Ventaja: las piezas largas se ubican primero en los huecos justos, ahorrando tubos comerciales.
    if usar_orden_original:
        piezas_ordenadas = piezas_expandidas
    else:
        piezas_ordenadas = sorted(piezas_expandidas, key=lambda x: x["L"], reverse=True)

    tubos_nuevos_usados = 0
    piezas_pendientes = []
    contador_tubos_nuevos = 1

    # =========================================================================
    # PASO 3: ASIGNACIÓN BEST-FIT DECREASING Y REGLA FÍSICA DEL CORTE (KERF)
    # =========================================================================
    for pieza in piezas_ordenadas:
        L_pieza = pieza["L"]
        candidatos = []  # Guardará tuplas: (remanente, Longitud_Inicial, Origen_ID, referencia_fuente)

        # 3.1 Evaluar todas las barras/retales ya abiertos o existentes en inventario
        for fuente in fuentes_disponibles:
            L_disp = fuente["Longitud_Actual"]
            # REGLA FÍSICA CASO A (Encaje exacto):
            # Si la pieza mide exactamente igual que el saldo disponible (L_disp == L_pieza),
            # NO se requiere corte con sierra -> pérdida por disco (kerf) = 0 mm y remanente = 0 mm.
            if L_disp == L_pieza:
                candidatos.append((0, fuente["Longitud_Inicial"], fuente["Origen_ID"], fuente))
            # REGLA FÍSICA CASO B (Corte estándar con disco):
            # Si la barra es más larga que la pieza, sí se realiza un corte físico; por lo tanto,
            # debe caber la pieza más el espesor del disco (L_disp >= L_pieza + kerf).
            elif L_disp >= L_pieza + kerf:
                candidatos.append((L_disp - (L_pieza + kerf), fuente["Longitud_Inicial"], fuente["Origen_ID"], fuente))

        # 3.2 Evaluar también la alternativa de abrir un tubo comercial nuevo (referencia = None)
        # Aplicando exactamente la misma regla física de ajuste (0 kerf si encaja exacto, +kerf si se corta).
        if l_comercial == L_pieza:
            candidatos.append((0, l_comercial, f"Tubo_Nuevo_{contador_tubos_nuevos}", None))
        elif l_comercial >= L_pieza + kerf:
            candidatos.append((l_comercial - (L_pieza + kerf), l_comercial, f"Tubo_Nuevo_{contador_tubos_nuevos}", None))

        # Si ninguna barra existente ni un tubo nuevo puede alojar la pieza (ej. pieza de 6500 mm en tubo de 6000 mm),
        # se registra en piezas_pendientes sin colapsar el programa ni comprar tubos inútiles.
        if not candidatos:
            piezas_pendientes.append(pieza)
            continue

        # 3.3 SELECCIÓN DEL MEJOR CANDIDATO CON 3 CRITERIOS DE DESEMPATE DETERMINISTAS:
        # 1º x[0] -> Menor remanente inmediato (criterio Best-Fit: encaje más ajustado posible).
        # 2º x[1] -> Menor longitud inicial de la barra (en empate, consume primero retales más cortos).
        # 3º x[2] -> Orden alfabético del Origen_ID (asegura que el resultado sea 100% reproducible).
        candidatos.sort(key=lambda x: (x[0], x[1], x[2]))
        mejor = candidatos[0]
        remanente = mejor[0]
        fuente_seleccionada = mejor[3]

        # Si la mejor opción fue None, significa que debemos abrir/comprar un nuevo tubo comercial
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

        # Aplicamos el corte real sobre la barra elegida:
        # 0 mm de pérdida si la pieza ocupó exactamente el saldo disponible; de lo contrario, se suma 'kerf'.
        kerf_aplicado = 0 if fuente_seleccionada["Longitud_Actual"] == L_pieza else kerf
        fuente_seleccionada["Piezas_Asignadas"].append(pieza)
        fuente_seleccionada["Kerf_Total"] += kerf_aplicado
        fuente_seleccionada["Longitud_Actual"] = remanente

    # =========================================================================
    # PASO 4: CLASIFICACIÓN DE SOBRANTES Y BALANCE DE MASAS (CONSERVACIÓN)
    # =========================================================================
    balance = {"material_total_origen": 0, "incorporado": 0, "perdida": 0, "descarte": 0, "nuevo_retal": 0}
    plan_csv = []

    for fuente in fuentes_disponibles:
        # Los retales del inventario que no recibieron ninguna pieza no entraron a la sierra,
        # por lo que se omiten del balance de esta orden de corte (quedan intactos en almacén).
        if not fuente["Piezas_Asignadas"]:
            continue

        balance["material_total_origen"] += fuente["Longitud_Inicial"]
        balance["perdida"] += fuente["Kerf_Total"]
        balance["incorporado"] += sum(p["L"] for p in fuente["Piezas_Asignadas"])

        # Regla de clasificación del sobrante restante en cada barra utilizada:
        # - sobrante >= umbral (ej. >= 200 mm) -> Retal Reutilizable (vuelve al almacén).
        # - 0 < sobrante < umbral              -> Descarte (merma no aprovechable / chatarra).
        # - sobrante == 0                      -> Exacto (aprovechamiento del 100% sin sobrante).
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

    # ECUACIÓN DE CONSERVACIÓN DE MASA (AUDITORÍA):
    # Material Origen Total debe ser EXACTAMENTE igual a: Incorporado + Pérdida + Descarte + Nuevo Retal
    total_calculado = balance["incorporado"] + balance["perdida"] + balance["descarte"] + balance["nuevo_retal"]
    balance["cuadra_perfecto"] = (balance["material_total_origen"] == total_calculado)

    return {
        "tubos_comprados": tubos_nuevos_usados,
        "balance": balance,
        "detalle_csv": plan_csv,
        "pendientes": piezas_pendientes
    }


def optimizar_multi_diametro(
    df_retales,
    df_pedidos,
    l_comercial,
    kerf,
    umbral,
    diametros_map,
    diametro_defecto='4" (Ø ext. 114.3 mm)',
    usar_orden_original=False
):
    """
    Ejecuta la optimización de cortes agrupando los pedidos por diámetro comercial NPS.
    Para cada diámetro presente en los pedidos, filtra únicamente los retales de Inventario
    que coinciden exactamente con ese diámetro y consolida el balance de masa global,
    el detalle por barra (con columnas 'Diametro' y 'Diametro_mm'), el desglose de tubos
    nuevos por diámetro y los retales de otros diámetros reservados en almacén.
    """
    df_ped = df_pedidos.copy() if not df_pedidos.empty else pd.DataFrame(columns=["ID_Pieza", "Diametro", "Longitud_mm", "Cantidad"])
    df_ret = df_retales.copy() if not df_retales.empty else pd.DataFrame(columns=["ID_Retal", "Diametro", "Longitud_mm", "Cantidad"])

    if "Diametro" not in df_ped.columns:
        df_ped["Diametro"] = diametro_defecto
    if "Diametro" not in df_ret.columns:
        df_ret["Diametro"] = diametro_defecto

    df_ped_act = df_ped[df_ped["Cantidad"] > 0].copy() if not df_ped.empty else df_ped
    df_ret_act = df_ret[df_ret["Cantidad"] > 0].copy() if not df_ret.empty else df_ret

    diametros_pedidos = list(dict.fromkeys(df_ped_act["Diametro"].tolist())) if not df_ped_act.empty else []

    balance_global = {
        "material_total_origen": 0,
        "incorporado": 0,
        "perdida": 0,
        "descarte": 0,
        "nuevo_retal": 0
    }
    tubos_totales = 0
    tubos_por_diametro = {}
    detalle_global = []
    pendientes_globales = []

    for diam in diametros_pedidos:
        sub_ped = df_ped_act[df_ped_act["Diametro"] == diam]
        sub_ret = df_ret_act[df_ret_act["Diametro"] == diam] if not df_ret_act.empty else pd.DataFrame()

        res_d = optimizar_cortes(
            sub_ret, sub_ped, l_comercial, kerf, umbral, usar_orden_original=usar_orden_original
        )

        diam_mm = float(diametros_map.get(diam, 114.3))
        diam_corto = diam.split(" (")[0]

        tubos_por_diametro[diam] = res_d["tubos_comprados"]
        tubos_totales += res_d["tubos_comprados"]

        for clave in balance_global:
            balance_global[clave] += res_d["balance"][clave]

        for fila in res_d["detalle_csv"]:
            fila_con_diam = {
                "Origen_ID": f"{fila['Origen_ID']} [{diam_corto}]",
                "Diametro": diam,
                "Diametro_mm": diam_mm,
                "Tipo": fila["Tipo"],
                "Longitud_Inicial": fila["Longitud_Inicial"],
                "Piezas_Asignadas": fila["Piezas_Asignadas"],
                "Kerf_Total": fila["Kerf_Total"],
                "Sobrante_mm": fila["Sobrante_mm"],
                "Clasificacion": fila["Clasificacion"]
            }
            detalle_global.append(fila_con_diam)

        for p in res_d["pendientes"]:
            p_copy = dict(p)
            p_copy["Diametro"] = diam
            pendientes_globales.append(p_copy)

    total_calc = (
        balance_global["incorporado"]
        + balance_global["perdida"]
        + balance_global["descarte"]
        + balance_global["nuevo_retal"]
    )
    balance_global["cuadra_perfecto"] = (balance_global["material_total_origen"] == total_calc)

    # Retales en almacén cuyos diámetros no fueron solicitados en los pedidos de esta orden
    if not df_ret_act.empty:
        df_reservados = df_ret_act[~df_ret_act["Diametro"].isin(diametros_pedidos)].copy()
        retales_reservados = df_reservados[["ID_Retal", "Diametro", "Longitud_mm", "Cantidad"]].to_dict("records")
    else:
        retales_reservados = []

    return {
        "tubos_comprados": tubos_totales,
        "tubos_por_diametro": tubos_por_diametro,
        "balance": balance_global,
        "detalle_csv": detalle_global,
        "pendientes": pendientes_globales,
        "retales_reservados": retales_reservados
    }