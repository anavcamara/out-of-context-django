from django.db import models

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
