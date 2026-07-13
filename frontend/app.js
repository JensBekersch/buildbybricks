const chatForm = document.querySelector("#chat-form");
const chatLog = document.querySelector("#chat-log");
const messageInput = document.querySelector("#message-input");

function appendMessage(author, text) {
  const message = document.createElement("article");
  message.textContent = `${author}: ${text}`;
  message.style.padding = "12px 16px";
  chatLog.append(message);
}

chatForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const message = messageInput.value.trim();

  if (!message) {
    return;
  }

  appendMessage("Du", message);
  appendMessage("System", "Die API wird im naechsten Schritt angebunden.");
  messageInput.value = "";
});
