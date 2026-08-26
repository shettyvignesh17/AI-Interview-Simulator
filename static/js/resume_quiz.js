import { drawTrendChart } from "./charts.js";
import { createRequestTracker, createSessionExitController } from "./session_exit.js";

const QUIZ_STATES = Object.freeze({
  NO_RESUME: "NO_RESUME",
  UPLOADING: "UPLOADING",
  ANALYZING_RESUME: "ANALYZING_RESUME",
  ANALYSIS_READY: "ANALYSIS_READY",
  GENERATING_QUIZ: "GENERATING_QUIZ",
  QUIZ_READY: "QUIZ_READY",
  QUIZ_ACTIVE: "QUIZ_ACTIVE",
  QUIZ_TIMEOUT: "QUIZ_TIMEOUT",
  EVALUATING: "EVALUATING",
  QUIZ_COMPLETE: "QUIZ_COMPLETE",
});

const state = {
  mode: QUIZ_STATES.NO_RESUME,
  user: null,
  resumeData: null,
  selectedFile: null,
  session: null,
  currentIndex: 0,
  responses: {},
  timeSpent: {},
  enteredQuestionAt: 0,
  timerId: null,
  deadlineAt: 0,
  warningsShown: new Set(),
  submitting: false,
  result: null,
  stats: null,
  exiting: false,
  timerWarningTimeout: null,
  timeoutDelay: null,
};

const refs = Object.fromEntries(
  Array.from(document.querySelectorAll("[id]")).map((element) => [element.id, element]),
);
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

function formatTime(seconds) {
  const safe = Math.max(0, Math.floor(Number(seconds) || 0));
  return `${Math.floor(safe / 60)}:${String(safe % 60).padStart(2, "0")}`;
}

function formatBytes(bytes) {
  const value = Number(bytes) || 0;
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}

function formatDate(value) {
  return value ? new Date(value).toLocaleString(undefined, { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" }) : "Not available";
}

function showToast(message, tone = "success") {
  refs.toast.textContent = message;
  refs.toast.className = `toast ${tone}`;
  window.clearTimeout(showToast.timeout);
  showToast.timeout = window.setTimeout(() => refs.toast.classList.add("hidden"), 4200);
}

async function api(url, options = {}, tracked = true) {
  const isForm = options.body instanceof FormData;
  let response;
  try {
    response = await requests.fetch(url, {
      credentials: "same-origin",
      headers: isForm ? (options.headers || {}) : { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    }, { tracked });
  } catch (error) {
    if (error?.name === "AbortError") throw error;
    throw new Error("The server could not be reached. Check your connection and try again.");
  }
  let payload = {};
  try { payload = await response.json(); } catch (_error) { payload = {}; }
  if (!response.ok) throw new Error(payload.error || "The request could not be completed.");
  return payload;
}

function applyTheme(theme) {
  document.body.dataset.theme = theme;
  localStorage.setItem("interview-theme", theme);
  const label = theme === "dark" ? "Switch to light theme" : "Switch to dark theme";
  refs.themeToggle.setAttribute("aria-label", label);
  refs.themeToggle.title = label;
  if (state.stats) drawTrendChart(refs.resumeTrendChart, state.stats.trend || []);
}

function setMode(mode) {
  state.mode = mode;
  const active = mode === QUIZ_STATES.QUIZ_ACTIVE;
  refs.landingSection.classList.toggle("hidden", active || mode === QUIZ_STATES.QUIZ_COMPLETE || mode === QUIZ_STATES.EVALUATING || mode === QUIZ_STATES.QUIZ_TIMEOUT);
  refs.analysisSection.classList.toggle("hidden", !state.resumeData || active || [QUIZ_STATES.QUIZ_COMPLETE, QUIZ_STATES.EVALUATING, QUIZ_STATES.QUIZ_TIMEOUT].includes(mode));
  refs.quizReadySection.classList.toggle("hidden", mode !== QUIZ_STATES.QUIZ_READY);
  refs.quizSection.classList.toggle("hidden", !active);
  refs.evaluatingSection.classList.toggle("hidden", mode !== QUIZ_STATES.EVALUATING);
  refs.resultsSection.classList.toggle("hidden", mode !== QUIZ_STATES.QUIZ_COMPLETE);
  refs.historySection.classList.toggle("hidden", active || mode === QUIZ_STATES.EVALUATING || mode === QUIZ_STATES.QUIZ_TIMEOUT);
}

function chooseFile(file) {
  if (!file) return;
  const extension = file.name.toLowerCase().split(".").pop();
  if (!["pdf", "docx"].includes(extension)) {
    showToast("Upload a PDF or DOCX resume.", "error");
    return;
  }
  if (!file.size) {
    showToast("The selected resume is empty.", "error");
    return;
  }
  if (file.size > 8 * 1024 * 1024) {
    showToast("The resume must be no larger than 8 MB.", "error");
    return;
  }
  state.selectedFile = file;
  refs.selectedFileName.textContent = file.name;
  refs.selectedFileMeta.textContent = `${extension.toUpperCase()} · ${formatBytes(file.size)}`;
  refs.selectedFileCard.classList.remove("hidden");
  refs.uploadResumeButton.disabled = false;
}

function clearSelectedFile() {
  state.selectedFile = null;
  refs.resumeFileInput.value = "";
  refs.selectedFileCard.classList.add("hidden");
  refs.uploadResumeButton.disabled = true;
}

function analysisLoadingSteps() {
  const messages = [
    "Extracting technical skills...",
    "Analyzing projects...",
    "Reviewing professional experience...",
    "Preparing source-grounded quiz topics...",
  ];
  let index = 0;
  refs.analysisLoadingText.textContent = messages[index];
  return window.setInterval(() => {
    index = (index + 1) % messages.length;
    refs.analysisLoadingText.textContent = messages[index];
  }, 900);
}

function evidenceItem(title, description, technologies = []) {
  return `
    <article class="resume-evidence-item">
      <strong>${escapeHtml(title)}</strong>
      ${description ? `<p>${escapeHtml(description)}</p>` : ""}
      ${technologies.length ? `<div class="chip-row">${technologies.map((skill) => `<span class="chip">${escapeHtml(skill)}</span>`).join("")}</div>` : ""}
    </article>`;
}

function emptyEvidence(message) {
  return `<article class="resume-evidence-item"><p>${escapeHtml(message)}</p></article>`;
}

function renderAnalysis(data) {
  state.resumeData = data;
  const { resume, analysis, counts } = data;
  refs.uploadedResumeName.textContent = resume.filename;
  refs.uploadedResumeStatus.textContent = resume.status;
  refs.uploadedResumeMeta.textContent = `${formatBytes(resume.fileSize)} · ${formatDate(resume.uploadedAt)}`;
  refs.skillCount.textContent = counts.technicalSkills;
  refs.experienceCount.textContent = counts.professionalExperience;
  refs.projectCount.textContent = counts.projects;
  refs.certificationCount.textContent = counts.certifications;
  refs.technicalSkillList.innerHTML = analysis.technicalSkills?.length
    ? analysis.technicalSkills.map((skill) => `<span class="chip">${escapeHtml(skill)}</span>`).join("")
    : '<span class="subtle">No supported technical skills detected.</span>';
  refs.experienceList.innerHTML = analysis.professionalExperience?.length
    ? analysis.professionalExperience.map((item) => evidenceItem(
      [item.role, item.organization].filter(Boolean).join(" · "),
      [item.duration, item.description].filter(Boolean).join(" · "),
      item.technologies || [],
    )).join("")
    : emptyEvidence("No professional experience section was detected. No experience questions will be invented.");
  refs.projectList.innerHTML = analysis.projects?.length
    ? analysis.projects.map((item) => evidenceItem(item.name, item.description, item.technologies || [])).join("")
    : emptyEvidence("No project section was detected. No project questions will be invented.");
  const extras = [
    ...(analysis.education || []).map((item) => evidenceItem("Education", item)),
    ...(analysis.certifications || []).map((item) => evidenceItem("Certification", item)),
    ...(analysis.research || []).map((item) => evidenceItem("Research", item)),
    ...(analysis.achievements || []).map((item) => evidenceItem("Achievement", item)),
  ];
  if (analysis.tools?.length) extras.unshift(evidenceItem("Tools & Technologies", "Detected toolchain", analysis.tools));
  refs.additionalAnalysis.innerHTML = extras.join("") || emptyEvidence("No additional supported sections were detected.");
  refs.analysisSection.classList.remove("hidden");
}

async function uploadResume(event) {
  event.preventDefault();
  if (!state.selectedFile) return;
  setMode(QUIZ_STATES.UPLOADING);
  refs.analysisLoading.classList.remove("hidden");
  refs.landingSection.classList.add("hidden");
  refs.analysisSection.classList.add("hidden");
  refs.uploadResumeButton.disabled = true;
  const loadingTimer = analysisLoadingSteps();
  const form = new FormData();
  form.append("resume", state.selectedFile);
  try {
    const payload = await api("/api/resume-quiz/resume", { method: "POST", body: form });
    renderAnalysis({ resume: payload.resume, analysis: payload.analysis, counts: payload.counts });
    clearSelectedFile();
    setMode(QUIZ_STATES.ANALYSIS_READY);
    showToast("Resume analyzed successfully. Review the detected evidence before generating your quiz.");
    refs.analysisSection.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    setMode(state.resumeData ? QUIZ_STATES.ANALYSIS_READY : QUIZ_STATES.NO_RESUME);
    refs.landingSection.classList.remove("hidden");
    showToast(error.message, "error");
  } finally {
    window.clearInterval(loadingTimer);
    refs.analysisLoading.classList.add("hidden");
    refs.uploadResumeButton.disabled = !state.selectedFile;
  }
}

async function removeResume() {
  if (!state.resumeData) return;
  const confirmed = window.confirm("Remove this resume and all Resume Quiz attempts connected to it?");
  if (!confirmed) return;
  await api(`/api/resume-quiz/resume/${state.resumeData.resume.id}`, { method: "DELETE" });
  state.resumeData = null;
  state.session = null;
  state.result = null;
  setMode(QUIZ_STATES.NO_RESUME);
  refs.analysisSection.classList.add("hidden");
  showToast("Resume and connected quiz data removed.");
  await loadSummary();
}

async function generateQuiz() {
  if (!state.resumeData || state.mode === QUIZ_STATES.GENERATING_QUIZ) return;
  setMode(QUIZ_STATES.GENERATING_QUIZ);
  refs.generateQuizButton.disabled = true;
  refs.generateQuizButton.textContent = "Generating Quiz...";
  try {
    const payload = await api("/api/resume-quiz/generate", {
      method: "POST",
      body: JSON.stringify({ resumeId: state.resumeData.resume.id }),
    });
    state.session = payload.session;
    const categories = Object.entries(payload.distribution.categories).map(([name, count]) => `${name}: ${count}`).join(" · ");
    const difficulties = Object.entries(payload.distribution.difficulties).map(([name, count]) => `${name}: ${count}`).join(" · ");
    refs.quizDistributionText.textContent = `${categories}. Difficulty mix: ${difficulties}. The timer starts only when you press Start.`;
    setMode(QUIZ_STATES.QUIZ_READY);
    refs.quizReadySection.scrollIntoView({ behavior: "smooth", block: "center" });
  } catch (error) {
    setMode(QUIZ_STATES.ANALYSIS_READY);
    showToast(error.message, "error");
  } finally {
    refs.generateQuizButton.disabled = false;
    refs.generateQuizButton.textContent = "Generate Resume Quiz";
  }
}

function currentQuestion() {
  return state.session?.questions?.[state.currentIndex];
}

function answeredCount() {
  return Object.values(state.responses).filter(Boolean).length;
}

function accrueQuestionTime() {
  const question = currentQuestion();
  if (!question || !state.enteredQuestionAt) return;
  const elapsed = Math.max(0, Math.round((Date.now() - state.enteredQuestionAt) / 1000));
  state.timeSpent[question.id] = (state.timeSpent[question.id] || 0) + elapsed;
  state.enteredQuestionAt = Date.now();
}

function renderQuestionMap() {
  refs.resumeQuestionMap.innerHTML = state.session.questions.map((question, index) => {
    const classes = ["question-map-button"];
    if (index === state.currentIndex) classes.push("active");
    if (state.responses[question.id]) classes.push("answered");
    return `<button class="${classes.join(" ")}" type="button" data-index="${index}">${index + 1}</button>`;
  }).join("");
}

function renderQuestion() {
  const question = currentQuestion();
  if (!question) return;
  const selected = state.responses[question.id] || "";
  const total = state.session.questions.length;
  refs.quizCategoryChip.textContent = question.category;
  refs.quizTopicChip.textContent = question.topic;
  refs.quizDifficultyChip.textContent = question.difficulty;
  refs.resumeQuestionCounter.textContent = `Question ${state.currentIndex + 1} of ${total}`;
  refs.resumeAnsweredCounter.textContent = `${answeredCount()} answered`;
  refs.resumeProgressFill.style.width = `${((state.currentIndex + 1) / total) * 100}%`;
  refs.resumeQuestionText.textContent = question.question;
  refs.resumeOptionList.innerHTML = question.options.map((option, index) => `
    <label class="quiz-option ${option === selected ? "selected" : ""}">
      <input type="radio" name="resumeAnswer" value="${escapeHtml(option)}" ${option === selected ? "checked" : ""} />
      <span class="option-letter">${String.fromCharCode(65 + index)}</span><span>${escapeHtml(option)}</span>
    </label>`).join("");
  refs.resumePreviousButton.disabled = state.currentIndex === 0;
  refs.resumeNextButton.classList.toggle("hidden", state.currentIndex === total - 1);
  refs.resumeSubmitButton.classList.toggle("hidden", state.currentIndex !== total - 1);
  renderQuestionMap();
  state.enteredQuestionAt = Date.now();
}

function stopTimer() {
  window.clearInterval(state.timerId);
  state.timerId = null;
}

function showTimerWarning(seconds) {
  if (state.warningsShown.has(seconds)) return;
  state.warningsShown.add(seconds);
  const message = seconds === 300 ? "5 minutes remaining" : seconds === 60 ? "1 minute remaining" : "30 seconds remaining";
  refs.timerWarning.textContent = `${seconds <= 60 ? "Warning: " : ""}${message}`;
  refs.timerWarning.classList.remove("hidden");
  window.clearTimeout(state.timerWarningTimeout);
  state.timerWarningTimeout = window.setTimeout(() => refs.timerWarning.classList.add("hidden"), 4500);
}

function startTimer(remainingSeconds) {
  stopTimer();
  state.deadlineAt = Date.now() + Math.max(0, Number(remainingSeconds)) * 1000;
  state.warningsShown = new Set();
  const tick = () => {
    const remaining = Math.max(0, Math.ceil((state.deadlineAt - Date.now()) / 1000));
    refs.resumeQuizTimer.textContent = formatTime(remaining);
    refs.resumeQuizClock.classList.toggle("warning", remaining <= 60);
    if ([300, 60, 30].includes(remaining)) showTimerWarning(remaining);
    if (remaining <= 0) {
      stopTimer();
      timeoutQuiz().catch(handleAsyncError);
    }
  };
  tick();
  state.timerId = window.setInterval(tick, 250);
}

async function beginQuiz(sessionPayload = null) {
  let session = sessionPayload;
  if (!session) {
    const payload = await api("/api/resume-quiz/start", {
      method: "POST", body: JSON.stringify({ sessionId: state.session.id }),
    });
    session = payload.session;
  }
  state.session = session;
  state.currentIndex = 0;
  state.responses = Object.fromEntries(
    Object.entries(session.responses || {}).map(([questionId, value]) => [questionId, value.selectedAnswer]),
  );
  state.timeSpent = Object.fromEntries(
    Object.entries(session.responses || {}).map(([questionId, value]) => [questionId, value.timeSpent || 0]),
  );
  state.submitting = false;
  state.exiting = false;
  setMode(QUIZ_STATES.QUIZ_ACTIVE);
  exitController.setActive(true);
  renderQuestion();
  startTimer(session.remainingSeconds);
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function selectAnswer(question, answer) {
  if (state.exiting) return;
  accrueQuestionTime();
  state.responses[question.id] = answer;
  renderQuestion();
  const payload = await api("/api/resume-quiz/answer", {
    method: "PATCH",
    body: JSON.stringify({
      sessionId: state.session.id, questionId: question.id, selectedAnswer: answer,
      timeSpent: state.timeSpent[question.id] || 0,
    }),
  });
  if (state.exiting) return;
  if (payload.timedOut) {
    state.result = payload.result;
    await showResults(payload.result);
  }
}

function navigateTo(index) {
  if (index < 0 || index >= state.session.questions.length || index === state.currentIndex) return;
  accrueQuestionTime();
  state.currentIndex = index;
  renderQuestion();
}

function requestSubmission() {
  if (state.submitting) return;
  accrueQuestionTime();
  const unanswered = state.session.questions.length - answeredCount();
  refs.submitDialogTitle.textContent = unanswered ? `${unanswered} unanswered question${unanswered === 1 ? "" : "s"}` : "All questions answered";
  refs.submitDialogText.textContent = unanswered
    ? `You have ${unanswered} unanswered question${unanswered === 1 ? "" : "s"}. Submit anyway?`
    : "Submit your answers for evaluation? You cannot change them afterward.";
  refs.submitAnywayButton.textContent = unanswered ? "Submit Anyway" : "Submit Quiz";
  refs.submitDialog.showModal();
}

async function timeoutQuiz() {
  if (state.submitting || state.exiting || state.mode !== QUIZ_STATES.QUIZ_ACTIVE) return;
  accrueQuestionTime();
  setMode(QUIZ_STATES.QUIZ_TIMEOUT);
  refs.timeoutOverlay.classList.remove("hidden");
  await new Promise((resolve) => {
    state.timeoutDelay = window.setTimeout(resolve, 1500);
  });
  state.timeoutDelay = null;
  if (state.exiting) return;
  refs.timeoutOverlay.classList.add("hidden");
  await submitQuiz(true);
}

async function submitQuiz(timedOut = false) {
  if (state.submitting || state.exiting || !state.session) return;
  state.submitting = true;
  stopTimer();
  setMode(QUIZ_STATES.EVALUATING);
  refs.evaluationMessage.textContent = timedOut ? "Time ended. Evaluating submitted answers..." : "Calculating source-linked analytics...";
  try {
    const payload = await api("/api/resume-quiz/submit", {
      method: "POST",
      body: JSON.stringify({ sessionId: state.session.id, responses: state.responses, timeSpent: state.timeSpent }),
    });
    if (state.exiting) return;
    state.result = payload.result;
    state.stats = payload.stats;
    renderStatistics(payload.stats);
    await showResults(payload.result);
    showToast(timedOut ? "Time ended. Your available answers were evaluated." : "Resume Quiz submitted successfully.");
  } catch (error) {
    if (error?.name === "AbortError" || state.exiting) return;
    state.submitting = false;
    showToast(error.message, "error");
    try {
      const recovery = await api(`/api/resume-quiz/session/${state.session.id}`, { method: "GET" });
      if (recovery.result) await showResults(recovery.result);
      else {
        setMode(QUIZ_STATES.QUIZ_ACTIVE);
        startTimer(recovery.session.remainingSeconds);
      }
    } catch (_recoveryError) {
      setMode(QUIZ_STATES.QUIZ_ACTIVE);
      refs.resumeSubmitButton.textContent = "Retry Submission";
      refs.resumeSubmitButton.classList.remove("hidden");
    }
  }
}

function accuracyList(target, performance, emptyText) {
  const entries = Object.entries(performance || {});
  target.innerHTML = entries.length ? entries.map(([label, value]) => `
    <div class="accuracy-row">
      <div><strong>${escapeHtml(label)}</strong><span>${value.correct}/${value.total} correct</span></div>
      <div class="accuracy-track"><span style="width:${value.accuracy}%"></span></div><strong>${value.accuracy}%</strong>
    </div>`).join("") : `<div class="empty-state">${escapeHtml(emptyText)}</div>`;
}

function renderChipSet(target, items, emptyText) {
  target.innerHTML = items?.length
    ? items.map((item) => `<span class="chip">${escapeHtml(item)}</span>`).join("")
    : `<span class="subtle">${escapeHtml(emptyText)}</span>`;
}

function optionLetter(options, answer) {
  const index = options.indexOf(answer);
  return index >= 0 ? String.fromCharCode(65 + index) : "-";
}

function renderReview(review) {
  refs.resumeReviewList.innerHTML = review.map((item) => {
    const unanswered = item.status === "Not Answered";
    return `
      <article class="review-card ${item.isCorrect ? "correct" : "incorrect"}">
        <div class="review-card-header"><div><p class="eyebrow">Question ${item.position} · ${escapeHtml(item.category)} · ${escapeHtml(item.difficulty)}</p><h4>${escapeHtml(item.question)}</h4></div><span class="review-verdict">${escapeHtml(item.status)}</span></div>
        <div class="review-answer-grid">
          <p><span>Your Answer</span><strong>${unanswered ? "Not Answered" : `${optionLetter(item.options, item.selectedAnswer)}. ${escapeHtml(item.selectedAnswer)}`}</strong></p>
          <p><span>Correct Answer</span><strong>${optionLetter(item.options, item.correctAnswer)}. ${escapeHtml(item.correctAnswer)}</strong></p>
        </div>
        <div class="review-explanation"><span>Explanation</span><p>${escapeHtml(item.explanation)}</p></div>
        <div class="review-explanation resume-connection"><span>Why This Was Asked</span><p>Your resume lists <strong>${escapeHtml(item.resumeSource.skill)}</strong> in <strong>${escapeHtml(item.resumeSource.item)}</strong>.</p></div>
      </article>`;
  }).join("");
}

async function showResults(result) {
  stopTimer();
  exitController?.setActive(false);
  state.result = result;
  state.submitting = false;
  setMode(QUIZ_STATES.QUIZ_COMPLETE);
  refs.resultHeadline.textContent = `You scored ${result.score} / ${result.totalQuestions}`;
  refs.resultTime.textContent = `${result.timedOut ? "Time expired" : "Submitted"} · Time used ${formatTime(result.timeUsedSeconds)} / 10:00`;
  refs.readinessScore.textContent = Math.round(result.readiness.score);
  refs.readinessLabel.textContent = result.readiness.label;
  refs.resultPercentage.textContent = `${result.percentage}%`;
  refs.resultCorrect.textContent = `${result.correctAnswers} / ${result.totalQuestions}`;
  refs.resultAttempted.textContent = `${result.questionsAttempted} / ${result.totalQuestions}`;
  refs.resultAverageTime.textContent = `${result.analytics.averageTimePerQuestion || 0} sec`;
  accuracyList(refs.categoryPerformance, result.analytics.categoryPerformance, "No category results available.");
  accuracyList(refs.skillPerformance, result.analytics.technicalSkillsPerformance, "No technical skill results available.");
  accuracyList(refs.projectPerformance, result.analytics.projectKnowledge, "This resume did not produce project-linked questions.");
  accuracyList(refs.experiencePerformance, result.analytics.experienceKnowledge, "This resume did not produce experience-linked questions.");
  renderChipSet(refs.strongAreaList, result.analytics.strongAreas, "No strong area signal yet.");
  renderChipSet(refs.weakAreaList, result.analytics.areasToImprove, "No major gaps detected.");
  refs.resumePracticeLinks.innerHTML = result.analytics.recommendedTopics?.length
    ? result.analytics.recommendedTopics.map((topic) => `<a href="/learning?search=${encodeURIComponent(topic)}">${escapeHtml(topic)} <span>Practice Topic</span></a>`).join("")
    : '<a href="/learning">Explore Interview Learning <span>Open Library</span></a>';
  refs.riskAreaList.innerHTML = result.analytics.riskAreas?.length
    ? result.analytics.riskAreas.map((risk) => `<article class="resume-risk-card"><strong>${escapeHtml(risk.topic)}</strong><p>${escapeHtml(risk.message)}</p><p><b>Recommended:</b> ${escapeHtml(risk.recommendation)}</p></article>`).join("")
    : '<div class="empty-state">No incorrect resume-linked concept signals were detected in this attempt.</div>';
  renderReview(result.review || []);
  refs.resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
  loadSummary(false).catch(() => {});
}

function handleAsyncError(error) {
  if (error?.name === "AbortError" || state.exiting) return;
  showToast(error.message, "error");
}

async function discardActiveResumeQuiz() {
  const sessionId = state.session?.id;
  requests.abortAll();
  if (!sessionId) return;
  try {
    await api(`/api/resume-quiz/session/${sessionId}`, { method: "DELETE" }, false);
  } catch (_error) {
    // The resume remains stored; only this temporary attempt is discarded best effort.
  }
}

function resetActiveResumeQuiz({ preserveResume = true } = {}) {
  stopTimer();
  window.clearTimeout(state.timerWarningTimeout);
  window.clearTimeout(state.timeoutDelay);
  state.timerWarningTimeout = null;
  state.timeoutDelay = null;
  if (refs.submitDialog.open) refs.submitDialog.close();
  refs.timeoutOverlay.classList.add("hidden");
  refs.timerWarning.classList.add("hidden");
  refs.resumeQuestionText.textContent = "Question text";
  refs.resumeOptionList.innerHTML = "";
  refs.resumeQuestionMap.innerHTML = "";
  refs.resumeProgressFill.style.width = "0%";
  refs.resumeQuestionCounter.textContent = "Question 1 of 10";
  refs.resumeAnsweredCounter.textContent = "0 answered";
  refs.resumeQuizTimer.textContent = "10:00";
  state.session = null;
  state.currentIndex = 0;
  state.responses = {};
  state.timeSpent = {};
  state.enteredQuestionAt = 0;
  state.deadlineAt = 0;
  state.warningsShown = new Set();
  state.submitting = false;
  state.result = null;
  if (!preserveResume) state.resumeData = null;
  setMode(preserveResume && state.resumeData ? QUIZ_STATES.ANALYSIS_READY : QUIZ_STATES.NO_RESUME);
}

async function leaveActiveResumeQuiz(destination) {
  if (state.exiting) return;
  state.exiting = true;
  stopTimer();
  await discardActiveResumeQuiz();
  resetActiveResumeQuiz({ preserveResume: destination !== "dashboard" });
  exitController.setActive(false);

  if (destination === "dashboard") {
    exitController.allowNavigation();
    window.location.href = "/dashboard";
    return;
  }

  state.exiting = false;
  const target = state.resumeData ? refs.analysisSection : refs.landingSection;
  target.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderHistory(history) {
  refs.resumeHistoryList.innerHTML = history?.length ? history.map((item, index) => `
    <article class="history-card">
      <div class="history-header"><div><p class="history-label">Attempt ${history.length - index}</p><h4>${escapeHtml(formatDate(item.date))}</h4></div><div class="history-score-block"><span>Score</span><strong>${item.score} / 10</strong></div></div>
      <div class="history-meta-row"><span class="chip">${item.percentage}%</span><span class="chip">${formatTime(item.timeUsedSeconds)}</span>${item.timedOut ? '<span class="chip">Timed out</span>' : ""}</div>
      <button class="ghost-button resume-history-result" type="button" data-session-id="${item.sessionId}">View Detailed Result</button>
    </article>`).join("") : '<article class="history-card empty-state">No Resume Quiz attempts yet.</article>';
}

function renderStatistics(stats) {
  state.stats = stats;
  refs.resumeAttemptCount.textContent = `${stats.attempts} attempt${stats.attempts === 1 ? "" : "s"}`;
  renderHistory(stats.history || []);
  window.requestAnimationFrame(() => drawTrendChart(refs.resumeTrendChart, stats.trend || []));
}

async function loadSummary(renderResume = true) {
  const payload = await api("/api/resume-quiz/summary", { method: "GET" });
  renderStatistics(payload.stats);
  if (renderResume && payload.latestResume) {
    renderAnalysis(payload.latestResume);
    setMode(QUIZ_STATES.ANALYSIS_READY);
  } else if (renderResume && !payload.latestResume) {
    setMode(QUIZ_STATES.NO_RESUME);
  }
  if (renderResume && payload.openSession) {
    state.session = payload.openSession;
    if (payload.openSession.status === "ready") {
      refs.quizDistributionText.textContent = "Your previously generated ten-question quiz is ready. The timer begins when you start.";
      setMode(QUIZ_STATES.QUIZ_READY);
    } else if (payload.openSession.status === "active") {
      const sessionPayload = await api(`/api/resume-quiz/session/${payload.openSession.id}`, { method: "GET" });
      if (sessionPayload.result) await showResults(sessionPayload.result);
      else await beginQuiz(sessionPayload.session);
    }
  }
}

async function retakeQuiz() {
  setMode(QUIZ_STATES.ANALYSIS_READY);
  await generateQuiz();
}

function bindEvents() {
  refs.themeToggle.addEventListener("click", () => applyTheme(document.body.dataset.theme === "dark" ? "light" : "dark"));
  refs.logoutButton.addEventListener("click", async () => {
    if (exitController.isActive()) {
      state.exiting = true;
      await discardActiveResumeQuiz();
      resetActiveResumeQuiz({ preserveResume: false });
      exitController.setActive(false);
    }
    await api("/api/auth/logout", { method: "POST", body: "{}" });
    exitController.allowNavigation();
    window.location.href = "/";
  });
  refs.resumeFileInput.addEventListener("change", () => chooseFile(refs.resumeFileInput.files[0]));
  refs.resumeDropZone.addEventListener("dragover", (event) => { event.preventDefault(); refs.resumeDropZone.classList.add("dragging"); });
  refs.resumeDropZone.addEventListener("dragleave", () => refs.resumeDropZone.classList.remove("dragging"));
  refs.resumeDropZone.addEventListener("drop", (event) => {
    event.preventDefault(); refs.resumeDropZone.classList.remove("dragging"); chooseFile(event.dataTransfer.files[0]);
  });
  refs.clearSelectedFileButton.addEventListener("click", clearSelectedFile);
  refs.resumeUploadForm.addEventListener("submit", uploadResume);
  refs.replaceResumeButton.addEventListener("click", () => { refs.resumeFileInput.click(); refs.landingSection.classList.remove("hidden"); refs.landingSection.scrollIntoView({ behavior: "smooth" }); });
  refs.removeResumeButton.addEventListener("click", () => removeResume().catch(handleAsyncError));
  refs.generateQuizButton.addEventListener("click", () => generateQuiz().catch(handleAsyncError));
  refs.startResumeQuizButton.addEventListener("click", () => beginQuiz().catch(handleAsyncError));
  refs.resumePreviousButton.addEventListener("click", () => navigateTo(state.currentIndex - 1));
  refs.resumeNextButton.addEventListener("click", () => navigateTo(state.currentIndex + 1));
  refs.resumeQuestionMap.addEventListener("click", (event) => {
    const button = event.target.closest("[data-index]"); if (button) navigateTo(Number(button.dataset.index));
  });
  refs.resumeOptionList.addEventListener("change", (event) => {
    if (event.target.name !== "resumeAnswer" || state.mode !== QUIZ_STATES.QUIZ_ACTIVE) return;
    selectAnswer(currentQuestion(), event.target.value).catch(handleAsyncError);
  });
  refs.resumeSubmitButton.addEventListener("click", requestSubmission);
  refs.continueQuizButton.addEventListener("click", () => refs.submitDialog.close());
  refs.submitAnywayButton.addEventListener("click", () => {
    refs.submitDialog.close(); submitQuiz(false).catch(handleAsyncError);
  });
  refs.retakeQuizButton.addEventListener("click", () => retakeQuiz().catch(handleAsyncError));
  refs.uploadDifferentButton.addEventListener("click", () => { setMode(QUIZ_STATES.ANALYSIS_READY); refs.resumeFileInput.click(); window.scrollTo({ top: 0, behavior: "smooth" }); });
  refs.resumeHistoryList.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-session-id]");
    if (!button) return;
    try {
      const payload = await api(`/api/resume-quiz/result/${button.dataset.sessionId}`, { method: "GET" });
      await showResults(payload.result);
    } catch (error) { showToast(error.message, "error"); }
  });
  window.addEventListener("pagehide", () => {
    const sessionId = exitController.isActive() ? state.session?.id : null;
    if (sessionId) {
      window.fetch(`/api/resume-quiz/session/${sessionId}`, {
        method: "DELETE",
        credentials: "same-origin",
        keepalive: true,
      }).catch(() => {});
    }
    stopTimer();
    requests.abortAll();
  });
}

async function bootstrap() {
  applyTheme(localStorage.getItem("interview-theme") || "dark");
  bindEvents();
  const session = await api("/api/auth/session", { method: "GET" });
  if (!session.authenticated) {
    refs.authNotice.classList.remove("hidden");
    return;
  }
  state.user = session.user;
  refs.logoutButton.classList.remove("hidden");
  refs.resumeQuizContent.classList.remove("hidden");
  await loadSummary();
}

exitController = createSessionExitController({
  backButton: refs.resumeQuizBackButton,
  quitButton: refs.resumeQuizQuitButton,
  back: {
    title: "Go Back?",
    message: "Going back will end your current session. Your analyzed resume will remain available.",
    cancelText: "Stay Here",
    confirmText: "Go Back",
  },
  quit: {
    title: "Quit Resume Quiz?",
    message: "Are you sure you want to quit? Your current resume quiz progress will be discarded.",
    cancelText: "Continue",
    confirmText: "Quit",
  },
  onBack: () => leaveActiveResumeQuiz("setup"),
  onQuit: () => leaveActiveResumeQuiz("dashboard"),
  onError: handleAsyncError,
});

bootstrap().catch(handleAsyncError);
