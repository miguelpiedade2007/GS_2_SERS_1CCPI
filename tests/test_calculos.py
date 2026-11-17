import math
import unittest

from energia import alternativas as alt
from energia import calculos as calc
from scripts import gerar_analise


class TestCalculos(unittest.TestCase):
    def test_energia_banho_metodo_fisico(self):
        # 42 L × 4,186 kJ/kg·K × 18 K = 3164,6 kJ → /3600 /0,95 = 0,925 kWh
        self.assertAlmostEqual(calc.energia_banho_kwh(10, 4.2, 18), 0.9253, places=3)

    def test_metodos_fisico_e_potencia_sao_coerentes(self):
        fisico = calc.energia_banho_kwh(10, 4.2, 18)
        potencia = calc.energia_banho_por_potencia_kwh(5500, 10)
        self.assertLess(abs(fisico - potencia) / potencia, 0.05)

    def test_consumo_mensal_familia_referencia(self):
        self.assertAlmostEqual(calc.consumo_mensal_kwh(calc.Perfil()), 0.92533 * 120, places=1)

    def test_potencia_informada_usa_p_vezes_t(self):
        p = calc.Perfil(potencia_chuveiro_w=7500)
        self.assertEqual(p.metodo, "potencia")
        self.assertAlmostEqual(calc.consumo_mensal_kwh(p), 7.5 * 10 / 60 * 120, places=6)

    def test_tarifa_social_limita_economia_ao_excedente(self):
        p = calc.Perfil(tarifa_social=True, consumo_total_kwh_mes=100)
        self.assertEqual(calc.kwh_faturavel_evitado(50, p), 20)
        p2 = calc.Perfil(tarifa_social=True, consumo_total_kwh_mes=70)
        self.assertEqual(calc.kwh_faturavel_evitado(50, p2), 0)
        self.assertEqual(calc.kwh_faturavel_evitado(50, calc.Perfil()), 50)

    def test_tarifa_social_valor_cobrado(self):
        p = calc.Perfil(tarifa_social=True, consumo_total_kwh_mes=150)
        atual = alt.situacao_atual(p)
        self.assertAlmostEqual(atual["energia_cobrada_casa_rs_mes"], 70 * 0.90)
        self.assertAlmostEqual(atual["custo_faturado_chuveiro_rs_mes"], 70 * 0.90)
        self.assertAlmostEqual(atual["custo_rs_mes"], calc.consumo_mensal_kwh(p) * 0.90)

    def test_payback(self):
        self.assertAlmostEqual(calc.payback_anos(1000, 600, 100), 2.0)
        self.assertTrue(math.isinf(calc.payback_anos(1000, 50, 100)))
        self.assertEqual(calc.payback_anos(0, 100, 0), 0.0)


class TestAlternativas(unittest.TestCase):
    def setUp(self):
        self.perfil = calc.Perfil()
        self.base = calc.consumo_mensal_kwh(self.perfil)
        self.a, self.b, self.c, self.ab = alt.comparar(self.perfil)

    def test_banho_consciente_mesma_temperatura_reduz_30_por_cento(self):
        self.assertAlmostEqual(self.a.energia_evitada_kwh_mes / self.base, 0.30, places=6)
        self.assertAlmostEqual(self.a.agua_economizada_l_mes / calc.agua_litros_mes(self.perfil), 0.30, places=6)

    def test_modo_verao_fica_fora_da_comparacao(self):
        extra = alt.modo_verao_adicional(self.perfil, minutos=7)
        self.assertGreater(extra["kwh_mes"], 0)
        self.assertAlmostEqual(self.a.consumo_kwh_mes, calc.consumo_mensal_kwh(self.perfil, minutos=7))

    def test_conservacao_de_energia(self):
        for r in (self.a, self.b, self.ab):
            self.assertAlmostEqual(r.consumo_kwh_mes + r.energia_evitada_kwh_mes, self.base, places=6)
            self.assertEqual(r.energia_compensada_kwh_mes, 0)

    def test_fotovoltaica_compensa_mas_nao_reduz_consumo(self):
        self.assertAlmostEqual(self.c.consumo_kwh_mes, self.base)
        self.assertEqual(self.c.energia_evitada_kwh_mes, 0)
        self.assertGreaterEqual(self.c.energia_compensada_kwh_mes, self.base)
        self.assertFalse(self.c.reduz_pico_noturno)

    def test_fotovoltaica_limitada_pelo_consumo_da_casa(self):
        p = calc.Perfil(consumo_total_kwh_mes=120)  # 120 − 50 de disponibilidade = 70 kWh aproveitáveis
        c = alt.fotovoltaica(p)
        self.assertAlmostEqual(c.energia_compensada_kwh_mes, 70)
        self.assertTrue(any("abatem a conta" in l for l in c.limitacoes))

    def test_aquecedor_solar_redimensiona_com_a_familia(self):
        b4 = alt.aquecedor_solar(calc.Perfil(pessoas=4))
        b10 = alt.aquecedor_solar(calc.Perfil(pessoas=10))
        self.assertEqual(b4.detalhes["volume_l"], 200)
        self.assertGreater(b10.detalhes["volume_l"], b4.detalhes["volume_l"])
        self.assertGreater(b10.investimento_rs, b4.investimento_rs)
        self.assertGreater(b10.area_telhado_m2, b4.area_telhado_m2)
        self.assertAlmostEqual(b4.investimento_rs, 5000)

    def test_aquecedor_avisa_quando_excede_residencial(self):
        b = alt.aquecedor_solar(calc.Perfil(pessoas=20, minutos_por_banho=15))
        self.assertTrue(b.detalhes["excede_residencial"])
        self.assertIn("projeto específico", b.limitacoes[0])

    def test_combinacao_usa_aquecedor_menor_e_economiza_mais(self):
        self.assertLess(self.ab.detalhes["volume_l"], self.b.detalhes["volume_l"])
        self.assertGreater(self.ab.economia_kwh_mes, self.a.economia_kwh_mes)
        self.assertGreater(self.ab.economia_kwh_mes, self.b.economia_kwh_mes)

    def test_sensibilidade_ordenada(self):
        for codigo, v in alt.sensibilidade(self.perfil).items():
            self.assertLessEqual(v["otimista"], v["base"], codigo)
            self.assertLessEqual(v["base"], v["pessimista"], codigo)


class TestDocumentos(unittest.TestCase):
    def test_documentos_com_numeros_iguais_ao_codigo(self):
        self.assertEqual(gerar_analise.documentos_desatualizados(), [],
                         "Rode: python -m scripts.gerar_analise")


if __name__ == "__main__":
    unittest.main()
