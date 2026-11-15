const state = {
  user: null,
  token: localStorage.getItem("rag_access_token"),
  chats: [],
  activeChatId: null,
};

const loginView = document.querySelector("#login-view");
const workspaceView = document.querySelector("#workspace-view");
const loginForm = document.querySelector("#login-form");
const nameField = document.querySelector("#name-field");
const nameInput = document.querySelector("#name");
const authModeToggle = document.querySelector("#auth-mode-toggle");
const authSubmitLabel = document.querySelector("#auth-submit-label");
const sessionTitle = document.querySelector("#session-title");
const roleBadge = document.querySelector("#role-badge");
const adminNav = document.querySelector("#admin-nav");
const historyList = document.querySelector("#history-list");
const messages = document.querySelector("#messages");
const chatForm = document.querySelector("#chat-form");
const queryInput = document.querySelector("#query-input");
const newChatBtn = document.querySelector("#new-chat-btn");
const logoutBtn = document.querySelector("#logout-btn");
const textUploadForm = document.querySelector("#text-upload-form");
const pdfUploadForm = document.querySelector("#pdf-upload-form");
const pdfFile = document.querySelector("#pdf-file");
const pdfFileName = document.querySelector("#pdf-file-name");
const uploadStatus = document.querySelector("#upload-status");

let authMode = "login";

function setAuthMode(mode) {
  authMode = mode;
  const isSignup = mode === "signup";
  nameField.classList.toggle("hidden", !isSignup);
  nameInput.required = isSignup;
  authSubmitLabel.textContent = isSignup ? "Create account" : "Sign in";
  authModeToggle.textContent = isSignup ? "Already have an account? Sign in" : "Need an account? Sign up";
}

function setPanel(panelId) {
  document.querySelectorAll(".panel").forEach((panel) => {
    panel.classList.toggle("hidden", panel.id !== panelId);
  });
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.panel === panelId);
  });
}

function formatDate(value) {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function activeChat() {
  return state.chats.find((chat) => chat.id === state.activeChatId);
}

function renderHistory() {
  historyList.innerHTML = "";

  if (!state.chats.length) {
    historyList.innerHTML = '<div class="history-item"><strong>No chats yet</strong><small>Start a query</small></div>';
    return;
  }

  state.chats.forEach((chat) => {
    const button = document.createElement("button");
    button.className = `history-item ${chat.id === state.activeChatId ? "active" : ""}`;
    button.type = "button";
    button.innerHTML = `<strong>${escapeHtml(chat.title || "Untitled chat")}</strong><small>${formatDate(chat.updatedAt)}</small>`;
    button.addEventListener("click", () => {
      state.activeChatId = chat.id;
      renderHistory();
      renderMessages();
    });
    historyList.appendChild(button);
  });
}

function renderMessages() {
  const chat = activeChat();
  messages.innerHTML = "";

  if (!chat || !chat.messages.length) {
    addMessage("meta", "Start a conversation. Replies will follow the language used in the query.");
    return;
  }

  chat.messages.forEach((message) => addMessage(message.role, message.content));
  messages.scrollTop = messages.scrollHeight;
}

function addMessage(role, content) {
  const bubble = document.createElement("div");
  bubble.className = `message ${role === "user" ? "user" : role === "meta" ? "meta" : "assistant"}`;
  bubble.textContent = content;
  messages.appendChild(bubble);
}

function escapeHtml(value) {
  return value.replace(/[&<>"']/g, (char) => {
    return {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#039;",
    }[char];
  });
}

async function loadWorkspace() {
  state.chats = [];
  state.activeChatId = null;
  sessionTitle.textContent = `${state.user.name || "User"}'s console`;
  roleBadge.textContent = "User";
  adminNav.classList.add("hidden");
  setPanel("chat-panel");
  renderHistory();
  renderMessages();
}

authModeToggle.addEventListener("click", () => setAuthMode(authMode === "login" ? "signup" : "login"));

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const submitButton = loginForm.querySelector("button[type='submit']");
  submitButton.disabled = true;
  submitButton.querySelector("span").textContent = authMode === "signup" ? "Creating account" : "Signing in";

  try {
    const email = document.querySelector("#email").value;
    const password = document.querySelector("#password").value;
    if (authMode === "signup") {
      await window.ragApi.signup({ name: nameInput.value.trim(), email, password });
      setAuthMode("login");
      alert("Account created. Please sign in.");
      return;
    }
    const result = await window.ragApi.login({ email, password });
    state.user = result.user;
    state.token = result.token;
    localStorage.setItem("rag_access_token", result.token);
    localStorage.setItem("rag_user_name", result.user.name || "User");
    loginView.classList.add("hidden");
    workspaceView.classList.remove("hidden");
    await loadWorkspace();
  } catch (error) {
    alert(error.message);
  } finally {
    submitButton.disabled = false;
    submitButton.querySelector("span").textContent = authMode === "signup" ? "Create account" : "Sign in";
  }
});

adminNav.addEventListener("click", (event) => {
  const button = event.target.closest(".tab");
  if (button) setPanel(button.dataset.panel);
});

newChatBtn.addEventListener("click", () => {
  state.activeChatId = null;
  renderHistory();
  renderMessages();
  queryInput.focus();
});

logoutBtn.addEventListener("click", () => {
  state.user = null;
  state.token = null;
  localStorage.removeItem("rag_access_token");
  localStorage.removeItem("rag_user_name");
  state.activeChatId = null;
  workspaceView.classList.add("hidden");
  loginView.classList.remove("hidden");
});

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const query = queryInput.value.trim();
  if (!query) return;

  queryInput.value = "";
  const optimisticChat = activeChat() || {
    id: `draft-${Date.now()}`,
    title: query.slice(0, 44),
    updatedAt: new Date().toISOString(),
    messages: [],
  };

  if (!activeChat()) {
    state.chats.unshift(optimisticChat);
    state.activeChatId = optimisticChat.id;
  }

  optimisticChat.messages.push({ role: "user", content: query });
  renderHistory();
  renderMessages();
  addMessage("assistant", "Thinking...");

  try {
    const answer = await window.ragApi.ask({ token: state.token, query });
    optimisticChat.messages.push({ role: "assistant", content: answer });
    renderMessages();
  } catch (error) {
    optimisticChat.messages.push({ role: "assistant", content: error.message });
    renderMessages();
  }
});

// Keep an existing browser session after a refresh. A failed protected request
// will still safely return the user to the sign-in screen.
if (state.token) {
  loginView.classList.add("hidden");
  workspaceView.classList.remove("hidden");
  state.user = { name: localStorage.getItem("rag_user_name") || "User" };
  loadWorkspace();
}

textUploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  uploadStatus.textContent = "Uploading raw text...";

  try {
    const result = await window.ragApi.uploadText({
      title: document.querySelector("#text-title").value.trim(),
      text: document.querySelector("#raw-text").value.trim(),
    });
    uploadStatus.textContent = `Text upload ${result.status}. Estimated chunks: ${result.chunks || "pending"}.`;
    textUploadForm.reset();
  } catch (error) {
    uploadStatus.textContent = error.message;
  }
});

pdfFile.addEventListener("change", () => {
  pdfFileName.textContent = pdfFile.files[0]?.name || "No file selected";
});

pdfUploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = pdfFile.files[0];
  if (!file) return;

  uploadStatus.textContent = "Uploading PDF for scraping...";

  try {
    const result = await window.ragApi.uploadPdf(file);
    uploadStatus.textContent = `PDF upload ${result.status}: ${result.fileName || file.name}.`;
    pdfUploadForm.reset();
    pdfFileName.textContent = "No file selected";
  } catch (error) {
    uploadStatus.textContent = error.message;
  }
});
