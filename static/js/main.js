import { createRequestTracker, createSessionExitController } from "./session_exit.js";

const INTERVIEW_STATES = Object.freeze({
  IDLE: "IDLE",
  PREPARING_QUESTION: "PREPARING_QUESTION",
  SPEAKING_QUESTION: "SPEAKING_QUESTION",
  WAITING_FOR_ANSWER: "WAITING_FOR_ANSWER",
  RECORDING_ANSWER: "RECORDING_ANSWER",
  TIMEOUT: "TIMEOUT",
  PROCESSING_ANSWER: "PROCESSING_ANSWER",
  QUESTION_COMPLETE: "QUESTION_COMPLETE",
  INTERVIEW_COMPLETE: "INTERVIEW_COMPLETE",
});

const MONITORING = Object.freeze({
  FACE_ABSENCE_MS: 5000,
  MULTIPLE_FACE_MS: 3000,
  EVENT_COOLDOWN_MS: 12000,
});

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

const state = {
  user: null,
  options: null,
  session: null,
  meta: null,
  phase: INTERVIEW_STATES.IDLE,
  replayCount: 0,
  questionStartedAt: 0,
  answerStartedAt: 0,
  interviewEndsAt: 0,
  questionEndsAt: 0,
  interviewTimer: null,
  questionTimer: null,
  mediaStream: null,
  stoppingMedia: false,
  awayStartedAt: null,
  awayEventType: null,
  ignoreBlurUntil: 0,
  faceDetector: null,
  faceCheckTimer: null,
  faceMissingSince: null,
  multipleFaceSince: null,
  lastFaceAbsenceEventAt: 0,
  lastMultipleFaceEventAt: 0,
  speechStream: null,
  recognition: null,
  recognitionActive: false,
  recognitionStarting: false,
  recognitionBaseText: "",
  recognitionUsingLocal: false,
  speechNetworkFallbackAttempted: false,
  speechStartedAt: 0,
  speechTimer: null,
  speechLastResultAt: 0,
  pauseCount: 0,
  advancedVoiceEnabled: false,
  questionSpeechToken: 0,
  questionSpeechWatchdog: null,
  voiceAutoStartTimer: null,
  voiceAutoSubmitTimer: null,
  silenceCountdownTimer: null,
  silenceDeadline: 0,
  recognitionStopReason: "",
  recognitionConfidenceTotal: 0,
  recognitionConfidenceSamples: 0,
  recognitionRestartCount: 0,
  currentVoiceAutoSubmitted: false,
  interviewerInterruptions: 0,
  silenceStops: 0,
  answerMode: null,
  questionFinalized: false,
  audioContext: null,
  analyser: null,
  audioFrame: null,
  systemChecked: false,
  report: null,
  exiting: false,
  mediaRequestToken: 0,
  speechRequestToken: 0,
  warningTimer: null,
  nextQuestionTimer: null,
  nextQuestionSpeechTimer: null,
  voiceSubmitDelayTimer: null,
  countdownTimer: null,
  countdownHideTimer: null,
  countdownResolve: null,
  systemCheckTimeout: null,
  answerDelayTimer: null,
  answerDelayResolve: null,
};

const refs = Object.fromEntries(
  Array.from(document.querySelectorAll("[id]")).map((element) => [element.id, element]),
);
const requests = createRequestTracker();
let exitController = null;

const ROUND_LABELS = {
  technical: "Technical Round",
  managerial: "Manager Round",
  hr: "HR Round",
};

function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function clamp(value, min = 0, max = 100) {
  return Math.min(Math.max(Number(value) || 0, min), max);
}

function formatScore(value) {
  return Math.round(Number(value) || 0);
}

function formatTime(seconds) {
  const safe = Math.max(0, Math.floor(Number(seconds) || 0));
  return `${Math.floor(safe / 60)}:${String(safe % 60).padStart(2, "0")}`;
}

function capitalize(value = "") {
  return String(value).charAt(0).toUpperCase() + String(value).slice(1);
}

function showToast(message, tone = "success") {
  refs.toast.textContent = message;
  refs.toast.className = `toast ${tone}`;
  window.clearTimeout(showToast.timeout);
  showToast.timeout = window.setTimeout(() => refs.toast.classList.add("hidden"), 4200);
}

async function api(url, options = {}, tracked = true) {
  let response;
  try {
    response = await requests.fetch(url, {
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    }, { tracked });
  } catch (error) {
    if (error?.name === "AbortError") throw error;
    throw new Error("The server could not be reached. Check your connection and try again.");
  }
  let payload = {};
  try {
    payload = await response.json();
  } catch (_error) {
    payload = {};
  }
  if (!response.ok) throw new Error(payload.error || "The request could not be completed.");
  return payload;
}

function applyTheme(theme) {
  document.body.dataset.theme = theme;
  localStorage.setItem("interview-theme", theme);
  const label = theme === "dark" ? "Switch to light theme" : "Switch to dark theme";
  refs.themeToggle.setAttribute("aria-label", label);
  refs.themeToggle.title = label;
}

function setAuthenticated(authenticated) {
  refs.authView.classList.toggle("hidden", authenticated);
  refs.appView.classList.toggle("hidden", !authenticated);
  [refs.learningLink, refs.aptitudeLink, refs.resumeQuizLink, refs.analyticsLink, refs.logoutButton].forEach((element) => {
    element.classList.toggle("hidden", !authenticated);
  });
}

function setPhase(nextPhase) {
  state.phase = nextPhase;
  const labels = {
    PREPARING_QUESTION: "Preparing the next question",
    SPEAKING_QUESTION: "Interviewer is asking the question",
    WAITING_FOR_ANSWER: "Waiting for your answer",
    RECORDING_ANSWER: "Listening to your answer",
    TIMEOUT: "Response time ended",
    PROCESSING_ANSWER: "Processing your response",
    QUESTION_COMPLETE: "Moving to the next question",
    INTERVIEW_COMPLETE: "Interview complete",
  };
  refs.interviewStateLabel.textContent = labels[nextPhase] || "Interview setup";
  refs.interviewerAvatar.classList.toggle("speaking", nextPhase === INTERVIEW_STATES.SPEAKING_QUESTION);
  refs.processingPanel.classList.toggle("hidden", nextPhase !== INTERVIEW_STATES.PROCESSING_ANSWER);
  refs.repeatQuestionButton.disabled = nextPhase !== INTERVIEW_STATES.WAITING_FOR_ANSWER || state.replayCount >= 2;
  refs.interruptInterviewerButton.classList.toggle(
    "hidden",
    nextPhase !== INTERVIEW_STATES.SPEAKING_QUESTION || !state.advancedVoiceEnabled,
  );
}

function populateSelect(select, items, preferred) {
  select.innerHTML = items
    .map((item) => {
      const value = typeof item === "object" ? item.value : item;
      const label = typeof item === "object" ? item.label : item;
      return `<option value="${escapeHtml(value)}">${escapeHtml(label)}</option>`;
    })
    .join("");
  if (preferred && Array.from(select.options).some((option) => option.value === preferred)) {
    select.value = preferred;
  }
}

function renderOptions(options) {
  state.options = options;
  populateSelect(refs.companySelect, options.companies, "NVIDIA");
  populateSelect(refs.roundSelect, options.rounds, "technical");
  populateSelect(refs.domainSelect, options.domains, "software_engineering");
  populateSelect(refs.difficultySelect, options.difficulties, "medium");
  refs.bankSizeChip.textContent = `${Number(options.questionBankSize).toLocaleString()} question bank`;
  refs.adaptiveEngineStatus.textContent = options.adaptiveFollowUps?.aiEnabled
    ? "AI + fallback ready"
    : "Local adaptive fallback";
}

function renderPerformance(performance = {}) {
  refs.performanceInterviews.textContent = performance.interviewsCompleted || 0;
  refs.performanceAverage.textContent = `${formatScore(performance.averageScore)}%`;
  refs.performanceTechnical.textContent = `${formatScore(performance.technicalScore)}%`;
  refs.performanceCommunication.textContent = `${formatScore(performance.communicationScore)}%`;
  refs.performanceDomain.textContent = performance.strongestDomain || "Start practicing";
  const trend = performance.recentTrend || [];
  if (!trend.length) {
    refs.performanceTrend.innerHTML = "<span>Your recent score trend will appear here after your first interview.</span>";
    return;
  }
  const width = 520;
  const height = 70;
  const points = trend
    .map((value, index) => {
      const x = trend.length === 1 ? width / 2 : (index / (trend.length - 1)) * width;
      const y = height - clamp(value) * 0.58 - 6;
      return `${x},${y}`;
    })
    .join(" ");
  refs.performanceTrend.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Recent scores: ${trend.join(", ")}"><polyline points="${points}" /></svg>`;
}

async function loadDashboard() {
  const payload = await api("/api/dashboard", { method: "GET" });
  renderPerformance(payload.performance);
}

function systemStatus(element, text, ready) {
  element.textContent = text;
  element.dataset.ready = ready ? "true" : "false";
}

function supportsSpeechInput() {
  return Boolean(SpeechRecognition && window.navigator?.mediaDevices?.getUserMedia);
}

function liveAudioTrack() {
  for (const stream of [state.mediaStream, state.speechStream]) {
    const track = stream?.getAudioTracks().find((item) => item.readyState === "live");
    if (track) return track;
  }
  return null;
}

function speechInputUnavailableMessage() {
  if (!window.navigator?.mediaDevices?.getUserMedia) {
    return "Microphone access is unavailable in this browser. Open this site in the latest Chrome or Edge.";
  }
  return "Live speech recognition is unavailable in this browser. Open this site in the latest Chrome or Edge.";
}

function speechRecognitionErrorMessage(errorCode) {
  const messages = {
    "not-allowed": "Microphone permission was blocked. Allow microphone access in the browser address bar, then try again.",
    "service-not-allowed": "Speech recognition is blocked by this browser. Open the site in Chrome or Edge and allow microphone access.",
    "audio-capture": "No usable microphone was found. Connect or enable a microphone, then run the system check again.",
    network: "The browser speech service could not be reached, and on-device recognition is unavailable. Open the site in the latest Chrome or Edge.",
    language: "The selected speech language is not supported by this browser.",
    "language-not-supported": "The English speech language pack is not supported by this browser.",
    "language-unavailable": "The English speech language pack is not installed in this browser.",
  };
  return messages[errorCode] || `Speech recognition stopped (${errorCode}). Please try again.`;
}

const SPEECH_LANGUAGE = "en-US";

async function localSpeechAvailability() {
  if (typeof SpeechRecognition?.available !== "function") return "unsupported";
  const basicOptions = { langs: [SPEECH_LANGUAGE], processLocally: true };
  try {
    return await SpeechRecognition.available({ ...basicOptions, quality: "dictation" });
  } catch (_qualityError) {
    try { return await SpeechRecognition.available(basicOptions); }
    catch (_error) { return "unsupported"; }
  }
}

async function installLocalSpeechPack() {
  if (typeof SpeechRecognition?.install !== "function") return false;
  const basicOptions = { langs: [SPEECH_LANGUAGE], processLocally: true };
  refs.speechStatusText.textContent = "Preparing on-device speech recognition...";
  try {
    return await SpeechRecognition.install({ ...basicOptions, quality: "dictation" });
  } catch (_qualityError) {
    try { return await SpeechRecognition.install(basicOptions); }
    catch (_error) { return false; }
  }
}

async function resolveSpeechRecognitionMode(forceLocal = false) {
  const availability = await localSpeechAvailability();
  if (availability === "available") return "local";
  if (!forceLocal) return "cloud";
  if (["downloadable", "downloading"].includes(availability)) {
    const installed = await installLocalSpeechPack();
    if (installed && await localSpeechAvailability() === "available") return "local";
  }
  throw new Error(
    "This browser cannot provide speech transcription. Open the site directly in the latest Chrome or Edge, then allow microphone access.",
  );
}

function microphoneAccessErrorMessage(error) {
  const messages = {
    NotAllowedError: "Microphone permission was blocked. Allow microphone access in the browser address bar, then try again.",
    NotFoundError: "No microphone was found. Connect or enable a microphone, then try again.",
    NotReadableError: "The microphone is busy in another application. Close the other application and try again.",
    SecurityError: "Microphone access is blocked for this page. Open the local site in Chrome or Edge.",
  };
  return messages[error?.name] || error?.message || "The microphone could not be opened.";
}

function renderVoiceCompatibility() {
  const supported = supportsSpeechInput();
  refs.advancedVoiceMode.disabled = !supported;
  refs.voiceSupportDescription.textContent = supported
    ? "The interviewer speaks, opens the microphone automatically, detects when you finish, and continues naturally."
    : "Voice input is unavailable in this browser. Open the site in the latest Chrome or Edge to enable it.";
}

async function stopMediaStream() {
  if (!state.mediaStream && !state.speechStream) return;
  state.stoppingMedia = true;
  const tracks = [state.mediaStream, state.speechStream]
    .filter(Boolean)
    .flatMap((stream) => stream.getTracks());
  [...new Set(tracks)].forEach((track) => track.stop());
  state.mediaStream = null;
  state.speechStream = null;
  refs.candidateVideo.srcObject = null;
  refs.cameraOverlay.classList.remove("hidden");
  refs.cameraLiveBadge.textContent = "Camera off";
  refs.cameraSignalStatus.textContent = "Unavailable";
  refs.microphoneSignalStatus.textContent = "Unavailable";
  stopAudioMeter();
  stopFaceChecks();
  window.setTimeout(() => { state.stoppingMedia = false; }, 0);
}

async function requestSpeechMicrophone() {
  const existingTrack = liveAudioTrack();
  if (existingTrack) return existingTrack;
  if (!window.navigator?.mediaDevices?.getUserMedia) {
    throw new Error(speechInputUnavailableMessage());
  }
  state.ignoreBlurUntil = Date.now() + 5000;
  const requestToken = ++state.speechRequestToken;
  let stream;
  try {
    stream = await window.navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      video: false,
    });
  } catch (error) {
    throw new Error(microphoneAccessErrorMessage(error));
  }
  if (requestToken !== state.speechRequestToken || state.exiting) {
    stream.getTracks().forEach((item) => item.stop());
    throw new DOMException("Microphone request was cancelled.", "AbortError");
  }
  state.speechStream = stream;
  const track = stream.getAudioTracks().find((item) => item.readyState === "live");
  if (!track) {
    stream.getTracks().forEach((item) => item.stop());
    state.speechStream = null;
    throw new Error("The microphone did not provide a usable audio track.");
  }
  refs.microphoneSignalStatus.textContent = "Active";
  track.addEventListener("ended", () => {
    refs.microphoneSignalStatus.textContent = "Lost";
    if (!state.stoppingMedia) {
      recordIntegrityEvent("MICROPHONE_INTERRUPTED", 0, 2, "Microphone became unavailable during the interview.");
    }
  }, { once: true });
  return track;
}

async function requestMedia() {
  if (!navigator.mediaDevices?.getUserMedia) throw new Error("This browser does not support camera or microphone access.");
  state.ignoreBlurUntil = Date.now() + 5000;
  if (state.mediaStream?.active) return state.mediaStream;
  const requestToken = ++state.mediaRequestToken;
  const stream = await navigator.mediaDevices.getUserMedia({
    video: { facingMode: "user", width: { ideal: 960 }, height: { ideal: 540 } },
    audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
  });
  if (requestToken !== state.mediaRequestToken || state.exiting) {
    stream.getTracks().forEach((track) => track.stop());
    throw new DOMException("Camera request was cancelled.", "AbortError");
  }
  state.mediaStream = stream;
  refs.candidateVideo.srcObject = state.mediaStream;
  refs.cameraOverlay.classList.add("hidden");
  refs.cameraLiveBadge.textContent = "Camera live";
  refs.cameraSignalStatus.textContent = "Active";
  refs.microphoneSignalStatus.textContent = "Active";
  refs.cameraToggleButton.textContent = "Disable Camera & Microphone";
  const videoTrack = state.mediaStream.getVideoTracks()[0];
  if (videoTrack) {
    videoTrack.addEventListener("ended", () => {
      refs.cameraSignalStatus.textContent = "Lost";
      if (!state.stoppingMedia) recordIntegrityEvent("CAMERA_INTERRUPTED", 0, 2, "Camera became unavailable during the interview.");
    }, { once: true });
  }
  const audioTrack = state.mediaStream.getAudioTracks()[0];
  if (audioTrack) {
    audioTrack.addEventListener("ended", () => {
      refs.microphoneSignalStatus.textContent = "Lost";
      if (!state.stoppingMedia) recordIntegrityEvent("MICROPHONE_INTERRUPTED", 0, 2, "Microphone became unavailable during the interview.");
    }, { once: true });
  }
  startFaceChecks();
  return state.mediaStream;
}

async function runSystemCheck() {
  refs.runSystemCheckButton.disabled = true;
  refs.runSystemCheckButton.textContent = "Checking devices...";
  const speakerReady = "speechSynthesis" in window;
  systemStatus(refs.speakerCheckStatus, speakerReady ? "Audio output ready" : "Speech output unavailable; transcript fallback enabled", speakerReady);
  systemStatus(refs.browserCheckStatus, document.visibilityState === "visible" ? "Browser ready" : "Return to this page", document.visibilityState === "visible");
  try {
    const stream = await Promise.race([
      requestMedia(),
      new Promise((_, reject) => {
        state.systemCheckTimeout = window.setTimeout(
          () => reject(new Error("Device permission is still pending.")),
          12000,
        );
      }),
    ]);
    const cameraReady = stream.getVideoTracks().some((track) => track.readyState === "live");
    const microphoneReady = stream.getAudioTracks().some((track) => track.readyState === "live");
    systemStatus(refs.cameraCheckStatus, cameraReady ? "Camera ready" : "Camera track unavailable", cameraReady);
    systemStatus(
      refs.microphoneCheckStatus,
      microphoneReady
        ? (SpeechRecognition ? "Microphone and speech input ready" : "Microphone ready; speech recognition unavailable")
        : "Microphone track unavailable",
      microphoneReady,
    );
    state.systemChecked = true;
  } catch (error) {
    if (state.exiting) return;
    systemStatus(refs.cameraCheckStatus, "Permission denied or device unavailable", false);
    try {
      await requestSpeechMicrophone();
      systemStatus(
        refs.microphoneCheckStatus,
        SpeechRecognition ? "Microphone and speech input ready" : "Microphone ready; speech recognition needs Chrome or Edge",
        Boolean(SpeechRecognition),
      );
      showToast("Camera is unavailable, but the microphone is ready for spoken answers.");
    } catch (microphoneError) {
      systemStatus(refs.microphoneCheckStatus, microphoneError.message, false);
      showToast(microphoneError.message || error.message, "error");
    }
    state.systemChecked = true;
  }
  window.clearTimeout(state.systemCheckTimeout);
  state.systemCheckTimeout = null;
  const cameraReady = Boolean(state.mediaStream?.getVideoTracks().some((track) => track.readyState === "live"));
  const microphoneReady = Boolean(liveAudioTrack());
  const deviceReady = cameraReady && microphoneReady;
  refs.systemOverallStatus.textContent = deviceReady ? "Ready" : (microphoneReady && supportsSpeechInput() ? "Voice ready" : "Limited mode");
  refs.systemOverallStatus.dataset.tone = deviceReady ? "ready" : "warning";
  refs.runSystemCheckButton.disabled = false;
  refs.runSystemCheckButton.textContent = "Run System Check Again";
}

function startFaceChecks() {
  stopFaceChecks();
  if (!("FaceDetector" in window)) {
    refs.faceSignalStatus.textContent = "Browser unsupported";
    return;
  }
  try {
    state.faceDetector = new window.FaceDetector({ fastMode: true, maxDetectedFaces: 3 });
  } catch (_error) {
    refs.faceSignalStatus.textContent = "Browser unsupported";
    return;
  }
  refs.faceSignalStatus.textContent = "Checking";
  state.faceCheckTimer = window.setInterval(checkFaces, 2200);
}

async function checkFaces() {
  if (!state.faceDetector || !state.mediaStream?.active || refs.candidateVideo.readyState < 2) return;
  try {
    const faces = await state.faceDetector.detect(refs.candidateVideo);
    if (faces.length === 1) {
      refs.faceSignalStatus.textContent = "Visible";
      refs.multiplePeopleStatus.textContent = "Single person";
      state.faceMissingSince = null;
      state.multipleFaceSince = null;
    } else if (faces.length > 1) {
      refs.faceSignalStatus.textContent = "Visible";
      refs.multiplePeopleStatus.textContent = "Multiple possible";
      state.faceMissingSince = null;
      state.multipleFaceSince ||= Date.now();
      const multipleDuration = Date.now() - state.multipleFaceSince;
      if (multipleDuration >= MONITORING.MULTIPLE_FACE_MS
          && Date.now() - state.lastMultipleFaceEventAt > MONITORING.EVENT_COOLDOWN_MS) {
        state.lastMultipleFaceEventAt = Date.now();
        recordIntegrityEvent(
          "MULTIPLE_FACE_DETECTED",
          multipleDuration / 1000,
          2,
          "Multiple people may be visible. Please continue independently when ready.",
        );
      }
    } else {
      refs.faceSignalStatus.textContent = "Not visible";
      refs.multiplePeopleStatus.textContent = "No face signal";
      state.multipleFaceSince = null;
      state.faceMissingSince ||= Date.now();
      const missingDurationMs = Date.now() - state.faceMissingSince;
      if (missingDurationMs >= MONITORING.FACE_ABSENCE_MS
          && Date.now() - state.lastFaceAbsenceEventAt > MONITORING.EVENT_COOLDOWN_MS) {
        state.lastFaceAbsenceEventAt = Date.now();
        recordIntegrityEvent("FACE_NOT_VISIBLE", missingDurationMs / 1000, 1, "Face not detected. Please return to the interview screen.");
      }
    }
  } catch (_error) {
    refs.faceSignalStatus.textContent = "Signal unavailable";
  }
}

function stopFaceChecks() {
  window.clearInterval(state.faceCheckTimer);
  state.faceCheckTimer = null;
  state.faceDetector = null;
  state.faceMissingSince = null;
  state.multipleFaceSince = null;
}

async function recordIntegrityEvent(eventType, duration = 0, severity = 1, warning = "") {
  if (!state.session || state.session.status !== "active") return;
  if (warning) {
    refs.warningBanner.textContent = warning;
    refs.warningBanner.classList.remove("hidden");
    window.clearTimeout(state.warningTimer);
    state.warningTimer = window.setTimeout(() => refs.warningBanner.classList.add("hidden"), 5500);
  }
  try {
    const payload = await api("/api/interview/integrity", {
      method: "POST",
      body: JSON.stringify({
        sessionId: state.session.id,
        eventType,
        duration,
        severity,
        questionNumber: state.session.questionNumber,
      }),
    });
    refs.integrityBadge.textContent = `Session: ${payload.integrity.status}`;
    refs.sessionStatusText.textContent = payload.integrity.status;
    refs.tabSwitchCount.textContent = payload.integrity.tabSwitchCount;
    refs.attentionWarningCount.textContent = payload.integrity.attentionWarningCount;
    refs.multiplePeopleStatus.textContent = payload.integrity.multipleFaceCount ? "Event recorded" : refs.multiplePeopleStatus.textContent;
  } catch (_error) {
    // Integrity telemetry is best effort and must never interrupt the interview.
  }
}

function focusWarning(count) {
  if (count <= 1) return "Please stay on the interview page.";
  if (count === 2) return "Multiple interview-page exits detected.";
  return "Repeated focus changes have been recorded.";
}

function handlePageHidden(eventType = "TAB_SWITCH") {
  if (Date.now() < state.ignoreBlurUntil || !state.session || state.session.status !== "active") return;
  refs.screenFocusStatus.textContent = "Inactive";
  if (!state.awayStartedAt) {
    state.awayStartedAt = Date.now();
    state.awayEventType = eventType;
  } else if (eventType === "TAB_SWITCH") {
    state.awayEventType = eventType;
  }
}

function handlePageVisible() {
  if (document.hidden) return;
  refs.screenFocusStatus.textContent = "Active";
  if (!state.awayStartedAt || !state.session || state.session.status !== "active") return;
  const duration = Math.max(0.1, (Date.now() - state.awayStartedAt) / 1000);
  const eventType = state.awayEventType || "WINDOW_BLUR";
  state.awayStartedAt = null;
  state.awayEventType = null;
  const nextCount = Number(refs.tabSwitchCount.textContent || 0) + 1;
  recordIntegrityEvent(eventType, duration, Math.min(3, nextCount), focusWarning(nextCount));
}

function currentQuestionIds() {
  const storageKey = "interview-asked-question-ids";
  let stored = [];
  try { stored = JSON.parse(localStorage.getItem(storageKey) || "[]"); } catch (_error) { stored = []; }
  return Array.isArray(stored) ? stored.slice(-300) : [];
}

function rememberQuestion(questionId) {
  if (!questionId) return;
  const ids = currentQuestionIds();
  const updated = [...new Set([...ids, questionId])].slice(-300);
  localStorage.setItem("interview-asked-question-ids", JSON.stringify(updated));
}

function renderSession() {
  const session = state.session;
  if (!session) return;
  refs.companyStyleLabel.textContent = session.companyLabel || `${session.company}-style interview`;
  refs.roundChip.textContent = ROUND_LABELS[session.roundType] || session.roundType;
  refs.domainChip.textContent = state.meta?.domainLabel || session.domain;
  refs.difficultyChip.textContent = `${capitalize(state.meta?.startLevel || session.startingDifficulty)} start`;
  refs.questionProgressLabel.textContent = `Question ${session.questionNumber} of ${session.questionLimit}`;
  refs.topicLabel.textContent = session.isFollowUp ? `Follow-up · ${session.currentTopic}` : session.currentTopic || "Interview question";
  refs.progressFill.style.width = `${((session.questionNumber - 1) / session.questionLimit) * 100}%`;
  refs.integrityBadge.textContent = `Session: ${session.integrityStatus || "Normal"}`;
  refs.sessionStatusText.textContent = session.integrityStatus || "Normal";
  refs.tabSwitchCount.textContent = session.tabSwitchCount || 0;
  refs.attentionWarningCount.textContent = session.attentionWarningCount || 0;
  refs.screenFocusStatus.textContent = document.hasFocus() ? "Active" : "Inactive";
  refs.questionTranscript.textContent = session.currentQuestion;
  refs.questionTranscript.classList.toggle("hidden", !refs.transcriptToggle.checked);
  refs.liveVoiceBadge.classList.toggle("hidden", !state.advancedVoiceEnabled);
  refs.adaptiveQuestionBadge.classList.toggle("hidden", !session.isFollowUp);
  refs.adaptiveQuestionBadge.textContent = session.followUpSource === "openai"
    ? "AI adaptive follow-up"
    : "Adaptive follow-up";
  state.replayCount = 0;
  state.questionFinalized = false;
  state.answerMode = null;
  refs.replayCount.textContent = "Question replays: 0 / 2";
  rememberQuestion(session.currentQuestionId);
}

function scheduleAutomaticListening(delay = 500) {
  window.clearTimeout(state.voiceAutoStartTimer);
  if (!state.advancedVoiceEnabled || state.questionFinalized) return;
  showSpokenAnswer();
  refs.speechStatusText.textContent = "Microphone opening automatically...";
  state.voiceAutoStartTimer = window.setTimeout(() => {
    startSpeaking({ automatic: true }).catch((error) => {
      showToast(error.message, "error");
      refs.speechStatusText.textContent = "Automatic listening failed. Use Start Speaking or type your answer.";
    });
  }, delay);
}

function selectInterviewerVoice() {
  const voices = window.speechSynthesis?.getVoices?.() || [];
  if (!voices.length) return null;
  const score = (voice) => {
    const name = `${voice.name} ${voice.voiceURI}`.toLowerCase();
    let value = voice.lang?.toLowerCase().startsWith("en") ? 20 : 0;
    if (/natural|premium|enhanced|neural/.test(name)) value += 14;
    if (/en-in|en-gb|en-us/i.test(voice.lang || "")) value += 8;
    if (voice.localService) value += 3;
    return value;
  };
  return [...voices].sort((left, right) => score(right) - score(left))[0] || null;
}

function speakQuestion(isReplay = false) {
  if (!state.session?.currentQuestion) return;
  if (isReplay) {
    if (state.replayCount >= 2) return;
    state.replayCount += 1;
    refs.replayCount.textContent = `Question replays: ${state.replayCount} / 2`;
  }
  const speechToken = ++state.questionSpeechToken;
  window.speechSynthesis?.cancel();
  if (!("speechSynthesis" in window) || !("SpeechSynthesisUtterance" in window)) {
    refs.transcriptToggle.checked = true;
    refs.questionTranscript.classList.remove("hidden");
    refs.spokenStateText.textContent = "Audio is unavailable. The accessible question transcript is shown below.";
    setPhase(INTERVIEW_STATES.WAITING_FOR_ANSWER);
    showAnswerMethod();
    if (!isReplay) startQuestionTimer();
    scheduleAutomaticListening();
    return;
  }
  setPhase(INTERVIEW_STATES.SPEAKING_QUESTION);
  refs.spokenStateText.textContent = "Interviewer is asking the question...";
  const utterance = new SpeechSynthesisUtterance(state.session.currentQuestion);
  let speechFinished = false;
  const finishQuestionAudio = (message) => {
    if (speechFinished || speechToken !== state.questionSpeechToken) return;
    speechFinished = true;
    window.clearTimeout(state.questionSpeechWatchdog);
    state.questionSpeechWatchdog = null;
    refs.spokenStateText.textContent = state.advancedVoiceEnabled
      ? "Question finished. The microphone will open automatically."
      : message;
    setPhase(INTERVIEW_STATES.WAITING_FOR_ANSWER);
    showAnswerMethod();
    if (!isReplay) startQuestionTimer();
    scheduleAutomaticListening();
  };
  utterance.rate = 0.95;
  utterance.pitch = 0.92;
  const interviewerVoice = selectInterviewerVoice();
  if (interviewerVoice) utterance.voice = interviewerVoice;
  utterance.onend = () => finishQuestionAudio("The interviewer has finished. Choose type or speak to answer.");
  utterance.onerror = () => {
    refs.transcriptToggle.checked = true;
    refs.questionTranscript.classList.remove("hidden");
    finishQuestionAudio("Question audio failed. The accessible transcript is shown below.");
  };
  window.speechSynthesis.speak(utterance);
  const estimatedSpeechMs = Math.min(25_000, Math.max(7_000, wordCount(state.session.currentQuestion) * 480 + 3_000));
  state.questionSpeechWatchdog = window.setTimeout(() => {
    window.speechSynthesis?.cancel();
    refs.transcriptToggle.checked = true;
    refs.questionTranscript.classList.remove("hidden");
    finishQuestionAudio("Question audio ended. The transcript is available below.");
  }, estimatedSpeechMs);
}

function interruptInterviewer() {
  if (state.phase !== INTERVIEW_STATES.SPEAKING_QUESTION) return;
  state.questionSpeechToken += 1;
  state.interviewerInterruptions += 1;
  window.clearTimeout(state.questionSpeechWatchdog);
  state.questionSpeechWatchdog = null;
  window.speechSynthesis?.cancel();
  refs.spokenStateText.textContent = "Interviewer paused. Your microphone is opening now.";
  setPhase(INTERVIEW_STATES.WAITING_FOR_ANSWER);
  showAnswerMethod();
  if (!state.questionTimer) startQuestionTimer();
  scheduleAutomaticListening(150);
}

function setTurnDetectionState(mode, primary, secondary) {
  refs.turnDetectionPanel.classList.toggle("detecting", mode === "detecting");
  refs.turnDetectionPanel.classList.toggle("finishing", mode === "finishing");
  refs.turnDetectionText.textContent = primary;
  refs.silenceCountdown.textContent = secondary;
}

function clearVoiceTurnTimers(resetStatus = true) {
  window.clearTimeout(state.voiceAutoStartTimer);
  window.clearTimeout(state.voiceAutoSubmitTimer);
  window.clearTimeout(state.voiceSubmitDelayTimer);
  window.clearInterval(state.silenceCountdownTimer);
  state.voiceAutoStartTimer = null;
  state.voiceAutoSubmitTimer = null;
  state.voiceSubmitDelayTimer = null;
  state.silenceCountdownTimer = null;
  state.silenceDeadline = 0;
  if (resetStatus) {
    setTurnDetectionState(
      state.advancedVoiceEnabled ? "detecting" : "manual",
      state.advancedVoiceEnabled ? "Automatic turn detection" : "Manual turn control",
      state.advancedVoiceEnabled ? "Listening for a complete answer" : "Use Stop or Submit when finished",
    );
  }
}

function armAutomaticTurnCompletion(delay = 2800) {
  if (!state.advancedVoiceEnabled || state.questionFinalized || wordCount(refs.spokenTranscript.value) < 4) return;
  window.clearTimeout(state.voiceAutoSubmitTimer);
  window.clearInterval(state.silenceCountdownTimer);
  state.silenceDeadline = Date.now() + delay;
  const updateCountdown = () => {
    const remaining = Math.max(0, state.silenceDeadline - Date.now());
    setTurnDetectionState(
      "finishing",
      "Possible end of answer detected",
      `Submitting in ${(remaining / 1000).toFixed(1)}s · keep speaking to continue`,
    );
  };
  updateCountdown();
  state.silenceCountdownTimer = window.setInterval(updateCountdown, 100);
  state.voiceAutoSubmitTimer = window.setTimeout(() => {
    if (state.questionFinalized || !refs.spokenTranscript.value.trim()) return;
    state.currentVoiceAutoSubmitted = true;
    state.silenceStops += 1;
    clearVoiceTurnTimers(false);
    setTurnDetectionState("finishing", "Answer turn complete", "Submitting your transcript...");
    stopRecognition("auto-submit", false);
    window.clearTimeout(state.voiceSubmitDelayTimer);
    state.voiceSubmitDelayTimer = window.setTimeout(() => {
      submitAnswer(refs.spokenTranscript.value, "spoken", { voiceAutoSubmitted: true });
    }, 180);
  }, delay);
}

function resetAnswerPanels() {
  window.clearTimeout(state.questionSpeechWatchdog);
  state.questionSpeechWatchdog = null;
  clearVoiceTurnTimers();
  stopRecognition("reset");
  stopAudioMeter();
  window.clearInterval(state.speechTimer);
  refs.answerMethodPanel.classList.add("hidden");
  refs.typedAnswerForm.classList.add("hidden");
  refs.spokenAnswerPanel.classList.add("hidden");
  refs.typedAnswerInput.value = "";
  refs.spokenTranscript.value = "";
  refs.typedWordCount.textContent = "0 words";
  refs.spokenWordCount.textContent = "0 words";
  refs.spokenElapsed.textContent = "0:00";
  refs.speechMetricPreview.textContent = "Pace appears after recording";
  refs.speechStatusText.textContent = "Ready to listen";
  refs.microphoneDot.classList.remove("listening");
  refs.audioVisualizer.classList.remove("listening");
  refs.submitSpokenButton.disabled = true;
  refs.stopSpeakingButton.disabled = true;
  refs.startSpeakingButton.disabled = false;
  [refs.typeModeButton, refs.speakModeButton].forEach((button) => button.classList.remove("selected"));
  state.answerStartedAt = 0;
  state.speechStartedAt = 0;
  state.speechLastResultAt = 0;
  state.recognitionStarting = false;
  state.recognitionBaseText = "";
  state.recognitionUsingLocal = false;
  state.speechNetworkFallbackAttempted = false;
  state.pauseCount = 0;
  state.recognitionConfidenceTotal = 0;
  state.recognitionConfidenceSamples = 0;
  state.recognitionRestartCount = 0;
  state.currentVoiceAutoSubmitted = false;
  state.interviewerInterruptions = 0;
  state.silenceStops = 0;
}

function showAnswerMethod() {
  if (!state.answerStartedAt) state.answerStartedAt = Date.now();
  refs.answerMethodPanel.classList.remove("hidden");
}

function showTypedAnswer() {
  if (state.recognitionActive) stopRecognition();
  if (!state.answerStartedAt) state.answerStartedAt = Date.now();
  state.answerMode = "typed";
  refs.answerMethodPanel.classList.remove("hidden");
  refs.typedAnswerForm.classList.remove("hidden");
  refs.spokenAnswerPanel.classList.add("hidden");
  refs.typeModeButton.classList.add("selected");
  refs.speakModeButton.classList.remove("selected");
  refs.typedAnswerInput.focus();
}

function showSpokenAnswer() {
  if (!state.answerStartedAt) state.answerStartedAt = Date.now();
  state.answerMode = "spoken";
  refs.answerMethodPanel.classList.remove("hidden");
  refs.typedAnswerForm.classList.add("hidden");
  refs.spokenAnswerPanel.classList.remove("hidden");
  refs.speakModeButton.classList.add("selected");
  refs.typeModeButton.classList.remove("selected");
  refs.speechStatusText.textContent = supportsSpeechInput()
    ? (state.advancedVoiceEnabled ? "Automatic turn detection is ready" : "Ready to listen")
    : speechInputUnavailableMessage();
  refs.startSpeakingButton.disabled = !supportsSpeechInput() || state.questionFinalized;
  clearVoiceTurnTimers();
  if (!supportsSpeechInput()) {
    setTurnDetectionState("manual", "Voice input unavailable here", "Use Chrome or Edge, or type your answer below");
  }
  refs.spokenTranscript.focus();
}

function repeatedPhrases(text) {
  const words = String(text || "").toLowerCase().match(/[a-z0-9']+/g) || [];
  const counts = new Map();
  for (let index = 0; index <= words.length - 3; index += 1) {
    const phrase = words.slice(index, index + 3).join(" ");
    counts.set(phrase, (counts.get(phrase) || 0) + 1);
  }
  return [...counts.entries()].filter(([, count]) => count > 1).sort((a, b) => b[1] - a[1]).slice(0, 5).map(([phrase]) => phrase);
}

function voiceMetrics() {
  const answer = refs.spokenTranscript.value;
  const seconds = Math.max(1, (Date.now() - (state.speechStartedAt || state.answerStartedAt)) / 1000);
  const words = wordCount(answer);
  const fillerMatches = answer.match(/\b(um|uh|like|basically|actually)\b/gi) || [];
  return {
    wordsPerMinute: Math.round(words / (seconds / 60)),
    fillerWords: fillerMatches.length,
    longPauses: state.pauseCount,
    repeatedPhrases: repeatedPhrases(answer),
    transcriptionConfidence: state.recognitionConfidenceSamples
      ? Math.round((state.recognitionConfidenceTotal / state.recognitionConfidenceSamples) * 100)
      : 0,
    turnDetection: state.advancedVoiceEnabled ? "automatic-silence" : "manual",
    autoSubmitted: state.currentVoiceAutoSubmitted,
    silenceStops: state.silenceStops,
    interviewerInterruptions: state.interviewerInterruptions,
  };
}

function updateSpokenMeta() {
  const metrics = voiceMetrics();
  refs.spokenWordCount.textContent = `${wordCount(refs.spokenTranscript.value)} words`;
  refs.spokenElapsed.textContent = formatTime((Date.now() - (state.speechStartedAt || Date.now())) / 1000);
  refs.speechMetricPreview.textContent = `${metrics.wordsPerMinute} WPM · ${metrics.fillerWords} filler words`;
  refs.submitSpokenButton.disabled = !refs.spokenTranscript.value.trim() || state.questionFinalized;
}

function stopAudioMeter() {
  window.cancelAnimationFrame(state.audioFrame);
  state.audioFrame = null;
  state.analyser = null;
  if (state.audioContext && state.audioContext.state !== "closed") state.audioContext.close().catch(() => {});
  state.audioContext = null;
  refs.audioVisualizer?.querySelectorAll("span").forEach((bar) => { bar.style.height = ""; });
}

function startAudioMeter() {
  stopAudioMeter();
  const audioTrack = liveAudioTrack();
  if (!audioTrack || !(window.AudioContext || window.webkitAudioContext)) return;
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  state.audioContext = new AudioContextClass();
  state.analyser = state.audioContext.createAnalyser();
  state.analyser.fftSize = 64;
  const source = state.audioContext.createMediaStreamSource(new MediaStream([audioTrack]));
  source.connect(state.analyser);
  const data = new Uint8Array(state.analyser.frequencyBinCount);
  const bars = [...refs.audioVisualizer.querySelectorAll("span")];
  const draw = () => {
    if (!state.analyser || !state.recognitionActive) return;
    state.analyser.getByteFrequencyData(data);
    bars.forEach((bar, index) => {
      const value = data[Math.floor((index / bars.length) * data.length)] || 0;
      bar.style.height = `${Math.max(10, Math.round(value / 5))}px`;
    });
    state.audioFrame = window.requestAnimationFrame(draw);
  };
  draw();
}

function stopRecognition(reason = "manual", resetTurnDetection = true) {
  if (!state.recognition) return;
  state.recognitionStopReason = reason;
  try { state.recognition.stop(); } catch (_error) { /* Recognition may already be stopped. */ }
  state.recognitionActive = false;
  state.recognitionStarting = false;
  refs.microphoneDot.classList.remove("listening");
  refs.audioVisualizer.classList.remove("listening");
  refs.stopSpeakingButton.disabled = true;
  window.clearInterval(state.speechTimer);
  if (resetTurnDetection) clearVoiceTurnTimers();
  stopAudioMeter();
}

async function startSpeaking(options = {}) {
  if (state.questionFinalized) return;
  if (state.recognitionActive || state.recognitionStarting) return;
  showSpokenAnswer();
  if (!supportsSpeechInput()) throw new Error(speechInputUnavailableMessage());
  state.recognitionStarting = true;
  refs.speechStatusText.textContent = options.forceLocal
    ? "Switching to on-device speech recognition..."
    : "Opening microphone...";
  refs.startSpeakingButton.disabled = true;
  refs.stopSpeakingButton.disabled = true;
  let recognitionMode;
  try {
    await requestSpeechMicrophone();
    recognitionMode = await resolveSpeechRecognitionMode(Boolean(options.forceLocal));
  } catch (error) {
    state.recognitionStarting = false;
    refs.startSpeakingButton.disabled = false;
    throw error;
  }
  const recognition = new SpeechRecognition();
  recognition.lang = "en-US";
  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.maxAlternatives = 1;
  if (recognitionMode === "local" && "processLocally" in recognition) recognition.processLocally = true;
  state.recognitionUsingLocal = recognitionMode === "local";
  recognition.onstart = () => {
    state.recognitionStarting = false;
    state.recognitionActive = true;
    setPhase(INTERVIEW_STATES.RECORDING_ANSWER);
    refs.speechStatusText.textContent = state.recognitionUsingLocal
      ? "Listening on this device..."
      : (options.automatic ? "Listening automatically..." : "Listening...");
    refs.microphoneDot.classList.add("listening");
    refs.audioVisualizer.classList.add("listening");
    refs.startSpeakingButton.disabled = true;
    refs.stopSpeakingButton.disabled = false;
    startAudioMeter();
  };
  recognition.onspeechstart = () => {
    window.clearTimeout(state.voiceAutoSubmitTimer);
    window.clearInterval(state.silenceCountdownTimer);
    setTurnDetectionState("detecting", "Speech detected", "Keep speaking naturally");
  };
  recognition.onspeechend = () => {
    armAutomaticTurnCompletion(2800);
  };
  recognition.onresult = (event) => {
    const now = Date.now();
    if (state.speechLastResultAt && now - state.speechLastResultAt > 2200) state.pauseCount += 1;
    state.speechLastResultAt = now;
    let finalText = "";
    let interimText = "";
    for (let index = 0; index < event.results.length; index += 1) {
      const transcript = event.results[index][0].transcript;
      if (event.results[index].isFinal) {
        finalText += `${transcript} `;
        const confidence = Number(event.results[index][0].confidence);
        if (index >= event.resultIndex && Number.isFinite(confidence) && confidence > 0) {
          state.recognitionConfidenceTotal += confidence;
          state.recognitionConfidenceSamples += 1;
        }
      }
      else interimText += transcript;
    }
    const recognizedText = `${finalText}${interimText}`.trim();
    refs.spokenTranscript.value = [state.recognitionBaseText, recognizedText].filter(Boolean).join(" ");
    if (refs.spokenTranscript.value.trim()) state.recognitionRestartCount = 0;
    updateSpokenMeta();
    armAutomaticTurnCompletion(2800);
  };
  recognition.onerror = (event) => {
    if (event.error === "network" && !state.recognitionUsingLocal && !state.speechNetworkFallbackAttempted) {
      state.speechNetworkFallbackAttempted = true;
      state.recognitionStopReason = "retry-local";
      refs.speechStatusText.textContent = "Online speech service unavailable. Switching to on-device recognition...";
      return;
    }
    if (event.error !== "no-speech" && event.error !== "aborted") {
      state.recognitionStopReason = `error-${event.error}`;
      const message = speechRecognitionErrorMessage(event.error);
      refs.speechStatusText.textContent = message;
      showToast(message, "error");
    }
  };
  recognition.onend = () => {
    const endedNaturally = !state.recognitionStopReason;
    state.recognitionActive = false;
    state.recognitionStarting = false;
    refs.microphoneDot.classList.remove("listening");
    refs.audioVisualizer.classList.remove("listening");
    refs.stopSpeakingButton.disabled = true;
    refs.startSpeakingButton.disabled = state.questionFinalized;
    if (state.recognitionStopReason === "retry-local") {
      refs.speechStatusText.textContent = "Preparing the on-device English language pack...";
      stopAudioMeter();
      window.clearTimeout(state.voiceAutoStartTimer);
      state.voiceAutoStartTimer = window.setTimeout(() => {
        startSpeaking({ automatic: options.automatic, forceLocal: true }).catch((error) => {
          refs.speechStatusText.textContent = error.message;
          refs.startSpeakingButton.disabled = false;
          showToast(error.message, "error");
        });
      }, 300);
      return;
    }
    if (!state.recognitionStopReason.startsWith("error-")) {
      refs.speechStatusText.textContent = refs.spokenTranscript.value.trim()
        ? (state.advancedVoiceEnabled ? "Speech paused. Detecting whether your answer is complete..." : "Recording stopped. Review or submit.")
        : "Ready to try again.";
    }
    stopAudioMeter();
    if (endedNaturally && state.advancedVoiceEnabled && !state.questionFinalized) {
      if (refs.spokenTranscript.value.trim()) {
        armAutomaticTurnCompletion(900);
      } else if (state.recognitionRestartCount < 2) {
        state.recognitionRestartCount += 1;
        refs.speechStatusText.textContent = "No speech detected. Listening will restart...";
        state.voiceAutoStartTimer = window.setTimeout(
          () => startSpeaking({ automatic: true }).catch((error) => showToast(error.message, "error")),
          700,
        );
      } else {
        refs.speechStatusText.textContent = "No speech detected. Use Start Speaking or type your answer.";
      }
    }
  };
  state.recognition = recognition;
  state.recognitionStopReason = "";
  state.recognitionBaseText = refs.spokenTranscript.value.trim();
  state.speechStartedAt = Date.now();
  state.speechLastResultAt = 0;
  state.pauseCount = 0;
  try {
    recognition.start();
  } catch (_error) {
    state.recognitionStarting = false;
    refs.startSpeakingButton.disabled = false;
    throw new Error("Speech recognition could not start. Check microphone permission and try again.");
  }
  setTurnDetectionState(
    state.advancedVoiceEnabled ? "detecting" : "manual",
    state.advancedVoiceEnabled ? "Automatic turn detection" : "Manual turn control",
    state.advancedVoiceEnabled ? "A short silence will complete your answer" : "Use Stop or Submit when finished",
  );
  state.speechTimer = window.setInterval(updateSpokenMeta, 500);
}

function startInterviewTimers() {
  stopInterviewTimers();
  state.interviewEndsAt = Date.now() + Number(state.meta.durationMinutes) * 60_000;
  const updateInterview = () => {
    const remaining = Math.ceil((state.interviewEndsAt - Date.now()) / 1000);
    refs.interviewTimerValue.textContent = formatTime(remaining);
    if (remaining <= 0) {
      window.clearInterval(state.interviewTimer);
      refs.interviewTimerValue.textContent = "0:00";
    }
  };
  updateInterview();
  state.interviewTimer = window.setInterval(updateInterview, 1000);
}

function startQuestionTimer() {
  window.clearInterval(state.questionTimer);
  state.questionStartedAt = Date.now();
  const seconds = 120;
  state.questionEndsAt = Date.now() + seconds * 1000;
  const update = () => {
    const remaining = Math.ceil((state.questionEndsAt - Date.now()) / 1000);
    refs.questionTimerValue.textContent = formatTime(remaining);
    if (remaining === 30) {
      refs.warningBanner.textContent = "30 seconds remaining. Prioritize your reasoning and conclusion.";
      refs.warningBanner.classList.remove("hidden");
    }
    if (remaining === 10) {
      refs.warningBanner.textContent = "You have 10 seconds left. Lead with your strongest point.";
      refs.warningBanner.classList.remove("hidden");
    }
    if (remaining <= 0) {
      window.clearInterval(state.questionTimer);
      if (state.session?.status === "active" && !state.questionFinalized) {
        const answerType = state.answerMode || "typed";
        const answer = answerType === "spoken" ? refs.spokenTranscript.value : refs.typedAnswerInput.value;
        setPhase(INTERVIEW_STATES.TIMEOUT);
        refs.warningBanner.textContent = "Time ended. Your current response has been locked and recorded.";
        refs.warningBanner.classList.remove("hidden");
        submitAnswer(answer, answerType, { timedOut: true });
      }
    }
  };
  update();
  state.questionTimer = window.setInterval(update, 1000);
}

function stopInterviewTimers() {
  window.clearInterval(state.interviewTimer);
  window.clearInterval(state.questionTimer);
  state.interviewTimer = null;
  state.questionTimer = null;
}

function wordCount(text) {
  return String(text || "").trim().split(/\s+/).filter(Boolean).length;
}

function setAnswerControlsDisabled(disabled) {
  refs.typedAnswerInput.disabled = disabled;
  refs.spokenTranscript.disabled = disabled;
  refs.typedAnswerForm.querySelectorAll("button").forEach((button) => { button.disabled = disabled; });
  refs.spokenAnswerPanel.querySelectorAll("button").forEach((button) => { button.disabled = disabled; });
  refs.answerMethodPanel.querySelectorAll("button").forEach((button) => { button.disabled = disabled; });
}

async function submitAnswer(answer, answerType, options = {}) {
  if (state.exiting || !state.session || state.questionFinalized || state.phase === INTERVIEW_STATES.PROCESSING_ANSWER) return;
  const cleaned = String(answer || "").trim();
  if (!cleaned && answerType !== "skipped" && !options.timedOut) {
    showToast("Add an answer before submitting.", "error");
    return;
  }
  if (options.voiceAutoSubmitted) state.currentVoiceAutoSubmitted = true;
  const submittedVoiceMetrics = answerType === "spoken" ? voiceMetrics() : {};
  state.questionFinalized = true;
  setAnswerControlsDisabled(true);
  clearVoiceTurnTimers(false);
  stopRecognition("submit", false);
  window.speechSynthesis?.cancel();
  window.clearInterval(state.questionTimer);
  if (options.timedOut) {
    await new Promise((resolve) => {
      state.answerDelayResolve = resolve;
      state.answerDelayTimer = window.setTimeout(() => {
        state.answerDelayTimer = null;
        state.answerDelayResolve = null;
        resolve();
      }, 650);
    });
  }
  if (state.exiting) return;
  setPhase(INTERVIEW_STATES.PROCESSING_ANSWER);
  const durationSeconds = options.timedOut
    ? 120
    : Math.max(1, Math.min(120, Math.round((Date.now() - (state.answerStartedAt || state.questionStartedAt)) / 1000)));
  try {
    const response = await api("/api/interview/answer", {
      method: "POST",
      body: JSON.stringify({
        sessionId: state.session.id,
        answer: cleaned,
        answerType,
        durationSeconds,
        timedOut: Boolean(options.timedOut),
        voiceMetrics: submittedVoiceMetrics,
        persistentQuestionIds: currentQuestionIds(),
      }),
    });
    if (state.exiting) return;
    state.session = response.session;
    refs.warningBanner.classList.add("hidden");
    if (response.evaluation.complete) {
      state.report = response.report;
      finishInterview();
      return;
    }
    setPhase(INTERVIEW_STATES.QUESTION_COMPLETE);
    renderSession();
    setAnswerControlsDisabled(false);
    resetAnswerPanels();
    window.clearTimeout(state.nextQuestionTimer);
    state.nextQuestionTimer = window.setTimeout(() => {
      if (state.exiting) return;
      setPhase(INTERVIEW_STATES.PREPARING_QUESTION);
      refs.spokenStateText.textContent = "The interviewer is selecting the next question...";
      window.clearTimeout(state.nextQuestionSpeechTimer);
      state.nextQuestionSpeechTimer = window.setTimeout(() => {
        if (!state.exiting) speakQuestion(false);
      }, 650);
    }, 500);
  } catch (error) {
    if (error?.name === "AbortError" || state.exiting) return;
    state.questionFinalized = false;
    setAnswerControlsDisabled(false);
    showToast(error.message, "error");
    setPhase(INTERVIEW_STATES.WAITING_FOR_ANSWER);
  }
}

function cancelCountdown() {
  window.clearInterval(state.countdownTimer);
  window.clearTimeout(state.countdownHideTimer);
  state.countdownTimer = null;
  state.countdownHideTimer = null;
  refs.countdownOverlay.classList.add("hidden");
  const resolve = state.countdownResolve;
  state.countdownResolve = null;
  resolve?.();
}

function countdown() {
  cancelCountdown();
  return new Promise((resolve) => {
    state.countdownResolve = resolve;
    refs.countdownOverlay.classList.remove("hidden");
    let value = 3;
    refs.countdownValue.textContent = value;
    state.countdownTimer = window.setInterval(() => {
      value -= 1;
      if (value > 0) refs.countdownValue.textContent = value;
      else {
        refs.countdownValue.textContent = "Started";
        window.clearInterval(state.countdownTimer);
        state.countdownTimer = null;
        state.countdownHideTimer = window.setTimeout(() => {
          refs.countdownOverlay.classList.add("hidden");
          const finish = state.countdownResolve;
          state.countdownResolve = null;
          state.countdownHideTimer = null;
          finish?.();
        }, 550);
      }
    }, 800);
  });
}

async function startInterview(event) {
  event.preventDefault();
  state.exiting = false;
  if (!refs.privacyConsent.checked) {
    showToast("Please review and accept the privacy notice before starting.", "error");
    return;
  }
  if (!state.systemChecked) {
    state.systemChecked = true;
    const speakerReady = "speechSynthesis" in window;
    systemStatus(refs.speakerCheckStatus, speakerReady ? "Audio output ready" : "Transcript fallback enabled", speakerReady);
    systemStatus(refs.browserCheckStatus, "Browser ready", true);
    systemStatus(refs.cameraCheckStatus, "Not checked; limited mode", false);
    systemStatus(refs.microphoneCheckStatus, "Not checked; typed answers remain available", false);
    refs.systemOverallStatus.textContent = "Limited mode";
    refs.systemOverallStatus.dataset.tone = "warning";
    showToast("Starting in limited mode. You can enable the camera during the interview.");
  }
  refs.startInterviewButton.disabled = true;
  refs.startInterviewButton.textContent = "Preparing interview...";
  const form = new FormData(refs.interviewSetupForm);
  state.advancedVoiceEnabled = Boolean(refs.advancedVoiceMode.checked && supportsSpeechInput());
  if (refs.advancedVoiceMode.checked && !supportsSpeechInput()) {
    showToast(`${speechInputUnavailableMessage()} Typed answers will remain available.`, "error");
  }
  try {
    const response = await api("/api/interview/start", {
      method: "POST",
      body: JSON.stringify({
        company: form.get("company"),
        roundType: form.get("roundType"),
        domain: form.get("domain"),
        difficulty: form.get("difficulty"),
        persistentQuestionIds: currentQuestionIds(),
      }),
    });
    state.session = response.session;
    state.meta = response.meta;
    state.report = null;
    refs.preInterviewView.classList.add("hidden");
    refs.reportView.classList.add("hidden");
    refs.interviewView.classList.remove("hidden");
    exitController.setActive(true);
    resetAnswerPanels();
    renderSession();
    setPhase(INTERVIEW_STATES.PREPARING_QUESTION);
    await countdown();
    if (state.exiting) return;
    startInterviewTimers();
    speakQuestion(false);
  } catch (error) {
    handleAsyncError(error);
  } finally {
    refs.startInterviewButton.disabled = false;
    refs.startInterviewButton.textContent = "Start Interview";
  }
}

function appendList(target, items, emptyText) {
  const values = Array.isArray(items) ? items.filter(Boolean) : [];
  target.innerHTML = (values.length ? values : [emptyText]).map((item) => `<li>${escapeHtml(item)}</li>`).join("");
}

function statRows(values) {
  return Object.entries(values)
    .map(([label, value]) => `<div><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`)
    .join("");
}

function renderReport(report) {
  refs.reportContext.textContent = `${report.company}-style ${ROUND_LABELS[report.roundType] || report.roundType} · ${capitalize(report.difficulty)}`;
  refs.reportOverall.textContent = formatScore(report.overallScore);
  refs.reportTechnical.textContent = formatScore(report.technicalScore);
  refs.reportCommunication.textContent = formatScore(report.communicationScore);
  refs.reportRelevance.textContent = formatScore(report.relevanceScore);
  appendList(refs.reportStrengths, report.strengths, "Complete another interview to build a stronger signal.");
  appendList(refs.reportWeaknesses, report.suggestions, "Keep adding examples and explicit trade-offs.");
  refs.recommendedTopics.innerHTML = (report.recommendedTopics || []).length
    ? report.recommendedTopics.map((topic) => `<a href="/learning?search=${encodeURIComponent(topic)}">${escapeHtml(topic)} <span>Practice in Learning</span></a>`).join("")
    : '<a href="/learning">Explore recommended questions <span>Open Learning</span></a>';
  refs.integrityAnalysis.innerHTML = statRows({
    "Session status": report.integrity.status,
    "Tab switches": report.integrity.tabSwitches,
    "Window focus losses": report.integrity.windowBlurs,
    "Total time away": `${Math.round(report.integrity.totalTimeAway)}s`,
    "Attention warnings": report.integrity.attentionWarnings,
    "Face absence events": report.integrity.faceAbsenceEvents,
    "Multiple people events": report.integrity.multiplePeopleEvents,
    "Camera interruptions": report.integrity.cameraInterruptions,
    "Microphone interruptions": report.integrity.microphoneInterruptions,
  });
  const adaptive = report.adaptive || {};
  const counts = adaptive.classificationCounts || {};
  refs.adaptiveAnalysis.innerHTML = statRows({
    "Starting difficulty": capitalize(adaptive.startingDifficulty),
    "Ending difficulty": capitalize(adaptive.endingDifficulty),
    "Strong answers": counts.strong || 0,
    "Partial answers": counts.partial || 0,
    "Wrong answers": counts.wrong || 0,
    "Insufficient answers": counts.insufficient || 0,
    "Timeouts": counts.timeout || 0,
    "Adaptive follow-ups": adaptive.generatedFollowUps || 0,
    "AI-generated": adaptive.aiGeneratedFollowUps || 0,
  });
  const voice = report.voice || {};
  refs.voiceAnalysis.innerHTML = statRows({
    "Speaking pace": voice.wordsPerMinute ? `${voice.wordsPerMinute} WPM` : "No spoken answers",
    "Filler words": voice.fillerWords || 0,
    "Long pauses": voice.longPauses || 0,
    "Automatic turn endings": voice.automaticTurnCompletions || 0,
    "Interviewer interruptions": voice.interviewerInterruptions || 0,
    "Transcript confidence": voice.averageTranscriptionConfidence ? `${voice.averageTranscriptionConfidence}%` : "Not reported",
  });
  refs.adaptiveTimeline.innerHTML = (adaptive.progression || []).map((step) => `
    <article class="adaptive-step">
      <span>Question ${step.questionNumber}</span>
      <strong>${escapeHtml(capitalize(step.classification))}</strong>
      <small>${escapeHtml(capitalize(step.fromDifficulty))} → ${escapeHtml(capitalize(step.toDifficulty))} · ${step.responseTime}s</small>
    </article>
  `).join("") || '<p class="subtle">Adaptive progression will appear after completed answers.</p>';
  refs.answerReviewList.innerHTML = (report.answers || []).map((answer) => `
    <details class="answer-review-card" ${answer.questionNumber === 1 ? "open" : ""}>
      <summary><span>Question ${answer.questionNumber} · ${escapeHtml(answer.topic)} ${answer.isFollowUp ? '<em class="classification-chip follow-up-chip">Adaptive follow-up</em>' : ""} <em class="classification-chip">${escapeHtml(answer.classification)}</em></span><strong>${formatScore(answer.score)} / 100</strong></summary>
      <div class="answer-review-content">
        <div class="review-block"><span>${escapeHtml(answer.company)} style · ${escapeHtml(capitalize(answer.difficulty))} · ${answer.responseTime}s${answer.timedOut ? " · Timed out" : ""}</span><p>${escapeHtml(answer.question)}</p></div>
        <div class="review-block"><span>Your ${escapeHtml(answer.answerType)} answer</span><p>${escapeHtml(answer.answer)}</p></div>
        <div class="review-columns">
          <div><h4>What you did well</h4><ul>${(answer.whatWentWell || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></div>
          <div><h4>What could improve</h4><ul>${(answer.couldImprove || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></div>
        </div>
        <div class="review-block ideal-answer"><span>Ideal answer</span><p>${escapeHtml(answer.idealAnswer)}</p></div>
        <div class="review-block"><span>Key concepts missed</span><div class="chip-row">${(answer.missedConcepts || []).map((item) => `<span class="chip">${escapeHtml(item)}</span>`).join("") || '<span class="subtle">No major keyword gaps detected.</span>'}</div></div>
        ${answer.isFollowUp && answer.followUpReason ? `<div class="review-block adaptive-explanation"><span>Why this follow-up was asked</span><p>${escapeHtml(answer.followUpReason)}</p></div>` : ""}
      </div>
    </details>
  `).join("");
}

function handleAsyncError(error) {
  if (error?.name === "AbortError" || state.exiting) return;
  showToast(error.message, "error");
}

function clearInterviewAsyncWork() {
  window.clearTimeout(state.warningTimer);
  window.clearTimeout(state.questionSpeechWatchdog);
  window.clearTimeout(state.nextQuestionTimer);
  window.clearTimeout(state.nextQuestionSpeechTimer);
  window.clearTimeout(state.systemCheckTimeout);
  window.clearTimeout(state.answerDelayTimer);
  window.clearInterval(state.speechTimer);
  state.warningTimer = null;
  state.questionSpeechWatchdog = null;
  state.nextQuestionTimer = null;
  state.nextQuestionSpeechTimer = null;
  state.systemCheckTimeout = null;
  state.answerDelayTimer = null;
  state.speechTimer = null;
  const resolveAnswerDelay = state.answerDelayResolve;
  state.answerDelayResolve = null;
  resolveAnswerDelay?.();
  clearVoiceTurnTimers(false);
  cancelCountdown();
}

async function cleanupInterviewResources() {
  state.exiting = true;
  state.mediaRequestToken += 1;
  state.speechRequestToken += 1;
  requests.abortAll();
  stopInterviewTimers();
  clearInterviewAsyncWork();
  state.questionSpeechToken += 1;
  window.speechSynthesis?.cancel();
  stopRecognition("exit", false);
  state.recognition = null;
  state.recognitionActive = false;
  state.recognitionStarting = false;
  stopAudioMeter();
  stopFaceChecks();
  state.awayStartedAt = null;
  state.awayEventType = null;
  refs.warningBanner.classList.add("hidden");
  await stopMediaStream();
}

async function abandonCurrentInterview(sessionId) {
  if (!sessionId) return;
  try {
    await api("/api/interview/abandon", {
      method: "POST",
      body: JSON.stringify({ sessionId }),
    }, false);
  } catch (_error) {
    // Resource cleanup and navigation must still complete if abandonment cannot be recorded.
  }
}

function resetActiveInterview() {
  state.session = null;
  state.meta = null;
  state.report = null;
  state.replayCount = 0;
  state.questionStartedAt = 0;
  state.answerStartedAt = 0;
  state.interviewEndsAt = 0;
  state.questionEndsAt = 0;
  state.answerMode = null;
  state.questionFinalized = false;
  state.advancedVoiceEnabled = false;
  state.awayStartedAt = null;
  state.awayEventType = null;
  resetAnswerPanels();
  setAnswerControlsDisabled(false);
  setPhase(INTERVIEW_STATES.IDLE);
  refs.progressFill.style.width = "0%";
  refs.interviewTimerValue.textContent = "30:00";
  refs.questionTimerValue.textContent = "02:00";
  refs.questionProgressLabel.textContent = "Question 1 of 5";
  refs.topicLabel.textContent = "Topic loading";
  refs.integrityBadge.textContent = "Session: Normal";
  refs.sessionStatusText.textContent = "Normal";
  refs.tabSwitchCount.textContent = "0";
  refs.attentionWarningCount.textContent = "0";
  refs.questionTranscript.textContent = "";
  refs.warningBanner.classList.add("hidden");
  refs.countdownOverlay.classList.add("hidden");
  refs.cameraToggleButton.textContent = "Enable Camera & Microphone";
  refs.runSystemCheckButton.disabled = false;
  refs.runSystemCheckButton.textContent = "Run System Check Again";
  refs.interviewView.classList.add("hidden");
  refs.reportView.classList.add("hidden");
  refs.preInterviewView.classList.remove("hidden");
}

async function leaveActiveInterview(destination) {
  if (state.exiting) return;
  const sessionId = state.session?.id;
  await cleanupInterviewResources();
  await abandonCurrentInterview(sessionId);
  resetActiveInterview();
  exitController.setActive(false);

  if (destination === "dashboard") {
    exitController.allowNavigation();
    window.location.href = "/dashboard";
    return;
  }

  state.exiting = false;
  refs.preInterviewView.scrollIntoView({ behavior: "smooth", block: "start" });
}

function finishInterview() {
  stopInterviewTimers();
  clearInterviewAsyncWork();
  stopRecognition();
  window.speechSynthesis?.cancel();
  stopMediaStream().catch(() => {});
  exitController.setActive(false);
  setPhase(INTERVIEW_STATES.INTERVIEW_COMPLETE);
  refs.progressFill.style.width = "100%";
  refs.interviewView.classList.add("hidden");
  refs.reportView.classList.remove("hidden");
  renderReport(state.report);
  loadDashboard().catch(() => {});
  refs.reportView.scrollIntoView({ behavior: "smooth", block: "start" });
}

function newInterview() {
  exitController.setActive(false);
  state.exiting = false;
  state.session = null;
  state.report = null;
  state.questionFinalized = false;
  resetAnswerPanels();
  setPhase(INTERVIEW_STATES.IDLE);
  refs.reportView.classList.add("hidden");
  refs.interviewView.classList.add("hidden");
  refs.preInterviewView.classList.remove("hidden");
  refs.preInterviewView.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function authSubmit(event, endpoint) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const body = Object.fromEntries(form.entries());
  try {
    const payload = await api(`/api/auth/${endpoint}`, { method: "POST", body: JSON.stringify(body) });
    state.user = payload.user;
    setAuthenticated(true);
    await Promise.all([loadDashboard(), loadOptions()]);
    showToast(endpoint === "signup" ? "Account created. Your interview room is ready." : "Welcome back.");
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function loadOptions() {
  renderOptions(await api("/api/interview/options", { method: "GET" }));
}

async function logout() {
  const activeSessionId = exitController.isActive() ? state.session?.id : null;
  if (activeSessionId) {
    await cleanupInterviewResources();
    await abandonCurrentInterview(activeSessionId);
    resetActiveInterview();
    exitController.setActive(false);
  } else {
    stopInterviewTimers();
    await stopMediaStream();
    clearInterviewAsyncWork();
    window.speechSynthesis?.cancel();
  }
  await api("/api/auth/logout", { method: "POST", body: "{}" });
  state.user = null;
  state.session = null;
  state.exiting = false;
  setAuthenticated(false);
}

function bindEvents() {
  document.querySelectorAll("[data-auth-tab]").forEach((button) => {
    button.addEventListener("click", () => {
      const signup = button.dataset.authTab === "signup";
      refs.loginForm.classList.toggle("hidden", signup);
      refs.signupForm.classList.toggle("hidden", !signup);
      document.querySelectorAll("[data-auth-tab]").forEach((item) => item.classList.toggle("active", item === button));
    });
  });
  refs.loginForm.addEventListener("submit", (event) => authSubmit(event, "login"));
  refs.signupForm.addEventListener("submit", (event) => authSubmit(event, "signup"));
  refs.logoutButton.addEventListener("click", () => logout().catch((error) => showToast(error.message, "error")));
  refs.themeToggle.addEventListener("click", () => applyTheme(document.body.dataset.theme === "dark" ? "light" : "dark"));
  refs.runSystemCheckButton.addEventListener("click", () => runSystemCheck().catch(handleAsyncError));
  refs.interviewSetupForm.addEventListener("submit", startInterview);
  refs.repeatQuestionButton.addEventListener("click", () => speakQuestion(true));
  refs.interruptInterviewerButton.addEventListener("click", interruptInterviewer);
  refs.transcriptToggle.addEventListener("change", () => refs.questionTranscript.classList.toggle("hidden", !refs.transcriptToggle.checked));
  refs.typedAnswerInput.addEventListener("input", () => {
    refs.typedWordCount.textContent = `${wordCount(refs.typedAnswerInput.value)} words`;
    refs.typedElapsed.textContent = `${formatTime((Date.now() - state.answerStartedAt) / 1000)} elapsed`;
  });
  refs.typedAnswerForm.addEventListener("submit", (event) => {
    event.preventDefault();
    submitAnswer(refs.typedAnswerInput.value, "typed");
  });
  refs.typeModeButton.addEventListener("click", showTypedAnswer);
  refs.speakModeButton.addEventListener("click", showSpokenAnswer);
  refs.startSpeakingButton.addEventListener("click", () => startSpeaking().catch(handleAsyncError));
  refs.stopSpeakingButton.addEventListener("click", () => {
    stopRecognition("manual-stop");
    setTurnDetectionState("manual", "Recording stopped", "Review the transcript or submit your answer");
    setPhase(INTERVIEW_STATES.WAITING_FOR_ANSWER);
  });
  refs.submitSpokenButton.addEventListener("click", () => {
    stopRecognition("manual-submit");
    window.clearTimeout(state.voiceSubmitDelayTimer);
    state.voiceSubmitDelayTimer = window.setTimeout(
      () => submitAnswer(refs.spokenTranscript.value, "spoken"),
      180,
    );
  });
  refs.spokenTranscript.addEventListener("input", updateSpokenMeta);
  refs.clearTypedButton.addEventListener("click", () => {
    refs.typedAnswerInput.value = "";
    refs.typedWordCount.textContent = "0 words";
    refs.typedAnswerInput.focus();
  });
  document.querySelectorAll(".skip-answer-button").forEach((button) => button.addEventListener("click", () => submitAnswer("Question skipped by candidate.", "skipped")));
  refs.cameraToggleButton.addEventListener("click", async () => {
    if (state.mediaStream) {
      await stopMediaStream();
      refs.cameraToggleButton.textContent = "Enable Camera & Microphone";
      recordIntegrityEvent("CAMERA_DISABLED", 0, 1, "Camera disabled. Re-enable it when you are ready.");
      recordIntegrityEvent("MICROPHONE_DISABLED", 0, 1);
    } else {
      try { await requestMedia(); } catch (error) { handleAsyncError(error); }
    }
  });
  refs.newInterviewButton.addEventListener("click", newInterview);
  document.addEventListener("visibilitychange", () => document.hidden ? handlePageHidden("TAB_SWITCH") : handlePageVisible());
  window.addEventListener("blur", () => { if (!document.hidden) handlePageHidden("WINDOW_BLUR"); });
  window.addEventListener("focus", handlePageVisible);
  window.addEventListener("pagehide", () => {
    const sessionId = exitController.isActive() ? state.session?.id : null;
    if (sessionId) {
      window.fetch("/api/interview/abandon", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sessionId }),
        credentials: "same-origin",
        keepalive: true,
      }).catch(() => {});
    }
    cleanupInterviewResources().catch(() => {});
  });
}

async function bootstrap() {
  applyTheme(localStorage.getItem("interview-theme") || "dark");
  renderVoiceCompatibility();
  bindEvents();
  await loadOptions();
  const sessionPayload = await api("/api/auth/session", { method: "GET" });
  setAuthenticated(sessionPayload.authenticated);
  if (sessionPayload.authenticated) {
    state.user = sessionPayload.user;
    await loadDashboard();
  }
}

exitController = createSessionExitController({
  backButton: refs.interviewBackButton,
  quitButton: refs.interviewQuitButton,
  back: {
    title: "Go Back?",
    message: "Going back will end your current session. Do you want to continue?",
    cancelText: "Stay Here",
    confirmText: "Go Back",
  },
  quit: {
    title: "Quit Interview?",
    message: "Are you sure you want to quit this interview? Your current interview progress will be discarded.",
    cancelText: "Continue",
    confirmText: "Quit",
  },
  onBack: () => leaveActiveInterview("setup"),
  onQuit: () => leaveActiveInterview("dashboard"),
  onError: handleAsyncError,
});

bootstrap().catch(handleAsyncError);
