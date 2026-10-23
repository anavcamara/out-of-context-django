const MAX_TENTATIVAS = 3;
const TOTAL_DICAS = 3;

const estado = {
  modo: null,
  partidaId: null,
  tentativasRestantes: MAX_TENTATIVAS,
  dicasUsadas: 0,
  diario: false,
  terminou: false,
  acertou: false,
  revelacao: null,
  ocupado: false
};

const elementos = {
  app: document.getElementById("app"),

  // Home
  homeScreen: document.getElementById("home-screen"),
  playButton: document.getElementById("play-button"),
  dailyButton: document.getElementById("daily-button"),
  brandButton: document.getElementById("brand-button"),
  headerAction: document.getElementById("header-action"),
  loadError: document.getElementById("load-error"),

  // Jogo
  gameScreen: document.getElementById("game-screen"),
  backButton: document.getElementById("back-button"),
  gameModeLabel: document.getElementById("game-mode-label"),
  gameEyebrow: document.getElementById("game-eyebrow"),
  gameTitle: document.getElementById("game-title"),
  gameCopy: document.getElementById("game-copy"),
  dialogo: document.getElementById("dialogo"),

  // Complete a cena
  completeForm: document.getElementById("complete-form"),
  answerInput: document.getElementById("answer-input"),
  answerFeedback: document.getElementById("answer-feedback"),

  // Fora de contexto
  contextForm: document.getElementById("context-form"),
  contextInput: document.getElementById("context-input"),
  contextFeedback: document.getElementById("context-feedback"),
  suggestions: document.getElementById("suggestions"),

  // Tentativas e dicas
  attemptDots: document.getElementById("attempt-dots"),
  hintButton: document.getElementById("hint-button"),
  hints: document.getElementById("hints"),

  // Feedback da rodada
  roundFeedback: document.getElementById("round-feedback"),
  feedbackMark: document.getElementById("feedback-mark"),
  feedbackEyebrow: document.getElementById("feedback-eyebrow"),
  feedbackTitle: document.getElementById("feedback-title"),
  feedbackMessage: document.getElementById("feedback-message"),
  feedbackAnswer: document.getElementById("feedback-answer"),
  feedbackWork: document.getElementById("feedback-work"),
  continueButton: document.getElementById("continue-button"),

  // Modais
  modeModal: document.getElementById("mode-modal"),
  howModal: document.getElementById("how-modal"),
  resultModal: document.getElementById("result-modal"),

  // Resultado
  resultEyebrow: document.getElementById("result-eyebrow"),
  resultTitle: document.getElementById("result-title"),
  resultCopy: document.getElementById("result-copy"),
  resultScore: document.getElementById("result-score"),
  resultWork: document.getElementById("result-work"),
  resultYear: document.getElementById("result-year"),
  resultGenre: document.getElementById("result-genre"),
  resultCharacter: document.getElementById("result-character"),
  resultAnswer: document.getElementById("result-answer"),
  playAgainButton: document.getElementById("play-again-button"),
  homeButton: document.getElementById("home-button")
};

// ==============================
// COMUNICAÇÃO COM O SERVIDOR
// ==============================

// O Django exige este token em todo POST (proteção CSRF).
// Ele vem de uma <meta> no HTML, preenchida pelo servidor.
const csrfToken = document
  .querySelector('meta[name="csrf-token"]')
  .getAttribute("content");

async function api(url, corpo = {}) {
  const resposta = await fetch(url, {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken
    },
    body: JSON.stringify(corpo)
  });

  const dados = await resposta.json().catch(() => ({}));

  if (!resposta.ok) {
    const erro = new Error(dados.erro || "Algo deu errado. Tente novamente.");
    erro.status = resposta.status;
    throw erro;
  }

  return dados;
}

// ==============================
// MODAIS
// ==============================

function abrirModal(modal) {
  modal.hidden = false;
}

function fecharModal(modal) {
  modal.hidden = true;
}

// ==============================
// HOME
// ==============================

elementos.playButton.addEventListener("click", () => {
  abrirModal(elementos.modeModal);
});

elementos.headerAction.addEventListener("click", () => {
  abrirModal(elementos.howModal);
});

elementos.brandButton.addEventListener("click", voltarParaHome);

// Fecha modais pelos botões X
document.querySelectorAll(".modal-close").forEach(botao => {
  botao.addEventListener("click", () => {
    fecharModal(botao.closest(".modal-layer"));
  });
});

// Fecha pelo backdrop (menos o modal de resultado)
document.querySelectorAll(".modal-backdrop").forEach(backdrop => {
  backdrop.addEventListener("click", () => {
    const modal = backdrop.closest(".modal-layer");

    if (modal.id !== "result-modal") {
      fecharModal(modal);
    }
  });
});

// ==============================
// ESCOLHA DO MODO
// ==============================

document.querySelectorAll(".mode-option").forEach(botao => {
  botao.addEventListener("click", () => {
    iniciarJogo(botao.dataset.mode);
  });
});

// ==============================
// INICIAR JOGO
// ==============================

async function iniciarJogo(modo) {
  if (estado.ocupado) {
    return;
  }

  estado.ocupado = true;

  try {
    // O servidor sorteia a cena e cria a partida.
    // Só volta o que o jogador pode ver: a resposta fica lá.
    const dados = await api("/api/partida/nova/", { modo });

    estado.modo = modo;
    estado.diario = false;
    estado.partidaId = dados.partida_id;
    estado.tentativasRestantes = dados.tentativas_restantes;
    estado.dicasUsadas = 0;
    estado.terminou = false;
    estado.acertou = false;
    estado.revelacao = null;

    elementos.loadError.hidden = true;
    fecharModal(elementos.modeModal);

    elementos.homeScreen.hidden = true;
    elementos.gameScreen.hidden = false;

    prepararTelaDoModo();
    carregarCena(dados.dialogo);

    requestAnimationFrame(() => {
      elementos.gameScreen.scrollIntoView({
        behavior: "smooth",
        block: "start"
      });
    });
  } catch (erro) {
    console.error(erro);
    fecharModal(elementos.modeModal);
    elementos.loadError.hidden = false;
  } finally {
    estado.ocupado = false;
  }
}

// ==============================
// DESAFIO DO DIA
// ==============================

async function iniciarDesafio() {
  if (estado.ocupado) {
    return;
  }

  estado.ocupado = true;

  try {
    const dados = await api("/api/desafio/hoje/");

    estado.modo = "complete";
    estado.diario = true;
    estado.terminou = false;
    estado.acertou = false;
    estado.revelacao = null;
    estado.dicasUsadas = 0;

    elementos.loadError.hidden = true;

    // Já jogou hoje: só mostra o resultado, sem abrir a tela de jogo.
    if (dados.ja_jogou) {
      estado.terminou = true;
      estado.acertou = dados.acertou;
      estado.revelacao = dados.revelacao;
      estado.tentativasRestantes = MAX_TENTATIVAS - dados.tentativas_usadas;
      mostrarResultado();
      return;
    }

    estado.partidaId = dados.partida_id;
    estado.tentativasRestantes = dados.tentativas_restantes;

    elementos.homeScreen.hidden = true;
    elementos.gameScreen.hidden = false;

    prepararTelaDoModo();
    carregarCena(dados.dialogo);

    // Se a pessoa recarregou a página no meio da partida,
    // as dicas já usadas voltam do servidor.
    dados.dicas.forEach(adicionarDica);
    estado.dicasUsadas = dados.dicas.length;
    atualizarBotaoDica();

    requestAnimationFrame(() => {
      elementos.gameScreen.scrollIntoView({
        behavior: "smooth",
        block: "start"
      });
    });
  } catch (erro) {
    console.error(erro);

    if (erro.status === 401) {
      window.location.href = "/contas/login/?next=/";
      return;
    }

    elementos.loadError.hidden = false;
  } finally {
    estado.ocupado = false;
  }
}

if (elementos.dailyButton) {
  elementos.dailyButton.addEventListener("click", iniciarDesafio);
}

// ==============================
// PREPARAR MODO
// ==============================

function prepararTelaDoModo() {
  if (estado.modo === "complete") {
    elementos.gameModeLabel.textContent =
      estado.diario ? "DESAFIO DO DIA" : "COMPLETE A CENA";
    elementos.gameEyebrow.textContent =
      estado.diario ? "A CENA DE HOJE" : "COMPLETE A FALA";
    elementos.gameTitle.textContent = "Continue a cena.";
    elementos.gameCopy.textContent =
      estado.diario
        ? "Uma cena por dia, igual para todo mundo. Você só tem uma partida."
        : "Complete a fala antes que suas três tentativas acabem.";

    elementos.completeForm.hidden = false;
    elementos.contextForm.hidden = true;
  } else {
    elementos.gameModeLabel.textContent = "FORA DE CONTEXTO";
    elementos.gameEyebrow.textContent = "DESCUBRA A OBRA";
    elementos.gameTitle.textContent = "De onde veio essa fala?";
    elementos.gameCopy.textContent =
      "Digite o nome da obra e descubra se você reconhece a cena.";

    elementos.completeForm.hidden = true;
    elementos.contextForm.hidden = false;
  }
}

// ==============================
// CARREGAR CENA
// ==============================

function carregarCena(dialogo) {
  elementos.answerInput.value = "";
  elementos.contextInput.value = "";

  elementos.answerInput.disabled = false;
  elementos.contextInput.disabled = false;

  elementos.completeForm.querySelector("button").disabled = false;
  elementos.contextForm.querySelector("button").disabled = false;

  elementos.answerFeedback.textContent = "";
  elementos.contextFeedback.textContent = "";

  esconderSugestoes();
  elementos.hints.innerHTML = "";

  elementos.roundFeedback.hidden = true;
  elementos.roundFeedback.classList.remove("correct", "incorrect");

  elementos.hintButton.disabled = false;
  elementos.hintButton.innerHTML = `
    <span class="hint-icon" aria-hidden="true">+</span>
    <span>PEDIR DICA</span>
  `;

  renderizarTentativas();

  elementos.dialogo.textContent = `“${dialogo}”`;

  const campo =
    estado.modo === "complete" ? elementos.answerInput : elementos.contextInput;

  setTimeout(() => campo.focus(), 100);
}

// ==============================
// TENTATIVAS
// ==============================

function renderizarTentativas() {
  elementos.attemptDots.innerHTML = "";

  for (let i = 0; i < MAX_TENTATIVAS; i++) {
    const ponto = document.createElement("span");
    ponto.classList.add("attempt-dot");

    if (i < estado.tentativasRestantes) {
      ponto.classList.add("available");
    }

    elementos.attemptDots.appendChild(ponto);
  }
}

// ==============================
// DICAS
// ==============================

function adicionarDica(dica) {
  const bloco = document.createElement("div");
  bloco.classList.add("hint");

  const numero = document.createElement("span");
  numero.classList.add("hint-number");
  numero.textContent = `DICA ${dica.numero}`;

  const titulo = document.createElement("strong");
  titulo.textContent = dica.titulo;

  const valor = document.createElement("p");
  valor.textContent = dica.valor || "Informação ainda não cadastrada.";

  bloco.append(numero, titulo, valor);
  elementos.hints.appendChild(bloco);
}

function atualizarBotaoDica() {
  if (estado.dicasUsadas >= TOTAL_DICAS) {
    elementos.hintButton.innerHTML = `<span>TODAS AS DICAS REVELADAS</span>`;
    elementos.hintButton.disabled = true;
  } else if (estado.dicasUsadas > 0) {
    elementos.hintButton.innerHTML = `
      <span class="hint-icon" aria-hidden="true">+</span>
      <span>PEDIR OUTRA DICA</span>
    `;
  }
}

async function mostrarDica() {
  if (estado.terminou || estado.ocupado) {
    return;
  }

  estado.ocupado = true;

  try {
    // O servidor decide qual é a próxima dica e quantas já foram dadas.
    const dica = await api(`/api/partida/${estado.partidaId}/dica/`);

    adicionarDica(dica);
    estado.dicasUsadas = dica.numero;
    atualizarBotaoDica();
  } catch (erro) {
    console.error(erro);
  } finally {
    estado.ocupado = false;
  }
}

elementos.hintButton.addEventListener("click", mostrarDica);

// ==============================
// ENVIAR RESPOSTA
// ==============================

elementos.completeForm.addEventListener("submit", event => {
  event.preventDefault();

  if (estado.modo !== "complete" || estado.terminou) {
    return;
  }

  enviarTentativa(elementos.answerInput.value, {
    input: elementos.answerInput,
    feedback: elementos.answerFeedback,
    vazio: "Digite uma resposta antes de enviar.",
    errou: "Não foi dessa vez. Tente novamente."
  });
});

elementos.contextForm.addEventListener("submit", event => {
  event.preventDefault();

  if (estado.modo !== "context" || estado.terminou) {
    return;
  }

  esconderSugestoes();

  enviarTentativa(elementos.contextInput.value, {
    input: elementos.contextInput,
    feedback: elementos.contextFeedback,
    vazio: "Digite uma obra antes de enviar.",
    errou: "Ainda não. Tente outra vez."
  });
});

async function enviarTentativa(texto, { input, feedback, vazio, errou }) {
  if (!texto.trim()) {
    feedback.textContent = vazio;
    input.focus();
    return;
  }

  if (estado.ocupado) {
    return;
  }

  estado.ocupado = true;

  try {
    // Quem confere a resposta e conta as tentativas é o servidor.
    const dados = await api(`/api/partida/${estado.partidaId}/tentativa/`, {
      resposta: texto
    });

    estado.tentativasRestantes = dados.tentativas_restantes;
    renderizarTentativas();

    if (dados.terminou) {
      estado.revelacao = dados.revelacao;
      finalizarRodada(dados.acertou);
    } else {
      feedback.textContent = errou;
    }
  } catch (erro) {
    console.error(erro);
    feedback.textContent = erro.message;
  } finally {
    estado.ocupado = false;
  }
}

// ==============================
// FINALIZAR RODADA
// ==============================

function finalizarRodada(acertou) {
  estado.acertou = acertou;
  estado.terminou = true;

  elementos.roundFeedback.classList.remove("correct", "incorrect");
  elementos.roundFeedback.classList.add(acertou ? "correct" : "incorrect");

  elementos.answerInput.disabled = true;
  elementos.contextInput.disabled = true;

  elementos.completeForm.querySelector("button").disabled = true;
  elementos.contextForm.querySelector("button").disabled = true;

  elementos.hintButton.disabled = true;
  esconderSugestoes();

  elementos.answerFeedback.textContent = "";
  elementos.contextFeedback.textContent = "";

  elementos.roundFeedback.hidden = false;

  if (acertou) {
    elementos.feedbackMark.textContent = "✓";
    elementos.feedbackEyebrow.textContent = "ACERTOU";
    elementos.feedbackTitle.textContent = "Você reconheceu a cena.";
    elementos.feedbackMessage.textContent = "Boa. Essa você não deixou passar.";
  } else {
    elementos.feedbackMark.textContent = "×";
    elementos.feedbackEyebrow.textContent = "FIM DAS TENTATIVAS";
    elementos.feedbackTitle.textContent = "Essa passou longe.";
    elementos.feedbackMessage.textContent =
      estado.modo === "context" ? "A obra era:" : "A resposta correta era:";
  }

  // No modo "Fora de contexto" a fala completa já está na tela,
  // então só a obra é revelada.
  const soObra = estado.modo === "context";

  elementos.feedbackAnswer.textContent = `"${estado.revelacao.resposta}"`;
  elementos.feedbackAnswer.parentElement.hidden = soObra;
  elementos.feedbackWork.closest(".reveal-grid")
    .classList.toggle("reveal-grid--single", soObra);
  elementos.feedbackWork.textContent = estado.revelacao.obra;

  elementos.continueButton.textContent = "VER RESULTADO";

  elementos.roundFeedback.scrollIntoView({
    behavior: "smooth",
    block: "nearest"
  });
}

// ==============================
// RESULTADO FINAL
// ==============================

function mostrarResultado() {
  const r = estado.revelacao;

  elementos.resultEyebrow.textContent =
    estado.acertou ? "VOCÊ ACERTOU" : "RESULTADO";

  elementos.resultTitle.textContent =
    estado.acertou ? "Essa você conhecia." : "Agora você conhece a resposta.";

  elementos.resultCopy.textContent = estado.diario
    ? "Volte amanhã para a próxima cena do desafio."
    : estado.acertou
      ? "Você completou o desafio."
      : "A cena fica registrada para a próxima tentativa.";

  elementos.playAgainButton.hidden = estado.diario;

  elementos.resultWork.textContent = r.obra || "Não informado";
  elementos.resultYear.textContent = r.ano || "Não informado";
  elementos.resultGenre.textContent = r.genero || "Não informado";
  elementos.resultCharacter.textContent = r.personagem || "Não informado";
  elementos.resultAnswer.textContent = `"${r.resposta}"`;
  elementos.resultAnswer.closest(".result-detail").hidden =
    estado.modo === "context";

  elementos.resultScore.textContent =
    `${MAX_TENTATIVAS - estado.tentativasRestantes} tentativa(s) utilizada(s)`;

  abrirModal(elementos.resultModal);
}

elementos.continueButton.addEventListener("click", mostrarResultado);

// ==============================
// JOGAR NOVAMENTE / VOLTAR
// ==============================

elementos.playAgainButton.addEventListener("click", () => {
  fecharModal(elementos.resultModal);
  iniciarJogo(estado.modo);
});

function voltarParaHome() {
  fecharModal(elementos.modeModal);
  fecharModal(elementos.howModal);
  fecharModal(elementos.resultModal);

  elementos.gameScreen.hidden = true;
  elementos.homeScreen.hidden = false;

  window.scrollTo({ top: 0, behavior: "smooth" });
}

elementos.homeButton.addEventListener("click", voltarParaHome);

elementos.backButton.addEventListener("click", () => {
  elementos.gameScreen.hidden = true;
  elementos.homeScreen.hidden = false;

  if (!estado.diario) {
    abrirModal(elementos.modeModal);
  }

  window.scrollTo({ top: 0, behavior: "smooth" });
});

// ==============================
// AUTOCOMPLETE (busca no servidor)
// ==============================

let temporizadorBusca = null;

elementos.contextInput.addEventListener("input", () => {
  clearTimeout(temporizadorBusca);

  if (estado.modo !== "context" || estado.terminou) {
    return;
  }

  const texto = elementos.contextInput.value.trim();

  if (texto.length < 2) {
    esconderSugestoes();
    return;
  }

  // Espera 200 ms sem digitar antes de perguntar ao servidor.
  temporizadorBusca = setTimeout(() => buscarObras(texto), 200);
});

async function buscarObras(texto) {
  try {
    const resposta = await fetch(`/api/obras/?q=${encodeURIComponent(texto)}`);

    if (!resposta.ok) {
      return;
    }

    const dados = await resposta.json();

    // Se a pessoa já digitou outra coisa ou a rodada acabou, ignora.
    if (elementos.contextInput.value.trim() !== texto || estado.terminou) {
      return;
    }

    mostrarSugestoes(dados.obras);
  } catch (erro) {
    console.error(erro);
  }
}

function mostrarSugestoes(resultados) {
  elementos.suggestions.innerHTML = "";

  if (resultados.length === 0) {
    return;
  }

  resultados.forEach(obra => {
    const opcao = document.createElement("button");

    opcao.type = "button";
    opcao.classList.add("suggestion-option");
    opcao.textContent = obra;

    opcao.addEventListener("click", () => {
      elementos.contextInput.value = obra;
      esconderSugestoes();
      elementos.contextInput.focus();
    });

    elementos.suggestions.appendChild(opcao);
  });
}

function esconderSugestoes() {
  clearTimeout(temporizadorBusca);
  elementos.suggestions.innerHTML = "";
}