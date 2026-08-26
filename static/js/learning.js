const state = {
  user: null,
  overview: null,
  metadata: { companies: [], topics: [], topicsByType: {}, categories: [], dailyGoals: [5, 10, 20, 30] },
  questions: [],
  pagination: { page: 1, total: 0, totalPages: 1, from: 0, to: 0 },
  view: "overview",
  filters: {
    search: "", type: "all", difficulty: "all", company: "all", topic: "all",
    status: "all", frequency: "all", sort: "recommended", page: 1,
  },
  openAnswers: new Set(),
  loading: false,
  studyIndex: 0,
  studyRevealed: false,
  studyMode: "study",
};

const ids = [
  "authNotice", "learningContent", "logoutButton", "themeToggle", "questionSearch", "clearSearchButton",
  "learningNav", "overviewView", "companiesView", "topicsView", "progressView", "catalogView",
  "sectionCards", "dailyGoalSelect", "dailyGoalCompleted", "dailyGoalTarget", "dailyGoalFill",
  "questionOfDayCard", "continueCard", "recommendedList", "recentList", "companyCardGrid",
  "targetCompanyList", "saveTargetsButton", "topicCardGrid", "progressViewed", "progressLearned",
  "progressBookmarked", "progressRevision", "weakTopicList", "strongTopicList", "mostStudiedList",
  "practiceWeakButton", "filterPanel", "closeFiltersButton", "typeFilter", "difficultyFilter",
  "companyFilter", "topicFilter", "statusFilter", "frequencyFilter", "sortFilter", "clearFiltersButton",
  "mobileFiltersButton", "studyModeButton", "catalogEyebrow", "catalogTitle", "catalogCount",
  "questionList", "pagination", "studyDialog", "studyModeLabel", "studyCounter", "studyProgressFill",
  "studyQuestionCard", "closeStudyButton", "studyPreviousButton", "studyRevealButton", "studyNextButton",
  "filterBackdrop", "heroLearnedValue", "heroTotalValue", "heroProgressFill", "toast",
];
const refs = Object.fromEntries(ids.map((id) => [id, document.getElementById(id)]));
refs.body = document.body;
refs.quickActions = Array.from(document.querySelectorAll("[data-action]"));

const TYPE_DETAILS = {
  aptitude: { icon: "🧠", title: "Aptitude Questions", description: "Quantitative, logical, verbal, data interpretation, probability, and analytical preparation." },
  coding: { icon: "💻", title: "Coding Questions", description: "Algorithms, data structures, programming, SQL, debugging, and computer science concepts." },
  interview: { icon: "🎯", title: "Interview Questions", description: "Technical, HR, behavioral, project, situational, software engineering, and AI/ML guidance." },
};

function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;").replaceAll("'", "&#39;");
}

function showToast(message, tone = "success") {
  refs.toast.textContent = message;
  refs.toast.className = `toast ${tone}`;
  window.clearTimeout(showToast.timeoutId);
  showToast.timeoutId = window.setTimeout(() => refs.toast.classList.add("hidden"), 2800);
}

async function api(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    credentials: "same-origin", ...options,
  });
  const payload = (response.headers.get("content-type") || "").includes("application/json") ? await response.json() : {};
  if (!response.ok) throw new Error(payload.error || "Something went wrong.");
  return payload;
}

function applyTheme(theme) {
  refs.body.dataset.theme = theme;
  localStorage.setItem("interview-theme", theme);
  const label = theme === "dark" ? "Switch to light theme" : "Switch to dark theme";
  refs.themeToggle.setAttribute("aria-label", label);
  refs.themeToggle.title = label;
}

function labelForType(type) {
  return TYPE_DETAILS[type]?.title || "Question Library";
}

function frequencyIcon(frequency) {
  return { "Very Common": "🔥", Common: "★", Moderate: "◉", Rare: "○" }[frequency] || "◉";
}

function difficultyClass(difficulty) {
  return String(difficulty || "").toLowerCase();
}

function progressPercent(value, total) {
  return total ? Math.min(100, Math.round((value / total) * 100)) : 0;
}

function populateMetadataFilters() {
  refs.companyFilter.innerHTML = '<option value="all">All Companies</option>' + state.metadata.companies
    .map((company) => `<option value="${escapeHtml(company)}">${escapeHtml(company)}</option>`).join("");
  updateTopicOptions(state.filters.type);
}

function updateTopicOptions(type) {
  const topics = state.metadata.topicsByType?.[type] || state.metadata.topics;
  const previous = state.filters.topic;
  refs.topicFilter.innerHTML = '<option value="all">All Topics</option>' + topics
    .map((topic) => `<option value="${escapeHtml(topic)}">${escapeHtml(topic)}</option>`).join("");
  if (topics.includes(previous)) refs.topicFilter.value = previous;
  else state.filters.topic = "all";
}

function syncFilterControls() {
  refs.typeFilter.value = state.filters.type;
  refs.difficultyFilter.value = state.filters.difficulty;
  refs.companyFilter.value = state.filters.company;
  updateTopicOptions(state.filters.type);
  refs.topicFilter.value = state.filters.topic;
  refs.statusFilter.value = state.filters.status;
  refs.frequencyFilter.value = state.filters.frequency;
  refs.sortFilter.value = state.filters.sort;
  refs.questionSearch.value = state.filters.search;
  refs.clearSearchButton.classList.toggle("hidden", !state.filters.search);
}

function sectionCard(type, section) {
  const details = TYPE_DETAILS[type];
  const continued = section.studied > 0;
  return `
    <article class="panel learning-section-card learning-section-${type}">
      <div class="learning-section-icon">${details.icon}</div>
      <p class="eyebrow">${escapeHtml(type)} library</p>
      <h3>${details.title}</h3>
      <p>${details.description}</p>
      <div class="learning-section-stats">
        <span><strong>${section.total}</strong> available</span>
        <span><strong>${section.studied}</strong> learned</span>
        <span><strong>${section.bookmarked}</strong> bookmarked</span>
      </div>
      <div class="section-progress-row"><span>${section.progress}% complete</span><strong>${section.studied} / ${section.total}</strong></div>
      <div class="learning-progress-track"><span style="width:${section.progress}%"></span></div>
      <button class="${continued ? "secondary-button" : "primary-button"}" data-open-type="${type}" type="button">
        ${continued ? "Continue Learning" : "Start Learning"}
      </button>
    </article>`;
}

function compactQuestion(item) {
  return `
    <button class="learning-compact-item" data-open-question="${item.questionId}" type="button">
      <span class="difficulty-dot ${difficultyClass(item.difficulty)}"></span>
      <span><strong>${escapeHtml(item.question)}</strong><small>${escapeHtml(item.company)} · ${escapeHtml(item.topic)}</small></span>
      <span class="compact-arrow">→</span>
    </button>`;
}

function featureQuestion(item, kind) {
  if (!item) {
    return `<p class="eyebrow">${kind}</p><h3>No learning trail yet</h3><p class="subtle">Open a question to build your personalized path.</p>`;
  }
  return `
    <p class="eyebrow">${kind}</p>
    <span class="learning-feature-company">${escapeHtml(item.companyLabel)}</span>
    <h3>${escapeHtml(item.question)}</h3>
    <div class="chip-row"><span class="chip">${escapeHtml(item.topic)}</span><span class="difficulty-badge ${difficultyClass(item.difficulty)}">${escapeHtml(item.difficulty)}</span></div>
    <button class="secondary-button" data-open-question="${item.questionId}" type="button">${kind === "Continue Where You Left Off" ? "Continue Learning" : "View Answer"}</button>`;
}

function renderOverview() {
  const overview = state.overview;
  if (!overview) return;
  refs.sectionCards.innerHTML = Object.entries(overview.sections).map(([type, section]) => sectionCard(type, section)).join("");
  refs.heroLearnedValue.textContent = overview.totals.learned;
  refs.heroTotalValue.textContent = overview.totals.questions.toLocaleString();
  refs.heroProgressFill.style.width = `${progressPercent(overview.totals.learned, overview.totals.questions)}%`;
  refs.dailyGoalSelect.value = String(overview.dailyGoal.target);
  refs.dailyGoalCompleted.textContent = overview.dailyGoal.completed;
  refs.dailyGoalTarget.textContent = overview.dailyGoal.target;
  refs.dailyGoalFill.style.width = `${progressPercent(overview.dailyGoal.completed, overview.dailyGoal.target)}%`;
  refs.questionOfDayCard.innerHTML = featureQuestion(overview.questionOfDay, "Question Of The Day");
  refs.continueCard.innerHTML = featureQuestion(overview.continueQuestion, "Continue Where You Left Off");
  refs.recommendedList.innerHTML = overview.recommended.length ? overview.recommended.map(compactQuestion).join("") : '<div class="empty-state">Study a few questions to personalize recommendations.</div>';
  refs.recentList.innerHTML = overview.recentlyViewed.length ? overview.recentlyViewed.map(compactQuestion).join("") : '<div class="empty-state">Questions you open will appear here.</div>';
  renderProgress();
  renderCompanyAndTopicViews();
}

function signalItems(items, weak = false) {
  return items?.length
    ? items.map((topic, index) => `<button class="learning-signal-item" data-topic="${escapeHtml(topic)}" type="button"><span>${index + 1}</span><strong>${escapeHtml(topic)}</strong>${weak ? "<small>Practice</small>" : ""}</button>`).join("")
    : '<div class="empty-state">Rate confidence or add questions to revision to generate topic signals.</div>';
}

function renderProgress() {
  if (!state.overview) return;
  const totals = state.overview.totals;
  refs.progressViewed.textContent = totals.viewed;
  refs.progressLearned.textContent = totals.learned;
  refs.progressBookmarked.textContent = totals.bookmarked;
  refs.progressRevision.textContent = totals.revision;
  refs.weakTopicList.innerHTML = signalItems(state.overview.weakTopics, true);
  refs.strongTopicList.innerHTML = signalItems(state.overview.strongTopics);
  refs.mostStudiedList.innerHTML = state.overview.mostStudiedTopics.length
    ? state.overview.mostStudiedTopics.map((topic) => `<button class="chip topic-chip-button" data-topic="${escapeHtml(topic)}" type="button">${escapeHtml(topic)}</button>`).join("")
    : '<span class="subtle">Your most studied topics will appear here.</span>';
  refs.practiceWeakButton.disabled = !state.overview.weakTopics.length;
}

function renderCompanyAndTopicViews() {
  const targets = new Set(state.overview?.preferences?.targetCompanies || []);
  refs.companyCardGrid.innerHTML = state.metadata.companies.map((company) => {
    const progress = state.overview?.companyProgress?.[company] || { studied: 0, total: 0, progress: 0 };
    return `
    <button class="learning-company-card" data-company="${escapeHtml(company)}" type="button">
      <span>${escapeHtml(company.slice(0, 2).toUpperCase())}</span><strong>${escapeHtml(company)}</strong>
      <small>${progress.studied} / ${progress.total} questions studied · ${progress.progress}%</small>
      <div class="learning-progress-track"><i style="width:${progress.progress}%"></i></div>
    </button>`;
  }).join("");
  refs.targetCompanyList.innerHTML = state.metadata.companies.slice(0, 12).map((company) => `
    <label class="target-company-choice"><input type="checkbox" value="${escapeHtml(company)}" ${targets.has(company) ? "checked" : ""} /><span>${escapeHtml(company)}</span></label>`).join("");
  refs.topicCardGrid.innerHTML = state.metadata.topics.map((topic) => `
    <button class="learning-topic-card" data-topic="${escapeHtml(topic)}" type="button"><span>▦</span><strong>${escapeHtml(topic)}</strong><small>Open topic questions</small></button>`).join("");
}

function setView(view) {
  state.view = view;
  [refs.overviewView, refs.companiesView, refs.topicsView, refs.progressView, refs.catalogView].forEach((element) => element.classList.add("hidden"));
  const directViews = { overview: refs.overviewView, companies: refs.companiesView, topics: refs.topicsView, progress: refs.progressView };
  (directViews[view] || refs.catalogView).classList.remove("hidden");
  Array.from(refs.learningNav.querySelectorAll("[data-view]")).forEach((button) => {
    button.classList.toggle("active", button.dataset.view === view || (["bookmarked", "revision", "aptitude", "coding", "interview", "flashcards"].includes(view) && button.dataset.view === view));
  });
}

function resetFilters() {
  Object.assign(state.filters, { search: "", type: "all", difficulty: "all", company: "all", topic: "all", status: "all", frequency: "all", sort: "recommended", page: 1 });
  syncFilterControls();
}

async function openCatalog(view = "catalog", overrides = {}) {
  if (["aptitude", "coding", "interview"].includes(view)) {
    resetFilters();
    state.filters.type = view;
  } else if (view === "bookmarked" || view === "revision") {
    resetFilters();
    state.filters.status = view;
  } else if (view === "flashcards") {
    resetFilters();
    state.filters.sort = "recommended";
  }
  Object.assign(state.filters, overrides, { page: overrides.page || 1 });
  syncFilterControls();
  setView(view);
  await loadQuestions();
  if (view === "flashcards") openStudyMode("flashcard");
}

function queryString() {
  const params = new URLSearchParams();
  Object.entries(state.filters).forEach(([key, value]) => {
    if (value !== "" && value !== "all") params.set(key, value);
  });
  params.set("page", state.filters.page);
  return params.toString();
}

function renderSkeletons() {
  refs.questionList.innerHTML = Array.from({ length: 4 }, () => '<article class="panel learning-question-card skeleton-card"><span></span><span></span><span></span><span></span></article>').join("");
}

async function loadQuestions() {
  if (state.loading) return;
  state.loading = true;
  renderSkeletons();
  try {
    const payload = await api(`/api/learning/questions?${queryString()}`, { method: "GET" });
    state.questions = payload.questions;
    state.pagination = payload.pagination;
    state.filters.page = payload.pagination.page;
    renderQuestions();
    renderPagination();
    renderCatalogHeading();
  } finally {
    state.loading = false;
  }
}

function renderCatalogHeading() {
  let title = "All Learning Questions";
  if (state.filters.type !== "all") title = labelForType(state.filters.type);
  if (state.filters.company !== "all") title = `Prepare for ${state.filters.company}`;
  if (state.filters.topic !== "all") title = state.filters.topic;
  if (state.filters.status === "bookmarked") title = "Bookmarked Questions";
  if (state.filters.status === "revision") title = "My Revision Questions";
  refs.catalogTitle.textContent = title;
  refs.catalogEyebrow.textContent = state.filters.search ? `Search: ${state.filters.search}` : "Question Library";
  refs.catalogCount.textContent = state.pagination.total
    ? `Showing questions ${state.pagination.from}–${state.pagination.to} of ${state.pagination.total}`
    : "No questions match the current filters.";
}

function actionButton(action, active, activeText, inactiveText) {
  return `<button class="question-action ${active ? "active" : ""}" data-question-action="${action}" type="button">${active ? activeText : inactiveText}</button>`;
}

function answerPanel(question) {
  const coding = question.type === "coding";
  return `
    <div class="learning-answer-panel">
      <section><p class="answer-section-label">✓ Answer</p><p>${escapeHtml(question.answer)}</p></section>
      <section><p class="answer-section-label">Detailed Explanation</p><p>${escapeHtml(question.detailedExplanation)}</p></section>
      ${question.approach ? `<section><p class="answer-section-label">Approach</p><p>${escapeHtml(question.approach)}</p></section>` : ""}
      ${coding && question.code ? `<section><p class="answer-section-label">Code</p><pre><code>${escapeHtml(question.code)}</code></pre></section>` : ""}
      ${question.timeComplexity ? `<section class="complexity-row"><p><span>Time Complexity</span><strong>${escapeHtml(question.timeComplexity)}</strong></p><p><span>Space Complexity</span><strong>${escapeHtml(question.spaceComplexity)}</strong></p></section>` : ""}
      ${question.example ? `<section><p class="answer-section-label">Example</p><div class="learning-example">${escapeHtml(question.example)}</div></section>` : ""}
      <section><p class="answer-section-label">Common Mistakes</p><p>${escapeHtml(question.commonMistakes)}</p></section>
      <section class="interview-tip-box"><p class="answer-section-label">Interview Tip</p><p>${escapeHtml(question.interviewTip)}</p></section>
      <section><p class="answer-section-label">Personal Notes</p><textarea class="learning-notes-input" rows="3" placeholder="Add your own memory aid, example, or follow-up...">${escapeHtml(question.notes)}</textarea><button class="ghost-button save-note-button" data-question-action="save-note" type="button">Save Notes</button></section>
      <section><p class="answer-section-label">How confident are you?</p><div class="confidence-row"><button class="confidence-button ${question.confidence === "low" ? "active" : ""}" data-confidence="low" type="button">Low</button><button class="confidence-button ${question.confidence === "medium" ? "active" : ""}" data-confidence="medium" type="button">Medium</button><button class="confidence-button ${question.confidence === "high" ? "active" : ""}" data-confidence="high" type="button">High</button></div></section>
      <section><p class="answer-section-label">Similar Questions</p><div class="related-question-list">${(question.relatedQuestions || []).map((item) => `<button data-open-question="${item.questionId}" type="button"><span>${escapeHtml(item.topic)}</span>${escapeHtml(item.question)}</button>`).join("") || '<span class="subtle">Open the detail again to refresh related questions.</span>'}</div></section>
    </div>`;
}

function questionCard(question, index) {
  const open = state.openAnswers.has(question.questionId);
  return `
    <article class="panel learning-question-card ${question.studied ? "learned" : ""}" data-question-id="${question.questionId}">
      <header class="learning-question-header">
        <div><p class="eyebrow">${escapeHtml(question.companyLabel)}</p><div class="question-metadata"><span class="difficulty-badge ${difficultyClass(question.difficulty)}">${escapeHtml(question.difficulty)}</span><span>${escapeHtml(question.topic)}</span><span>${frequencyIcon(question.frequency)} ${escapeHtml(question.frequency)}</span><span>${question.estimatedStudyTime} min</span></div></div>
        <span class="question-number">${state.pagination.from + index}</span>
      </header>
      <h3>${escapeHtml(question.question)}</h3>
      <div class="chip-row">${question.tags.slice(0, 5).map((tag) => `<span class="chip">${escapeHtml(tag)}</span>`).join("")}</div>
      <div class="learning-question-actions">
        <button class="secondary-button" data-question-action="answer" type="button">${open ? "Hide Answer" : "Show Answer"}</button>
        ${actionButton("bookmark", question.bookmarked, "Bookmarked", "Bookmark")}
        ${actionButton("learned", question.studied, "Learned ✓", "Mark as Learned")}
        ${actionButton("revision", question.revision, "In Revision", "Add to Revision")}
        <button class="question-action" data-question-action="copy" type="button">Copy Question</button>
      </div>
      ${open ? answerPanel(question) : ""}
    </article>`;
}

function renderQuestions() {
  refs.questionList.innerHTML = state.questions.length
    ? state.questions.map(questionCard).join("")
    : `<section class="panel learning-empty-state"><strong>No questions found</strong><p>Try changing your filters or search keywords.</p><button class="secondary-button" data-empty-action="clear" type="button">Clear Filters</button></section>`;
}

function pageNumbers(current, total) {
  const pages = new Set([1, total, current - 2, current - 1, current, current + 1, current + 2]);
  return [...pages].filter((page) => page >= 1 && page <= total).sort((a, b) => a - b);
}

function renderPagination() {
  const { page, totalPages } = state.pagination;
  if (!state.pagination.total) {
    refs.pagination.innerHTML = "";
    refs.pagination.classList.add("hidden");
    return;
  }
  refs.pagination.classList.remove("hidden");
  const pages = pageNumbers(page, totalPages);
  let previousPage = 0;
  const numberButtons = pages.map((number) => {
    const gap = previousPage && number - previousPage > 1 ? '<span class="pagination-gap">…</span>' : "";
    previousPage = number;
    return `${gap}<button class="pagination-button ${number === page ? "active" : ""}" data-page="${number}" type="button">${number}</button>`;
  }).join("");
  refs.pagination.innerHTML = `<button class="pagination-button" data-page="${page - 1}" ${page === 1 ? "disabled" : ""} type="button">Previous</button>${numberButtons}<button class="pagination-button" data-page="${page + 1}" ${page === totalPages ? "disabled" : ""} type="button">Next</button>`;
}

async function showQuestionById(questionId) {
  const payload = await api(`/api/learning/questions/${encodeURIComponent(questionId)}`, { method: "GET" });
  state.questions = [payload.question];
  state.pagination = { page: 1, total: 1, totalPages: 1, from: 1, to: 1 };
  state.openAnswers = new Set([questionId]);
  setView("catalog");
  renderQuestions();
  renderPagination();
  refs.catalogTitle.textContent = payload.question.topic;
  refs.catalogCount.textContent = "Focused question view";
  await patchQuestion(questionId, { viewed: true, section: state.view }, false);
  refs.catalogView.scrollIntoView({ behavior: "smooth", block: "start" });
}

function replaceQuestion(updated) {
  state.questions = state.questions.map((question) => question.questionId === updated.questionId ? updated : question);
}

async function patchQuestion(questionId, changes, rerender = true) {
  const payload = await api(`/api/learning/questions/${encodeURIComponent(questionId)}/progress`, {
    method: "PATCH", body: JSON.stringify(changes),
  });
  replaceQuestion(payload.question);
  state.overview = payload.overview;
  renderOverview();
  if (rerender) renderQuestions();
  return payload.question;
}

async function handleQuestionAction(button) {
  const card = button.closest("[data-question-id]");
  if (!card) return;
  const questionId = card.dataset.questionId;
  const question = state.questions.find((item) => item.questionId === questionId);
  if (!question) return;
  const action = button.dataset.questionAction;
  if (action === "answer") {
    const opening = !state.openAnswers.has(questionId);
    if (opening) {
      state.openAnswers.add(questionId);
      const detail = await api(`/api/learning/questions/${encodeURIComponent(questionId)}`, { method: "GET" });
      replaceQuestion(detail.question);
      await patchQuestion(questionId, { viewed: true, section: state.view }, false);
    } else state.openAnswers.delete(questionId);
    renderQuestions();
  } else if (action === "bookmark") {
    await patchQuestion(questionId, { bookmarked: !question.bookmarked });
    showToast(question.bookmarked ? "Removed from bookmarks." : "Saved to bookmarks.");
  } else if (action === "learned") {
    await patchQuestion(questionId, { studied: !question.studied });
    showToast(question.studied ? "Marked as not studied." : "Marked as learned.");
  } else if (action === "revision") {
    await patchQuestion(questionId, { revision: !question.revision });
    showToast(question.revision ? "Removed from revision." : "Added to revision.");
  } else if (action === "copy") {
    await navigator.clipboard.writeText(question.question);
    showToast("Question copied.");
  } else if (action === "save-note") {
    const notes = card.querySelector(".learning-notes-input").value;
    await patchQuestion(questionId, { notes });
    showToast(notes.trim() ? "Notes saved." : "Notes deleted.");
  }
}

function studyQuestion() {
  return state.questions[state.studyIndex] || null;
}

function renderStudyMode() {
  const question = studyQuestion();
  if (!question) return;
  refs.studyModeLabel.textContent = state.studyMode === "flashcard" ? "Flashcard Mode" : "Study Mode";
  refs.studyCounter.textContent = `Question ${state.studyIndex + 1} of ${state.questions.length}`;
  refs.studyProgressFill.style.width = `${progressPercent(state.studyIndex + 1, state.questions.length)}%`;
  refs.studyPreviousButton.disabled = state.studyIndex === 0;
  refs.studyNextButton.textContent = state.studyIndex === state.questions.length - 1 ? "Finish" : "Next";
  refs.studyRevealButton.textContent = state.studyRevealed ? "Hide Answer" : "Reveal Answer";
  refs.studyQuestionCard.innerHTML = `
    <p class="eyebrow">${escapeHtml(question.companyLabel)}</p>
    <div class="question-metadata"><span class="difficulty-badge ${difficultyClass(question.difficulty)}">${question.difficulty}</span><span>${escapeHtml(question.topic)}</span></div>
    <h2>${escapeHtml(question.question)}</h2>
    ${state.studyRevealed ? `<div class="study-answer"><p class="answer-section-label">Answer</p><p>${escapeHtml(question.answer)}</p><p class="answer-section-label">Why It Matters</p><p>${escapeHtml(question.detailedExplanation)}</p>${question.code ? `<pre><code>${escapeHtml(question.code)}</code></pre>` : ""}</div>` : '<div class="study-answer-placeholder">Recall the answer before revealing it.</div>'}
    <div class="study-card-actions">
      ${actionButton("study-bookmark", question.bookmarked, "Bookmarked", "Bookmark")}
      ${actionButton("study-learned", question.studied, "Learned ✓", "Learned")}
      ${actionButton("study-revision", question.revision, "In Revision", "Revision")}
    </div>
    ${state.studyMode === "flashcard" && state.studyRevealed ? '<div class="flashcard-rating"><span>How difficult was recall?</span><button data-flashcard="easy" type="button">Easy</button><button data-flashcard="medium" type="button">Medium</button><button data-flashcard="difficult" type="button">Difficult</button></div>' : ""}`;
}

function openStudyMode(mode = "study") {
  if (!state.questions.length) {
    showToast("No questions are available for this study mode.", "error");
    return;
  }
  state.studyMode = mode;
  state.studyIndex = 0;
  state.studyRevealed = false;
  renderStudyMode();
  refs.studyDialog.showModal();
}

async function randomQuestion(surprise = false) {
  const params = surprise ? "" : queryString();
  const payload = await api(`/api/learning/random${params ? `?${params}` : ""}`, { method: "GET" });
  await showQuestionById(payload.question.questionId);
}

async function saveTargets() {
  const targetCompanies = Array.from(refs.targetCompanyList.querySelectorAll("input:checked")).map((input) => input.value);
  const payload = await api("/api/learning/preferences", { method: "PATCH", body: JSON.stringify({ targetCompanies }) });
  state.overview.preferences = payload.preferences;
  renderCompanyAndTopicViews();
  showToast("Target companies saved.");
}

function debounce(callback, wait) {
  let timer;
  return (...args) => {
    window.clearTimeout(timer);
    timer = window.setTimeout(() => callback(...args), wait);
  };
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
  refs.learningContent.classList.remove("hidden");
  const payload = await api("/api/learning/overview", { method: "GET" });
  state.overview = payload.overview;
  state.metadata = payload.metadata;
  populateMetadataFilters();
  syncFilterControls();
  renderOverview();
  setView("overview");
}

function bindEvents() {
  refs.themeToggle.addEventListener("click", () => applyTheme(refs.body.dataset.theme === "dark" ? "light" : "dark"));
  refs.logoutButton.addEventListener("click", async () => {
    await api("/api/auth/logout", { method: "POST", body: "{}" });
    window.location.href = "/";
  });
  refs.learningNav.addEventListener("click", (event) => {
    const button = event.target.closest("[data-view]");
    if (!button) return;
    const view = button.dataset.view;
    if (["overview", "companies", "progress"].includes(view)) setView(view);
    else openCatalog(view).catch((error) => showToast(error.message, "error"));
  });
  refs.sectionCards.addEventListener("click", (event) => {
    const button = event.target.closest("[data-open-type]");
    if (button) openCatalog(button.dataset.openType).catch((error) => showToast(error.message, "error"));
  });
  refs.quickActions.forEach((button) => button.addEventListener("click", () => {
    const action = button.dataset.action;
    if (action === "companies") setView("companies");
    else if (action === "topics") setView("topics");
    else if (action === "random" || action === "surprise") randomQuestion(action === "surprise").catch((error) => showToast(error.message, "error"));
    else if (action === "study") openCatalog("catalog").then(() => openStudyMode("study")).catch((error) => showToast(error.message, "error"));
    else openCatalog(action).catch((error) => showToast(error.message, "error"));
  }));
  document.addEventListener("click", (event) => {
    const questionButton = event.target.closest("[data-open-question]");
    if (questionButton) showQuestionById(questionButton.dataset.openQuestion).catch((error) => showToast(error.message, "error"));
    const companyButton = event.target.closest("[data-company]");
    if (companyButton) openCatalog("catalog", { company: companyButton.dataset.company }).catch((error) => showToast(error.message, "error"));
    const topicButton = event.target.closest("[data-topic]");
    if (topicButton) openCatalog("catalog", { topic: topicButton.dataset.topic }).catch((error) => showToast(error.message, "error"));
  });
  refs.questionList.addEventListener("click", (event) => {
    const empty = event.target.closest("[data-empty-action='clear']");
    if (empty) openCatalog("catalog").catch((error) => showToast(error.message, "error"));
    const action = event.target.closest("[data-question-action]");
    if (action) handleQuestionAction(action).catch((error) => showToast(error.message, "error"));
    const confidence = event.target.closest("[data-confidence]");
    if (confidence) {
      const card = confidence.closest("[data-question-id]");
      patchQuestion(card.dataset.questionId, { confidence: confidence.dataset.confidence }).then(() => showToast("Confidence saved.")).catch((error) => showToast(error.message, "error"));
    }
  });
  refs.pagination.addEventListener("click", (event) => {
    const button = event.target.closest("[data-page]");
    if (!button || button.disabled) return;
    state.filters.page = Number(button.dataset.page);
    loadQuestions().then(() => refs.catalogView.scrollIntoView({ behavior: "smooth", block: "start" })).catch((error) => showToast(error.message, "error"));
  });
  const filterMap = [[refs.typeFilter, "type"], [refs.difficultyFilter, "difficulty"], [refs.companyFilter, "company"], [refs.topicFilter, "topic"], [refs.statusFilter, "status"], [refs.frequencyFilter, "frequency"], [refs.sortFilter, "sort"]];
  filterMap.forEach(([element, key]) => element.addEventListener("change", () => {
    state.filters[key] = element.value;
    if (key === "type") updateTopicOptions(element.value);
    state.filters.page = 1;
    loadQuestions().catch((error) => showToast(error.message, "error"));
  }));
  const search = debounce(() => {
    state.filters.search = refs.questionSearch.value.trim(); state.filters.page = 1;
    refs.clearSearchButton.classList.toggle("hidden", !state.filters.search);
    setView("catalog"); loadQuestions().catch((error) => showToast(error.message, "error"));
  }, 280);
  refs.questionSearch.addEventListener("input", search);
  refs.clearSearchButton.addEventListener("click", () => { refs.questionSearch.value = ""; state.filters.search = ""; refs.clearSearchButton.classList.add("hidden"); openCatalog("catalog").catch((error) => showToast(error.message, "error")); });
  refs.clearFiltersButton.addEventListener("click", () => openCatalog("catalog").catch((error) => showToast(error.message, "error")));
  refs.dailyGoalSelect.addEventListener("change", async () => {
    const payload = await api("/api/learning/preferences", { method: "PATCH", body: JSON.stringify({ dailyGoal: Number(refs.dailyGoalSelect.value) }) });
    state.overview.preferences = payload.preferences;
    state.overview.dailyGoal.target = payload.preferences.dailyGoal;
    renderOverview(); showToast("Daily goal updated.");
  });
  refs.saveTargetsButton.addEventListener("click", () => saveTargets().catch((error) => showToast(error.message, "error")));
  refs.practiceWeakButton.addEventListener("click", () => {
    const topic = state.overview.weakTopics[0];
    if (topic) openCatalog("catalog", { topic }).catch((error) => showToast(error.message, "error"));
  });
  refs.mobileFiltersButton.addEventListener("click", () => { refs.filterPanel.classList.add("open"); refs.filterBackdrop.classList.remove("hidden"); });
  const closeFilters = () => { refs.filterPanel.classList.remove("open"); refs.filterBackdrop.classList.add("hidden"); };
  refs.closeFiltersButton.addEventListener("click", closeFilters);
  refs.filterBackdrop.addEventListener("click", closeFilters);
  refs.studyModeButton.addEventListener("click", () => openStudyMode("study"));
  refs.closeStudyButton.addEventListener("click", () => refs.studyDialog.close());
  refs.studyPreviousButton.addEventListener("click", () => { if (state.studyIndex > 0) { state.studyIndex -= 1; state.studyRevealed = false; renderStudyMode(); } });
  refs.studyRevealButton.addEventListener("click", () => { state.studyRevealed = !state.studyRevealed; renderStudyMode(); });
  refs.studyNextButton.addEventListener("click", () => {
    if (state.studyIndex === state.questions.length - 1) refs.studyDialog.close();
    else { state.studyIndex += 1; state.studyRevealed = false; renderStudyMode(); }
  });
  refs.studyQuestionCard.addEventListener("click", (event) => {
    const question = studyQuestion();
    const action = event.target.closest("[data-question-action]")?.dataset.questionAction;
    const flashcard = event.target.closest("[data-flashcard]")?.dataset.flashcard;
    const changes = action === "study-bookmark" ? { bookmarked: !question.bookmarked }
      : action === "study-learned" ? { studied: !question.studied }
      : action === "study-revision" ? { revision: !question.revision }
      : flashcard ? { flashcardDifficulty: flashcard, revision: flashcard === "difficult" || question.revision }
      : null;
    if (changes) patchQuestion(question.questionId, changes, false).then(() => renderStudyMode()).catch((error) => showToast(error.message, "error"));
  });
}

bindEvents();
bootstrap().catch((error) => showToast(error.message, "error"));
