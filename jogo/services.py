import re
import unicodedata

TOLERANCIA = 0.85
MAX_TENTATIVAS = 3
MAX_RESPOSTA = 300  # limite de caracteres aceito em uma tentativa


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
            if a[i - 1] == b[j - 1]:
                matriz[i][j] = matriz[i - 1][j - 1]
            else:
                matriz[i][j] = min(
                    matriz[i - 1][j - 1] + 1,
                    matriz[i][j - 1] + 1,
                    matriz[i - 1][j] + 1,
                )

    return matriz[len(a)][len(b)]


def similaridade(a, b):
    distancia = levenshtein(a, b)
    tamanho_maximo = max(len(a), len(b))
    tamanho_minimo = min(len(a), len(b))

    if tamanho_maximo == 0:
        return 1

    proximidade = 1 - distancia / tamanho_maximo
    penalidade_tamanho = tamanho_minimo / tamanho_maximo

    return proximidade * penalidade_tamanho


def _palavras_contidas(maior, menor):
    """True se `menor` aparece em `maior` como sequência de palavras inteiras."""
    return f" {menor} " in f" {maior} "


def titulo_correto(texto, titulo):
    """Confere se `texto` identifica a obra `titulo` (modo Fora de contexto).

    Aceita: o título (com pequenos erros de digitação), um trecho dele formado
    por palavras inteiras (ex.: "Harry Potter") ou um texto que contenha o
    título completo. Fragmentos soltos de palavras (ex.: "ast") não valem.
    """
    texto = normalizar(texto)
    titulo = normalizar(titulo)

    if not texto or not titulo:
        return False

    if similaridade(texto, titulo) >= TOLERANCIA:
        return True

    if len(texto) >= 4 and _palavras_contidas(titulo, texto):
        return True

    return _palavras_contidas(texto, titulo)


def resposta_correta(partida, texto):
    if partida.modo == "complete":
        esperada = normalizar(partida.cena.resposta)
        return similaridade(normalizar(texto), esperada) >= TOLERANCIA

    return titulo_correto(texto, partida.cena.obra.titulo)
