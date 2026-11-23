import io
import unittest
from unittest.mock import MagicMock
import pandas as pd
from core.optimizador import optimizar_cortes
from components.validaciones import validar_datos_entrada, cargar_csv_datos
import components.graficos as graficos_mod
from components.graficos import (
    crear_gemelo_digital_3d,
    crear_grafico_balance_dona,
    crear_simulacion_paso_a_paso,
    generar_reporte_texto
)


class TestOptimizadorCortes(unittest.TestCase):

    def setUp(self):
        self.l_comercial = 6000
        self.kerf = 4
        self.umbral = 200

    def test_caso_comprobacion(self):
        df_ret = pd.DataFrame([{"ID_Retal": "R1", "Longitud_mm": 3000, "Cantidad": 1}])
        df_ped = pd.DataFrame([
            {"ID_Pieza": "P2900", "Longitud_mm": 2900, "Cantidad": 1},
            {"ID_Pieza": "P2000", "Longitud_mm": 2000, "Cantidad": 1},
            {"ID_Pieza": "P1900", "Longitud_mm": 1900, "Cantidad": 1},
            {"ID_Pieza": "P1800", "Longitud_mm": 1800, "Cantidad": 1}
        ])
        res = optimizar_cortes(df_ret, df_ped, self.l_comercial, self.kerf, self.umbral)
        self.assertEqual(res["tubos_comprados"], 1)
        self.assertEqual(res["balance"]["material_total_origen"], 9000)
        self.assertEqual(res["balance"]["incorporado"], 8600)
        self.assertEqual(res["balance"]["perdida"], 16)
        self.assertEqual(res["balance"]["descarte"], 96)
        self.assertEqual(res["balance"]["nuevo_retal"], 288)
        self.assertTrue(res["balance"]["cuadra_perfecto"])

    def test_caso_comprobacion_material_total(self):
        df_ret = pd.DataFrame([{"ID_Retal": "R1", "Longitud_mm": 3000, "Cantidad": 1}])
        df_ped = pd.DataFrame([
            {"ID_Pieza": "P2900", "Longitud_mm": 2900, "Cantidad": 1},
            {"ID_Pieza": "P2000", "Longitud_mm": 2000, "Cantidad": 1},
            {"ID_Pieza": "P1900", "Longitud_mm": 1900, "Cantidad": 1},
            {"ID_Pieza": "P1800", "Longitud_mm": 1800, "Cantidad": 1}
        ])
        res = optimizar_cortes(df_ret, df_ped, self.l_comercial, self.kerf, self.umbral)
        self.assertEqual(res["balance"]["material_total_origen"], 9000)

    def test_pieza_5999_mm_rechazada(self):
        df_ped = pd.DataFrame([{"ID_Pieza": "P1", "Longitud_mm": 5999, "Cantidad": 1}])
        valido, msg = validar_datos_entrada(pd.DataFrame(), df_ped, self.l_comercial, self.kerf)
        self.assertFalse(valido)
        self.assertIn("imposibles", msg.lower())

    def test_pieza_exacta_en_retal(self):
        df_ret = pd.DataFrame([{"ID_Retal": "R1", "Longitud_mm": 3000, "Cantidad": 1}])
        df_ped = pd.DataFrame([{"ID_Pieza": "P1", "Longitud_mm": 3000, "Cantidad": 1}])
        res = optimizar_cortes(df_ret, df_ped, self.l_comercial, self.kerf, self.umbral)
        self.assertEqual(res["balance"]["perdida"], 0)
        self.assertEqual(res["balance"]["descarte"], 0)
        self.assertEqual(res["tubos_comprados"], 0)

    def test_sobrante_exactamente_200(self):
        df_ped = pd.DataFrame([{"ID_Pieza": "P1", "Longitud_mm": 5796, "Cantidad": 1}])
        res = optimizar_cortes(pd.DataFrame(), df_ped, self.l_comercial, self.kerf, self.umbral)
        self.assertEqual(res["balance"]["nuevo_retal"], 200)
        self.assertEqual(res["balance"]["descarte"], 0)
        self.assertEqual(res["detalle_csv"][0]["Clasificacion"], "Retal Reutilizable")

    def test_sobrante_limite_inferior_199_es_descarte(self):
        df_ped = pd.DataFrame([{"ID_Pieza": "P1", "Longitud_mm": 5797, "Cantidad": 1}])
        res = optimizar_cortes(pd.DataFrame(), df_ped, self.l_comercial, self.kerf, self.umbral)
        self.assertEqual(res["balance"]["nuevo_retal"], 0)
        self.assertEqual(res["balance"]["descarte"], 199)
        self.assertEqual(res["detalle_csv"][0]["Clasificacion"], "Descarte")

    def test_sobrante_exactamente_cero(self):
        df_ped = pd.DataFrame([{"ID_Pieza": "P1", "Longitud_mm": 6000, "Cantidad": 1}])
        res = optimizar_cortes(pd.DataFrame(), df_ped, 6000, self.kerf, self.umbral)
        self.assertEqual(res["tubos_comprados"], 1)
        self.assertEqual(res["balance"]["nuevo_retal"], 0)
        self.assertEqual(res["balance"]["descarte"], 0)
        self.assertEqual(res["balance"]["perdida"], 0)

    def test_cantidad_cero_se_ignora(self):
        df_ped = pd.DataFrame([
            {"ID_Pieza": "P1", "Longitud_mm": 2000, "Cantidad": 0},
            {"ID_Pieza": "P2", "Longitud_mm": 2000, "Cantidad": 1}
        ])
        res = optimizar_cortes(pd.DataFrame(), df_ped, self.l_comercial, self.kerf, self.umbral)
        self.assertEqual(res["tubos_comprados"], 1)
        self.assertEqual(res["balance"]["incorporado"], 2000)

    def test_ids_duplicados_rechazados(self):
        df_ped = pd.DataFrame([
            {"ID_Pieza": "P1", "Longitud_mm": 2000, "Cantidad": 1},
            {"ID_Pieza": "P1", "Longitud_mm": 3000, "Cantidad": 1}
        ])
        valido, _ = validar_datos_entrada(pd.DataFrame(), df_ped, self.l_comercial, self.kerf)
        self.assertFalse(valido)

    def test_retal_mayor_tubo_rechazado(self):
        df_ret = pd.DataFrame([{"ID_Retal": "R1", "Longitud_mm": 7000, "Cantidad": 1}])
        df_ped = pd.DataFrame([{"ID_Pieza": "P1", "Longitud_mm": 1000, "Cantidad": 1}])
        valido, msg = validar_datos_entrada(df_ret, df_ped, self.l_comercial, self.kerf)
        self.assertFalse(valido)
        self.assertIn("retales mayores", msg.lower())

    def test_orden_original_vs_optimizado(self):
        df_ret = pd.DataFrame([{"ID_Retal": "R1", "Longitud_mm": 3000, "Cantidad": 1}])
        df_ped = pd.DataFrame([
            {"ID_Pieza": "P1800", "Longitud_mm": 1800, "Cantidad": 1},
            {"ID_Pieza": "P1900", "Longitud_mm": 1900, "Cantidad": 1},
            {"ID_Pieza": "P2000", "Longitud_mm": 2000, "Cantidad": 1},
            {"ID_Pieza": "P2900", "Longitud_mm": 2900, "Cantidad": 1}
        ])
        res_opt = optimizar_cortes(df_ret, df_ped, self.l_comercial, self.kerf, self.umbral, False)
        res_orig = optimizar_cortes(df_ret, df_ped, self.l_comercial, self.kerf, self.umbral, True)
        self.assertEqual(res_opt["tubos_comprados"], 1)
        self.assertEqual(res_orig["tubos_comprados"], 2)

    def test_pieza_imposible_llega_al_optimizador_no_crashea(self):
        df_ped = pd.DataFrame([{"ID_Pieza": "P1", "Longitud_mm": 8000, "Cantidad": 1}])
        res = optimizar_cortes(pd.DataFrame(), df_ped, self.l_comercial, self.kerf, self.umbral)
        self.assertEqual(len(res["pendientes"]), 1)
        self.assertEqual(res["tubos_comprados"], 0)

    def test_cantidades_anomalas_ignoradas(self):
        df_ped = pd.DataFrame([
            {"ID_Pieza": "P1", "Longitud_mm": 2000, "Cantidad": -5},
            {"ID_Pieza": "P2", "Longitud_mm": 2000, "Cantidad": 0.5}
        ])
        res = optimizar_cortes(pd.DataFrame(), df_ped, self.l_comercial, self.kerf, self.umbral)
        self.assertEqual(res["balance"]["incorporado"], 0)

    def test_desempate_reproducible(self):
        df_ret = pd.DataFrame([
            {"ID_Retal": "R2", "Longitud_mm": 3000, "Cantidad": 1},
            {"ID_Retal": "R1", "Longitud_mm": 3000, "Cantidad": 1}
        ])
        df_ped = pd.DataFrame([{"ID_Pieza": "P1", "Longitud_mm": 2000, "Cantidad": 1}])
        res = optimizar_cortes(df_ret, df_ped, self.l_comercial, self.kerf, self.umbral)
        origenes_usados = [corte["Origen_ID"] for corte in res["detalle_csv"]]
        self.assertIn("Retal_R1_1", origenes_usados)
        self.assertNotIn("Retal_R2_1", origenes_usados)

    def test_validacion_cantidad_negativa_decimal(self):
        df_ret = pd.DataFrame()

        df_ped_neg = pd.DataFrame([{"ID_Pieza": "P1", "Longitud_mm": 2000, "Cantidad": -1}])
        valido_neg, msg_neg = validar_datos_entrada(df_ret, df_ped_neg, self.l_comercial, self.kerf)
        self.assertFalse(valido_neg)
        self.assertIn("negativas", msg_neg.lower())

        df_ped_dec = pd.DataFrame([{"ID_Pieza": "P2", "Longitud_mm": 2000, "Cantidad": 1.5}])
        valido_dec, msg_dec = validar_datos_entrada(df_ret, df_ped_dec, self.l_comercial, self.kerf)
        self.assertFalse(valido_dec)
        self.assertIn("decimales", msg_dec.lower())

    def test_conflicto_desempate_menor_longitud_inicial(self):
        # A_Grande (4500 mm) tras cortar P_Previa (2496 mm + 4 kerf) queda con saldo 2000 mm.
        # Z_Chico (2000 mm) no puede alojar P_Previa (2496 mm), por lo que conserva su saldo inicial de 2000 mm.
        # Para P_Objetivo (1500 mm), ambos dejan remanente 496 mm; debe elegirse Z_Chico por menor Longitud_Inicial (2000 < 4500).
        df_ret = pd.DataFrame([
            {"ID_Retal": "A_Grande", "Longitud_mm": 4500, "Cantidad": 1},
            {"ID_Retal": "Z_Chico", "Longitud_mm": 2000, "Cantidad": 1}
        ])
        df_ped = pd.DataFrame([
            {"ID_Pieza": "P_Previa", "Longitud_mm": 2496, "Cantidad": 1},
            {"ID_Pieza": "P_Objetivo", "Longitud_mm": 1500, "Cantidad": 1}
        ])
        res = optimizar_cortes(df_ret, df_ped, self.l_comercial, self.kerf, self.umbral)
        detalle_por_id = {fila["Origen_ID"]: fila for fila in res["detalle_csv"]}
        self.assertIn("P_Objetivo(1500)", detalle_por_id["Retal_Z_Chico_1"]["Piezas_Asignadas"])

    def test_pieza_imposible_6500_mm(self):
        df_ped = pd.DataFrame([{"ID_Pieza": "P6500", "Longitud_mm": 6500, "Cantidad": 1}])
        valido, msg = validar_datos_entrada(pd.DataFrame(), df_ped, self.l_comercial, self.kerf)
        self.assertFalse(valido)
        self.assertIn("P6500", msg)

        res = optimizar_cortes(pd.DataFrame(), df_ped, self.l_comercial, self.kerf, self.umbral)
        self.assertEqual(res["tubos_comprados"], 0)
        self.assertEqual(len(res["pendientes"]), 1)
        self.assertEqual(res["pendientes"][0]["L"], 6500)
        self.assertTrue(res["balance"]["cuadra_perfecto"])

    def test_cargar_csv_delimitador_coma_y_punto_y_coma(self):
        csv_coma = "ID_Retal,Longitud_mm,Cantidad\nR1,3000,1\n"
        df_inv, err_inv = cargar_csv_datos(io.StringIO(csv_coma), tipo="inventario")
        self.assertEqual(err_inv, "")
        self.assertEqual(int(df_inv.iloc[0]["Longitud_mm"]), 3000)
        self.assertEqual(int(df_inv.iloc[0]["Cantidad"]), 1)

        csv_punto_coma = (
            "ID_Pieza;Longitud_mm;Cantidad\n"
            "P2900;2900;1\n"
            "P2000;2000;1\n"
            "P1900;1900;1\n"
            "P1800;1800;1\n"
        )
        df_ped, err_ped = cargar_csv_datos(io.StringIO(csv_punto_coma), tipo="pedidos")
        self.assertEqual(err_ped, "")
        self.assertEqual(len(df_ped), 4)

        # El resultado de CSV debe cumplir exactamente el caso oficial
        res = optimizar_cortes(df_inv, df_ped, self.l_comercial, self.kerf, self.umbral)
        self.assertEqual(res["tubos_comprados"], 1)
        self.assertEqual(res["balance"]["incorporado"], 8600)
        self.assertEqual(res["balance"]["material_total_origen"], 9000)

    def test_cargar_csv_decimales_coma_y_punto_a_enteros(self):
        csv_decimales = (
            "ID_Pieza;Longitud_mm;Cantidad\n"
            "P1;2900,0;1,0\n"
            "P2;1999.6;2.0\n"
        )
        df_ped, err = cargar_csv_datos(io.StringIO(csv_decimales), tipo="pedidos")
        self.assertEqual(err, "")
        self.assertEqual(list(df_ped["Longitud_mm"]), [2900, 2000])
        self.assertEqual(list(df_ped["Cantidad"]), [1, 2])
        self.assertTrue(pd.api.types.is_integer_dtype(df_ped["Longitud_mm"]))
        self.assertTrue(pd.api.types.is_integer_dtype(df_ped["Cantidad"]))

    def test_cargar_csv_errores_claros_espanol(self):
        csv_col_faltante = "ID_Pieza,Longitud_mm\nP1,2000\n"
        df_err1, msg1 = cargar_csv_datos(io.StringIO(csv_col_faltante), tipo="pedidos")
        self.assertIsNone(df_err1)
        self.assertIn("faltan las columnas", msg1.lower())

        csv_cant_decimal = "ID_Pieza;Longitud_mm;Cantidad\nP1;2000;1,5\n"
        df_err2, msg2 = cargar_csv_datos(io.StringIO(csv_cant_decimal), tipo="pedidos")
        self.assertIsNone(df_err2)
        self.assertIn("decimales", msg2.lower())

    def test_validacion_celdas_vacias_e_id_vacio(self):
        df_nan = pd.DataFrame([{"ID_Pieza": "P1", "Longitud_mm": None, "Cantidad": 1}])
        valido_nan, msg_nan = validar_datos_entrada(pd.DataFrame(), df_nan, self.l_comercial, self.kerf)
        self.assertFalse(valido_nan)
        self.assertIn("vacías", msg_nan.lower())

        df_id_vacio = pd.DataFrame([{"ID_Pieza": "   ", "Longitud_mm": 2000, "Cantidad": 1}])
        valido_id, msg_id = validar_datos_entrada(pd.DataFrame(), df_id_vacio, self.l_comercial, self.kerf)
        self.assertFalse(valido_id)
        self.assertIn("vacío", msg_id.lower())

    def test_generar_reporte_texto_con_pendientes_y_parentesis(self):
        df_ped = pd.DataFrame([
            {"ID_Pieza": "P_Valida(A)", "Longitud_mm": 2000, "Cantidad": 1},
            {"ID_Pieza": "P_Imposible", "Longitud_mm": 6500, "Cantidad": 1}
        ])
        res = optimizar_cortes(pd.DataFrame(), df_ped, self.l_comercial, self.kerf, self.umbral)
        reporte = generar_reporte_texto(res, res, self.l_comercial, self.kerf, self.umbral)
        self.assertIn("Pieza P_Imposible: 6500 mm", reporte)
        self.assertNotIn("Pieza None", reporte)

        # Verificar que el parser de paréntesis en gráficos no lance ValueError con 'P_Valida(A)(2000)'
        go_original = graficos_mod.go
        if go_original is None:
            graficos_mod.go = MagicMock()
        try:
            fig_3d = crear_gemelo_digital_3d(res["detalle_csv"], kerf_nominal=self.kerf)
            fig_sim = crear_simulacion_paso_a_paso(res["detalle_csv"][0], 2000, kerf_nominal=self.kerf)
            self.assertIsNotNone(fig_3d)
            self.assertIsNotNone(fig_sim)
        finally:
            graficos_mod.go = go_original

    def test_archivos_datos_ejemplo(self):
        with open("datos_ejemplo/inventario_valido.csv", "rb") as f:
            df_inv, err_inv = cargar_csv_datos(f, tipo="inventario")
        self.assertEqual(err_inv, "")

        with open("datos_ejemplo/pedidos_validos.csv", "rb") as f:
            df_ped, err_ped = cargar_csv_datos(f, tipo="pedidos")
        self.assertEqual(err_ped, "")

        res_coma = optimizar_cortes(df_inv, df_ped, self.l_comercial, self.kerf, self.umbral)
        self.assertEqual(res_coma["tubos_comprados"], 1)
        self.assertEqual(res_coma["balance"]["incorporado"], 8600)
        self.assertEqual(res_coma["balance"]["material_total_origen"], 9000)

        with open("datos_ejemplo/datos_punto_y_coma.csv", "rb") as f:
            df_pyc, err_pyc = cargar_csv_datos(f, tipo="pedidos")
        self.assertEqual(err_pyc, "")
        res_pyc = optimizar_cortes(df_inv, df_pyc, self.l_comercial, self.kerf, self.umbral)
        self.assertEqual(res_pyc["balance"], res_coma["balance"])

        with open("datos_ejemplo/pedidos_con_errores.csv", "rb") as f:
            df_err, err_msg = cargar_csv_datos(f, tipo="pedidos")
        self.assertIsNone(df_err)
        self.assertIn("decimales", err_msg.lower())

    def test_cargar_csv_inventario_autogenera_ids_secuenciales(self):
        csv_sin_id = "Longitud_mm,Cantidad\n3000,1\n1500,2\n"
        df_inv1, err1 = cargar_csv_datos(io.StringIO(csv_sin_id), tipo="inventario")
        self.assertEqual(err1, "")
        self.assertEqual(list(df_inv1["ID_Retal"]), ["R1", "R2"])
        self.assertEqual(list(df_inv1["Longitud_mm"]), [3000, 1500])

        csv_con_id_viejo = "ID_Retal;Longitud_mm;Cantidad\nRET_X;2500;1\nRET_Y;1200;3\n"
        df_inv2, err2 = cargar_csv_datos(io.StringIO(csv_con_id_viejo), tipo="inventario")
        self.assertEqual(err2, "")
        self.assertEqual(list(df_inv2["ID_Retal"]), ["R1", "R2"])
        self.assertEqual(list(df_inv2["Cantidad"]), [1, 3])

    def test_graficos_cilindros_huecos_dona_y_simulador(self):
        df_ret = pd.DataFrame([{"ID_Retal": "R1", "Longitud_mm": 3000, "Cantidad": 1}])
        df_ped = pd.DataFrame([
            {"ID_Pieza": "P2900", "Longitud_mm": 2900, "Cantidad": 1},
            {"ID_Pieza": "P2000", "Longitud_mm": 2000, "Cantidad": 1},
            {"ID_Pieza": "P1900", "Longitud_mm": 1900, "Cantidad": 1},
            {"ID_Pieza": "P1800", "Longitud_mm": 1800, "Cantidad": 1}
        ])
        res = optimizar_cortes(df_ret, df_ped, self.l_comercial, self.kerf, self.umbral)

        # 1. Reporte incluye diámetro y pulgadas
        reporte = generar_reporte_texto(res, res, self.l_comercial, self.kerf, self.umbral, diametro_mm=200)
        self.assertIn("200 mm", reporte)
        self.assertIn("7.87 in", reporte)

        # 2. Gemelo 3D construye cilindros huecos (96 vértices y 192 triángulos con 24 segmentos)
        fig_3d = crear_gemelo_digital_3d(res["detalle_csv"], kerf_nominal=self.kerf, diametro_mm=200)
        self.assertGreater(len(fig_3d.data), 0)
        primera_malla = fig_3d.data[0]
        self.assertEqual(len(primera_malla.x), 96)
        self.assertEqual(len(primera_malla.i), 192)
        self.assertAlmostEqual(max(primera_malla.z), 100.0, places=1)

        # 3. Dona oculta porcentajes menores al 2% (Pérdida=16/9000=0.18%, Descarte=96/9000=1.07%)
        fig_dona = crear_grafico_balance_dona(res["balance"])
        pie_trace = fig_dona.data[0]
        texto_por_etiqueta = dict(zip(pie_trace.labels, pie_trace.text))
        self.assertEqual(texto_por_etiqueta["Pérdida por Corte"], "")
        self.assertEqual(texto_por_etiqueta["Descarte Inútil"], "")
        self.assertNotEqual(texto_por_etiqueta["Material Incorporado"], "")
        self.assertNotEqual(texto_por_etiqueta["Retal Reutilizable"], "")

        # 4. Simulador muestra solo mm cuando sobrante < 300 mm (288 mm en Tubo_Nuevo_1)
        fila_tubo = next(f for f in res["detalle_csv"] if f["Origen_ID"] == "Tubo_Nuevo_1")
        fig_sim = crear_simulacion_paso_a_paso(fila_tubo, fila_tubo["Longitud_Inicial"], kerf_nominal=self.kerf)
        traza_sobrante = next(t for t in fig_sim.data if t.name == "Sobrante")
        self.assertEqual(traza_sobrante.text, "288 mm")


if __name__ == "__main__":
    unittest.main()