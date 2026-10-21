import json

from django.test import TestCase

from .models import Cena, Obra
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

class PartidaApiTests(TestCase):
    def setUp(self):
        obra = Obra.objects.create(
            titulo="Apollo 13", tipo="filme", ano=1995, genero="Drama"
        )
        Cena.objects.create(
            obra=obra,
            personagem="Jim Lovell",
            contexto="Falha na nave.",
            dialogo="Houston, temos",
            resposta="um problema.",
        )

    def post(self, url, dados):
        return self.client.post(
            url, json.dumps(dados), content_type="application/json"
        )

    def nova_partida(self, modo="complete"):
        return self.post("/api/partida/nova/", {"modo": modo}).json()["partida_id"]

    def test_nova_partida_nao_revela_a_resposta(self):
        resposta = self.post("/api/partida/nova/", {"modo": "complete"})
        self.assertEqual(resposta.status_code, 200)
        self.assertNotIn("problema", resposta.content.decode())

    def test_modo_invalido(self):
        resposta = self.post("/api/partida/nova/", {"modo": "banana"})
        self.assertEqual(resposta.status_code, 400)

    def test_acerto_encerra_e_revela(self):
        pid = self.nova_partida()
        dados = self.post(f"/api/partida/{pid}/tentativa/", {"resposta": "Um problema"}).json()
        self.assertTrue(dados["acertou"])
        self.assertTrue(dados["terminou"])
        self.assertEqual(dados["revelacao"]["obra"], "Apollo 13")

    def test_tres_erros_encerram_a_partida(self):
        pid = self.nova_partida()
        url = f"/api/partida/{pid}/tentativa/"

        for restantes in (2, 1):
            dados = self.post(url, {"resposta": "banana"}).json()
            self.assertFalse(dados["terminou"])
            self.assertEqual(dados["tentativas_restantes"], restantes)

        dados = self.post(url, {"resposta": "banana"}).json()
        self.assertTrue(dados["terminou"])
        self.assertFalse(dados["acertou"])
        self.assertIn("revelacao", dados)

    def test_nao_aceita_tentativa_depois_do_fim(self):
        pid = self.nova_partida()
        url = f"/api/partida/{pid}/tentativa/"
        self.post(url, {"resposta": "um problema"})
        self.assertEqual(self.post(url, {"resposta": "um problema"}).status_code, 400)