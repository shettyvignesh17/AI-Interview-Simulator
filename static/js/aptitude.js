import { createRequestTracker, createSessionExitController } from "./session_exit.js";

const state = {
  user: null,
  stats: null,
  attempt: null,
  meta: null,
  currentIndex: 0,
  responses: {},
  timerId: null,
  secondsRemaining: 0,
  submitting: false,
  exiting: false,
};

const refs = Object.fromEntries(
  [
    "authNotice", "aptitudeContent", "logoutButton", "themeToggle", "quizIntro",
    "startQuizButton", "quizSection", "companyLabel", "categoryChip", "difficultyChip",
    "quizTimer", "questionCounter", "answeredCounter", "quizProgressFill", "questionText",
    "optionList", "previousButton", "nextButton", "submitQuizButton", "questionMap",
    "resultsSection", "resultHeadline", "resultStatus", "resultScoreRing", "resultPercentage",
    "totalQuestionsValue", "correctAnswersValue", "wrongAnswersValue", "passFailValue",
    "companyResultGrid", "reviewList", "newQuizButton", "bankCountLabel", "attemptsValue",
    "highestScoreValue", "averageScoreValue", "accuracyValue", "companyAccuracyList",
    "strongCategoryList", "weakCategoryList", "aptitudeHistoryList", "toast",
    "aptitudeBackButton", "aptitudeQuitButton",
  ].map((id) => [id, document.getElementById(id)]),
);
refs.body = document.body;
const requests = createRequestTracker();
let exitController = null;

function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

async function api(url, options = {}, tracked = true) {
  const response = await requests.fetch(url, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    credentials: "same-origin",
    ...options,
  }, { tracked });
  const payload = (response.headers.get("content-type") || "").includes("application/json")
    ? await response.json()
    : {};
  if (!response.ok) throw new Error(payload.error || "Something went wrong.");
  return payload;
}

function showToast(message, tone = "success") {
  refs.toast.textContent = message;
  refs.toast.className = `toast ${tone}`;
  window.clearTimeout(showToast.timeoutId);
  showToast.timeoutId = window.setTimeout(() => refs.toast.classList.add("hidden"), 2800);
}

function applyTheme(theme) {
  refs.body.dataset.theme = theme;
  localStorage.setItem("interview-theme", theme);
  const label = theme === "dark" ? "Switch to light theme" : "Switch to dark theme";
  refs.themeToggle.setAttribute("aria-label", label);
  refs.themeToggle.title = label;
}

function formatTimer(seconds) {
  const minutes = Math.floor(Math.max(0, seconds) / 60);
  const remainder = Math.max(0, seconds) % 60;
  return `${String(minutes).padStart(2, "0")}:${String(remainder).padStart(2, "0")}`;
}

function formatDate(value) {
  return new Date(value).toLocaleString(undefined, {
    month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit",
  });
}

function currentQuestion() {
  return state.attempt?.questions?.[state.currentIndex] || null;
}

function answeredCount() {
  return Object.values(state.responses).filter(Boolean).length;
}

function renderQuestionMap() {
  refs.questionMap.innerHTML = state.attempt.questions
    .map((question, index) => {
      const classes = ["question-map-button"];
      if (index === state.currentIndex) classes.push("active");
      if (state.responses[question.id]) classes.push("answered");
      return `<button class="${classes.join(" ")}" type="button" data-index="${index}">${index + 1}</button>`;
    })
    .join("");
}

function renderQuestion() {
  const question = currentQuestion();
  if (!question) return;
  const total = state.attempt.questions.length;
  const selectedAnswer = state.responses[question.id] || "";

  refs.companyLabel.textContent = `Company: ${question.company}`;
  refs.categoryChip.textContent = question.category;
  refs.difficultyChip.textContent = question.difficulty;
  refs.questionCounter.textContent = `Question ${state.currentIndex + 1} of ${total}`;
  refs.answeredCounter.textContent = `${answeredCount()} answered`;
  refs.quizProgressFill.style.width = `${((state.currentIndex + 1) / total) * 100}%`;
  refs.questionText.textContent = question.question;
  refs.optionList.innerHTML = question.options
    .map((option, index) => {
      const selected = option === selectedAnswer;
      return `
        <label class="quiz-option ${selected ? "selected" : ""}">
          <input type="radio" name="aptitudeAnswer" value="${escapeHtml(option)}" ${selected ? "checked" : ""} />
          <span class="option-letter">${String.fromCharCode(65 + index)}</span>
          <span>${escapeHtml(option)}</span>
        </label>`;
    })
    .join("");

  refs.previousButton.disabled = state.currentIndex === 0;
  refs.nextButton.classList.toggle("hidden", state.currentIndex === total - 1);
  refs.submitQuizButton.classList.toggle("hidden", state.currentIndex !== total - 1);
  renderQuestionMap();
}

function stopTimer() {
  window.clearInterval(state.timerId);
  state.timerId = null;
}

function startTimer(seconds) {
  stopTimer();
  state.secondsRemaining = seconds;
  refs.quizTimer.textContent = formatTimer(seconds);
  refs.quizTimer.parentElement.classList.remove("warning");
  state.timerId = window.setInterval(() => {
    state.secondsRemaining -= 1;
    refs.quizTimer.textContent = formatTimer(state.secondsRemaining);
    refs.quizTimer.parentElement.classList.toggle("warning", state.secondsRemaining <= 60);
    if (state.secondsRemaining <= 0) {
      stopTimer();
      submitQuiz(true).catch(handleAsyncError);
    }
  }, 1000);
}

async function startQuiz() {
  refs.startQuizButton.disabled = true;
  try {
    const payload = await api("/api/aptitude/start", { method: "POST", body: JSON.stringify({}) });
    state.attempt = payload.attempt;
    state.meta = payload.meta;
    state.currentIndex = 0;
    state.responses = {};
    state.submitting = false;
    refs.quizIntro.classList.add("hidden");
    refs.resultsSection.classList.add("hidden");
    refs.quizSection.classList.remove("hidden");
    exitController.setActive(true);
    renderQuestion();
    startTimer(payload.meta.timerSeconds);
    window.scrollTo({ top: 0, behavior: "smooth" });
  } finally {
    refs.startQuizButton.disabled = false;
  }
}

function optionLetter(options, answer) {
  const index = options.indexOf(answer);
  return index >= 0 ? String.fromCharCode(65 + index) : "-";
}

function renderCompanyPerformance(performance) {
  refs.companyResultGrid.innerHTML = Object.entries(performance)
    .map(([company, values]) => `
      <article class="company-performance-card">
        <span>${escapeHtml(company)}</span>
        <strong>${values.correct} / ${values.total}</strong>
      </article>`)
    .join("");
}

function renderReview(review) {
  refs.reviewList.innerHTML = review
    .map((item) => `
      <article class="review-card ${item.correct ? "correct" : "incorrect"}">
        <div class="review-card-header">
          <div>
            <p class="eyebrow">Question ${item.number} · ${escapeHtml(item.company)}</p>
            <h4>${escapeHtml(item.question)}</h4>
          </div>
          <span class="review-verdict">${item.correct ? "Correct" : "Incorrect"}</span>
        </div>
        <div class="review-answer-grid">
          <p><span>Your Answer</span><strong>${optionLetter(item.options, item.yourAnswer)}. ${escapeHtml(item.yourAnswer)}</strong></p>
          <p><span>Correct Answer</span><strong>${optionLetter(item.options, item.correctAnswer)}. ${escapeHtml(item.correctAnswer)}</strong></p>
        </div>
        <div class="review-explanation"><span>Explanation</span><p>${escapeHtml(item.explanation)}</p></div>
      </article>`)
    .join("");
}

function renderResults(result) {
  refs.resultHeadline.textContent = `You scored ${result.score} / ${result.totalQuestions}`;
  refs.resultStatus.textContent = result.passed
    ? "Pass. Your reasoning held up under pressure."
    : "Not passed yet. Use the review below to target the next attempt.";
  refs.resultPercentage.textContent = `${result.percentage}%`;
  refs.resultScoreRing.style.setProperty("--score-angle", `${result.percentage * 3.6}deg`);
  refs.totalQuestionsValue.textContent = result.totalQuestions;
  refs.correctAnswersValue.textContent = result.correctAnswers;
  refs.wrongAnswersValue.textContent = result.wrongAnswers;
  refs.passFailValue.textContent = result.passed ? "Pass" : "Fail";
  renderCompanyPerformance(result.companyPerformance);
  renderReview(result.review);
}

async function submitQuiz(autoSubmitted = false) {
  if (state.submitting || state.exiting || !state.attempt) return;
  state.submitting = true;
  refs.submitQuizButton.disabled = true;
  stopTimer();
  try {
    const payload = await api("/api/aptitude/submit", {
      method: "POST",
      body: JSON.stringify({ attemptId: state.attempt.id, responses: state.responses }),
    });
    if (state.exiting) return;
    exitController.setActive(false);
    refs.quizSection.classList.add("hidden");
    refs.resultsSection.classList.remove("hidden");
    renderResults(payload.result);
    renderStatistics(payload.stats);
    showToast(autoSubmitted ? "Time ended. Your quiz was submitted." : "Quiz submitted successfully.");
    refs.resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
  } finally {
    state.submitting = false;
    refs.submitQuizButton.disabled = false;
  }
}

function handleAsyncError(error) {
  if (error?.name === "AbortError" || state.exiting) return;
  showToast(error.message, "error");
}

async function abandonCurrentAttempt() {
  const attemptId = state.attempt?.id;
  requests.abortAll();
  if (!attemptId) return;
  try {
    await api("/api/aptitude/abandon", {
      method: "POST",
      body: JSON.stringify({ attemptId }),
    }, false);
  } catch (_error) {
    // Local cleanup must still succeed if the best-effort abandonment request fails.
  }
}

function resetActiveQuiz() {
  stopTimer();
  state.attempt = null;
  state.meta = null;
  state.currentIndex = 0;
  state.responses = {};
  state.secondsRemaining = 0;
  state.submitting = false;
  refs.questionText.textContent = "Question text";
  refs.optionList.innerHTML = "";
  refs.questionMap.innerHTML = "";
  refs.quizProgressFill.style.width = "0%";
  refs.questionCounter.textContent = "Question 1 of 10";
  refs.answeredCounter.textContent = "0 answered";
  refs.quizTimer.textContent = "12:00";
  refs.quizSection.classList.add("hidden");
  refs.resultsSection.classList.add("hidden");
  refs.quizIntro.classList.remove("hidden");
}

async function leaveActiveQuiz(destination) {
  if (state.exiting) return;
  state.exiting = true;
  stopTimer();
  await abandonCurrentAttempt();
  resetActiveQuiz();
  exitController.setActive(false);

  if (destination === "dashboard") {
    exitController.allowNavigation();
    window.location.href = "/dashboard";
    return;
  }

  state.exiting = false;
  refs.quizIntro.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderAccuracyList(companyAccuracy) {
  const entries = Object.entries(companyAccuracy || {});
  refs.companyAccuracyList.innerHTML = entries.length
    ? entries.map(([company, values]) => `
        <div class="accuracy-row">
          <div><strong>${escapeHtml(company)}</strong><span>${values.correct}/${values.total} correct</span></div>
          <div class="accuracy-track"><span style="width:${values.accuracy}%"></span></div>
          <strong>${values.accuracy}%</strong>
        </div>`).join("")
    : '<div class="empty-state">Complete a quiz to unlock company accuracy.</div>';
}

function renderCategoryChips(target, items, emptyText) {
  target.innerHTML = items?.length
    ? items.map((item) => `<span class="chip">${escapeHtml(item)}</span>`).join("")
    : `<span class="subtle">${emptyText}</span>`;
}

function renderHistory(history) {
  refs.aptitudeHistoryList.innerHTML = history?.length
    ? history.map((item, index) => `
        <article class="history-card">
          <div class="history-header">
            <div><p class="history-label">Attempt ${history.length - index}</p><h4>${escapeHtml(formatDate(item.date))}</h4></div>
            <div class="history-score-block"><span>Score</span><strong>${item.score} / ${item.totalQuestions}</strong></div>
          </div>
          <div class="history-meta-row">
            <span class="chip">${item.percentage}%</span>
            <span class="chip">${item.passed ? "Pass" : "Fail"}</span>
          </div>
          <details class="history-details">
            <summary>Expand company details</summary>
            <div class="company-performance-grid history-company-grid">
              ${Object.entries(item.companyPerformance || {}).map(([company, values]) => `
                <article class="company-performance-card"><span>${escapeHtml(company)}</span><strong>${values.correct}/${values.total}</strong></article>`).join("")}
            </div>
          </details>
        </article>`).join("")
    : '<article class="history-card empty-state">No aptitude attempts yet. Your completed quizzes will appear here.</article>';
}

function renderStatistics(stats) {
  state.stats = stats;
  refs.attemptsValue.textContent = stats.attempts;
  refs.highestScoreValue.textContent = `${stats.highestScore} / 10`;
  refs.averageScoreValue.textContent = `${stats.averageScore} / 10`;
  refs.accuracyValue.textContent = `${stats.accuracy}%`;
  renderAccuracyList(stats.companyAccuracy);
  renderCategoryChips(refs.strongCategoryList, stats.strongCategories, "No data yet.");
  renderCategoryChips(refs.weakCategoryList, stats.weakCategories, "No data yet.");
  renderHistory(stats.history);
}

async function bootstrap() {
  applyTheme(localStorage.getItem("interview-theme") || "dark");
  const session = await api("/api/auth/session", { method: "GET" });
  if (!session.authenticated) {
    refs.authNotice.classList.remove("hidden");
    return;
  }
  state.user = session.user;
  refs.logoutButton.classList.remove("hidden");
  refs.aptitudeContent.classList.remove("hidden");
  const payload = await api("/api/aptitude/summary", { method: "GET" });
  refs.bankCountLabel.textContent = `${payload.questionBank.totalQuestions} questions ready`;
  renderStatistics(payload.stats);
}

function bindEvents() {
  refs.themeToggle.addEventListener("click", () => applyTheme(refs.body.dataset.theme === "dark" ? "light" : "dark"));
  refs.logoutButton.addEventListener("click", async () => {
    if (exitController.isActive()) {
      state.exiting = true;
      await abandonCurrentAttempt();
      resetActiveQuiz();
      exitController.setActive(false);
    }
    await api("/api/auth/logout", { method: "POST", body: JSON.stringify({}) });
    exitController.allowNavigation();
    window.location.href = "/";
  });
  refs.startQuizButton.addEventListener("click", () => startQuiz().catch(handleAsyncError));
  refs.newQuizButton.addEventListener("click", () => startQuiz().catch(handleAsyncError));
  refs.previousButton.addEventListener("click", () => { state.currentIndex -= 1; renderQuestion(); });
  refs.nextButton.addEventListener("click", () => { state.currentIndex += 1; renderQuestion(); });
  refs.optionList.addEventListener("change", (event) => {
    if (event.target.name !== "aptitudeAnswer") return;
    state.responses[currentQuestion().id] = event.target.value;
    renderQuestion();
  });
  refs.questionMap.addEventListener("click", (event) => {
    const button = event.target.closest("[data-index]");
    if (!button) return;
    state.currentIndex = Number(button.dataset.index);
    renderQuestion();
  });
  refs.submitQuizButton.addEventListener("click", () => submitQuiz(false).catch(handleAsyncError));
  window.addEventListener("pagehide", () => {
    const attemptId = exitController.isActive() ? state.attempt?.id : null;
    if (attemptId) {
      window.fetch("/api/aptitude/abandon", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ attemptId }),
        credentials: "same-origin",
        keepalive: true,
      }).catch(() => {});
    }
    stopTimer();
    requests.abortAll();
  });
}

exitController = createSessionExitController({
  backButton: refs.aptitudeBackButton,
  quitButton: refs.aptitudeQuitButton,
  back: {
    title: "Go Back?",
    message: "Going back will end your current session. Do you want to continue?",
    cancelText: "Stay Here",
    confirmText: "Go Back",
  },
  quit: {
    title: "Quit Aptitude Quiz?",
    message: "Are you sure you want to quit? Your current answers and quiz progress will be discarded.",
    cancelText: "Continue",
    confirmText: "Quit",
  },
  onBack: () => leaveActiveQuiz("setup"),
  onQuit: () => leaveActiveQuiz("dashboard"),
  onError: handleAsyncError,
});

bindEvents();
bootstrap().catch((error) => showToast(error.message, "error"));
