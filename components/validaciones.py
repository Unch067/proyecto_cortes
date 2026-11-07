import pandas as pd


def validar_datos_entrada(df_inventario, df_pedidos, l_comercial, kerf):
    # 1. Validar decimales y negativos ANTES de filtrar
    for nombre, df in [("Inventario", df_inventario), ("Pedidos", df_pedidos)]:
        if df.empty:
            continue

        if (df["Cantidad"] % 1 != 0).any():
            return False, f"Error en {nombre}: Las cantidades no admiten decimales."

        if (df["Cantidad"] < 0).any():
            return False, f"Error en {nombre}: Las cantidades no pueden ser negativas."

        if (df["Longitud_mm"] % 1 != 0).any() or (df["Longitud_mm"] <= 0).any():
            return False, f"Error en {nombre}: Las longitudes deben ser números enteros positivos."

    # 2. Filtrar cantidades 0
    df_inv_val = df_inventario[df_inventario["Cantidad"] > 0] if not df_inventario.empty else df_inventario
    df_ped_val = df_pedidos[df_pedidos["Cantidad"] > 0] if not df_pedidos.empty else df_pedidos

    # 3. Validar duplicados
    if not df_inv_val.empty and df_inv_val["ID_Retal"].duplicated().any():
        return False, "IDs de retales duplicados."
    if not df_ped_val.empty and df_ped_val["ID_Pieza"].duplicated().any():
        return False, "IDs de piezas duplicados."

    # 4. Validar viabilidad física y kerf
    if not df_inv_val.empty and (df_inv_val["Longitud_mm"] > l_comercial).any():
        return False, "Existen retales mayores al tubo nuevo."

    if not df_ped_val.empty:
        imposibles = df_ped_val[
            ~((df_ped_val["Longitud_mm"] == l_comercial) |
              (df_ped_val["Longitud_mm"] + kerf <= l_comercial))
        ]
        if not imposibles.empty:
            return False, f"Piezas imposibles de cortar considerando kerf: {imposibles['ID_Pieza'].tolist()}"

    return True, ""