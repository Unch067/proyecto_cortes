import unittest
import pandas as pd
from core.optimizador import optimizar_cortes
from components.validaciones import validar_datos_entrada


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
        self.assertEqual(res["balance"]["descarte"], 96)
        self.assertEqual(res["balance"]["nuevo_retal"], 288)
        self.assertEqual(res["balance"]["perdida"], 16)
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


if __name__ == "__main__":
    unittest.main()