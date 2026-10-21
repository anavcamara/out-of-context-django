from django.shortcuts import render
import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from .models import Cena, Partida
from .services import MAX_TENTATIVAS, resposta_correta


@require_POST
def nova_partida(request):
    dados = json.loads(request.body or "{}")
    modo = dados.get("modo")

    if modo not in ("complete", "context"):
        return JsonResponse({"erro": "Modo inválido."}, status=400)

    cena = Cena.objects.order_by("?").select_related("obra").first()
    if cena is None:
        return JsonResponse({"erro": "Nenhuma cena cadastrada."}, status=503)

    partida = Partida.objects.create(cena=cena, modo=modo)

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


@require_POST
def tentativa(request, partida_id):
    partida = get_object_or_404(Partida, id=partida_id)

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
    return render(request, "jogo/index.html")


