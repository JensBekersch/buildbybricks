const appDescription = document.querySelector("#app-description");
const runtimeStatus = document.querySelector("#runtime-status");
const showGeneratorViewButton = document.querySelector("#show-generator-view");
const showAdminViewButton = document.querySelector("#show-admin-view");
const architectureView = document.querySelector("#architecture-view");
const workflowAdminView = document.querySelector("#workflow-admin-view");

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
const refreshWorkflowsButton = document.querySelector("#refresh-workflows");
const createWorkflowDraftButton = document.querySelector("#create-workflow-draft");
const refreshWorkflowRunsButton = document.querySelector("#refresh-workflow-runs");
const validateWorkflowButton = document.querySelector("#validate-workflow");
const startWorkflowTestRunButton = document.querySelector("#start-workflow-test-run");
const queueWorkflowRunButton = document.querySelector("#queue-workflow-run");
const workflowList = document.querySelector("#workflow-list");
const workflowDetailTitle = document.querySelector("#workflow-detail-title");
const workflowValidationBadge = document.querySelector("#workflow-validation-badge");
const workflowDetailMeta = document.querySelector("#workflow-detail-meta");
const workflowEditorMode = document.querySelector("#workflow-editor-mode");
const workflowEditorId = document.querySelector("#workflow-editor-id");
const workflowEditorName = document.querySelector("#workflow-editor-name");
const workflowEditorSlug = document.querySelector("#workflow-editor-slug");
const workflowEditorDescription = document.querySelector("#workflow-editor-description");
const workflowEditorFinalOutput = document.querySelector("#workflow-editor-final-output");
const saveWorkflowButton = document.querySelector("#save-workflow");
const deleteWorkflowButton = document.querySelector("#delete-workflow");
const workflowStepCount = document.querySelector("#workflow-step-count");
const workflowStepTemplateCount = document.querySelector("#workflow-step-template-count");
const workflowStepTemplate = document.querySelector("#workflow-step-template");
const workflowStepKey = document.querySelector("#workflow-step-key");
const workflowStepName = document.querySelector("#workflow-step-name");
const workflowStepOutputKey = document.querySelector("#workflow-step-output-key");
const workflowStepAgent = document.querySelector("#workflow-step-agent");
const addWorkflowStepButton = document.querySelector("#add-workflow-step");
const workflowStepTemplateDescription = document.querySelector("#workflow-step-template-description");
const workflowStepList = document.querySelector("#workflow-step-list");
const workflowStepDetail = document.querySelector("#workflow-step-detail");
const workflowTestPayload = document.querySelector("#workflow-test-payload");
const workflowAdminStatus = document.querySelector("#workflow-admin-status");
const workflowRunList = document.querySelector("#workflow-run-list");
const workflowArtifactList = document.querySelector("#workflow-artifact-list");
const workflowArtifactTitle = document.querySelector("#workflow-artifact-title");
const workflowArtifactViewer = document.querySelector("#workflow-artifact-viewer");

let applications = [];
let runtimeConfig = null;
let activeAppId = "software-factory";
let activeArchitectureJobId = "";
let activeArchitectureJob = null;
let activeAgentStepKey = "";
let architectureEventSource = null;
let architecturePollingTimer = null;
let workflows = [];
let workflowStepTemplates = [];
let activeWorkflowId = "";
let activeWorkflowDetail = null;
let activeWorkflowRunId = "";
let activeWorkflowRun = null;
let activeWorkflowStepKey = "";
let activeWorkflowArtifactKey = "";

function appPath(appId, ...segments) {
  return ["/apps", appId, ...segments]
    .map((part, index) => (index === 0 ? part : encodeURIComponent(part)))
    .join("/");
}

async function getJson(url) {
  const response = await fetch(url);
  return parseJsonResponse(response);
}

async function postJson(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  return parseJsonResponse(response);
}

async function putJson(url, body) {
  const response = await fetch(url, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  return parseJsonResponse(response);
}

async function deleteJson(url) {
  const response = await fetch(url, {
    method: "DELETE",
  });
  return parseJsonResponse(response);
}

async function parseJsonResponse(response) {
  const rawBody = await response.text();
  let payload = {};

  if (rawBody) {
    try {
      payload = JSON.parse(rawBody);
    } catch (error) {
      payload = { error: rawBody };
    }
  }

  if (!response.ok) {
    throw new Error(payload.error || `Die Anfrage ist mit Status ${response.status} fehlgeschlagen.`);
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

function switchView(viewName) {
  const adminActive = viewName === "admin";
  workflowAdminView.hidden = !adminActive;
  architectureView.hidden = adminActive;
  showAdminViewButton.dataset.active = adminActive ? "true" : "false";
  showGeneratorViewButton.dataset.active = adminActive ? "false" : "true";

  if (adminActive && workflows.length === 0) {
    loadWorkflowAdmin().catch((error) => setRuntimeStatus(error.message, "error"));
  }
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

function renderJson(value) {
  return JSON.stringify(value, null, 2);
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

async function loadWorkflowAdmin() {
  workflowAdminStatus.textContent = "Workflows werden geladen.";
  await loadWorkflowStepTemplates();
  const payload = await getJson(appPath(activeAppId, "workflows"));
  workflows = payload.workflows || [];
  renderWorkflowList(workflows);
  workflowAdminStatus.textContent = `${workflows.length} Workflow(s) geladen.`;

  if (!activeWorkflowId && workflows.length > 0) {
    await openWorkflow(workflows[0].id);
  } else if (activeWorkflowId) {
    await openWorkflow(activeWorkflowId);
  }
}

async function loadWorkflowStepTemplates() {
  const payload = await getJson(appPath(activeAppId, "step-templates"));
  workflowStepTemplates = payload.templates || [];
  renderWorkflowStepTemplateOptions();
}

function renderWorkflowStepTemplateOptions() {
  workflowStepTemplate.replaceChildren();
  workflowStepTemplateCount.textContent = `${workflowStepTemplates.length} Templates`;

  workflowStepTemplates.forEach((template) => {
    const option = document.createElement("option");
    option.value = template.id;
    option.textContent = `${template.name} · ${template.step_type}`;
    workflowStepTemplate.append(option);
  });

  renderSelectedWorkflowStepTemplate();
}

function selectedWorkflowStepTemplate() {
  return workflowStepTemplates.find((template) => template.id === workflowStepTemplate.value) || null;
}

function renderSelectedWorkflowStepTemplate() {
  const template = selectedWorkflowStepTemplate();

  if (!template) {
    workflowStepTemplateDescription.textContent = "Keine Step-Templates geladen.";
    workflowStepName.value = "";
    workflowStepOutputKey.value = "";
    workflowStepAgent.value = "";
    return;
  }

  const defaults = template.defaults || {};
  workflowStepTemplateDescription.textContent = template.description || "";
  workflowStepName.value = defaults.name || template.name || "";
  workflowStepOutputKey.value = defaults.output_key || "";
  workflowStepAgent.value = defaults.agent || "";
}

function prepareNewWorkflowDraft() {
  activeWorkflowId = "";
  activeWorkflowDetail = null;
  activeWorkflowStepKey = "";
  activeWorkflowRunId = "";
  activeWorkflowRun = null;
  activeWorkflowArtifactKey = "";
  renderWorkflowList(workflows);
  renderWorkflowEditor({
    id: "",
    name: "",
    slug: "",
    description: "",
    status: "draft",
    final_output_key: "",
    is_new: true,
  });
  workflowDetailTitle.textContent = "Neuer Workflow";
  workflowValidationBadge.textContent = "Draft";
  workflowValidationBadge.dataset.tone = "neutral";
  workflowDetailMeta.replaceChildren();
  workflowStepCount.textContent = "0";
  addWorkflowStepButton.disabled = true;
  workflowStepList.replaceChildren(createElement("li", "empty-state", "Noch keine Steps konfiguriert."));
  workflowStepDetail.textContent = "Speichere den Workflow zuerst. Danach koennen Steps konfiguriert werden.";
  workflowRunList.replaceChildren(createElement("li", "empty-state", "Noch keine Runs."));
  workflowArtifactList.replaceChildren(createElement("li", "empty-state", "Noch keine Step-Outputs."));
  workflowArtifactTitle.textContent = "Output Viewer";
  workflowArtifactViewer.textContent = "Noch kein Workflow ausgewaehlt.";
  workflowAdminStatus.textContent = "Neuer Draft vorbereitet.";
}

function renderWorkflowList(items) {
  workflowList.replaceChildren();

  if (!items || items.length === 0) {
    workflowList.append(createElement("li", "empty-state", "Keine Workflows gefunden."));
    return;
  }

  items.forEach((workflow) => {
    const item = document.createElement("li");
    const button = document.createElement("button");
    const title = createElement("strong", "", workflow.name || workflow.id);
    const meta = createElement(
      "span",
      "",
      [
        `v${workflow.version_number || "-"}`,
        workflow.status || "-",
        (workflow.validation || {}).valid ? "valide" : "mit Fehlern",
      ].join(" · ")
    );

    button.type = "button";
    button.className = "admin-list-button";
    button.dataset.active = workflow.id === activeWorkflowId ? "true" : "false";
    button.append(title, meta);
    button.addEventListener("click", () => openWorkflow(workflow.id));
    item.append(button);
    workflowList.append(item);
  });
}

async function openWorkflow(workflowId) {
  activeWorkflowId = workflowId;
  activeWorkflowRunId = "";
  activeWorkflowRun = null;
  activeWorkflowArtifactKey = "";

  const payload = await getJson(appPath(activeAppId, "workflows", workflowId));
  activeWorkflowDetail = payload.workflow;
  renderWorkflowList(workflows);
  renderWorkflowDetail(payload);
  renderWorkflowTestPayload();
  await loadWorkflowRuns();
}

function renderWorkflowDetail(payload) {
  const workflowVersion = payload.workflow || {};
  const workflow = workflowVersion.workflow || {};
  const validation = payload.validation || {};
  const steps = workflowVersion.steps || [];

  workflowDetailTitle.textContent = workflow.name || payload.workflow_id || "Workflow";
  workflowValidationBadge.textContent = validation.valid ? "Schema gueltig" : "Schemafehler";
  workflowValidationBadge.dataset.tone = validation.valid ? "ok" : "warn";
  workflowStepCount.textContent = String(steps.length);
  workflowDetailMeta.replaceChildren();
  appendMeta(workflowDetailMeta, "ID", payload.workflow_id || "-");
  appendMeta(workflowDetailMeta, "Slug", workflow.slug || "-");
  appendMeta(workflowDetailMeta, "Version", workflowVersion.version_number ? `v${workflowVersion.version_number}` : "-");
  appendMeta(workflowDetailMeta, "Status", workflowVersion.status || "-");
  appendMeta(workflowDetailMeta, "Final Output", workflowVersion.final_output_key || "-");
  appendMeta(workflowDetailMeta, "Beschreibung", workflow.description || "-");
  renderWorkflowEditor({
    id: payload.workflow_id || "",
    name: workflow.name || "",
    slug: workflow.slug || "",
    description: workflow.description || "",
    status: workflowVersion.status || "",
    final_output_key: workflowVersion.final_output_key || "",
    is_new: false,
  });

  workflowStepList.replaceChildren();
  if (steps.length === 0) {
    workflowStepList.append(createElement("li", "empty-state", "Keine Steps konfiguriert."));
  }

  steps.forEach((step) => {
    const item = document.createElement("li");
    const button = document.createElement("button");
    const agent = step.agent_version ? step.agent_version.agent || {} : null;
    const title = createElement("strong", "", step.name || step.step_key);
    const meta = createElement(
      "span",
      "",
      [
        `#${step.position}`,
        step.step_type,
        step.output_key ? `Output: ${step.output_key}` : "",
        agent ? `Agent: ${agent.name || agent.slug}` : "Task",
      ]
        .filter(Boolean)
        .join(" · ")
    );

    button.type = "button";
    button.className = "admin-list-button";
    button.dataset.stepKey = step.step_key;
    button.dataset.active = step.step_key === activeWorkflowStepKey ? "true" : "false";
    button.append(title, meta);
    button.addEventListener("click", () => renderWorkflowStepDetail(step));
    item.append(button);
    workflowStepList.append(item);
  });

  const selectedStep = steps.find((step) => step.step_key === activeWorkflowStepKey) || steps[0];
  if (selectedStep) {
    renderWorkflowStepDetail(selectedStep);
  } else {
    activeWorkflowStepKey = "";
    workflowStepDetail.textContent = "Noch kein Step konfiguriert.";
  }
}

function renderWorkflowEditor(workflow) {
  const published = workflow.status === "published";
  workflowEditorId.value = workflow.id || "";
  workflowEditorName.value = workflow.name || "";
  workflowEditorSlug.value = workflow.slug || "";
  workflowEditorDescription.value = workflow.description || "";
  workflowEditorFinalOutput.value = workflow.final_output_key || "";
  workflowEditorMode.textContent = workflow.is_new ? "Neuer Draft" : workflow.status || "draft";
  workflowEditorMode.dataset.tone = published ? "locked" : "draft";
  workflowEditorId.disabled = !workflow.is_new;
  saveWorkflowButton.disabled = published;
  deleteWorkflowButton.disabled = workflow.is_new || published;
  addWorkflowStepButton.disabled = workflow.is_new || published || !workflow.id;
}

function workflowEditorPayload() {
  return {
    id: workflowEditorId.value.trim(),
    name: workflowEditorName.value.trim(),
    slug: workflowEditorSlug.value.trim(),
    description: workflowEditorDescription.value.trim(),
    final_output_key: workflowEditorFinalOutput.value.trim(),
    status: "draft",
  };
}

async function saveWorkflowDraft() {
  const payload = workflowEditorPayload();

  if (!payload.id) {
    workflowAdminStatus.textContent = "Workflow-ID ist erforderlich.";
    workflowEditorId.focus();
    return;
  }

  saveWorkflowButton.disabled = true;
  workflowAdminStatus.textContent = activeWorkflowId ? "Workflow wird gespeichert." : "Workflow wird angelegt.";

  try {
    const response = activeWorkflowId
      ? await putJson(appPath(activeAppId, "workflows", activeWorkflowId), payload)
      : await postJson(appPath(activeAppId, "workflows"), payload);

    activeWorkflowId = response.workflow_id;
    activeWorkflowDetail = response.workflow;
    workflowAdminStatus.textContent = `Workflow ${response.workflow_id} wurde gespeichert.`;
    await loadWorkflowAdmin();
  } finally {
    saveWorkflowButton.disabled = false;
  }
}

async function deleteWorkflowDraft() {
  if (!activeWorkflowId) {
    return;
  }

  deleteWorkflowButton.disabled = true;
  workflowAdminStatus.textContent = "Workflow wird geloescht.";

  try {
    await deleteJson(appPath(activeAppId, "workflows", activeWorkflowId));
    workflowAdminStatus.textContent = `Workflow ${activeWorkflowId} wurde geloescht.`;
    activeWorkflowId = "";
    activeWorkflowDetail = null;
    await loadWorkflowAdmin();
  } finally {
    deleteWorkflowButton.disabled = false;
  }
}

async function addWorkflowStepFromTemplate() {
  if (!activeWorkflowId) {
    workflowAdminStatus.textContent = "Bitte zuerst einen Workflow speichern oder auswaehlen.";
    return;
  }

  const template = selectedWorkflowStepTemplate();
  if (!template) {
    workflowAdminStatus.textContent = "Bitte zuerst ein Step-Template auswaehlen.";
    return;
  }

  const payload = {
    template_id: template.id,
    step_key: workflowStepKey.value.trim(),
    name: workflowStepName.value.trim(),
    output_key: workflowStepOutputKey.value.trim(),
  };

  if ((template.step_type || "").toUpperCase() === "AGENT") {
    payload.agent = workflowStepAgent.value.trim();
  }

  addWorkflowStepButton.disabled = true;
  workflowAdminStatus.textContent = "Step wird hinzugefuegt.";

  try {
    const response = await postJson(appPath(activeAppId, "workflows", activeWorkflowId, "steps"), payload);
    activeWorkflowDetail = response.workflow;
    activeWorkflowStepKey = (response.workflow.steps || []).slice(-1)[0]?.step_key || "";
    workflowStepKey.value = "";
    workflowAdminStatus.textContent = `Step wurde zu ${response.workflow_id} hinzugefuegt.`;
    await loadWorkflowAdmin();
  } finally {
    const workflowVersion = activeWorkflowDetail || {};
    addWorkflowStepButton.disabled = (workflowVersion.status || "") === "published";
  }
}

function appendMeta(container, label, value) {
  const group = document.createElement("div");
  group.append(createElement("dt", "", label));
  group.append(createElement("dd", "", valueText(value)));
  container.append(group);
}

function renderWorkflowStepDetail(step) {
  activeWorkflowStepKey = step.step_key;
  workflowStepList.querySelectorAll("button").forEach((button) => {
    button.dataset.active = button.dataset.stepKey === step.step_key ? "true" : "false";
  });
  workflowStepDetail.textContent = renderJson({
    step_key: step.step_key,
    name: step.name,
    step_type: step.step_type,
    position: step.position,
    output_key: step.output_key,
    input_mapping: step.input_mapping,
    task_definition: step.task_definition,
    configuration: step.configuration,
    agent: step.agent_version
      ? {
          name: (step.agent_version.agent || {}).name,
          slug: (step.agent_version.agent || {}).slug,
          version_number: step.agent_version.version_number,
          input_contract: step.agent_version.input_contract,
          output_schema: step.agent_version.output_schema,
          validators: step.agent_version.validators,
          model_configuration: step.agent_version.model_configuration,
        }
      : null,
  });
}

async function validateActiveWorkflow() {
  if (!activeWorkflowId) {
    return;
  }
  workflowAdminStatus.textContent = "Workflow wird validiert.";
  const payload = await postJson(appPath(activeAppId, "workflows", activeWorkflowId, "validate"), {});
  workflowAdminStatus.textContent = payload.validation.valid
    ? "Workflow ist strukturell gueltig."
    : `Workflow hat ${payload.validation.errors.length} Fehler.`;
  workflowArtifactTitle.textContent = "Validierung";
  workflowArtifactViewer.textContent = renderJson(payload.validation);
}

async function loadWorkflowRuns() {
  if (!activeWorkflowId) {
    return;
  }

  const payload = await getJson(appPath(activeAppId, "workflows", activeWorkflowId, "runs"));
  renderWorkflowRuns(payload.runs || []);
}

function renderWorkflowRuns(runs) {
  workflowRunList.replaceChildren();
  workflowArtifactList.replaceChildren();

  if (!runs || runs.length === 0) {
    workflowRunList.append(createElement("li", "empty-state", "Noch keine Admin-Testlaeufe."));
    workflowArtifactList.append(createElement("li", "empty-state", "Noch keine Step-Outputs."));
    workflowArtifactTitle.textContent = "Output Viewer";
    workflowArtifactViewer.textContent = "Starte einen Testlauf oder waehle einen vorhandenen Run aus.";
    return;
  }

  runs.forEach((run) => {
    const item = document.createElement("li");
    const button = document.createElement("button");
    const title = createElement("strong", "", run.id);
    const meta = createElement(
      "span",
      "",
      [run.status, formatDateTime(run.started_at || run.finished_at), `${run.artifact_count || 0} Artefakte`]
        .filter(Boolean)
        .join(" · ")
    );

    button.type = "button";
    button.className = "admin-list-button";
    button.dataset.active = run.id === activeWorkflowRunId ? "true" : "false";
    button.append(title, meta);
    button.addEventListener("click", () => openWorkflowRun(run.id));
    item.append(button);
    workflowRunList.append(item);
  });
}

async function openWorkflowRun(runId) {
  activeWorkflowRunId = runId;
  activeWorkflowArtifactKey = "";
  const payload = await getJson(appPath(activeAppId, "workflows", activeWorkflowId, "runs", runId));
  activeWorkflowRun = payload.run;
  await loadWorkflowRuns();
  renderWorkflowRunArtifacts(activeWorkflowRun);
}

function renderWorkflowRunArtifacts(run) {
  workflowArtifactList.replaceChildren();
  const artifacts = run.artifacts || [];
  const stepRuns = run.step_runs || [];

  if (artifacts.length === 0) {
    workflowArtifactList.append(createElement("li", "empty-state", "Dieser Run hat keine Artefakte."));
  }

  artifacts.forEach((artifact) => {
    const stepRun = stepRuns.find((item) => item.workflow_step.step_key === artifact.step_key) || null;
    const item = document.createElement("li");
    const button = document.createElement("button");
    const title = createElement("strong", "", artifact.artifact_key);
    const meta = createElement(
      "span",
      "",
      [artifact.step_key, artifact.artifact_type, artifact.is_validated ? "validiert" : ""]
        .filter(Boolean)
        .join(" · ")
    );

    button.type = "button";
    button.className = "admin-list-button";
    button.dataset.artifactKey = artifact.artifact_key;
    button.dataset.active = artifact.artifact_key === activeWorkflowArtifactKey ? "true" : "false";
    button.append(title, meta);
    button.addEventListener("click", () => renderWorkflowArtifact(run, artifact, stepRun));
    item.append(button);
    workflowArtifactList.append(item);
  });

  const selectedArtifact =
    artifacts.find((artifact) => artifact.artifact_key === activeWorkflowArtifactKey) || artifacts[0];
  if (selectedArtifact) {
    const selectedStepRun = stepRuns.find((item) => item.workflow_step.step_key === selectedArtifact.step_key) || null;
    renderWorkflowArtifact(run, selectedArtifact, selectedStepRun);
  }
}

function renderWorkflowArtifact(run, artifact, stepRun) {
  activeWorkflowArtifactKey = artifact.artifact_key;
  workflowArtifactList.querySelectorAll("button").forEach((button) => {
    button.dataset.active = button.dataset.artifactKey === artifact.artifact_key ? "true" : "false";
  });
  workflowArtifactTitle.textContent = `${artifact.artifact_key} · ${artifact.step_key || "Run"}`;
  workflowArtifactViewer.textContent = renderJson({
    run: {
      id: run.id,
      status: run.status,
      started_at: run.started_at,
      finished_at: run.finished_at,
      error_summary: run.error_summary,
    },
    artifact,
    step_run: stepRun
      ? {
          status: stepRun.status,
          resolved_input: stepRun.resolved_input,
          parsed_output: stepRun.parsed_output,
          validated_output: stepRun.validated_output,
          validation_result: stepRun.validation_result,
          model_metadata: stepRun.model_metadata,
          error_message: stepRun.error_message,
          rendered_system_prompt: stepRun.rendered_system_prompt,
          rendered_user_prompt: stepRun.rendered_user_prompt,
        }
      : null,
  });
}

async function startWorkflowTestRun() {
  if (!activeWorkflowId) {
    return;
  }

  let payload;
  try {
    payload = JSON.parse(workflowTestPayload.value || "{}");
  } catch (error) {
    workflowAdminStatus.textContent = "Testlauf-Payload ist kein gueltiges JSON.";
    return;
  }

  workflowAdminStatus.textContent = "Testlauf wird gestartet.";
  startWorkflowTestRunButton.disabled = true;
  try {
    const response = await postJson(appPath(activeAppId, "workflows", activeWorkflowId, "test-runs"), payload);
    activeWorkflowRunId = response.run.id;
    activeWorkflowRun = response.run;
    workflowAdminStatus.textContent = `Testlauf ${response.run.id} ist ${response.run.status}.`;
    await loadWorkflowRuns();
    renderWorkflowRunArtifacts(response.run);
  } finally {
    startWorkflowTestRunButton.disabled = false;
  }
}

async function queueWorkflowRun() {
  if (!activeWorkflowId) {
    return;
  }

  let payload;
  try {
    payload = JSON.parse(workflowTestPayload.value || "{}");
  } catch (error) {
    workflowAdminStatus.textContent = "Run-Payload ist kein gueltiges JSON.";
    return;
  }

  const queuedPayload = {
    description: payload.description || "",
    input: payload.input || {},
    started_by: payload.started_by || "workflow-admin-ui",
  };
  workflowAdminStatus.textContent = "Worker-Run wird angelegt.";
  queueWorkflowRunButton.disabled = true;
  try {
    const response = await postJson(appPath(activeAppId, "workflows", activeWorkflowId, "runs"), queuedPayload);
    activeWorkflowRunId = response.run.id;
    workflowAdminStatus.textContent = `Worker-Run ${response.run.id} wartet auf Ausfuehrung.`;
    await loadWorkflowRuns();
  } finally {
    queueWorkflowRunButton.disabled = false;
  }
}

function renderWorkflowTestPayload() {
  workflowTestPayload.value = renderJson({
    description: "Eine einfache Team-Todo-Liste mit Aufgaben und Status.",
    responses: workflowFakeResponses(),
  });
}

function workflowFakeResponses() {
  return [
    {
      parsed_output: {
        schema_version: "2.0.0",
        artifact_name: "Team-Todo-Liste",
        business_goal: {
          description: "Teammitglieder verwalten eine gemeinsam sichtbare Aufgabenliste.",
          evidence: { source: "input" },
        },
        input_summary: "Eine einfache Team-Todo-Liste mit Aufgaben und Status.",
        roles: [{ name: "Teammitglieder", description: "Nutzen die gemeinsame Aufgabenliste." }],
        domain_entities: [{ name: "Aufgabe", description: "Aufgabenbeschreibung und Status." }],
        enumerations: [{ name: "Aufgabenstatus", values: ["offen", "in Bearbeitung", "fertig"] }],
        functional_requirements: [
          { description: "Aufgabe erfassen." },
          { description: "Aufgabenliste anzeigen." },
          { description: "Status aendern." },
        ],
        crud_requirements: [],
        validation_rules: [],
        security_rules: [],
        ui_requirements: [],
        technical_constraints: [],
        delivery_requirements: [],
        test_requirements: [],
        quality_requirements: [],
        in_scope: ["Aufgabe", "Aufgabe erfassen", "Status aendern", "Aufgabenliste anzeigen"],
        explicitly_excluded: [],
        not_requested: [],
        not_evidenced: [],
        future_ideas: [],
        core_facts: ["Aufgabe", "Aufgabe erfassen", "Status aendern"],
        risks: [],
        assumptions: [],
        open_questions: [],
        readiness: "ready",
      },
    },
    {
      parsed_output: {
        architecture_sheet: {
          artifact_name: "Team-Todo-Liste",
          business_goal: "Teammitglieder verwalten eine gemeinsam sichtbare Aufgabenliste.",
          requirement_version: "2.0.0",
          building_blocks: [{ name: "Aufgabe", responsibility: "Speichert Beschreibung und Status." }],
          runtime_scenarios: [
            { name: "Aufgabe erfassen", steps: ["Beschreibung eingeben.", "Aufgabe speichern."] },
          ],
          arc42: {
            building_block_view: "Der Baustein Aufgabe kapselt Beschreibung und Status.",
            runtime_view: "Im Szenario Aufgabe erfassen wird eine Beschreibung gespeichert.",
          },
        },
      },
    },
    {
      parsed_output: {
        passes: true,
        findings: [],
        required_corrections: [],
      },
    },
  ];
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

showGeneratorViewButton.addEventListener("click", () => switchView("generator"));

showAdminViewButton.addEventListener("click", () => switchView("admin"));

refreshWorkflowsButton.addEventListener("click", async () => {
  try {
    await loadWorkflowAdmin();
    setRuntimeStatus("Workflows aktualisiert", "ok");
  } catch (error) {
    workflowAdminStatus.textContent = error.message;
    setRuntimeStatus(error.message, "error");
  }
});

createWorkflowDraftButton.addEventListener("click", () => {
  prepareNewWorkflowDraft();
  setRuntimeStatus("Workflow Draft vorbereitet", "ok");
});

saveWorkflowButton.addEventListener("click", async () => {
  try {
    await saveWorkflowDraft();
    setRuntimeStatus("Workflow gespeichert", "ok");
  } catch (error) {
    workflowAdminStatus.textContent = error.message;
    setRuntimeStatus(error.message, "error");
  }
});

deleteWorkflowButton.addEventListener("click", async () => {
  try {
    await deleteWorkflowDraft();
    setRuntimeStatus("Workflow geloescht", "ok");
  } catch (error) {
    workflowAdminStatus.textContent = error.message;
    setRuntimeStatus(error.message, "error");
  }
});

workflowStepTemplate.addEventListener("change", renderSelectedWorkflowStepTemplate);

addWorkflowStepButton.addEventListener("click", async () => {
  try {
    await addWorkflowStepFromTemplate();
    setRuntimeStatus("Step hinzugefuegt", "ok");
  } catch (error) {
    workflowAdminStatus.textContent = error.message;
    setRuntimeStatus(error.message, "error");
  }
});

refreshWorkflowRunsButton.addEventListener("click", async () => {
  try {
    await loadWorkflowRuns();
    setRuntimeStatus("Runs aktualisiert", "ok");
  } catch (error) {
    workflowAdminStatus.textContent = error.message;
    setRuntimeStatus(error.message, "error");
  }
});

validateWorkflowButton.addEventListener("click", async () => {
  try {
    await validateActiveWorkflow();
    setRuntimeStatus("Workflow validiert", "ok");
  } catch (error) {
    workflowAdminStatus.textContent = error.message;
    setRuntimeStatus(error.message, "error");
  }
});

startWorkflowTestRunButton.addEventListener("click", async () => {
  try {
    await startWorkflowTestRun();
    setRuntimeStatus("Testlauf abgeschlossen", "ok");
  } catch (error) {
    workflowAdminStatus.textContent = error.message;
    setRuntimeStatus(error.message, "error");
  }
});

queueWorkflowRunButton.addEventListener("click", async () => {
  try {
    await queueWorkflowRun();
    setRuntimeStatus("Worker-Run angelegt", "ok");
  } catch (error) {
    workflowAdminStatus.textContent = error.message;
    setRuntimeStatus(error.message, "error");
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
