const chatForm = document.querySelector("#chat-form");
const chatLog = document.querySelector("#chat-log");
const messageInput = document.querySelector("#message-input");

function appendMessage(author, text, details = []) {
  const message = document.createElement("article");
  const content = document.createElement("p");
  content.textContent = `${author}: ${text}`;
  message.style.padding = "12px 16px";
  message.append(content);

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

    appendMessage("Agent", payload.answer, payload.trace || []);
  } catch (error) {
    appendMessage("System", "Die API ist nicht erreichbar.");
  }
});
