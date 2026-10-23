from datetime import timedelta

from django.utils import timezone

from .models import Cena, DesafioDiario, Partida


def desafio_de_hoje():
    hoje = timezone.localdate()

    desafio = DesafioDiario.objects.select_related("cena__obra").filter(data=hoje).first()
    if desafio:
        return desafio

    usadas = DesafioDiario.objects.values_list("cena_id", flat=True)
    cena = (
        Cena.objects.exclude(id__in=usadas).order_by("?").first()
        or Cena.objects.order_by("?").first()
    )
    if cena is None:
        return None

    desafio, _ = DesafioDiario.objects.get_or_create(data=hoje, defaults={"cena": cena})
    return desafio


def sequencia_diaria(usuario, hoje):
    vitorias = set(
        Partida.objects.filter(
            usuario=usuario, desafio__isnull=False, acertou=True
        ).values_list("desafio__data", flat=True)
    )

    dia = hoje if hoje in vitorias else hoje - timedelta(days=1)
    sequencia = 0

    while dia in vitorias:
        sequencia += 1
        dia -= timedelta(days=1)

    return sequencia

def _contar_sequencia(datas, hoje):
    dia = hoje if hoje in datas else hoje - timedelta(days=1)
    sequencia = 0

    while dia in datas:
        sequencia += 1
        dia -= timedelta(days=1)

    return sequencia


def sequencia_diaria(usuario, hoje):
    vitorias = set(
        Partida.objects.filter(
            usuario=usuario, desafio__isnull=False, acertou=True
        ).values_list("desafio__data", flat=True)
    )
    return _contar_sequencia(vitorias, hoje)


def ranking_sequencias(hoje, limite=10):
    vitorias = {}

    linhas = Partida.objects.filter(
        usuario__isnull=False, desafio__isnull=False, acertou=True
    ).values_list("usuario__username", "desafio__data")

    for username, data in linhas:
        vitorias.setdefault(username, set()).add(data)

    ranking = []
    for username, datas in vitorias.items():
        sequencia = _contar_sequencia(datas, hoje)
        if sequencia > 0:
            ranking.append((username, sequencia))

    ranking.sort(key=lambda item: (-item[1], item[0]))
    return ranking[:limite]