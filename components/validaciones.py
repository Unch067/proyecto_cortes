"""
Módulo de validación de dominio y carga de archivos CSV - OptiCorte 1D.
Actúa como guardia de seguridad antes de ejecutar el motor de optimización,
protegiendo el cálculo contra datos corruptos, vacíos, negativos o físicamente imposibles.
"""
import io
import pandas as pd

# Tabla estándar de tubería comercial ANSI/ASME B36.10M (NPS -> Diámetro exterior real en mm)
DIAMETROS_COMERCIALES_NPS = {
    '1/2" (Ø ext. 21.3 mm)': 21.3,
    '3/4" (Ø ext. 26.7 mm)': 26.7,
    '1" (Ø ext. 33.4 mm)': 33.4,
    '1 1/4" (Ø ext. 42.2 mm)': 42.2,
    '1 1/2" (Ø ext. 48.3 mm)': 48.3,
    '2" (Ø ext. 60.3 mm)': 60.3,
    '2 1/2" (Ø ext. 73.0 mm)': 73.0,
    '3" (Ø ext. 88.9 mm)': 88.9,
    '4" (Ø ext. 114.3 mm)': 114.3,
    '6" (Ø ext. 168.3 mm)': 168.3,
    '8" (Ø ext. 219.1 mm)': 219.1,
    '10" (Ø ext. 273.1 mm)': 273.1,
    '12" (Ø ext. 323.9 mm)': 323.9,
    '14" (Ø ext. 355.6 mm)': 355.6,
    '16" (Ø ext. 406.4 mm)': 406.4,
    '18" (Ø ext. 457.2 mm)': 457.2,
    '20" (Ø ext. 508.0 mm)': 508.0,
    '24" (Ø ext. 609.6 mm)': 609.6,
}
DEFAULT_DIAMETRO_ETIQUETA = '4" (Ø ext. 114.3 mm)'


def cargar_csv_datos(archivo, tipo="inventario", diametro_por_defecto=DEFAULT_DIAMETRO_ETIQUETA):
    """
    Lee y sanitiza archivos CSV externos de Inventario o Pedidos.
    - Detecta automáticamente delimitadores ',' o ';' (compatible con Excel en español).
    - Convierte decimales escritos con coma o punto en milímetros enteros (int).
    - Para Inventario, acepta opcionalmente la columna 'Diametro' (validando que pertenezca
      a la tabla comercial NPS; si no existe, asigna 'diametro_por_defecto') y autogenera ID_Retal (R1..Rn).
    Retorna (df_limpio, "") si es válido, o (None, mensaje_error_espanol) si falla.
    """
    es_inventario = (tipo == "inventario")
    col_id = "ID_Retal" if es_inventario else "ID_Pieza"
    nombre_tabla = "Inventario" if es_inventario else "Pedidos"
    # En Inventario solo se exigen Longitud_mm y Cantidad porque ID_Retal se autogenera (R1..Rn)
    columnas_esperadas = ["Longitud_mm", "Cantidad"] if es_inventario else [col_id, "Longitud_mm", "Cantidad"]

    try:
        if hasattr(archivo, "getvalue"):
            raw = archivo.getvalue()
        elif hasattr(archivo, "read"):
            raw = archivo.read()
        else:
            raw = archivo

        # Intenta decodificar en UTF-8 con BOM, UTF-8 estándar o Latin-1 (común en Excel Windows)
        if isinstance(raw, bytes):
            texto = None
            for enc in ("utf-8-sig", "utf-8", "latin-1"):
                try:
                    texto = raw.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            if texto is None:
                return None, f"Error en CSV de {nombre_tabla}: No se pudo decodificar el archivo."
        else:
            texto = str(raw)

        lineas = [l.strip() for l in texto.splitlines() if l.strip()]
        if not lineas:
            return None, f"Error en CSV de {nombre_tabla}: El archivo está vacío."

        # Detección determinista de delimitador analizando la primera línea (encabezado)
        cabecera = lineas[0]
        delimitador = ";" if cabecera.count(";") > cabecera.count(",") else ","

        df = pd.read_csv(io.StringIO("\n".join(lineas)), sep=delimitador, dtype=str)
        df.columns = [c.strip() for c in df.columns]

        faltantes = [c for c in columnas_esperadas if c not in df.columns]
        if faltantes:
            return None, (
                f"Error en CSV de {nombre_tabla}: Faltan las columnas {faltantes}. "
                f"Se requieren: {', '.join(columnas_esperadas)}."
            )

        tiene_col_diametro = es_inventario and ("Diametro" in df.columns)
        cols_a_extraer = columnas_esperadas + (["Diametro"] if tiene_col_diametro else [])
        df = df[cols_a_extraer].copy()
        if df.empty:
            return None, f"Error en CSV de {nombre_tabla}: El archivo no contiene filas de datos."

        if df.isna().any().any():
            return None, f"Error en CSV de {nombre_tabla}: Existen celdas vacías en el archivo."

        if not es_inventario:
            df[col_id] = df[col_id].astype(str).str.strip()
            if (df[col_id] == "").any():
                return None, f"Error en CSV de {nombre_tabla}: El identificador ({col_id}) no puede estar vacío."

        # Validar columna Diametro en Inventario si viene incluida en el CSV
        if tiene_col_diametro:
            df["Diametro"] = df["Diametro"].astype(str).str.strip()
            invalidos = [d for d in df["Diametro"].unique() if d not in DIAMETROS_COMERCIALES_NPS]
            if invalidos:
                return None, (
                    f"Error en CSV de {nombre_tabla}: Diámetro(s) fuera de la tabla estándar NPS: {invalidos}."
                )

        # Conversión de Longitud_mm (admite decimales con coma o punto y convierte a int mm)
        longitudes_str = df["Longitud_mm"].astype(str).str.strip().str.replace(",", ".", regex=False)
        longitudes_num = pd.to_numeric(longitudes_str, errors="coerce")
        if longitudes_num.isna().any():
            return None, f"Error en CSV de {nombre_tabla}: 'Longitud_mm' contiene valores no numéricos."
        df["Longitud_mm"] = longitudes_num.round().astype(int)

        # Conversión de Cantidad (admite formato '2', '2.0', '2,0', rechaza decimales fraccionarios como '1,5')
        cantidades_str = df["Cantidad"].astype(str).str.strip().str.replace(",", ".", regex=False)
        cantidades_num = pd.to_numeric(cantidades_str, errors="coerce")
        if cantidades_num.isna().any():
            return None, f"Error en CSV de {nombre_tabla}: 'Cantidad' contiene valores no numéricos."
        if (cantidades_num % 1 != 0).any():
            return None, f"Error en CSV de {nombre_tabla}: Las cantidades no admiten decimales."
        df["Cantidad"] = cantidades_num.astype(int)

        # Para Inventario, se genera automáticamente la secuencia limpia R1..Rn y se asegura la columna Diametro
        if es_inventario:
            df = df.reset_index(drop=True)
            if not tiene_col_diametro:
                df["Diametro"] = diametro_por_defecto
            df.insert(0, "ID_Retal", [f"R{i + 1}" for i in range(len(df))])
            df = df[["ID_Retal", "Diametro", "Longitud_mm", "Cantidad"]]

        return df, ""
    except Exception as e:
        return None, f"Error al procesar el archivo CSV de {nombre_tabla}: {str(e)}"


def normalizar_ids_inventario(df_editado, n_filas_base=None, diametro_por_defecto=DEFAULT_DIAMETRO_ETIQUETA):
    """
    Asegura que la columna ID_Retal tenga la secuencia exacta ['R1', 'R2', ..., 'Rn']
    y que cualquier fila recién agregada reciba por defecto el diámetro activo del proyecto,
    sin descartar filas que aún tengan Longitud_mm o Cantidad en None/NaN.

    Retorna una tupla (df_normalizado, requiere_rerun):
    - requiere_rerun=True indica a la interfaz que debe refrescar el editor con los nuevos códigos/diámetros.
    - requiere_rerun=False evita ciclos infinitos de st.rerun() cuando los códigos y diámetros ya están asignados.
    """
    df_norm = df_editado.reset_index(drop=True).copy()
    ids_esperados = [f"R{i + 1}" for i in range(len(df_norm))]

    falta_col_diam = "Diametro" not in df_norm.columns
    if falta_col_diam:
        df_norm["Diametro"] = diametro_por_defecto

    tiene_nulos_id = bool(df_norm["ID_Retal"].isna().any()) if not df_norm.empty else False
    tiene_nulos_diam = bool(
        df_norm["Diametro"].isna().any() or (df_norm["Diametro"].astype(str).str.strip() == "").any()
    ) if not df_norm.empty else False
    ids_actuales = df_norm["ID_Retal"].tolist() if not df_norm.empty else []
    cambio_cantidad_filas = (n_filas_base is not None and len(df_norm) != n_filas_base)

    # Si el usuario agregó/eliminó filas o algún ID/Diámetro llegó vacío (None/NaN), se renumera de R1 a Rn
    if falta_col_diam or cambio_cantidad_filas or tiene_nulos_id or tiene_nulos_diam or ids_actuales != ids_esperados:
        df_norm["ID_Retal"] = ids_esperados
        if not df_norm.empty:
            mask_diam_vacio = df_norm["Diametro"].isna() | (df_norm["Diametro"].astype(str).str.strip() == "")
            df_norm.loc[mask_diam_vacio, "Diametro"] = diametro_por_defecto
        return df_norm, True

    return df_norm, False


def filtrar_inventario_por_diametro(df_inventario, diametro_objetivo):
    """
    Filtra el inventario para entregar al optimizador únicamente los retales activos (Cantidad > 0)
    cuyo diámetro coincide exactamente con el diámetro seleccionado en Configuración.
    Retorna (df_compatibles, unidades_compatibles, unidades_otros_diametros).
    """
    if df_inventario.empty:
        return df_inventario.copy(), 0, 0

    df_activos = df_inventario[df_inventario["Cantidad"] > 0].copy()
    if df_activos.empty:
        return df_activos, 0, 0

    if "Diametro" not in df_activos.columns:
        return df_activos, int(df_activos["Cantidad"].sum()), 0

    mask_match = df_activos["Diametro"] == diametro_objetivo
    df_compatibles = df_activos[mask_match].copy()
    unidades_compatibles = int(df_compatibles["Cantidad"].sum())
    unidades_otros = int(df_activos[~mask_match]["Cantidad"].sum())
    return df_compatibles, unidades_compatibles, unidades_otros


def _validar_tabla_base(df, nombre, col_id):
    """
    Reglas base compartidas por Inventario y Pedidos (se ejecutan ANTES de filtrar Cantidad == 0):
    1. Bloquea celdas vacías (NaN/None) e identificadores en blanco.
    2. Bloquea cantidades decimales (ej. 1.5 piezas) y cantidades negativas (ej. -1).
    3. Exige longitudes en milímetros enteros estrictamente positivos (> 0).
    """
    if df.empty:
        return True, ""

    if df[[col_id, "Longitud_mm", "Cantidad"]].isna().any().any():
        return False, f"Error en {nombre}: Existen celdas vacías o sin completar."

    if (df[col_id].astype(str).str.strip() == "").any():
        return False, f"Error en {nombre}: El identificador ({col_id}) no puede estar vacío."

    # El operador módulo (% 1 != 0) detecta si el número tiene parte fraccionaria
    if (df["Cantidad"] % 1 != 0).any():
        return False, f"Error en {nombre}: Las cantidades no admiten decimales."

    if (df["Cantidad"] < 0).any():
        return False, f"Error en {nombre}: Las cantidades no pueden ser negativas."

    if (df["Longitud_mm"] % 1 != 0).any() or (df["Longitud_mm"] <= 0).any():
        return False, f"Error en {nombre}: Las longitudes deben ser números enteros positivos."

    return True, ""


def validar_inventario(df_inventario, l_comercial):
    """
    Valida las reglas de negocio específicas del Paso 2 (Inventario de Retales):
    - Reglas base de integridad numérica y celdas vacías.
    - Verifica que la columna Diametro (si está presente) no tenga celdas vacías ni valores fuera de la tabla NPS.
    - No permite IDs duplicados entre retales activos (Cantidad > 0).
    - Ningún retal puede medir más que la longitud de un tubo comercial nuevo (l_comercial).
    """
    es_valido, msg = _validar_tabla_base(df_inventario, "Inventario", "ID_Retal")
    if not es_valido:
        return False, msg

    if not df_inventario.empty and "Diametro" in df_inventario.columns:
        if df_inventario["Diametro"].isna().any() or (df_inventario["Diametro"].astype(str).str.strip() == "").any():
            return False, "Error en Inventario: Existen filas sin diámetro comercial asignado."
        invalidos = [
            d for d in df_inventario["Diametro"].astype(str).str.strip().unique()
            if d not in DIAMETROS_COMERCIALES_NPS
        ]
        if invalidos:
            return False, f"Error en Inventario: Diámetro(s) fuera de la tabla estándar NPS: {invalidos}."

    # Se filtran filas con Cantidad > 0 (Cantidad == 0 se permite para desactivar filas sin borrarlas)
    df_inv_val = df_inventario[df_inventario["Cantidad"] > 0] if not df_inventario.empty else df_inventario

    if not df_inv_val.empty and df_inv_val["ID_Retal"].duplicated().any():
        return False, "IDs de retales duplicados."

    # Regla física de almacén: un retal sobrante nunca puede ser más largo que el tubo nuevo original
    if not df_inv_val.empty and (df_inv_val["Longitud_mm"] > l_comercial).any():
        return False, "Existen retales mayores al tubo nuevo."

    return True, ""


def validar_pedidos(df_pedidos, l_comercial, kerf):
    """
    Valida las reglas de negocio específicas del Paso 3 (Pedidos de Piezas):
    - Reglas base de integridad numérica y celdas vacías.
    - No permite IDs duplicados entre piezas activas (Cantidad > 0).
    - Bloquea piezas físicamente imposibles considerando el kerf:
      Ejemplo: con tubo de 6000 mm y kerf de 4 mm, una pieza de 5999 mm requiere
      5999 + 4 = 6003 mm (> 6000 mm), por lo que es imposible de cortar.
      Solo se admiten piezas con Longitud == l_comercial (sin corte) o Longitud + kerf <= l_comercial.
    """
    es_valido, msg = _validar_tabla_base(df_pedidos, "Pedidos", "ID_Pieza")
    if not es_valido:
        return False, msg

    df_ped_val = df_pedidos[df_pedidos["Cantidad"] > 0] if not df_pedidos.empty else df_pedidos

    if not df_ped_val.empty and df_ped_val["ID_Pieza"].duplicated().any():
        return False, "IDs de piezas duplicados."

    if not df_ped_val.empty:
        # Condición de viabilidad física: o encaja exacta sin corte (== l_comercial), o cabe con kerf (<= l_comercial)
        imposibles = df_ped_val[
            ~((df_ped_val["Longitud_mm"] == l_comercial) |
              (df_ped_val["Longitud_mm"] + kerf <= l_comercial))
        ]
        if not imposibles.empty:
            return False, f"Piezas imposibles de cortar considerando kerf: {imposibles['ID_Pieza'].tolist()}"

    return True, ""


def validar_datos_entrada(df_inventario, df_pedidos, l_comercial, kerf):
    """
    Validador integral que ejecuta secuencialmente validar_inventario y validar_pedidos.
    """
    inv_ok, msg_inv = validar_inventario(df_inventario, l_comercial)
    if not inv_ok:
        return False, msg_inv

    ped_ok, msg_ped = validar_pedidos(df_pedidos, l_comercial, kerf)
    if not ped_ok:
        return False, msg_ped

    return True, ""