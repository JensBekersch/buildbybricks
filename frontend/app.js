const appSelect = document.querySelector("#app-select");
const appDescription = document.querySelector("#app-description");
const collectionSelect = document.querySelector("#collection-select");
const refreshCollectionsButton = document.querySelector("#refresh-collections");
const documentList = document.querySelector("#document-list");
const documentCount = document.querySelector("#document-count");
const uploadForm = document.querySelector("#upload-form");
const uploadCollectionInput = document.querySelector("#upload-collection");
const uploadFilenameInput = document.querySelector("#upload-filename");
const uploadContentInput = document.querySelector("#upload-content");
const uploadStatus = document.querySelector("#upload-status");
const runtimeStatus = document.querySelector("#runtime-status");
const chatForm = document.querySelector("#chat-form");
const chatLog = document.querySelector("#chat-log");
const messageInput = document.querySelector("#message-input");
const modeTabs = document.querySelectorAll("[data-view-target]");
const views = document.querySelectorAll(".view");

const architectureForm = document.querySelector("#architecture-form");
const architectureDescription = document.querySelector("#architecture-description");
const architectureGenerationMode = document.querySelector("#architecture-generation-mode");
const generateArchitectureButton = document.querySelector("#generate-architecture");
const architectureStatus = document.querySelector("#architecture-status");
const architectureProgress = document.querySelector("#architecture-progress");
const architectureProgressLabel = document.querySelector("#architecture-progress-label");
const architectureProgressElapsed = document.querySelector("#architecture-progress-elapsed");
const architectureProgressSteps = document.querySelector("#architecture-progress-steps");
const architectureEmpty = document.querySelector("#architecture-empty");
const architectureResult = document.querySelector("#architecture-result");
const architectureTitle = document.querySelector("#architecture-title");
const architectureBusinessGoal = document.querySelector("#architecture-business-goal");
const architectureValidation = document.querySelector("#architecture-validation");
const architectureGeneration = document.querySelector("#architecture-generation");
const architectureSections = document.querySelector("#architecture-sections");
const architectureJson = document.querySelector("#architecture-json");
const architectureReviewStatus = document.querySelector("#architecture-review-status");
const architectureSchema = document.querySelector("#architecture-schema");
const architectureProvider = document.querySelector("#architecture-provider");
const architecturePipeline = document.querySelector("#architecture-pipeline");
const architectureSourceCount = document.querySelector("#architecture-source-count");
const architectureSources = document.querySelector("#architecture-sources");
const architectureTrace = document.querySelector("#architecture-trace");

let applications = [];
let activeAppId = "default";
let activeCollection = "";

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

function selectedApplication() {
  return applications.find((application) => application.id === activeAppId);
}

function setRuntimeStatus(text, tone = "neutral") {
  runtimeStatus.textContent = text;
  runtimeStatus.dataset.tone = tone;
}

function renderApplications() {
  appSelect.replaceChildren();

  applications.forEach((application) => {
    const option = document.createElement("option");
    option.value = application.id;
    option.textContent = application.name;
    appSelect.append(option);
  });

  if (applications.some((application) => application.id === activeAppId)) {
    appSelect.value = activeAppId;
  } else if (applications.length > 0) {
    activeAppId = applications[0].id;
    appSelect.value = activeAppId;
  }

  const application = selectedApplication();
  appDescription.textContent = application
    ? `${application.name} · ${application.description || application.id}`
    : "Keine Anwendung gefunden";
}

function renderCollections(collections) {
  collectionSelect.replaceChildren();

  collections.forEach((collection) => {
    const option = document.createElement("option");
    option.value = collection.name;
    option.textContent = `${collection.name} (${collection.document_count})`;
    collectionSelect.append(option);
  });

  if (collections.some((collection) => collection.name === activeCollection)) {
    collectionSelect.value = activeCollection;
  } else if (collections.length > 0) {
    activeCollection = collections[0].name;
    collectionSelect.value = activeCollection;
  } else {
    activeCollection = "";
  }

  uploadCollectionInput.value = activeCollection;
}

function renderDocuments(documents) {
  documentList.replaceChildren();
  documentCount.textContent = String(documents.length);

  if (documents.length === 0) {
    const emptyItem = document.createElement("li");
    emptyItem.className = "empty-state";
    emptyItem.textContent = "Keine Dokumente";
    documentList.append(emptyItem);
    return;
  }

  documents.forEach((sourceDocument) => {
    const item = document.createElement("li");
    const title = document.createElement("strong");
    const meta = document.createElement("span");

    title.textContent = sourceDocument.title || sourceDocument.filename;
    meta.textContent = `${sourceDocument.relative_path} · ${sourceDocument.char_count} Zeichen`;
    item.append(title, meta);
    documentList.append(item);
  });
}

async function loadApplications() {
  const payload = await getJson("/apps");
  applications = payload.applications || [];
  renderApplications();
}

async function loadCollections() {
  if (!activeAppId) {
    return;
  }

  const payload = await getJson(appPath(activeAppId, "collections"));
  renderCollections(payload.collections || []);
  await loadDocuments();
}

async function loadDocuments() {
  if (!activeAppId || !activeCollection) {
    renderDocuments([]);
    return;
  }

  const payload = await getJson(
    appPath(activeAppId, "collections", activeCollection, "documents")
  );
  renderDocuments(payload.documents || []);
}

async function setActiveApplication(appId) {
  activeAppId = appId;
  activeCollection = "";
  renderApplications();
  await loadCollections();
}

function appendMessage(author, text, details = [], sources = [], uncertainty = "") {
  const message = document.createElement("article");
  const content = document.createElement("p");
  content.textContent = `${author}: ${text}`;
  message.className = "chat-message";
  message.append(content);

  if (uncertainty) {
    const uncertaintyNote = document.createElement("p");
    uncertaintyNote.className = "uncertainty";
    uncertaintyNote.textContent = `Unsicherheit: ${uncertainty}`;
    message.append(uncertaintyNote);
  }

  if (sources.length > 0) {
    const sourceList = document.createElement("ol");
    sourceList.className = "source-list";

    sources.forEach((source) => {
      const sourceItem = document.createElement("li");
      sourceItem.textContent = `${source.title} (${source.location})`;

      if (source.excerpt) {
        const excerpt = document.createElement("small");
        excerpt.textContent = source.excerpt;
        sourceItem.append(excerpt);
      }

      sourceList.append(sourceItem);
    });

    message.append(sourceList);
  }

  if (details.length > 0) {
    const trace = document.createElement("small");
    trace.textContent = details.join(" -> ");
    trace.className = "trace";
    message.append(trace);
  }

  chatLog.append(message);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function activateView(targetId) {
  views.forEach((view) => {
    view.hidden = view.id !== targetId;
  });

  modeTabs.forEach((button) => {
    button.classList.toggle("is-active", button.dataset.viewTarget === targetId);
  });
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
  architectureProgress.hidden = false;
  architectureProgressSteps.replaceChildren();

  const activeStep = (job.steps || []).find((step) => step.key === job.current_step);
  const statusText = {
    queued: "Job wurde angelegt und wartet auf Ausfuehrung.",
    running: activeStep ? activeStep.label : "Job wird ausgefuehrt.",
    completed: "Architecture Sheet ist erstellt.",
    failed: job.error || "Job ist fehlgeschlagen.",
    canceled: job.error || "Job wurde abgebrochen.",
  };

  architectureProgressLabel.textContent = statusText[job.status] || job.status;
  architectureProgressElapsed.textContent = formatElapsedTime(job.started_at || job.created_at, job.finished_at);

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
  }
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
      const title = valueText(item.name || item.title || item.decision || item.scenario || item.risk);
      const description = valueText(
        item.description ||
          item.responsibility ||
          item.rationale ||
          item.mitigation ||
          item.trigger ||
          item.value
      );
      const meta = valueText(
        item.impact ||
          item.status ||
          item.priority ||
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

function appendSection(title, content) {
  const section = createElement("section", "sheet-section");
  section.append(createElement("h3", "", title));

  if (Array.isArray(content)) {
    appendList(section, content);
  } else {
    const text = valueText(content);
    section.append(createElement("p", "", text || "Noch offen"));
  }

  architectureSections.append(section);
}

function renderArchitectureSections(sheet) {
  architectureSections.replaceChildren();

  appendSection("Architecture Drivers", sheet.architecture_drivers || sheet.drivers || []);
  appendSection("Qualitaetsziele", sheet.quality_goals || []);
  appendSection("Kontext & Schnittstellen", sheet.context || sheet.external_interfaces || []);
  appendSection("Bausteine", sheet.building_blocks || []);
  appendSection("Laufzeitszenarien", sheet.runtime_scenarios || []);
  appendSection("Architekturentscheidungen", sheet.architecture_decisions || sheet.decisions || []);
  appendSection("Risiken", sheet.risks || []);
  appendSection("Annahmen", sheet.assumptions || []);
  appendSection("Offene Fragen", sheet.open_questions || []);
  appendSection("Akzeptanzkriterien", sheet.acceptance_criteria || []);
  appendSection("Teststrategie", sheet.test_strategy || []);
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
  const sheet = payload.architecture_sheet || {};
  const validation = payload.validation || {};
  const generation = payload.generation || {};
  const sources = payload.sources || [];
  const trace = payload.trace || [];
  const provider =
    generation.provider ||
    (generation.llm_provider && generation.llm_provider !== "none" ? generation.llm_provider : "") ||
    generation.mode ||
    "Regelbasiert";
  const model = generation.model || (generation.llm_model !== "none" ? generation.llm_model : "");
  const usedLlm = Boolean(generation.used_llm || (generation.llm_provider && generation.llm_provider !== "none"));

  architectureEmpty.hidden = true;
  architectureResult.hidden = false;
  architectureTitle.textContent = sheet.artifact_name || sheet.title || sheet.name || "Unbenanntes Artefakt";
  architectureBusinessGoal.textContent = valueText(sheet.business_goal || sheet.goal) || "Business-Ziel noch offen.";
  architectureValidation.textContent = validation.valid ? "Schema gueltig" : "Schema pruefen";
  architectureValidation.dataset.tone = validation.valid ? "ok" : "warn";
  architectureGeneration.textContent = provider;
  architectureGeneration.dataset.tone = usedLlm ? "accent" : "neutral";
  architectureJson.textContent = JSON.stringify(sheet, null, 2);

  architectureReviewStatus.textContent = validation.valid ? "Bestanden" : "Mit Hinweisen";
  architectureSchema.textContent = payload.schema_id || "-";
  architectureProvider.textContent = model ? `${provider} · ${model}` : provider;
  architecturePipeline.textContent = generation.pipeline || generation.requested_mode || generation.mode || "-";
  architectureSourceCount.textContent = String(sources.length);

  renderArchitectureSections(sheet);
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

    renderArchitectureJob(payload.job);
    architectureStatus.textContent = `Job ${payload.job.id} wurde angelegt.`;
    setRuntimeStatus("Bereit", "ok");
  } catch (error) {
    architectureProgress.hidden = false;
    architectureProgressLabel.textContent = error.message || "Job konnte nicht angelegt werden.";
    architectureProgressElapsed.textContent = "0s";
    architectureProgressSteps.replaceChildren();
    throw error;
  } finally {
    generateArchitectureButton.disabled = false;
    generateArchitectureButton.textContent = "Architecture Job anlegen";
  }
}

async function initialize() {
  try {
    setRuntimeStatus("Verbinden...");
    await loadApplications();
    await loadCollections();
    setRuntimeStatus("Bereit", "ok");
  } catch (error) {
    setRuntimeStatus(error.message || "API nicht erreichbar", "error");
    renderDocuments([]);
  }
}

modeTabs.forEach((button) => {
  button.addEventListener("click", async () => {
    const targetId = button.dataset.viewTarget;
    activateView(targetId);

    if (
      targetId === "architecture-view" &&
      activeAppId !== "software-factory" &&
      applications.some((application) => application.id === "software-factory")
    ) {
      try {
        await setActiveApplication("software-factory");
        setRuntimeStatus("Bereit", "ok");
      } catch (error) {
        setRuntimeStatus(error.message, "error");
      }
    }
  });
});

appSelect.addEventListener("change", async () => {
  try {
    await setActiveApplication(appSelect.value);
    setRuntimeStatus("Bereit", "ok");
  } catch (error) {
    setRuntimeStatus(error.message, "error");
  }
});

collectionSelect.addEventListener("change", async () => {
  activeCollection = collectionSelect.value;
  uploadCollectionInput.value = activeCollection;

  try {
    await loadDocuments();
  } catch (error) {
    setRuntimeStatus(error.message, "error");
  }
});

refreshCollectionsButton.addEventListener("click", async () => {
  try {
    await loadCollections();
    setRuntimeStatus("Aktualisiert", "ok");
  } catch (error) {
    setRuntimeStatus(error.message, "error");
  }
});

uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const collection = uploadCollectionInput.value.trim();
  const filename = uploadFilenameInput.value.trim();
  const content = uploadContentInput.value.trim();

  if (!collection || !filename || !content) {
    uploadStatus.textContent = "Collection, Dateiname und Inhalt sind erforderlich.";
    return;
  }

  try {
    uploadStatus.textContent = "Upload laeuft...";
    await postJson(appPath(activeAppId, "collections", collection, "documents"), {
      filename,
      content,
    });
    activeCollection = collection;
    uploadFilenameInput.value = "";
    uploadContentInput.value = "";
    uploadStatus.textContent = "Gespeichert.";
    await loadCollections();
  } catch (error) {
    uploadStatus.textContent = error.message;
  }
});

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = messageInput.value.trim();

  if (!message) {
    return;
  }

  appendMessage("Du", message);
  messageInput.value = "";

  try {
    const payload = await postJson(appPath(activeAppId, "chat"), {
      message,
      collection: activeCollection || undefined,
    });

    const details = [...(payload.trace || [])];
    if (payload.tool_calls && payload.tool_calls.length > 0) {
      details.push(...payload.tool_calls.map((toolCall) => toolCall.name));
    }
    appendMessage("Agent", payload.answer, details, payload.sources || [], payload.uncertainty || "");
  } catch (error) {
    appendMessage("System", error.message || "Die API ist nicht erreichbar.");
  }
});

architectureForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  try {
    await generateArchitectureSheet();
  } catch (error) {
    architectureStatus.textContent = error.message || "Architecture Sheet konnte nicht erstellt werden.";
    setRuntimeStatus("Fehler", "error");
  }
});

initialize();
