(() => {
  "use strict";

  const STORAGE = {
    server: "kii.mobile.serverUrl",
    apiKey: "kii.mobile.apiKey",
    messages: "kii.mobile.messages.v1",
    session: "kii.mobile.sessionId"
  };
  const API_PATH = "/api/v1/chat";
  const $ = (selector) => document.querySelector(selector);

  const form = $("#chat-form");
  const input = $("#message-input");
  const messagesNode = $("#chat-messages");
  const sendButton = $("#send-button");
  const settingsDialog = $("#settings-dialog");
  const settingsForm = $("#settings-form");
  const serverInput = $("#server-url");
  const apiKeyInput = $("#api-key");
  const connectionIndicator = $("#connection-indicator");
  const connectionTest = $("#connection-test");
  const connectionResult = $("#connection-result");
  const settingsError = $("#settings-error");
  const toast = $("#toast");

  let messages = loadMessages();
  let sending = false;
  let toastTimer;

  function getSessionId() {
    let id = localStorage.getItem(STORAGE.session);
    if (!id) {
      id = typeof crypto.randomUUID === "function"
        ? crypto.randomUUID()
        : "kii-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2);
      localStorage.setItem(STORAGE.session, id);
    }
    return id;
  }

  function loadMessages() {
    try {
      const parsed = JSON.parse(localStorage.getItem(STORAGE.messages) || "[]");
      return Array.isArray(parsed) ? parsed.slice(-100) : [];
    } catch {
      return [];
    }
  }

  function saveMessages() {
    try {
      localStorage.setItem(STORAGE.messages, JSON.stringify(messages.slice(-100)));
    } catch {
      showToast("Не удалось сохранить историю в браузере.");
    }
  }

  function addMessage(role, text, options = {}) {
    const message = { role, text: String(text), time: new Date().toISOString(), error: Boolean(options.error) };
    messages.push(message);
    messages = messages.slice(-100);
    renderMessage(message);
    saveMessages();
    return message;
  }

  function renderMessage(message) {
    const article = document.createElement("article");
    article.className = "message " + (message.role === "user" ? "user-message" : "assistant-message");
    if (message.error) article.classList.add("error");

    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.textContent = message.role === "user" ? "В" : "K";

    const content = document.createElement("div");
    content.className = "message-content";

    const meta = document.createElement("div");
    meta.className = "message-meta";
    meta.textContent = message.role === "user" ? "ВЫ" : "KII";
    if (message.error) {
      const tag = document.createElement("span");
      tag.textContent = "ОШИБКА";
      meta.appendChild(tag);
    }

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = message.text;

    const time = document.createElement("div");
    time.className = "message-time";
    time.textContent = formatTime(message.time);

    content.append(meta, bubble, time);
    article.append(avatar, content);
    messagesNode.appendChild(article);
    messagesNode.scrollTop = messagesNode.scrollHeight;
    article.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function formatTime(value) {
    try {
      return new Intl.DateTimeFormat("ru-RU", { hour: "2-digit", minute: "2-digit" }).format(new Date(value));
    } catch {
      return "";
    }
  }

  function renderHistory() {
    // Keep the welcome card from index.html for a brand-new local session.
    if (messages.length === 0) return;
    messagesNode.replaceChildren();
    messages.forEach(renderMessage);
  }

  function serverUrl() {
    return (localStorage.getItem(STORAGE.server) || "").trim().replace(/\/+$/, "");
  }

  function setConnection(connected, label) {
    connectionIndicator.classList.toggle("connected", connected);
    connectionIndicator.querySelector("span").textContent = label;
  }

  function openSettings() {
    serverInput.value = serverUrl();
    apiKeyInput.value = localStorage.getItem(STORAGE.apiKey) || "";
    settingsError.textContent = "";
    connectionResult.textContent = "";
    settingsDialog.showModal();
  }

  function normalizeServerUrl(value) {
    const parsed = new URL(value.trim());
    if (!["http:", "https:"].includes(parsed.protocol)) throw new Error("Используй адрес http:// или https://.");
    if (parsed.username || parsed.password) throw new Error("Не добавляй логин и пароль в URL.");
    return parsed.toString().replace(/\/+$/, "");
  }

  async function checkConnection(baseUrl, apiKey = "", timeoutMs = 5000) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      // Health endpoint is part of the planned API contract.
      const response = await fetch(baseUrl + "/health", {
        method: "GET",
        headers: { "Accept": "application/json", ...(apiKey ? { "X-KII-API-Key": apiKey } : {}) },
        signal: controller.signal
      });
      if (!response.ok) throw new Error("Сервер ответил HTTP " + response.status + ".");
      const data = await response.json();
      if (data.status && data.status !== "ok" && data.status !== "healthy") {
        throw new Error("Сервер доступен, но сообщил статус: " + data.status);
      }
      return true;
    } finally {
      clearTimeout(timer);
    }
  }

  settingsForm.addEventListener("submit", (event) => {
    event.preventDefault();
    settingsError.textContent = "";
    try {
      const value = serverInput.value.trim();
      if (!value) {
        localStorage.removeItem(STORAGE.server);
        localStorage.removeItem(STORAGE.apiKey);
        setConnection(false, "Не подключён");
        settingsDialog.close();
        showToast("Адрес сервера очищен.");
        return;
      }
      const normalized = normalizeServerUrl(value);
      localStorage.setItem(STORAGE.server, normalized);
      if (apiKeyInput.value.trim()) localStorage.setItem(STORAGE.apiKey, apiKeyInput.value.trim());
      else localStorage.removeItem(STORAGE.apiKey);
      setConnection(false, "Адрес сохранён");
      settingsDialog.close();
      showToast("Адрес сервера сохранён. Проверь связь перед отправкой сообщений.");
    } catch (error) {
      settingsError.textContent = error.message || "Некорректный адрес.";
    }
  });

  connectionTest.addEventListener("click", async () => {
    settingsError.textContent = "";
    connectionResult.textContent = "";
    let baseUrl;
    try {
      baseUrl = normalizeServerUrl(serverInput.value);
    } catch (error) {
      settingsError.textContent = error.message || "Некорректный адрес.";
      return;
    }

    connectionTest.disabled = true;
    connectionTest.textContent = "Проверяю…";
    try {
      await checkConnection(baseUrl, apiKeyInput.value.trim());
      connectionResult.textContent = "Связь есть. Сервер отвечает на /health.";
      connectionResult.style.color = "var(--green)";
    } catch (error) {
      connectionResult.textContent = error.name === "AbortError"
        ? "Время ожидания истекло. Проверь адрес и доступность сервера."
        : "Проверка не прошла: " + (error.message || "ошибка сети") + " Серверный API KII может быть ещё не развёрнут.";
      connectionResult.style.color = "#ff9a8d";
    } finally {
      connectionTest.disabled = false;
      connectionTest.textContent = "Проверить связь";
    }
  });

  $("#settings-open").addEventListener("click", openSettings);
  $("#side-settings").addEventListener("click", openSettings);
  $("#settings-close").addEventListener("click", () => settingsDialog.close());

  async function sendMessage(text) {
    const baseUrl = serverUrl();
    if (!baseUrl) {
      addMessage("assistant", "Сервер не настроен. Открой настройки подключения и укажи адрес API KII. Сейчас мобильный клиент не может отправить запрос в ядро.");
      openSettings();
      return;
    }

    sending = true;
    sendButton.disabled = true;
    sendButton.querySelector("span").textContent = "Отправка…";
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 60000);

    try {
      const response = await fetch(baseUrl + API_PATH, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json",
          ...(localStorage.getItem(STORAGE.apiKey) ? { "X-KII-API-Key": localStorage.getItem(STORAGE.apiKey) } : {})
        },
        body: JSON.stringify({ message: text, session_id: getSessionId(), client: "kii-mobile" }),
        signal: controller.signal
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = data.detail || data.error || data.message || ("HTTP " + response.status);
        throw new Error(String(detail));
      }
      const reply = data.reply ?? data.response ?? data.message;
      if (typeof reply !== "string" || !reply.trim()) {
        throw new Error("Сервер ответил, но не вернул текст в поле reply, response или message.");
      }
      setConnection(true, "Подключён");
      addMessage("assistant", reply);
    } catch (error) {
      const description = error.name === "AbortError"
        ? "Сервер не ответил за 60 секунд."
        : error instanceof TypeError
          ? "Не удалось подключиться. Проверь адрес, доступность сервера и настройки HTTPS/CORS."
          : error.message || "Неизвестная ошибка.";
      setConnection(false, "Нет связи");
      addMessage("assistant", "Не удалось получить ответ от KII: " + description, { error: true });
    } finally {
      clearTimeout(timer);
      sending = false;
      sendButton.disabled = false;
      sendButton.querySelector("span").textContent = "Отправить";
      input.focus();
    }
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const text = input.value.trim();
    if (!text || sending) return;
    addMessage("user", text);
    input.value = "";
    resizeInput();
    await sendMessage(text);
  });

  function resizeInput() {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 160) + "px";
  }

  input.addEventListener("input", resizeInput);
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      form.requestSubmit();
    }
  });

  document.querySelectorAll("[data-prompt]").forEach((button) => {
    button.addEventListener("click", () => {
      input.value = button.dataset.prompt || "";
      resizeInput();
      input.focus();
    });
  });

  document.querySelectorAll("[data-coming]").forEach((button) => {
    button.addEventListener("click", () => showToast(button.dataset.coming + " появится на следующем этапе."));
  });

  function showToast(message) {
    toast.textContent = message;
    toast.classList.add("visible");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("visible"), 3000);
  }

  renderHistory();
  if (serverUrl()) setConnection(false, "Адрес сохранён");

  if ("serviceWorker" in navigator && location.protocol.startsWith("http")) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("./sw.js").catch(() => {
        // The app remains usable if service-worker registration is blocked.
      });
    });
  }
})();
