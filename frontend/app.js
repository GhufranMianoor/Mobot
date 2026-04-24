const API_BASE = "http://localhost:8000";

const chatThread = document.getElementById("chatThread");
const chatForm = document.getElementById("chatForm");
const messageInput = document.getElementById("messageInput");
const chips = document.getElementById("chips");
const cardTemplate = document.getElementById("phoneCardTemplate");

function autoResize() {
  messageInput.style.height = "auto";
  messageInput.style.height = `${Math.min(messageInput.scrollHeight, 132)}px`;
}

function appendBubble(text, role = "bot") {
  const bubble = document.createElement("article");
  bubble.className = `bubble ${role}`;

  const p = document.createElement("p");
  p.textContent = text;
  bubble.appendChild(p);

  chatThread.appendChild(bubble);
  chatThread.scrollTop = chatThread.scrollHeight;
  return bubble;
}

function addTypingIndicator() {
  const bubble = document.createElement("article");
  bubble.className = "bubble bot";
  bubble.innerHTML = '<span class="typing"><i></i><i></i><i></i></span>';
  chatThread.appendChild(bubble);
  chatThread.scrollTop = chatThread.scrollHeight;
  return bubble;
}

function renderResult(data) {
  const bubble = document.createElement("article");
  bubble.className = "bubble bot";

  const lead = document.createElement("p");
  lead.textContent = data.reply;
  bubble.appendChild(lead);

  const head = document.createElement("div");
  head.className = "result-head";
  head.innerHTML = `
    <span class="badge">${data.tier}</span>
    <span>confidence: ${Math.round(data.confidence * 100)}%</span>
    <span>nlp: ${data.nlp_source}</span>
  `;
  bubble.appendChild(head);

  const list = document.createElement("ul");
  list.className = "phone-list";

  for (const phone of data.phones) {
    const node = cardTemplate.content.cloneNode(true);
    node.querySelector(".phone-name").textContent = phone.name;
    node.querySelector(".phone-specs").textContent = phone.specs;
    node.querySelector(".price").textContent = `Rs. ${phone.price_pkr.toLocaleString()}`;

    const link = node.querySelector(".source-link");
    link.textContent = phone.source;
    link.href = phone.url;

    list.appendChild(node);
  }

  bubble.appendChild(list);
  chatThread.appendChild(bubble);
  chatThread.scrollTop = chatThread.scrollHeight;
}

async function sendMessage(text) {
  appendBubble(text, "user");
  const typingNode = addTypingIndicator();

  try {
    const response = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, history: [] }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    typingNode.remove();

    if (Array.isArray(data.phones) && data.phones.length > 0) {
      renderResult(data);
    } else {
      appendBubble(data.reply || "No matching phones found.", "bot");
    }
  } catch (error) {
    typingNode.remove();
    appendBubble("Server is unavailable. Start backend on http://localhost:8000.", "bot");
    console.error(error);
  }
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = messageInput.value.trim();
  if (!text) return;

  messageInput.value = "";
  autoResize();
  await sendMessage(text);
});

messageInput.addEventListener("input", autoResize);
messageInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    chatForm.requestSubmit();
  }
});

chips.addEventListener("click", (event) => {
  if (!(event.target instanceof HTMLButtonElement)) return;
  const text = event.target.textContent?.trim();
  if (!text) return;

  messageInput.value = text;
  autoResize();
  chatForm.requestSubmit();
});
