const DIFFICULTY_LADDER = ["beginner", "intermediate", "advanced"];

export const SAMPLE_QUESTION_BANKS = {
  technical: {
    beginner: [
      { id: "tech-beg-1", question: "How would you break a new web feature into frontend, backend, and data responsibilities?" },
      { id: "tech-beg-2", question: "What steps would you take first if a deployed API suddenly started timing out?" },
      { id: "tech-beg-3", question: "How do you decide what to test before releasing a feature?" },
      { id: "tech-beg-4", question: "Explain a project where you had to work with an existing codebase instead of starting fresh." },
    ],
    intermediate: [
      { id: "tech-int-1", question: "Describe how you would redesign a slow endpoint when the database, cache, and client payload all contribute to latency." },
      { id: "tech-int-2", question: "How would you roll out a backward-compatible API change used by several clients?" },
      { id: "tech-int-3", question: "Tell me how you would debug an issue that only appears under production traffic." },
      { id: "tech-int-4", question: "What trade-offs do you make when choosing between synchronous and asynchronous processing?" },
    ],
    advanced: [
      { id: "tech-adv-1", question: "Design a strategy for scaling a user-facing system 10x while protecting latency and availability." },
      { id: "tech-adv-2", question: "How would you isolate failure domains in a distributed architecture that serves multiple critical workflows?" },
      { id: "tech-adv-3", question: "Explain how you would balance consistency, observability, and rollback safety in a large migration." },
      { id: "tech-adv-4", question: "If a high-impact incident keeps recurring, how would you turn quick fixes into systemic prevention?" },
    ],
  },
  managerial: {
    beginner: [
      { id: "mgr-beg-1", question: "Tell me about a time you had to coordinate work across teammates with different priorities." },
      { id: "mgr-beg-2", question: "How do you keep a team calm and focused when deadlines are tight?" },
      { id: "mgr-beg-3", question: "Describe how you give feedback when a teammate is struggling." },
      { id: "mgr-beg-4", question: "What does ownership look like to you in a delivery-focused role?" },
    ],
    intermediate: [
      { id: "mgr-int-1", question: "How would you align stakeholders who disagree on scope, timing, and success metrics?" },
      { id: "mgr-int-2", question: "Describe a situation where you had to make progress despite ambiguity from leadership." },
      { id: "mgr-int-3", question: "How do you balance short-term delivery pressure with long-term team health?" },
      { id: "mgr-int-4", question: "Tell me about a time you had to reset execution after a plan started failing." },
    ],
    advanced: [
      { id: "mgr-adv-1", question: "How would you lead a team through a high-risk change where the wrong decision could hurt trust or revenue?" },
      { id: "mgr-adv-2", question: "Describe how you would make a fast decision when senior stakeholders want conflicting outcomes." },
      { id: "mgr-adv-3", question: "What is your playbook for recovering team alignment after a visible delivery miss?" },
      { id: "mgr-adv-4", question: "How would you coach strong individual contributors into broader leadership ownership?" },
    ],
  },
  hr: {
    beginner: [
      { id: "hr-beg-1", question: "Why are you interested in this role, and what kind of work energizes you most?" },
      { id: "hr-beg-2", question: "What strengths do teammates usually rely on you for?" },
      { id: "hr-beg-3", question: "Tell me about a challenge that helped you grow professionally." },
      { id: "hr-beg-4", question: "How do you handle feedback that is difficult to hear?" },
    ],
    intermediate: [
      { id: "hr-int-1", question: "How does your background prepare you to contribute quickly in a new team?" },
      { id: "hr-int-2", question: "Tell me about a time your motivation was tested and how you responded." },
      { id: "hr-int-3", question: "How do you build trust with teammates who work very differently from you?" },
      { id: "hr-int-4", question: "What do you want your next role to help you develop?" },
    ],
    advanced: [
      { id: "hr-adv-1", question: "What makes you a strong fit for a role with high ambiguity and accountability?" },
      { id: "hr-adv-2", question: "Describe how you would create impact in your first 90 days while still learning the organization." },
      { id: "hr-adv-3", question: "How do you evaluate whether a role is right for you beyond title and compensation?" },
      { id: "hr-adv-4", question: "When your values and a business decision pull in different directions, how do you respond?" },
    ],
  },
};

function safeReadJson(storage, key, fallback) {
  try {
    const raw = storage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch (_error) {
    return fallback;
  }
}

function safeWriteJson(storage, key, value) {
  try {
    storage.setItem(key, JSON.stringify(value));
  } catch (_error) {
    // Ignore storage quota and privacy-mode failures.
  }
}

function normalizeLevel(level) {
  return DIFFICULTY_LADDER.includes(level) ? level : "beginner";
}

function clamp(value, min = 0, max = 100) {
  return Math.max(min, Math.min(max, value));
}

function getStorageScope({ userId, roundType, domain }) {
  const safeUserId = userId || "anonymous";
  const safeRoundType = roundType || "general";
  const safeDomain = domain || "general";
  return `${safeUserId}:${safeRoundType}:${safeDomain}`;
}

export function formatLevelLabel(level) {
  const normalized = normalizeLevel(level);
  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}

export function getAdaptiveLevel(userScore, currentLevel) {
  const normalizedLevel = normalizeLevel(currentLevel);
  const currentIndex = DIFFICULTY_LADDER.indexOf(normalizedLevel);

  if (userScore >= 70) {
    return DIFFICULTY_LADDER[Math.min(currentIndex + 1, DIFFICULTY_LADDER.length - 1)];
  }

  if (userScore < 40) {
    return DIFFICULTY_LADDER[Math.max(currentIndex - 1, 0)];
  }

  return normalizedLevel;
}

export function getRandomQuestion(level, questionBank, askedQuestions = new Set()) {
  const normalizedLevel = normalizeLevel(level);
  const levelQuestions = questionBank?.[normalizedLevel] || [];
  const available = levelQuestions.filter((item) => !askedQuestions.has(item.id));

  if (!available.length) {
    return null;
  }

  const index = Math.floor(Math.random() * available.length);
  return available[index];
}

export function getNextQuestion(userScore, currentLevel, questionBank, askedQuestions = new Set()) {
  const nextLevel = getAdaptiveLevel(userScore, currentLevel);
  const searchOrder = Array.from(
    new Set([nextLevel, currentLevel, ...DIFFICULTY_LADDER.filter((level) => level !== nextLevel && level !== currentLevel)]),
  );

  for (const level of searchOrder) {
    const question = getRandomQuestion(level, questionBank, askedQuestions);
    if (question) {
      return {
        level,
        question,
        recycled: false,
      };
    }
  }

  for (const level of searchOrder) {
    const firstQuestion = questionBank?.[level]?.[0];
    if (firstQuestion) {
      return {
        level,
        question: firstQuestion,
        recycled: true,
      };
    }
  }

  return {
    level: normalizeLevel(currentLevel),
    question: null,
    recycled: true,
  };
}

export function createAdaptiveInterviewTracker({ userId, roundType, domain, maxQuestions = 3 }) {
  const scope = getStorageScope({ userId, roundType, domain });
  const persistentKey = `adaptive-persistent:${scope}`;
  const sessionKey = `adaptive-session:${scope}`;
  const stateKey = `adaptive-state:${scope}`;

  let sessionAsked = new Set(safeReadJson(window.sessionStorage, sessionKey, []));
  let persistentAsked = new Set(safeReadJson(window.localStorage, persistentKey, []));
  let trackerState = {
    currentLevel: "beginner",
    questionNumber: 0,
    maxQuestions,
  };

  const savedState = safeReadJson(window.sessionStorage, stateKey, null);
  if (savedState) {
    trackerState = {
      currentLevel: normalizeLevel(savedState.currentLevel),
      questionNumber: Number(savedState.questionNumber) || 0,
      maxQuestions: Number(savedState.maxQuestions) || maxQuestions,
    };
  }

  function persist() {
    safeWriteJson(window.sessionStorage, sessionKey, Array.from(sessionAsked));
    safeWriteJson(window.localStorage, persistentKey, Array.from(persistentAsked));
    safeWriteJson(window.sessionStorage, stateKey, trackerState);
  }

  function resetSession(startLevel = "beginner") {
    sessionAsked = new Set();
    trackerState = {
      currentLevel: normalizeLevel(startLevel),
      questionNumber: 0,
      maxQuestions: trackerState.maxQuestions || maxQuestions,
    };
    persist();
  }

  function markAsked(questionLike) {
    const questionId = typeof questionLike === "string" ? questionLike : questionLike?.id;
    if (!questionId) {
      return;
    }

    sessionAsked.add(questionId);
    persistentAsked.add(questionId);
    persist();
  }

  function syncFromSession(session) {
    if (!session) {
      return;
    }

    const askedQuestions = Array.isArray(session.askedQuestions) ? session.askedQuestions : [];
    sessionAsked = new Set();

    askedQuestions.forEach((question) => {
      if (question?.id) {
        sessionAsked.add(question.id);
        persistentAsked.add(question.id);
      }
    });

    trackerState = {
      currentLevel: normalizeLevel(session.currentLevel || session.difficulty),
      questionNumber: Number(session.questionNumber || session.questionIndex || askedQuestions.length) || 0,
      maxQuestions: trackerState.maxQuestions || maxQuestions,
    };

    persist();
  }

  function setMaxQuestions(value) {
    trackerState.maxQuestions = Number(value) || trackerState.maxQuestions || maxQuestions;
    persist();
  }

  function setCurrentLevel(level) {
    trackerState.currentLevel = normalizeLevel(level);
    persist();
  }

  function setQuestionNumber(value) {
    trackerState.questionNumber = Number(value) || 0;
    persist();
  }

  function getProgressPercent() {
    return clamp((trackerState.questionNumber / Math.max(trackerState.maxQuestions, 1)) * 100);
  }

  return {
    scope,
    resetSession,
    markAsked,
    syncFromSession,
    setMaxQuestions,
    setCurrentLevel,
    setQuestionNumber,
    getCurrentLevel: () => trackerState.currentLevel,
    getQuestionNumber: () => trackerState.questionNumber,
    getMaxQuestions: () => trackerState.maxQuestions,
    getProgressPercent,
    getSessionAskedIds: () => Array.from(sessionAsked),
    getPersistentAskedIds: () => Array.from(persistentAsked),
  };
}
