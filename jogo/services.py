import re
import unicodedata


def normalizar(texto):
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = texto.lower()
    texto = re.sub(r"[.!?,;:\"'“”‘’]", "", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def levenshtein(a, b):
    matriz = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    
    for i in range(len(a) + 1):
        matriz[i][0] = i
    
    for j in range(len(b) + 1):
        matriz[0][j] = j
        
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            if (a [i - 1] == b[j - 1]):
                matriz[i][j] = matriz[i - 1][j - 1]
            else:
                matriz[i][j] = min(matriz[i - 1][j - 1] + 1, matriz[i][j - 1] + 1, matriz[i - 1][j] + 1)
    
    return matriz[len(a)][len(b)]
    
def similaridade(a, b):
    distancia = levenshtein(a, b)
    tamanhoMaximo = max(len(a), len(b))
    tamanhoMinimo = min(len(a), len(b))
    
    if tamanhoMaximo == 0:
        return 1
    
    proximidade = 1 - distancia / tamanhoMaximo
    penalidadeTamanho = tamanhoMinimo / tamanhoMaximo
    
    return proximidade * penalidadeTamanho

TOLERANCIA = 0.85
MAX_TENTATIVAS = 3

def resposta_correta(partida, texto):
    texto = normalizar(texto)

    if partida.modo == "complete":
        esperada = normalizar(partida.cena.resposta)
        return similaridade(texto, esperada) >= TOLERANCIA

    obra = normalizar(partida.cena.obra.titulo)
    return len(texto) >= 3 and (texto in obra or obra in texto)