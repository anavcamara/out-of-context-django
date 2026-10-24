import json

from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import PermissionDenied
from django.db.models import Avg, Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .diario import desafio_de_hoje, ranking_sequencias, sequencia_diaria
from .models import Cena, Obra, Partida
from .services import (
    MAX_RESPOSTA,
    MAX_TENTATIVAS,
    normalizar,
    resposta_correta,
)

# Quantas partidas anônimas uma mesma sessão consegue continuar usando.
MAX_PARTIDAS_NA_SESSAO = 50


# ==============================
# FUNÇÕES DE APOIO
# ==============================

class RequisicaoInvalida(Exception):
    """Corpo da requisição ausente, malformado ou com tipos inesperados."""


def _erro(mensagem, status=400):
    return JsonResponse({"erro": mensagem}, status=status)


def _ler_json(request):
    try:
        dados = json.loads(request.body or b"{}")
    except (ValueError, UnicodeDecodeError):
        raise RequisicaoInvalida("Requisição inválida.")

    if not isinstance(dados, dict):
        raise RequisicaoInvalida("Requisição inválida.")

    return dados


def _registrar_partida_anonima(request, partida_id):
    # Partidas sem dono só podem ser usadas pela sessão que as criou.
    ids = request.session.get("partidas_anonimas", [])
    ids.append(partida_id)
    request.session["partidas_anonimas"] = ids[-MAX_PARTIDAS_NA_SESSAO:]


def _buscar_partida(request, partida_id):
    partida = get_object_or_404(
        Partida.objects.select_related("cena__obra"), id=partida_id
    )

    if partida.usuario_id is not None:
        if partida.usuario_id != request.user.id:
            raise PermissionDenied
    elif partida.id not in request.session.get("partidas_anonimas", []):
        raise PermissionDenied

    return partida


def _revelacao(cena):
    return {
        "resposta": cena.resposta,
        "obra": cena.obra.titulo,
        "ano": cena.obra.ano,
        "genero": cena.obra.genero,
        "personagem": cena.personagem,
    }


def _dicas(cena):
    return [
        ("ANO", cena.obra.ano),
        ("GÊNERO", cena.obra.genero),
        ("PERSONAGEM", cena.personagem),
    ]


# ==============================
# PÁGINAS
# ==============================

def home(request):
    contexto = {}

    if request.user.is_authenticated:
        hoje = timezone.localdate()
        contexto["sequencia_diaria"] = sequencia_diaria(request.user, hoje)
        contexto["jogou_hoje"] = Partida.objects.filter(
            usuario=request.user, desafio__data=hoje, terminou=True
        ).exists()

    return render(request, "jogo/index.html", contexto)


def cadastro(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            login(request, usuario)
            return redirect("home")
    else:
        form = UserCreationForm()

    return render(request, "registration/cadastro.html", {"form": form})


@login_required
def perfil(request):
    finalizadas = request.user.partidas.filter(terminou=True)

    resumo = finalizadas.aggregate(
        total=Count("id"),
        acertos=Count("id", filter=Q(acertou=True)),
        media_tentativas=Avg("tentativas_usadas", filter=Q(acertou=True)),
    )
    total = resumo["total"]
    resumo["taxa"] = round(100 * resumo["acertos"] / total) if total else 0

    sequencia = 0
    resultados = finalizadas.order_by("-criada_em", "-id").values_list(
        "acertou", flat=True
    )
    for acertou in resultados:
        if not acertou:
            break
        sequencia += 1

    nomes_modos = dict(Partida.MODOS)
    por_modo = [
        {
            "modo": nomes_modos[linha["modo"]],
            "total": linha["total"],
            "acertos": linha["acertos"],
        }
        for linha in finalizadas.values("modo")
        .annotate(total=Count("id"), acertos=Count("id", filter=Q(acertou=True)))
        .order_by("modo")
    ]

    recentes = finalizadas.select_related("cena__obra").order_by(
        "-criada_em", "-id"
    )[:10]

    return render(request, "jogo/perfil.html", {
        "resumo": resumo,
        "sequencia": sequencia,
        "por_modo": por_modo,
        "recentes": recentes,
    })


def ranking(request):
    Usuario = get_user_model()

    geral = (
        Usuario.objects.annotate(
            acertos=Count("partidas", filter=Q(partidas__acertou=True)),
            total=Count("partidas", filter=Q(partidas__terminou=True)),
        )
        .filter(acertos__gt=0)
        .order_by("-acertos", "total", "username")[:10]
    )

    return render(request, "jogo/ranking.html", {
        "geral": geral,
        "sequencias": ranking_sequencias(timezone.localdate()),
    })


# ==============================
# API DO JOGO
# ==============================

@require_POST
def nova_partida(request):
    try:
        dados = _ler_json(request)
    except RequisicaoInvalida as erro:
        return _erro(str(erro))

    modo = dados.get("modo")

    if modo not in ("complete", "context"):
        return _erro("Modo inválido.")

    cena = Cena.objects.order_by("?").select_related("obra").first()
    if cena is None:
        return _erro("Nenhuma cena cadastrada.", status=503)

    usuario = request.user if request.user.is_authenticated else None
    partida = Partida.objects.create(cena=cena, modo=modo, usuario=usuario)

    if usuario is None:
        _registrar_partida_anonima(request, partida.id)

    if modo == "complete":
        dialogo = cena.dialogo
    else:
        dialogo = f"{cena.dialogo} {cena.resposta}"

    return JsonResponse({
        "partida_id": partida.id,
        "dialogo": dialogo,
        "tentativas_restantes": MAX_TENTATIVAS,
    })


@require_POST
def tentativa(request, partida_id):
    partida = _buscar_partida(request, partida_id)

    if partida.terminou:
        return _erro("Esta partida já terminou.")

    try:
        dados = _ler_json(request)
    except RequisicaoInvalida as erro:
        return _erro(str(erro))

    texto = dados.get("resposta")

    if not isinstance(texto, str) or not texto.strip():
        return _erro("Digite uma resposta.")

    texto = texto.strip()

    if len(texto) > MAX_RESPOSTA:
        return _erro(f"A resposta pode ter no máximo {MAX_RESPOSTA} caracteres.")

    usadas = partida.tentativas_usadas + 1
    acertou = resposta_correta(partida, texto)
    terminou = acertou or usadas >= MAX_TENTATIVAS

    # Grava só se ninguém mexeu na partida desde a leitura. Assim, pedidos
    # simultâneos não conseguem testar várias respostas gastando uma tentativa.
    gravada = Partida.objects.filter(
        pk=partida.pk, terminou=False, tentativas_usadas=partida.tentativas_usadas
    ).update(tentativas_usadas=usadas, terminou=terminou, acertou=acertou)

    if not gravada:
        return _erro(
            "Sua tentativa anterior ainda está sendo processada. Tente de novo.",
            status=409,
        )

    resposta = {
        "acertou": acertou,
        "terminou": terminou,
        "tentativas_restantes": MAX_TENTATIVAS - usadas,
    }

    if terminou:
        resposta["revelacao"] = _revelacao(partida.cena)

    return JsonResponse(resposta)


@require_POST
def dica(request, partida_id):
    partida = _buscar_partida(request, partida_id)

    if partida.terminou:
        return _erro("Esta partida já terminou.")

    dicas = _dicas(partida.cena)

    if partida.dicas_usadas >= len(dicas):
        return _erro("Todas as dicas já foram reveladas.")

    gravada = Partida.objects.filter(
        pk=partida.pk, terminou=False, dicas_usadas=partida.dicas_usadas
    ).update(dicas_usadas=partida.dicas_usadas + 1)

    if not gravada:
        return _erro("Pedido de dica em andamento. Tente de novo.", status=409)

    numero = partida.dicas_usadas + 1
    titulo, valor = dicas[partida.dicas_usadas]

    return JsonResponse({
        "numero": numero,
        "titulo": titulo,
        "valor": str(valor),
        "restantes": len(dicas) - numero,
    })


def obras(request):
    busca = normalizar(request.GET.get("q", ""))

    if len(busca) < 2:
        return JsonResponse({"obras": []})

    titulos = Obra.objects.values_list("titulo", flat=True)
    encontrados = [t for t in titulos if busca in normalizar(t)][:5]

    return JsonResponse({"obras": encontrados})


@require_POST
def desafio_hoje(request):
    if not request.user.is_authenticated:
        return _erro("Entre na sua conta para jogar o desafio diário.", status=401)

    desafio = desafio_de_hoje()
    if desafio is None:
        return _erro("Nenhuma cena cadastrada.", status=503)

    partida, _ = Partida.objects.get_or_create(
        usuario=request.user,
        desafio=desafio,
        defaults={"cena": desafio.cena, "modo": "complete"},
    )
    cena = partida.cena

    if partida.terminou:
        return JsonResponse({
            "ja_jogou": True,
            "acertou": partida.acertou,
            "tentativas_usadas": partida.tentativas_usadas,
            "revelacao": _revelacao(cena),
        })

    dicas = [
        {"numero": numero, "titulo": titulo, "valor": str(valor)}
        for numero, (titulo, valor) in enumerate(
            _dicas(cena)[: partida.dicas_usadas], start=1
        )
    ]

    return JsonResponse({
        "ja_jogou": False,
        "partida_id": partida.id,
        "dialogo": cena.dialogo,
        "tentativas_restantes": MAX_TENTATIVAS - partida.tentativas_usadas,
        "dicas": dicas,
    })
