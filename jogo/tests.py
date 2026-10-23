import json
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from .diario import desafio_de_hoje, ranking_sequencias, sequencia_diaria
from .models import Cena, DesafioDiario, Obra, Partida
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
        
    def test_dicas_em_ordem_e_com_limite(self):
        pid = self.nova_partida()
        url = f"/api/partida/{pid}/dica/"

        primeira = self.post(url, {}).json()
        self.assertEqual(primeira["titulo"], "ANO")
        self.assertEqual(primeira["restantes"], 2)

        self.post(url, {})
        self.post(url, {})
        self.assertEqual(self.post(url, {}).status_code, 400)

    def test_busca_de_obras_ignora_acentos(self):
        Obra.objects.create(titulo="Amélie", tipo="filme", ano=2001, genero="Romance")
        dados = self.client.get("/api/obras/", {"q": "amelie"}).json()
        self.assertEqual(dados["obras"], ["Amélie"])
        
    def test_partida_fica_ligada_ao_usuario_logado(self):
        usuario = User.objects.create_user("ana", password="senha-forte-123")
        self.client.login(username="ana", password="senha-forte-123")
        pid = self.nova_partida()
        self.assertEqual(Partida.objects.get(id=pid).usuario, usuario)

    def test_partida_anonima_continua_funcionando(self):
        pid = self.nova_partida()
        self.assertIsNone(Partida.objects.get(id=pid).usuario)
        
class ContasTests(TestCase):
    def test_cadastro_cria_usuario_e_faz_login(self):
        resposta = self.client.post("/contas/cadastro/", {
            "username": "bia",
            "password1": "senha-forte-123",
            "password2": "senha-forte-123",
        })
        self.assertEqual(resposta.status_code, 302)
        self.assertTrue(User.objects.filter(username="bia").exists())
        
class PerfilTests(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user("ana", password="senha-forte-123")
        obra = Obra.objects.create(
            titulo="Apollo 13", tipo="filme", ano=1995, genero="Drama"
        )
        self.cena = Cena.objects.create(
            obra=obra,
            personagem="Jim Lovell",
            contexto="Falha na nave.",
            dialogo="Houston, temos",
            resposta="um problema.",
        )

    def criar(self, **campos):
        return Partida.objects.create(
            cena=self.cena, usuario=self.usuario, modo="complete", **campos
        )

    def entrar(self):
        self.client.login(username="ana", password="senha-forte-123")

    def test_perfil_exige_login(self):
        resposta = self.client.get("/perfil/")
        self.assertEqual(resposta.status_code, 302)
        self.assertIn("/contas/login/", resposta.url)

    def test_estatisticas_ignoram_partidas_nao_terminadas(self):
        self.criar(terminou=True, acertou=True, tentativas_usadas=1)
        self.criar(terminou=True, acertou=False, tentativas_usadas=3)
        self.criar(terminou=False, tentativas_usadas=1)
        self.entrar()

        resumo = self.client.get("/perfil/").context["resumo"]
        self.assertEqual(resumo["total"], 2)
        self.assertEqual(resumo["acertos"], 1)
        self.assertEqual(resumo["taxa"], 50)

    def test_sequencia_conta_os_acertos_mais_recentes(self):
        self.criar(terminou=True, acertou=False, tentativas_usadas=3)
        self.criar(terminou=True, acertou=True, tentativas_usadas=1)
        self.criar(terminou=True, acertou=True, tentativas_usadas=2)
        self.entrar()

        resposta = self.client.get("/perfil/")
        self.assertEqual(resposta.context["sequencia"], 2)

class DesafioDiarioTests(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user("ana", password="senha-forte-123")
        obra = Obra.objects.create(
            titulo="Apollo 13", tipo="filme", ano=1995, genero="Drama"
        )
        self.cena = Cena.objects.create(
            obra=obra,
            personagem="Jim Lovell",
            contexto="Falha na nave.",
            dialogo="Houston, temos",
            resposta="um problema.",
        )
        Cena.objects.create(
            obra=obra,
            personagem="Fred Haise",
            contexto="Outra cena.",
            dialogo="Outra fala",
            resposta="uma continuação.",
        )

    def entrar(self):
        self.client.login(username="ana", password="senha-forte-123")

    def abrir_desafio(self):
        return self.client.post("/api/desafio/hoje/", content_type="application/json")

    def test_desafio_exige_login(self):
        self.assertEqual(self.abrir_desafio().status_code, 401)

    def test_mesmo_desafio_o_dia_todo(self):
        primeiro = desafio_de_hoje()
        segundo = desafio_de_hoje()
        self.assertEqual(primeiro.id, segundo.id)
        self.assertEqual(DesafioDiario.objects.count(), 1)

    def test_reabrir_continua_a_mesma_partida(self):
        self.entrar()
        primeira = self.abrir_desafio().json()["partida_id"]
        segunda = self.abrir_desafio().json()["partida_id"]
        self.assertEqual(primeira, segunda)

    def test_depois_de_terminar_devolve_o_resultado(self):
        self.entrar()
        pid = self.abrir_desafio().json()["partida_id"]
        certa = desafio_de_hoje().cena.resposta

        self.client.post(
            f"/api/partida/{pid}/tentativa/",
            json.dumps({"resposta": certa}),
            content_type="application/json",
        )

        de_novo = self.abrir_desafio().json()
        self.assertTrue(de_novo["ja_jogou"])
        self.assertTrue(de_novo["acertou"])

    def test_nao_mexe_na_partida_de_outro_usuario(self):
        self.entrar()
        pid = self.abrir_desafio().json()["partida_id"]

        self.client.logout()
        User.objects.create_user("bia", password="senha-forte-123")
        self.client.login(username="bia", password="senha-forte-123")

        resposta = self.client.post(
            f"/api/partida/{pid}/tentativa/",
            json.dumps({"resposta": "qualquer coisa"}),
            content_type="application/json",
        )
        self.assertEqual(resposta.status_code, 403)

    def test_sequencia_diaria(self):
        hoje = timezone.localdate()

        for dias in (0, 1, 2, 4):
            desafio = DesafioDiario.objects.create(
                data=hoje - timedelta(days=dias), cena=self.cena
            )
            Partida.objects.create(
                cena=self.cena,
                usuario=self.usuario,
                modo="complete",
                desafio=desafio,
                terminou=True,
                acertou=True,
            )

        self.assertEqual(sequencia_diaria(self.usuario, hoje), 3)

class HomeTests(TestCase):
    def test_home_anonima_funciona(self):
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_home_logada_traz_dados_do_desafio(self):
        User.objects.create_user("ana", password="senha-forte-123")
        self.client.login(username="ana", password="senha-forte-123")

        resposta = self.client.get("/")
        self.assertEqual(resposta.context["sequencia_diaria"], 0)
        self.assertFalse(resposta.context["jogou_hoje"])
        
class RankingTests(TestCase):
    def setUp(self):
        self.ana = User.objects.create_user("ana", password="senha-forte-123")
        self.bia = User.objects.create_user("bia", password="senha-forte-123")
        self.carla = User.objects.create_user("carla", password="senha-forte-123")

        obra = Obra.objects.create(
            titulo="Apollo 13", tipo="filme", ano=1995, genero="Drama"
        )
        self.cena = Cena.objects.create(
            obra=obra,
            personagem="Jim Lovell",
            contexto="Falha na nave.",
            dialogo="Houston, temos",
            resposta="um problema.",
        )

    def partida(self, usuario, acertou, desafio=None):
        return Partida.objects.create(
            cena=self.cena,
            usuario=usuario,
            modo="complete",
            desafio=desafio,
            terminou=True,
            acertou=acertou,
        )

    def test_ranking_geral_ordena_por_acertos(self):
        self.partida(self.ana, True)
        self.partida(self.ana, True)
        self.partida(self.bia, True)
        self.partida(self.bia, False)

        resposta = self.client.get("/ranking/")
        nomes = [jogador.username for jogador in resposta.context["geral"]]
        self.assertEqual(nomes, ["ana", "bia"])

    def test_quem_so_errou_nao_aparece(self):
        self.partida(self.carla, False)

        resposta = self.client.get("/ranking/")
        self.assertEqual(list(resposta.context["geral"]), [])

    def test_ranking_de_sequencias(self):
        hoje = timezone.localdate()
        desafio_hoje = DesafioDiario.objects.create(data=hoje, cena=self.cena)
        desafio_ontem = DesafioDiario.objects.create(
            data=hoje - timedelta(days=1), cena=self.cena
        )

        self.partida(self.ana, True, desafio_hoje)
        self.partida(self.ana, True, desafio_ontem)
        self.partida(self.bia, True, desafio_hoje)

        self.assertEqual(
            ranking_sequencias(hoje), [("ana", 2), ("bia", 1)]
        )