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

appSelect.addEventListener("change", async () => {
  activeAppId = appSelect.value;
  activeCollection = "";
  renderApplications();

  try {
    await loadCollections();
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

initialize();
