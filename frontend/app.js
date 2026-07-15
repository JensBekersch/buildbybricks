const appDescription = document.querySelector("#app-description");
const runtimeStatus = document.querySelector("#runtime-status");

const architectureForm = document.querySelector("#architecture-form");
const architectureDescription = document.querySelector("#architecture-description");
const architectureGenerationMode = document.querySelector("#architecture-generation-mode");
const generateArchitectureButton = document.querySelector("#generate-architecture");
const cancelArchitectureJobButton = document.querySelector("#cancel-architecture-job");
const retryArchitectureJobButton = document.querySelector("#retry-architecture-job");
const refreshArchitectureJobsButton = document.querySelector("#refresh-architecture-jobs");
const llmProvider = document.querySelector("#llm-provider");
const llmModel = document.querySelector("#llm-model");
const llmTimeout = document.querySelector("#llm-timeout");
const llmTokenBudget = document.querySelector("#llm-token-budget");
const llmPipelineMode = document.querySelector("#llm-pipeline-mode");
const architectureStatus = document.querySelector("#architecture-status");
const architectureProgress = document.querySelector("#architecture-progress");
const architectureProgressLabel = document.querySelector("#architecture-progress-label");
const architectureProgressElapsed = document.querySelector("#architecture-progress-elapsed");
const architectureProgressSteps = document.querySelector("#architecture-progress-steps");
const architectureEmpty = document.querySelector("#architecture-empty");
const architectureResult = document.querySelector("#architecture-result");
const agentStepList = document.querySelector("#agent-step-list");
const agentViewerKicker = document.querySelector("#agent-viewer-kicker");
const agentViewerTitle = document.querySelector("#agent-viewer-title");
const agentViewerStatus = document.querySelector("#agent-viewer-status");
const agentViewerBody = document.querySelector("#agent-viewer-body");
const architectureReviewStatus = document.querySelector("#architecture-review-status");
const architectureSchema = document.querySelector("#architecture-schema");
const architectureProvider = document.querySelector("#architecture-provider");
const architecturePipeline = document.querySelector("#architecture-pipeline");
const architectureArtifact = document.querySelector("#architecture-artifact");
const architectureSourceCount = document.querySelector("#architecture-source-count");
const architectureSources = document.querySelector("#architecture-sources");
const architectureJobList = document.querySelector("#architecture-job-list");
const architectureJobLogs = document.querySelector("#architecture-job-logs");
const architectureTrace = document.querySelector("#architecture-trace");

let applications = [];
let runtimeConfig = null;
let activeAppId = "software-factory";
let activeArchitectureJobId = "";
let activeArchitectureJob = null;
let activeAgentStepKey = "";
let architectureEventSource = null;
let architecturePollingTimer = null;

function appPath(appId, ...segments) {
  return ["/apps", appId, ...segments]
    .map((part, index) => (index === 0 ? part : encodeURIComponent(part)))
    .join("/");
}

async function getJson(url) {
  const response = await fetch(url);
  const payload = await response.json();

  if (!response.ok) {
    throw new Error(payload.error || "Die Anfrage konnte nicht verarbeitet werden.");
  }

  return payload;
}

async function postJson(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  const payload = await response.json();

  if (!response.ok) {
    throw new Error(payload.error || "Die Anfrage konnte nicht verarbeitet werden.");
  }

  return payload;
}

function formatDateTime(value) {
  if (!value) {
    return "-";
  }

  return new Intl.DateTimeFormat("de-DE", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function selectedApplication() {
  return applications.find((application) => application.id === activeAppId);
}

function setRuntimeStatus(text, tone = "neutral") {
  runtimeStatus.textContent = text;
  runtimeStatus.dataset.tone = tone;
}

function renderApplicationDescription() {
  const application = selectedApplication();
  appDescription.textContent = application
    ? `${application.name} · ${application.description || application.id}`
    : "Software Factory";
}

async function loadApplications() {
  const payload = await getJson("/apps");
  applications = payload.applications || [];
  renderApplicationDescription();
}

async function loadRuntimeConfig() {
  runtimeConfig = await getJson("/runtime/config");
  renderRuntimeConfig(runtimeConfig);
}

function renderRuntimeConfig(config) {
  const llm = config.llm || {};
  const architecturePipeline = (config.pipelines || {}).architecture_sheet || {};

  llmProvider.textContent = llm.provider || "-";
  llmModel.textContent = llm.model || "-";
  llmTimeout.textContent = llm.timeout_seconds ? `${llm.timeout_seconds}s` : "-";
  llmTokenBudget.textContent = llm.max_tokens ? `${llm.max_tokens} Tokens` : "-";
  llmPipelineMode.textContent = architecturePipeline.mode || "-";

  if (
    architecturePipeline.mode &&
    Array.from(architectureGenerationMode.options).some((option) => option.value === architecturePipeline.mode)
  ) {
    architectureGenerationMode.value = architecturePipeline.mode;
  }
}

function createElement(tagName, className, text = "") {
  const element = document.createElement(tagName);
  if (className) {
    element.className = className;
  }
  if (text) {
    element.textContent = text;
  }
  return element;
}

function formatElapsedTime(startedAt, finishedAt = "") {
  if (!startedAt) {
    return "0s";
  }

  const start = new Date(startedAt).getTime();
  const end = finishedAt ? new Date(finishedAt).getTime() : Date.now();
  const totalSeconds = Math.max(0, Math.floor((end - start) / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;

  if (minutes === 0) {
    return `${seconds}s`;
  }

  return `${minutes}m ${String(seconds).padStart(2, "0")}s`;
}

function renderArchitectureJob(job) {
  activeArchitectureJob = job;
  architectureProgress.hidden = false;
  architectureProgressSteps.replaceChildren();

  const activeStep = (job.steps || []).find((step) => step.key === job.current_step);
  const statusText = {
    queued: "Job wurde angelegt und wartet auf Ausfuehrung.",
    running: activeStep ? activeStep.label : "Job wird ausgefuehrt.",
    completed: "Workflow-Factory-Lauf ist abgeschlossen.",
    failed: job.error || "Job ist fehlgeschlagen.",
    canceled: job.error || "Job wurde abgebrochen.",
  };

  architectureProgressLabel.textContent = statusText[job.status] || job.status;
  architectureProgressElapsed.textContent = formatElapsedTime(job.started_at || job.created_at, job.finished_at);
  cancelArchitectureJobButton.disabled = !["queued", "running"].includes(job.status);
  retryArchitectureJobButton.disabled = !["failed", "canceled"].includes(job.status);

  (job.steps || []).forEach((step) => {
    const item = document.createElement("li");
    item.dataset.state =
      step.status === "completed"
        ? "done"
        : step.status === "running"
          ? "active"
          : step.status === "failed"
            ? "failed"
            : step.status || "waiting";
    item.textContent = step.label;
    architectureProgressSteps.append(item);
  });

  if (job.result) {
    renderArchitectureResult(job.result);
  } else {
    renderAgentRuns(job, null);
  }

  renderArchitectureJobLogs(job.logs || []);
}

function isTerminalArchitectureJob(job) {
  return ["completed", "failed", "canceled"].includes(job.status);
}

function stopArchitectureJobUpdates() {
  if (architectureEventSource) {
    architectureEventSource.close();
    architectureEventSource = null;
  }

  if (architecturePollingTimer) {
    window.clearTimeout(architecturePollingTimer);
    architecturePollingTimer = null;
  }
}

function completeArchitectureJobUi(job) {
  generateArchitectureButton.disabled = false;
  generateArchitectureButton.textContent = "Workflow-Job anlegen";

  if (job.status === "completed") {
    architectureStatus.textContent = `Job ${job.id} ist abgeschlossen.`;
    setRuntimeStatus("Workflow Factory abgeschlossen", "ok");
    return;
  }

  architectureStatus.textContent = `Job ${job.id} wurde beendet.`;
  setRuntimeStatus(job.error || "Job beendet", job.status === "failed" ? "error" : "neutral");
}

function renderArchitectureJobLogs(logs) {
  architectureJobLogs.replaceChildren();

  if (!logs || logs.length === 0) {
    architectureJobLogs.append(createElement("li", "", "Noch keine Logs"));
    return;
  }

  logs.slice(-14).reverse().forEach((log) => {
    const item = document.createElement("li");
    item.dataset.level = log.level || "info";
    item.append(createElement("strong", "", log.message || "Log"));
    item.append(createElement("span", "", `${formatDateTime(log.created_at)} · ${log.step || "Job"}`));
    architectureJobLogs.append(item);
  });
}

function renderArchitectureJobs(jobs) {
  architectureJobList.replaceChildren();

  if (!jobs || jobs.length === 0) {
    architectureJobList.append(createElement("li", "empty-state", "Noch keine Jobs"));
    return;
  }

  jobs.forEach((job) => {
    const item = document.createElement("li");
    const button = document.createElement("button");
    const title = createElement("strong", "", job.description || job.id);
    const meta = createElement("span", "", `${job.status} · ${formatDateTime(job.updated_at || job.created_at)}`);

    button.type = "button";
    button.className = "job-list-button";
    button.dataset.active = job.id === activeArchitectureJobId ? "true" : "false";
    button.append(title, meta);
    button.addEventListener("click", () => openArchitectureJob(job.id));
    item.append(button);
    architectureJobList.append(item);
  });
}

async function loadArchitectureJobs() {
  const payload = await getJson(appPath("software-factory", "architecture-sheet", "jobs"));
  renderArchitectureJobs(payload.jobs || []);
}

async function openArchitectureJob(jobId) {
  stopArchitectureJobUpdates();
  const payload = await getJson(appPath("software-factory", "architecture-sheet", "jobs", jobId));
  const job = payload.job;

  activeArchitectureJobId = job.id;
  renderArchitectureJob(job);
  renderArchitectureJobs((await getJson(appPath("software-factory", "architecture-sheet", "jobs"))).jobs || []);

  if (isTerminalArchitectureJob(job)) {
    completeArchitectureJobUi(job);
    return;
  }

  generateArchitectureButton.disabled = true;
  generateArchitectureButton.textContent = "Generierung laeuft...";
  setRuntimeStatus("Workflow Factory arbeitet...", "neutral");
  subscribeArchitectureJob(job.id);
}

async function pollArchitectureJob(jobId) {
  try {
    const payload = await getJson(appPath("software-factory", "architecture-sheet", "jobs", jobId));
    const job = payload.job;

    if (job.id !== activeArchitectureJobId) {
      return;
    }

    renderArchitectureJob(job);

    if (isTerminalArchitectureJob(job)) {
      stopArchitectureJobUpdates();
      completeArchitectureJobUi(job);
      loadArchitectureJobs().catch((error) => setRuntimeStatus(error.message, "error"));
      return;
    }

    architecturePollingTimer = window.setTimeout(() => pollArchitectureJob(jobId), 2000);
  } catch (error) {
    architectureProgressLabel.textContent = error.message || "Job-Status konnte nicht geladen werden.";
    setRuntimeStatus(error.message || "Job-Status nicht erreichbar", "error");
    architecturePollingTimer = window.setTimeout(() => pollArchitectureJob(jobId), 4000);
  }
}

function startArchitectureJobPolling(jobId) {
  if (architecturePollingTimer) {
    window.clearTimeout(architecturePollingTimer);
  }

  architectureStatus.textContent = `Job ${jobId} laeuft. Live-Stream nicht verfuegbar, nutze Status-Polling.`;
  architecturePollingTimer = window.setTimeout(() => pollArchitectureJob(jobId), 1000);
}

function subscribeArchitectureJob(jobId) {
  stopArchitectureJobUpdates();
  activeArchitectureJobId = jobId;

  if (!window.EventSource) {
    startArchitectureJobPolling(jobId);
    return;
  }

  const eventSource = new EventSource(appPath("software-factory", "architecture-sheet", "jobs", jobId, "events"));
  architectureEventSource = eventSource;
  architectureStatus.textContent = `Job ${jobId} laeuft. Live-Status verbunden.`;

  eventSource.addEventListener("job", (event) => {
    const payload = JSON.parse(event.data);
    const job = payload.job;

    if (!job || job.id !== activeArchitectureJobId) {
      return;
    }

    renderArchitectureJob(job);

    if (isTerminalArchitectureJob(job)) {
      stopArchitectureJobUpdates();
      completeArchitectureJobUi(job);
      loadArchitectureJobs().catch((error) => setRuntimeStatus(error.message, "error"));
    }
  });

  eventSource.addEventListener("error", (event) => {
    if (architectureEventSource !== eventSource) {
      return;
    }

    eventSource.close();
    architectureEventSource = null;
    startArchitectureJobPolling(jobId);
  });
}

async function cancelArchitectureJob() {
  if (!activeArchitectureJobId || cancelArchitectureJobButton.disabled) {
    return;
  }

  cancelArchitectureJobButton.disabled = true;
  architectureStatus.textContent = "Job wird abgebrochen.";

  const payload = await postJson(
    appPath("software-factory", "architecture-sheet", "jobs", activeArchitectureJobId, "cancel"),
    {}
  );
  renderArchitectureJob(payload.job);
  stopArchitectureJobUpdates();
  completeArchitectureJobUi(payload.job);
  await loadArchitectureJobs();
}

async function retryArchitectureJob() {
  if (!activeArchitectureJobId || retryArchitectureJobButton.disabled) {
    return;
  }

  retryArchitectureJobButton.disabled = true;
  architectureStatus.textContent = "Retry-Job wird angelegt.";

  const payload = await postJson(
    appPath("software-factory", "architecture-sheet", "jobs", activeArchitectureJobId, "retry"),
    {}
  );
  activeArchitectureJobId = payload.job.id;
  renderArchitectureJob(payload.job);
  await loadArchitectureJobs();
  generateArchitectureButton.disabled = true;
  generateArchitectureButton.textContent = "Generierung laeuft...";
  setRuntimeStatus("Workflow Factory arbeitet...", "neutral");
  subscribeArchitectureJob(payload.job.id);
}

function valueText(value) {
  if (value === null || value === undefined || value === "") {
    return "";
  }
  if (Array.isArray(value)) {
    return value.map(valueText).filter(Boolean).join(", ");
  }
  if (typeof value === "object") {
    return Object.entries(value)
      .map(([key, entry]) => `${key.replaceAll("_", " ")}: ${valueText(entry)}`)
      .join("; ");
  }
  return String(value);
}

function appendList(container, items) {
  const list = createElement("ul", "sheet-list");
  const normalizedItems = Array.isArray(items) ? items : [items].filter(Boolean);

  if (normalizedItems.length === 0) {
    list.append(createElement("li", "", "Noch offen"));
  }

  normalizedItems.forEach((item) => {
    const listItem = document.createElement("li");
    if (typeof item === "object" && item !== null) {
      const title = valueText(item.name || item.title || item.term || item.decision || item.scenario || item.risk);
      const description = valueText(
        item.description ||
          item.definition ||
          item.responsibility ||
          item.rationale ||
          item.mitigation ||
          item.trigger ||
          item.value
      );
      const meta = valueText(
        item.impact ||
          displayStatus(item.status) ||
          displayPriority(item.priority) ||
          item.category ||
          item.django_mapping ||
          item.verification
      );

      if (title) {
        listItem.append(createElement("strong", "", title));
      }
      if (description) {
        listItem.append(createElement("span", "", description));
      }
      if (meta) {
        listItem.append(createElement("small", "", meta));
      }
    } else {
      listItem.textContent = valueText(item);
    }
    list.append(listItem);
  });

  container.append(list);
}

function displayPriority(priority) {
  if (!priority) {
    return "";
  }
  const normalized = String(priority).toLowerCase();
  if (normalized === "high") {
    return "hoch";
  }
  if (normalized === "medium") {
    return "mittel";
  }
  if (normalized === "low") {
    return "niedrig";
  }
  return priority;
}

function agentStepTitle(step) {
  const labels = {
    validate_description: "Input Guard",
    load_schema: "Schema Loader",
    load_method_sources: "Method Knowledge Loader",
    analyze_requirements: "Requirement Analyst",
    synthesize_architecture: "Architecture Synthesizer",
    review_architecture: "Architecture Reviewer",
    validate_contract: "Contract Validator",
    final_result: "Final Architecture Artifact",
  };
  return labels[step.key] || step.label || step.key;
}

function stepLogs(job, stepKey) {
  return (job.logs || []).filter((log) => (log.step || "") === stepKey);
}

function stepOutputFromLogs(logs) {
  const outputLog = [...logs].reverse().find((log) => (log.metadata || {}).kind === "step_output");
  return outputLog ? (outputLog.metadata || {}).output || null : null;
}

function artifactContent(result, key) {
  const artifact = (result.validated_artifacts || []).find((item) => item.key === key);
  return artifact ? artifact.content : null;
}

function stepDuration(step) {
  if (!step.started_at || !step.finished_at) {
    return "";
  }
  return formatElapsedTime(step.started_at, step.finished_at);
}

function buildAgentRunItems(job, payload) {
  const result = payload || job.result || {};
  const generation = result.generation || {};
  const sheet = result.architecture_sheet || {};
  const requirementArtifact = artifactContent(result, "requirements_analysis");
  const sheetArtifact = artifactContent(result, "architecture_sheet");
  const reviewArtifact = artifactContent(result, "architecture_review");
  const items = (job.steps || []).map((step) => {
    const logs = stepLogs(job, step.key);
    const llmLogs = logs.filter((log) => (log.metadata || {}).kind === "llm_call");
    let output = stepOutputFromLogs(logs);

    if (!output && step.key === "analyze_requirements") {
      output = requirementArtifact || generation.requirement_analysis || null;
    } else if (!output && step.key === "synthesize_architecture") {
      output = sheetArtifact || (sheet && Object.keys(sheet).length > 0 ? sheet : null);
    } else if (!output && step.key === "review_architecture") {
      output = reviewArtifact || generation.architecture_review || null;
    } else if (!output && step.key === "validate_contract") {
      output = result.validation || null;
    } else if (!output && step.key === "load_method_sources") {
      output = result.sources || null;
    } else if (!output && step.key === "load_schema") {
      output = { schema_id: result.schema_id || "-", valid: (result.validation || {}).valid || false };
    } else if (!output && step.key === "validate_description") {
      output = { description: job.description };
    }

    return {
      key: step.key,
      title: agentStepTitle(step),
      label: step.label,
      status: step.status,
      message: step.message || step.error || "",
      error: step.error || "",
      duration: stepDuration(step),
      logs,
      llmLogs,
      output,
    };
  });

  if (result.architecture_sheet) {
    items.push({
      key: "final_result",
      title: "Finales Architekturartefakt",
      label: "Finales Architekturartefakt",
      status: (result.validation || {}).valid ? "completed" : "failed",
      message: result.artifact && result.artifact.json_path ? result.artifact.json_path : "Finales Ergebnis",
      error: "",
      duration: "",
      logs: [],
      llmLogs: [],
      output: sheetArtifact || result.architecture_sheet,
    });
  }

  return items;
}

function renderAgentRuns(job, payload) {
  const result = payload || job.result || {};
  const items = buildAgentRunItems(job, result);

  architectureEmpty.hidden = true;
  architectureResult.hidden = false;

  agentStepList.replaceChildren();
  items.forEach((item) => {
    const listItem = document.createElement("li");
    const button = document.createElement("button");
    const title = createElement("strong", "", item.title);
    const meta = createElement(
      "span",
      "",
      [displayStepStatus(item.status), item.duration, item.llmLogs.length ? `${item.llmLogs.length} LLM Call(s)` : ""]
        .filter(Boolean)
        .join(" · ")
    );

    button.type = "button";
    button.className = "agent-step-button";
    button.dataset.state = item.status || "pending";
    button.dataset.active = item.key === activeAgentStepKey ? "true" : "false";
    button.append(title, meta);
    button.addEventListener("click", () => {
      activeAgentStepKey = item.key;
      renderAgentRuns(job, result);
      renderAgentViewer(item);
    });
    listItem.append(button);
    agentStepList.append(listItem);
  });

  const selected = items.find((item) => item.key === activeAgentStepKey) || items.find((item) => item.status === "running") || items[0];
  if (selected) {
    activeAgentStepKey = selected.key;
    renderAgentViewer(selected);
  }
}

function displayStepStatus(status) {
  const labels = {
    pending: "wartet",
    running: "laeuft",
    completed: "fertig",
    failed: "fehlgeschlagen",
    skipped: "uebersprungen",
  };
  return labels[status] || status || "";
}

function appendViewerSection(title, value, options = {}) {
  const section = createElement("section", "viewer-section");
  section.append(createElement("h3", "", title));

  if (value === null || value === undefined || value === "") {
    section.append(createElement("p", "empty-state", options.emptyText || "Noch keine Daten."));
  } else if (options.json) {
    const pre = createElement("pre", "viewer-json");
    pre.textContent = JSON.stringify(value, null, 2);
    section.append(pre);
  } else if (Array.isArray(value)) {
    appendList(section, value.length > 0 ? value : [options.emptyText || "Noch keine Daten."]);
  } else if (typeof value === "object") {
    const pre = createElement("pre", "viewer-json");
    pre.textContent = JSON.stringify(value, null, 2);
    section.append(pre);
  } else {
    section.append(createElement("p", "", valueText(value)));
  }

  agentViewerBody.append(section);
}

function renderAgentViewer(item) {
  agentViewerBody.replaceChildren();
  agentViewerKicker.textContent = item.label || "Agent Output";
  agentViewerTitle.textContent = item.title;
  agentViewerStatus.textContent = displayStepStatus(item.status);
  agentViewerStatus.dataset.tone = item.status === "completed" ? "ok" : item.status === "failed" ? "warn" : "neutral";

  appendViewerSection("Status", item.error || item.message || displayStepStatus(item.status));
  appendViewerSection("Output", item.output, { json: true, emptyText: "Dieser Schritt hat noch kein gespeichertes Ergebnis." });

  if (item.llmLogs.length > 0) {
    appendViewerSection(
      "LLM Calls",
      item.llmLogs.map((log) => ({
        step: (log.metadata || {}).llm_step,
        provider: (log.metadata || {}).provider,
        model: (log.metadata || {}).model,
        status: (log.metadata || {}).status,
        duration_seconds: (log.metadata || {}).duration_seconds,
        error: (log.metadata || {}).error,
      })),
      { json: true }
    );
  }

  appendViewerSection(
    "Logs",
    item.logs.map((log) => ({
      time: formatDateTime(log.created_at),
      level: log.level,
      message: log.message,
      metadata: log.metadata || {},
    })),
    { json: true, emptyText: "Keine Logs fuer diesen Schritt." }
  );
}

function displayStatus(status) {
  if (!status) {
    return "";
  }
  const normalized = String(status).toLowerCase();
  const labels = {
    proposed: "vorgeschlagen",
    accepted: "akzeptiert",
    rejected: "verworfen",
    superseded: "ersetzt",
    draft: "Entwurf",
    "needs-clarification": "Klaerungsbedarf",
    "ready-for-review": "bereit fuer Review",
    approved: "freigegeben"
  };
  return labels[normalized] || status;
}

function renderSupportList(element, items, emptyText, formatter) {
  element.replaceChildren();

  if (!items || items.length === 0) {
    const item = document.createElement("li");
    item.textContent = emptyText;
    element.append(item);
    return;
  }

  items.forEach((entry) => {
    const item = document.createElement("li");
    formatter(item, entry);
    element.append(item);
  });
}

function renderArchitectureResult(payload) {
  const validation = payload.validation || {};
  const generation = payload.generation || {};
  const artifact = payload.artifact || {};
  const sources = payload.sources || [];
  const trace = payload.trace || [];
  const provider =
    generation.provider ||
    (generation.llm_provider && generation.llm_provider !== "none" ? generation.llm_provider : "") ||
    generation.mode ||
    "Regelbasiert";
  const model = generation.model || (generation.llm_model !== "none" ? generation.llm_model : "");

  if (activeArchitectureJob) {
    renderAgentRuns(activeArchitectureJob, payload);
  }

  architectureReviewStatus.textContent = validation.valid ? "Bestanden" : "Mit Hinweisen";
  architectureSchema.textContent = payload.schema_id || "-";
  architectureProvider.textContent = model ? `${provider} · ${model}` : provider;
  architecturePipeline.textContent = generation.pipeline || generation.requested_mode || generation.mode || "-";
  architectureArtifact.textContent = artifact.json_path
    ? `${artifact.json_path} · ${artifact.markdown_path || "Markdown offen"}`
    : "-";
  architectureSourceCount.textContent = String(sources.length);

  renderSupportList(architectureSources, sources, "Keine Quellen", (item, source) => {
    item.append(createElement("strong", "", source.title || "Quelle"));
    item.append(createElement("span", "", source.location || source.relative_path || ""));
  });
  renderSupportList(architectureTrace, trace, "Noch kein Trace", (item, entry) => {
    item.textContent = valueText(entry);
  });
}

async function generateArchitectureSheet() {
  const description = architectureDescription.value.trim();

  if (!description) {
    architectureStatus.textContent = "Bitte beschreibe zuerst das Softwareartefakt.";
    return;
  }

  architectureStatus.textContent = "Job wird angelegt.";
  generateArchitectureButton.disabled = true;
  generateArchitectureButton.textContent = "Job wird angelegt...";
  setRuntimeStatus("Job anlegen...", "neutral");

  try {
    const payload = await postJson(appPath("software-factory", "architecture-sheet", "jobs"), {
      description,
      generation_mode: architectureGenerationMode.value,
    });

    activeArchitectureJobId = payload.job.id;
    renderArchitectureJob(payload.job);
    await loadArchitectureJobs();
    generateArchitectureButton.textContent = "Generierung laeuft...";
    setRuntimeStatus("Workflow Factory arbeitet...", "neutral");
    subscribeArchitectureJob(payload.job.id);
  } catch (error) {
    architectureProgress.hidden = false;
    architectureProgressLabel.textContent = error.message || "Job konnte nicht angelegt werden.";
    architectureProgressElapsed.textContent = "0s";
    architectureProgressSteps.replaceChildren();
    generateArchitectureButton.disabled = false;
    generateArchitectureButton.textContent = "Workflow-Job anlegen";
    throw error;
  }
}

async function initialize() {
  try {
    setRuntimeStatus("Verbinden...");
    await loadRuntimeConfig();
    await loadApplications();
    await loadArchitectureJobs();
    setRuntimeStatus("Bereit", "ok");
  } catch (error) {
    setRuntimeStatus(error.message || "API nicht erreichbar", "error");
  }
}

refreshArchitectureJobsButton.addEventListener("click", async () => {
  try {
    await loadArchitectureJobs();
    setRuntimeStatus("Jobs aktualisiert", "ok");
  } catch (error) {
    setRuntimeStatus(error.message, "error");
  }
});

cancelArchitectureJobButton.addEventListener("click", async () => {
  try {
    await cancelArchitectureJob();
  } catch (error) {
    setRuntimeStatus(error.message, "error");
    architectureStatus.textContent = error.message;
    if (activeArchitectureJob) {
      renderArchitectureJob(activeArchitectureJob);
    }
  }
});

retryArchitectureJobButton.addEventListener("click", async () => {
  try {
    await retryArchitectureJob();
  } catch (error) {
    setRuntimeStatus(error.message, "error");
    architectureStatus.textContent = error.message;
    if (activeArchitectureJob) {
      renderArchitectureJob(activeArchitectureJob);
    }
  }
});

architectureForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  try {
    await generateArchitectureSheet();
  } catch (error) {
    architectureStatus.textContent = error.message || "Workflow-Job konnte nicht erstellt werden.";
    setRuntimeStatus("Fehler", "error");
  }
});

initialize();
