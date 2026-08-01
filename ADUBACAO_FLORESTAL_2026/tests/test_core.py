"""Testes unitários — NPK e normalização de talhão."""
import unittest

from etl import normalizar_talhao, talhao_base
from npk import calcular_nutrientes, parse_formula


class TestNPK(unittest.TestCase):
    def test_parse_sulfammo(self):
        f = parse_formula("Sulfammo 10-05-18")
        self.assertEqual((f.n, f.p2o5, f.k2o), (10.0, 5.0, 18.0))

    def test_parse_kcl(self):
        f = parse_formula("kcl 00-00-58")
        self.assertEqual(f.k2o, 58.0)

    def test_calculo(self):
        r = calcular_nutrientes("14-14-10", 200, 10)
        self.assertAlmostEqual(r.n_kg_ha, 28.0)
        self.assertAlmostEqual(r.n_total_kg, 280.0)
        self.assertAlmostEqual(r.adubo_total_kg, 2000.0)


class TestTalhao(unittest.TestCase):
    def test_normalizar(self):
        self.assertEqual(normalizar_talhao(277), "277")
        self.assertEqual(normalizar_talhao("172A"), "172A")
        self.assertEqual(talhao_base("172A"), "172")


if __name__ == "__main__":
    unittest.main()
