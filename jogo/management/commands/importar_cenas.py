import json

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from jogo.models import Cena, Obra

CAMPOS_OBRIGATORIOS = (
    "obra", "tipo", "ano", "genero", "personagem", "contexto", "dialogo", "resposta",
)


class Command(BaseCommand):
    help = "Importa cenas de um arquivo JSON (rodar de novo não duplica nada)."

    def add_arguments(self, parser):
        parser.add_argument("caminho", type=str)

    def handle(self, *args, **options):
        try:
            with open(options["caminho"], encoding="utf-8") as arquivo:
                dados = json.load(arquivo)
        except FileNotFoundError:
            raise CommandError(f"Arquivo não encontrado: {options['caminho']}")
        except json.JSONDecodeError as erro:
            raise CommandError(f"JSON inválido: {erro}")

        if not isinstance(dados, list):
            raise CommandError("O JSON deve ser uma lista de cenas.")

        for posicao, item in enumerate(dados, start=1):
            faltando = [c for c in CAMPOS_OBRIGATORIOS if c not in item]
            if faltando:
                raise CommandError(
                    f"Cena {posicao}: faltam os campos {', '.join(faltando)}."
                )

        criadas = 0

        # Tudo ou nada: se algo falhar no meio, nada é gravado.
        with transaction.atomic():
            for item in dados:
                obra, _ = Obra.objects.get_or_create(
                    titulo=item["obra"],
                    defaults={
                        "tipo": item["tipo"],
                        "ano": item["ano"],
                        "genero": item["genero"],
                    },
                )

                _, foi_criada = Cena.objects.get_or_create(
                    obra=obra,
                    dialogo=item["dialogo"],
                    defaults={
                        "personagem": item["personagem"],
                        "contexto": item["contexto"],
                        "resposta": item["resposta"],
                    },
                )

                if foi_criada:
                    criadas += 1

        self.stdout.write(self.style.SUCCESS(f"{criadas} cenas novas importadas."))
