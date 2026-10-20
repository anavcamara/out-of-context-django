from django.test import TestCase

from .services import levenshtein, normalizar, similaridade


class ServicesTests(TestCase):
    def test_normalizar_remove_acentos_e_pontuacao(self):
        self.assertEqual(normalizar("  Um BRUXO, Harry! "), "um bruxo harry")

    def test_levenshtein(self):
        self.assertEqual(levenshtein("gato", "gata"), 1)
        self.assertEqual(levenshtein("", "abc"), 3)

    def test_similaridade_de_textos_iguais(self):
        self.assertEqual(similaridade("o lar", "o lar"), 1)
        self.assertEqual(similaridade("", ""), 1)

    def test_erro_de_digitacao_ainda_acerta(self):
        self.assertGreaterEqual(similaridade("um problema", "um problena"), 0.85)

    def test_resposta_errada_nao_acerta(self):
        self.assertLess(similaridade("um problema", "o lar"), 0.85)

    def test_resposta_incompleta_nao_acerta(self):
        self.assertLess(similaridade("um", "um problema"), 0.85)
