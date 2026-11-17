import csv
import tempfile
import unittest
from pathlib import Path

from energia import Sessao, responder
from energia.feedback import registrar


class TestAssistente(unittest.TestCase):
    def perguntar(self, texto, sessao=None):
        return responder(texto, sessao or Sessao())

    def test_intencoes_principais(self):
        casos = {
            "Quanto gasta meu chuveiro?": "consumo",
            "Quais as alternativas?": "comparar",
            "Dicas para economizar": "banho_consciente",
            "Aquecedor solar vale a pena?": "aquecedor_solar",
            "E a placa solar?": "fotovoltaica",
            "O que é tarifa social?": "tarifa_social",
            "Qual o impacto ambiental?": "ambiente",
            "Como você calculou?": "calculo",
            "Quais as fontes?": "fontes",
            "Isso é garantido?": "limitacoes",
            "ajuda": "ajuda",
        }
        for pergunta, esperado in casos.items():
            with self.subTest(pergunta=pergunta):
                self.assertEqual(self.perguntar(pergunta).intencao, esperado)

    def test_respostas_tecnicas_trazem_fontes_e_limitacoes(self):
        for pergunta in ("Quanto gasta meu chuveiro?", "Quais as alternativas?", "Aquecedor solar vale a pena?",
                         "E a placa solar?", "Dicas para economizar"):
            with self.subTest(pergunta=pergunta):
                r = self.perguntar(pergunta)
                self.assertTrue(r.referencias)
                self.assertTrue(r.limitacoes)

    def test_extrai_perfil_da_mensagem(self):
        s = Sessao()
        r = self.perguntar("Somos 5 pessoas, banho de 12 minutos, chuveiro de 7500 W, tarifa 0,95", s)
        self.assertEqual(s.perfil.pessoas, 5)
        self.assertEqual(s.perfil.minutos_por_banho, 12)
        self.assertEqual(s.perfil.potencia_chuveiro_w, 7500)
        self.assertAlmostEqual(s.perfil.tarifa_kwh, 0.95)
        self.assertIn("Anotei", r.texto)
        # 7,5 kW × 0,2 h × 150 banhos = 225 kWh
        self.assertAlmostEqual(r.dados["situacao_atual"]["consumo_kwh_mes"], 225, places=6)

    def test_explicacao_do_calculo_usa_os_mesmos_dados(self):
        s = Sessao()
        r1 = self.perguntar("5 pessoas, banho de 12 minutos, chuveiro de 7500 W", s)
        r2 = self.perguntar("Como você calculou?", s)
        self.assertEqual(r2.dados["metodo"], "potencia")
        self.assertAlmostEqual(r2.dados["consumo_kwh_mes"], r1.dados["situacao_atual"]["consumo_kwh_mes"])
        self.assertIn("7.500 W", r2.texto)
        self.assertIn("225,0 kWh", r2.texto)
        self.assertNotIn("5.500", r2.texto)

    def test_entradas_invalidas_pedem_novo_valor(self):
        for frase in ("banho de 0 minutos", "0 banhos por dia", "0 pessoas", "chuveiro de 800 W", "tarifa 0"):
            with self.subTest(frase=frase):
                s = Sessao()
                r = self.perguntar(frase, s)
                self.assertEqual(r.intencao, "valor_invalido")
                self.assertEqual(s.perfil, Sessao().perfil)

    def test_tarifa_social_mostra_valor_cobrado(self):
        r = self.perguntar("temos tarifa social e consumo de 150 kWh")
        self.assertIn("R$ 63,00", r.texto)
        self.assertIn("equivaleria", r.texto)

    def test_potencia_em_kw(self):
        s = Sessao()
        self.perguntar("meu chuveiro tem 5,5 kW", s)
        self.assertEqual(s.perfil.potencia_chuveiro_w, 5500)

    def test_tarifa_social_com_consumo(self):
        s = Sessao()
        r = self.perguntar("temos tarifa social e consumo de 90 kWh", s)
        self.assertTrue(s.perfil.tarifa_social)
        self.assertEqual(s.perfil.consumo_total_kwh_mes, 90)
        r2 = self.perguntar("dicas para economizar", s)
        self.assertAlmostEqual(r2.dados["alternativa"]["economia_rs_mes"], 10 * s.perfil.tarifa_kwh, places=6)
        self.assertTrue(any("Tarifa Social" in l for l in r2.limitacoes))

    def test_perfil_permanece_na_sessao(self):
        s = Sessao()
        self.perguntar("3 pessoas", s)
        r = self.perguntar("quais as alternativas?", s)
        self.assertEqual(s.perfil.pessoas, 3)
        self.assertIn("3 pessoa", self.perguntar("quanto gasta?", s).texto)
        self.assertEqual(len(r.dados["alternativas"]), 4)

    def test_mensagem_desconhecida(self):
        self.assertEqual(self.perguntar("qual a capital da França?").intencao, "nao_entendi")


class TestFeedback(unittest.TestCase):
    def test_registro_remove_dados_pessoais(self):
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "fb.csv"
            registrar("P1", "meu cpf é 123.456.789-00", "consumo", True, False,
                      "me liga no (11) 98765-4321 ou joao@email.com", arquivo=arquivo)
            with open(arquivo, encoding="utf-8") as f:
                linha = next(csv.DictReader(f))
            self.assertNotIn("123.456", linha["pergunta"])
            self.assertNotIn("98765", linha["comentario"])
            self.assertNotIn("@", linha["comentario"])
            self.assertEqual(linha["entendeu"], "sim")
            self.assertEqual(linha["util"], "nao")


if __name__ == "__main__":
    unittest.main()
