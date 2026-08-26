const ROUND_LABELS = {
  managerial: "Managerial Round",
  technical: "Technical Interview",
  hr: "HR Interview",
};

const DOMAIN_LABELS = {
  software_engineering: "Software Engineering",
  data_science: "Data Science",
  ai_ml: "AI / ML",
  core_engineering: "Core Engineering",
};

const state = {
  user: null,
  summary: null,
  history: [],
};

const refs = {
  body: document.body,
  themeToggle: document.getElementById("themeToggle"),
  logoutButton: document.getElementById("logoutButton"),
  authNotice: document.getElementById("authNotice"),
  dashboardContent: document.getElementById("dashboardContent"),
  dashboardUserName: document.getElementById("dashboardUserName"),
  dashboardUserEmail: document.getElementById("dashboardUserEmail"),
  totalInterviewsValue: document.getElementById("totalInterviewsValue"),
  averageScoreValue: document.getElementById("averageScoreValue"),
  summaryDateValue: document.getElementById("summaryDateValue"),
  summaryScoreValue: document.getElementById("summaryScoreValue"),
  strengthList: document.getElementById("strengthList"),
  weaknessList: document.getElementById("weaknessList"),
  suggestionList: document.getElementById("suggestionList"),
  historyList: document.getElementById("historyList"),
  toast: document.getElementById("toast"),
};

function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatScore(value) {
  return Number.isFinite(value) ? Math.round(value) : 0;
}

function formatDate(value) {
  if (!value) {
    return "Not available";
  }
  return new Date(value).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function capitalize(value = "") {
  return value ? value.charAt(0).toUpperCase() + value.slice(1) : "";
}

function showToast(message, tone = "success") {
  refs.toast.textContent = message;
  refs.toast.className = `toast ${tone}`;
  refs.toast.classList.remove("hidden");
  window.clearTimeout(showToast.timeoutId);
  showToast.timeoutId = window.setTimeout(() => refs.toast.classList.add("hidden"), 2600);
}

async function api(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    credentials: "same-origin",
    ...options,
  });

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : {};

  if (!response.ok) {
    throw new Error(payload.error || "Something went wrong.");
  }

  return payload;
}

function applyTheme(theme) {
  refs.body.dataset.theme = theme;
  localStorage.setItem("interview-theme", theme);
  const label = theme === "dark" ? "Switch to light theme" : "Switch to dark theme";
  refs.themeToggle.setAttribute("aria-label", label);
  refs.themeToggle.title = label;
}

function appendList(target, items, emptyText) {
  if (!items || !items.length) {
    target.innerHTML = `<li>${escapeHtml(emptyText)}</li>`;
    return;
  }

  target.innerHTML = items.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
}

function pickLatestInterview(history) {
  return history.find((item) => item.status === "completed") || history[0] || null;
}

function renderHistory(history) {
  if (!history.length) {
    refs.historyList.innerHTML = `
      <article class="history-card empty-state">
        No interview history yet. Complete a round on the main page and come back here for analytics.
      </article>
    `;
    return;
  }

  refs.historyList.innerHTML = history
    .map(
      (item, index) => `
        <article class="history-card">
          <div class="history-header">
            <div>
              <p class="history-label">${escapeHtml(ROUND_LABELS[item.roundType] || item.roundType)}</p>
              <h4>${escapeHtml(formatDate(item.completedAt || item.createdAt))}</h4>
            </div>
            <div class="history-score-block">
              <span>Score</span>
              <strong>${formatScore(item.score)}</strong>
            </div>
          </div>
          <div class="history-meta-row">
            <span class="chip">${escapeHtml(DOMAIN_LABELS[item.domain] || item.domain)}</span>
            <span class="chip">${escapeHtml(capitalize(item.difficulty))}</span>
            <span class="chip">${escapeHtml(capitalize(item.status))}</span>
          </div>
          <details class="history-details" ${index === 0 ? "open" : ""}>
            <summary>Expand to view details</summary>
            <div class="history-detail-content">
              <div class="detail-grid">
                <div>
                  <p class="detail-label">Strengths</p>
                  <ul class="detail-list">
                    ${(item.strengths || []).length
                      ? item.strengths.map((entry) => `<li>${escapeHtml(entry)}</li>`).join("")
                      : "<li>No strengths recorded.</li>"}
                  </ul>
                </div>
                <div>
                  <p class="detail-label">Weaknesses</p>
                  <ul class="detail-list">
                    ${(item.weaknesses || []).length
                      ? item.weaknesses.map((entry) => `<li>${escapeHtml(entry)}</li>`).join("")
                      : "<li>No weaknesses recorded.</li>"}
                  </ul>
                </div>
                <div>
                  <p class="detail-label">Improvements</p>
                  <ul class="detail-list">
                    ${(item.suggestions || []).length
                      ? item.suggestions.map((entry) => `<li>${escapeHtml(entry)}</li>`).join("")
                      : "<li>No improvement suggestions recorded.</li>"}
                  </ul>
                </div>
                <div>
                  <p class="detail-label">Interview Details</p>
                  <ul class="detail-list">
                    <li>Date: ${escapeHtml(formatDate(item.completedAt || item.createdAt))}</li>
                    <li>Score: ${formatScore(item.score)}</li>
                    <li>Round: ${escapeHtml(ROUND_LABELS[item.roundType] || item.roundType)}</li>
                    <li>Domain: ${escapeHtml(DOMAIN_LABELS[item.domain] || item.domain)}</li>
                    <li>Difficulty: ${escapeHtml(capitalize(item.difficulty))}</li>
                  </ul>
                </div>
              </div>
            </div>
          </details>
        </article>
      `,
    )
    .join("");
}

function renderDashboard() {
  refs.dashboardUserName.textContent = state.user?.name || "Interview Candidate";
  refs.dashboardUserEmail.textContent = state.user?.email || "Signed-in analytics profile";

  refs.totalInterviewsValue.textContent = String(state.history.length);
  refs.averageScoreValue.textContent = String(formatScore(state.summary?.overallAverage || 0));

  const latestInterview = pickLatestInterview(state.history);
  if (!latestInterview) {
    refs.summaryDateValue.textContent = "No interviews yet";
    refs.summaryScoreValue.textContent = "0";
    appendList(refs.strengthList, [], "No strengths yet.");
    appendList(refs.weaknessList, [], "No weaknesses yet.");
    appendList(refs.suggestionList, [], "No improvements yet.");
    renderHistory([]);
    return;
  }

  refs.summaryDateValue.textContent = formatDate(latestInterview.completedAt || latestInterview.createdAt);
  refs.summaryScoreValue.textContent = String(formatScore(latestInterview.score));
  appendList(refs.strengthList, latestInterview.strengths, "No strengths recorded.");
  appendList(refs.weaknessList, latestInterview.weaknesses, "No weaknesses recorded.");
  appendList(refs.suggestionList, latestInterview.suggestions, "No improvement suggestions recorded.");
  renderHistory(state.history);
}

async function handleLogout() {
  await api("/api/auth/logout", { method: "POST", body: JSON.stringify({}) });
  window.location.href = "/";
}

async function bootstrap() {
  applyTheme(localStorage.getItem("interview-theme") || "dark");

  const sessionPayload = await api("/api/auth/session", { method: "GET" });
  if (!sessionPayload.authenticated) {
    refs.authNotice.classList.remove("hidden");
    refs.dashboardContent.classList.add("hidden");
    refs.logoutButton.classList.add("hidden");
    return;
  }

  state.user = sessionPayload.user;
  refs.authNotice.classList.add("hidden");
  refs.dashboardContent.classList.remove("hidden");
  refs.logoutButton.classList.remove("hidden");

  const [summaryPayload, historyPayload] = await Promise.all([
    api("/api/dashboard", { method: "GET" }),
    api("/api/history", { method: "GET" }),
  ]);

  state.summary = summaryPayload.summary;
  state.history = historyPayload.sessions || [];
  renderDashboard();
}

function bindEvents() {
  refs.themeToggle.addEventListener("click", () => {
    const nextTheme = refs.body.dataset.theme === "dark" ? "light" : "dark";
    applyTheme(nextTheme);
  });

  refs.logoutButton.addEventListener("click", () => {
    handleLogout().catch((error) => showToast(error.message, "error"));
  });
}

bindEvents();
bootstrap().catch((error) => showToast(error.message, "error"));
