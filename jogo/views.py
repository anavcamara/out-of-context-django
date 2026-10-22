from django.shortcuts import render
from django.utils import timezone
import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Cena, Obra, Partida
from .services import MAX_TENTATIVAS, normalizar, resposta_correta

from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q

from django.core.exceptions import PermissionDenied
from .diario import desafio_de_hoje, sequencia_diaria

@require_POST
def nova_partida(request):
    dados = json.loads(request.body or "{}")
    modo = dados.get("modo")

    if modo not in ("complete", "context"):
        return JsonResponse({"erro": "Modo inválido."}, status=400)

    cena = Cena.objects.order_by("?").select_related("obra").first()
    if cena is None:
        return JsonResponse({"erro": "Nenhuma cena cadastrada."}, status=503)

    usuario = request.user if request.user.is_authenticated else None
    partida = Partida.objects.create(cena=cena, modo=modo, usuario=usuario)

    if modo == "complete":
        dialogo = cena.dialogo
    else:
        dialogo = f"{cena.dialogo} {cena.resposta}"

    return JsonResponse({
        "partida_id": partida.id,
        "dialogo": dialogo,
        "tentativas_restantes": MAX_TENTATIVAS,
    })
    
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

@require_POST
def tentativa(request, partida_id):
    partida = _buscar_partida(request, partida_id)

    if partida.terminou:
        return JsonResponse({"erro": "Esta partida já terminou."}, status=400)

    dados = json.loads(request.body or "{}")
    texto = dados.get("resposta", "").strip()

    if not texto:
        return JsonResponse({"erro": "Digite uma resposta."}, status=400)

    partida.tentativas_usadas += 1
    acertou = resposta_correta(partida, texto)

    if acertou or partida.tentativas_usadas >= MAX_TENTATIVAS:
        partida.terminou = True
        partida.acertou = acertou

    partida.save()

    resposta = {
        "acertou": acertou,
        "terminou": partida.terminou,
        "tentativas_restantes": MAX_TENTATIVAS - partida.tentativas_usadas,
    }

    if partida.terminou:
        resposta["revelacao"] = _revelacao(partida.cena)

    return JsonResponse(resposta)

def home(request):
    contexto = {}

    if request.user.is_authenticated:
        hoje = timezone.localdate()
        contexto["sequencia_diaria"] = sequencia_diaria(request.user, hoje)
        contexto["jogou_hoje"] = Partida.objects.filter(
            usuario=request.user, desafio__data=hoje, terminou=True
        ).exists()

    return render(request, "jogo/index.html", contexto)


@require_POST
def dica(request, partida_id):
    partida = get_object_or_404(
        Partida.objects.select_related("cena__obra"), id=partida_id
    )

    if partida.terminou:
        return JsonResponse({"erro": "Esta partida já terminou."}, status=400)

    dicas = _dicas(partida.cena)

    if partida.dicas_usadas >= len(dicas):
        return JsonResponse({"erro": "Todas as dicas já foram reveladas."}, status=400)

    titulo, valor = dicas[partida.dicas_usadas]
    partida.dicas_usadas += 1
    partida.save()

    return JsonResponse({
        "numero": partida.dicas_usadas,
        "titulo": titulo,
        "valor": str(valor),
        "restantes": len(dicas) - partida.dicas_usadas,
    })


def obras(request):
    busca = normalizar(request.GET.get("q", ""))

    if len(busca) < 2:
        return JsonResponse({"obras": []})

    titulos = Obra.objects.values_list("titulo", flat=True)
    encontrados = [t for t in titulos if busca in normalizar(t)][:5]

    return JsonResponse({"obras": encontrados})


def cadastro(request):
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

    recentes = finalizadas.select_related("cena__obra").order_by("-criada_em")[:10]

    return render(request, "jogo/perfil.html", {
        "resumo": resumo,
        "sequencia": sequencia,
        "por_modo": por_modo,
        "recentes": recentes,
    })
    
def _buscar_partida(request, partida_id):
    partida = get_object_or_404(
        Partida.objects.select_related("cena__obra"), id=partida_id
    )

    if partida.usuario_id is not None and partida.usuario_id != request.user.id:
        raise PermissionDenied

    return partida


@require_POST
def desafio_hoje(request):
    if not request.user.is_authenticated:
        return JsonResponse(
            {"erro": "Entre na sua conta para jogar o desafio diário."}, status=401
        )

    desafio = desafio_de_hoje()
    if desafio is None:
        return JsonResponse({"erro": "Nenhuma cena cadastrada."}, status=503)

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

