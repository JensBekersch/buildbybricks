const chatForm = document.querySelector("#chat-form");
const chatLog = document.querySelector("#chat-log");
const messageInput = document.querySelector("#message-input");

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
    trace.style.color = "#5f6368";
    message.append(trace);
  }

  chatLog.append(message);
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = messageInput.value.trim();

  if (!message) {
    return;
  }

  appendMessage("Du", message);
  messageInput.value = "";

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ message }),
    });

    const payload = await response.json();

    if (!response.ok) {
      appendMessage("System", payload.error || "Die Anfrage konnte nicht verarbeitet werden.");
      return;
    }

    const details = [...(payload.trace || [])];
    if (payload.tool_calls && payload.tool_calls.length > 0) {
      details.push(...payload.tool_calls.map((toolCall) => toolCall.name));
    }
    appendMessage("Agent", payload.answer, details, payload.sources || [], payload.uncertainty || "");
  } catch (error) {
    appendMessage("System", "Die API ist nicht erreichbar.");
  }
});
