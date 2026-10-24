from django.contrib import admin

from .models import Cena, DesafioDiario, Obra, Partida


@admin.register(Obra)
class ObraAdmin(admin.ModelAdmin):
    list_display = ("titulo", "tipo", "ano", "genero")
    list_filter = ("tipo",)
    search_fields = ("titulo",)


@admin.register(Cena)
class CenaAdmin(admin.ModelAdmin):
    list_display = ("dialogo", "resposta", "obra", "personagem")
    list_select_related = ("obra",)
    search_fields = ("dialogo", "resposta", "obra__titulo", "personagem")


@admin.register(DesafioDiario)
class DesafioDiarioAdmin(admin.ModelAdmin):
    list_display = ("data", "cena")
    list_select_related = ("cena__obra",)
    ordering = ("-data",)


@admin.register(Partida)
class PartidaAdmin(admin.ModelAdmin):
    list_display = (
        "id", "usuario", "modo", "cena", "tentativas_usadas",
        "terminou", "acertou", "criada_em",
    )
    list_select_related = ("usuario", "cena__obra")
    list_filter = ("modo", "terminou", "acertou")
    date_hierarchy = "criada_em"
