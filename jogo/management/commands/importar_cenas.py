import json

from django.core.management.base import BaseCommand

from jogo.models import Obra, Cena


class Command(BaseCommand):
    help = "Importa cenas de um arquivo JSON"

    def add_arguments(self, parser):
        parser.add_argument("caminho", type=str)

    def handle(self, *args, **options):
        with open(options["caminho"], encoding="utf-8") as arquivo:
            dados = json.load(arquivo)

        criadas = 0

        for item in dados:
            obra, _ = Obra.objects.get_or_create(
                titulo=item["obra"],
                defaults={
                    "tipo": item["tipo"],
                    "ano": item["ano"],
                    "genero": item["genero"],
                },
            )

            cena, foi_criada = Cena.objects.get_or_create(
                obra = obra,
                dialogo=item["dialogo"],
                defaults={
                    "personagem": item["personagem"],
                    "contexto": item["contexto"],
                    "resposta": item["resposta"],
                },
            )
            
            if foi_criada:
                criadas +=1
                
        self.stdout.write(self.style.SUCCESS(f"{criadas} cenas novas importadas."))