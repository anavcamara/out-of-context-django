from django.db import models
from django.conf import settings

class Obra(models.Model):
    TIPOS = [
        ("filme", "Filme"),
        ("serie", "Série"),
    ]

    titulo = models.CharField(max_length=200)
    tipo = models.CharField(max_length=10, choices=TIPOS)
    ano = models.PositiveSmallIntegerField()
    genero = models.CharField(max_length=200)

    def __str__(self):
        return self.titulo

class Cena(models.Model):
    obra = models.ForeignKey(Obra, on_delete=models.CASCADE, related_name="cenas")
    personagem = models.CharField(max_length=100)
    contexto = models.TextField()
    dialogo = models.CharField(max_length=300)
    resposta = models.CharField(max_length=300)
    
    def __str__(self):
        return f"{self.obra.titulo}: {self.dialogo}"
    
class Partida(models.Model):
    MODOS = [
        ("complete", "Complete a cena"),
        ("context", "Fora de contexto"),
    ]
    
    usuario = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    null=True,
    blank=True,
    on_delete=models.SET_NULL,
    related_name="partidas",
    )

    cena = models.ForeignKey(Cena, on_delete=models.PROTECT, related_name="partidas")
    modo = models.CharField(max_length=10, choices=MODOS)
    tentativas_usadas = models.PositiveSmallIntegerField(default=0)
    dicas_usadas = models.PositiveSmallIntegerField(default=0)
    terminou = models.BooleanField(default=False)
    acertou = models.BooleanField(default=False)
    criada_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Partida {self.pk} ({self.modo}) - {self.cena}"
