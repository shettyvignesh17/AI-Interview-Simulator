export function createRequestTracker() {
  const controllers = new Set();

  function trackedFetch(url, options = {}, { tracked = true } = {}) {
    if (!tracked || options.signal) return window.fetch(url, options);

    const controller = new AbortController();
    controllers.add(controller);
    return window.fetch(url, { ...options, signal: controller.signal })
      .finally(() => controllers.delete(controller));
  }

  function abortAll() {
    controllers.forEach((controller) => controller.abort());
    controllers.clear();
  }

  return { fetch: trackedFetch, abortAll };
}

export function createSessionExitController({
  backButton,
  quitButton,
  back,
  quit,
  onBack,
  onQuit,
  onError = () => {},
}) {
  const dialog = document.createElement("dialog");
  dialog.className = "session-exit-dialog";
  dialog.setAttribute("aria-labelledby", "sessionExitDialogTitle");
  dialog.setAttribute("aria-describedby", "sessionExitDialogMessage");
  dialog.innerHTML = `
    <div class="session-exit-dialog-card">
      <div class="session-exit-dialog-icon" aria-hidden="true">!</div>
      <p class="eyebrow">Active Session</p>
      <h2 id="sessionExitDialogTitle"></h2>
      <p id="sessionExitDialogMessage" class="session-exit-dialog-message"></p>
      <div class="session-exit-dialog-actions">
        <button class="secondary-button session-exit-cancel" type="button"></button>
        <button class="session-exit-confirm" type="button"></button>
      </div>
    </div>`;
  document.body.append(dialog);

  const title = dialog.querySelector("#sessionExitDialogTitle");
  const message = dialog.querySelector("#sessionExitDialogMessage");
  const cancelButton = dialog.querySelector(".session-exit-cancel");
  const confirmButton = dialog.querySelector(".session-exit-confirm");
  let sessionActive = false;
  let navigationApproved = false;
  let busy = false;
  let pendingAction = null;

  function setBusy(nextBusy) {
    busy = nextBusy;
    dialog.setAttribute("aria-busy", String(nextBusy));
    cancelButton.disabled = nextBusy;
    confirmButton.disabled = nextBusy;
    backButton.disabled = nextBusy;
    quitButton.disabled = nextBusy;
  }

  function closeDialog() {
    if (!busy && dialog.open) dialog.close();
  }

  function openDialog(kind) {
    if (!sessionActive || busy) return;
    const config = kind === "back" ? back : quit;
    pendingAction = kind;
    title.textContent = config.title;
    message.textContent = config.message;
    cancelButton.textContent = config.cancelText;
    confirmButton.textContent = config.confirmText;
    confirmButton.className = `session-exit-confirm ${kind === "quit" ? "danger-button" : "primary-button"}`;
    dialog.dataset.variant = kind;
    dialog.showModal();
    window.requestAnimationFrame(() => cancelButton.focus());
  }

  async function confirmExit() {
    if (busy || !pendingAction) return;
    const action = pendingAction;
    setBusy(true);
    navigationApproved = true;
    try {
      await (action === "back" ? onBack : onQuit)();
      sessionActive = false;
      if (dialog.open) dialog.close();
    } catch (error) {
      navigationApproved = false;
      setBusy(false);
      onError(error);
      return;
    }
    pendingAction = null;
    setBusy(false);
    navigationApproved = false;
  }

  function warnBeforeUnload(event) {
    if (!sessionActive || navigationApproved) return undefined;
    event.preventDefault();
    event.returnValue = "";
    return "";
  }

  backButton.addEventListener("click", () => openDialog("back"));
  quitButton.addEventListener("click", () => openDialog("quit"));
  cancelButton.addEventListener("click", closeDialog);
  confirmButton.addEventListener("click", confirmExit);
  dialog.addEventListener("cancel", (event) => {
    if (busy) event.preventDefault();
  });
  window.addEventListener("beforeunload", warnBeforeUnload);

  return {
    setActive(active) {
      sessionActive = Boolean(active);
      if (!sessionActive && dialog.open && !busy) dialog.close();
    },
    isActive() {
      return sessionActive;
    },
    allowNavigation() {
      navigationApproved = true;
    },
    destroy() {
      window.removeEventListener("beforeunload", warnBeforeUnload);
      dialog.remove();
    },
  };
}
