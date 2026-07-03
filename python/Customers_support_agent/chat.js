/**
 * Support Console front-end controller.
 *
 * Responsibilities:
 *  - Manage a per-browser session id (persisted in localStorage).
 *  - Open/maintain a WebSocket connection to /ws/chat and render streamed
 *    answer chunks + source citations as they arrive.
 *  - Handle multi-file drag & drop / browse upload to /api/upload with a
 *    progress bar, and list indexed documents.
 *  - Surface connection/health status and expose a "new conversation" reset.
 */

(() => {
  "use strict";

  const SESSION_STORAGE_KEY = "support_console_session_id";
  const WS_RECONNECT_DELAY_MS = 2000;

  const els = {
    dropzone: document.getElementById("dropzone"),
    fileInput: document.getElementById("file-input"),
    uploadProgress: document.getElementById("upload-progress"),
    progressFill: document.getElementById("progress-fill"),
    progressLabel: document.getElementById("progress-label"),
    docList: document.getElementById("doc-list"),
    statusDot: document.getElementById("status-dot"),
    statusText: document.getElementById("status-text"),
    newSessionBtn: document.getElementById("new-session-btn"),
    messages: document.getElementById("messages"),
    chatForm: document.getElementById("chat-form"),
    chatInput: document.getElementById("chat-input"),
    sendBtn: document.getElementById("send-btn"),
    citationTemplate: document.getElementById("citation-template"),
  };

  /** Thin wrapper around the streaming chat WebSocket connection. */
  class ChatSocket {
    /**
     * @param {(event: object) => void} onEvent Callback invoked with every
     *   parsed server event.
     * @param {(connected: boolean) => void} onStatusChange Callback invoked
     *   whenever the connection opens or closes.
     */
    constructor(onEvent, onStatusChange) {
      this._onEvent = onEvent;
      this._onStatusChange = onStatusChange;
      this._socket = null;
      this._reconnectTimer = null;
      this._shouldReconnect = true;
      this._connect();
    }

    _connect() {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const url = `${protocol}//${window.location.host}/ws/chat`;
      this._socket = new WebSocket(url);

      this._socket.addEventListener("open", () => this._onStatusChange(true));
      this._socket.addEventListener("close", () => {
        this._onStatusChange(false);
        if (this._shouldReconnect) {
          this._reconnectTimer = window.setTimeout(
            () => this._connect(),
            WS_RECONNECT_DELAY_MS
          );
        }
      });
      this._socket.addEventListener("error", () => this._socket.close());
      this._socket.addEventListener("message", (evt) => {
        try {
          const data = JSON.parse(evt.data);
          this._onEvent(data);
        } catch {
          // Ignore malformed frames rather than crashing the UI.
        }
      });
    }

    /**
     * Send a chat message over the socket.
     * @param {string} sessionId Current session id.
     * @param {string} message User message text.
     */
    send(sessionId, message) {
      if (!this._socket || this._socket.readyState !== WebSocket.OPEN) {
        this._onEvent({ type: "error", detail: "Not connected. Reconnecting…" });
        return;
      }
      this._socket.send(JSON.stringify({ session_id: sessionId, message }));
    }

    dispose() {
      this._shouldReconnect = false;
      if (this._reconnectTimer) window.clearTimeout(this._reconnectTimer);
      if (this._socket) this._socket.close();
    }
  }

  /** Drives the whole console: session, sockets, uploads, rendering. */
  class SupportConsoleApp {
    constructor() {
      this.sessionId = this._loadOrCreateSessionId();
      this.currentAssistantBubble = null;
      this.currentAssistantText = "";

      this.socket = new ChatSocket(
        (event) => this._handleServerEvent(event),
        (connected) => this._setConnectionStatus(connected)
      );

      this._bindEvents();
    }

    _loadOrCreateSessionId() {
      let id = window.localStorage.getItem(SESSION_STORAGE_KEY);
      if (!id) {
        id = crypto.randomUUID();
        window.localStorage.setItem(SESSION_STORAGE_KEY, id);
      }
      return id;
    }

    _bindEvents() {
      els.chatForm.addEventListener("submit", (e) => this._onSubmit(e));
      els.chatInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          els.chatForm.requestSubmit();
        }
      });
      els.chatInput.addEventListener("input", () => this._autoGrow());

      els.newSessionBtn.addEventListener("click", () => this._startNewSession());

      els.dropzone.addEventListener("click", () => els.fileInput.click());
      els.dropzone.addEventListener("dragover", (e) => {
        e.preventDefault();
        els.dropzone.classList.add("dragover");
      });
      els.dropzone.addEventListener("dragleave", () =>
        els.dropzone.classList.remove("dragover")
      );
      els.dropzone.addEventListener("drop", (e) => {
        e.preventDefault();
        els.dropzone.classList.remove("dragover");
        if (e.dataTransfer.files.length) this._uploadFiles(e.dataTransfer.files);
      });
      els.fileInput.addEventListener("change", () => {
        if (els.fileInput.files.length) this._uploadFiles(els.fileInput.files);
        els.fileInput.value = "";
      });
    }

    _autoGrow() {
      els.chatInput.style.height = "auto";
      els.chatInput.style.height = `${Math.min(els.chatInput.scrollHeight, 160)}px`;
    }

    // -- Connection status -------------------------------------------------

    _setConnectionStatus(connected) {
      els.statusDot.classList.toggle("online", connected);
      els.statusDot.classList.toggle("offline", !connected);
      els.statusText.textContent = connected ? "Connected" : "Reconnecting…";
      els.sendBtn.disabled = !connected;
    }

    // -- Sending / receiving chat -------------------------------------------

    _onSubmit(e) {
      e.preventDefault();
      const text = els.chatInput.value.trim();
      if (!text) return;

      this._appendUserMessage(text);
      els.chatInput.value = "";
      this._autoGrow();

      this.currentAssistantBubble = this._appendAssistantMessage("", { typing: true });
      this.currentAssistantText = "";

      this.socket.send(this.sessionId, text);
    }

    _handleServerEvent(event) {
      switch (event.type) {
        case "chunk":
          this._appendChunk(event.text);
          break;
        case "sources":
          this._renderSources(event.sources || []);
          break;
        case "error":
          this._renderError(event.detail || "Something went wrong.");
          break;
        case "done":
          this.currentAssistantBubble = null;
          break;
        default:
          break;
      }
    }

    _appendChunk(text) {
      if (!this.currentAssistantBubble) {
        this.currentAssistantBubble = this._appendAssistantMessage("", {});
      }
      const bubble = this.currentAssistantBubble.querySelector(".bubble");
      const typing = bubble.querySelector(".typing-dots");
      if (typing) typing.remove();

      this.currentAssistantText += text;
      let p = bubble.querySelector("p.answer-text");
      if (!p) {
        p = document.createElement("p");
        p.className = "answer-text";
        bubble.prepend(p);
      }
      p.textContent = this.currentAssistantText;
      this._scrollToBottom();
    }

    _renderSources(sources) {
      if (!this.currentAssistantBubble || sources.length === 0) return;
      const bubble = this.currentAssistantBubble.querySelector(".bubble");

      const wrap = document.createElement("div");
      wrap.className = "citations";

      const label = document.createElement("p");
      label.className = "citations-label";
      label.textContent = `Sources (${sources.length})`;
      wrap.appendChild(label);

      for (const source of sources) {
        const node = els.citationTemplate.content.cloneNode(true);
        node.querySelector(".citation-doc").textContent = source.document_name;
        const pct = Math.round((source.score || 0) * 100);
        node.querySelector(".citation-score-label").textContent = `${pct}%`;
        node.querySelector(".citation-score-fill").style.width = `${pct}%`;
        node.querySelector(".citation-text").textContent = source.chunk_text;
        wrap.appendChild(node);
      }

      bubble.appendChild(wrap);
      this._scrollToBottom();
    }

    _renderError(detail) {
      if (this.currentAssistantBubble) {
        const bubble = this.currentAssistantBubble.querySelector(".bubble");
        const typing = bubble.querySelector(".typing-dots");
        if (typing) typing.remove();
        if (!this.currentAssistantText) {
          this.currentAssistantBubble.remove();
        }
      }
      this.currentAssistantBubble = null;

      const msg = document.createElement("div");
      msg.className = "message error";
      msg.innerHTML = `
        <div class="avatar assistant-avatar">!</div>
        <div class="bubble"><p></p></div>
      `;
      msg.querySelector("p").textContent = detail;
      els.messages.appendChild(msg);
      this._scrollToBottom();
    }

    _appendUserMessage(text) {
      const msg = document.createElement("div");
      msg.className = "message user";
      msg.innerHTML = `
        <div class="avatar user-avatar">You</div>
        <div class="bubble"><p></p></div>
      `;
      msg.querySelector("p").textContent = text;
      els.messages.appendChild(msg);
      this._scrollToBottom();
      return msg;
    }

    _appendAssistantMessage(text, { typing = false } = {}) {
      const msg = document.createElement("div");
      msg.className = "message assistant";
      msg.innerHTML = `
        <div class="avatar assistant-avatar">◈</div>
        <div class="bubble"></div>
      `;
      const bubble = msg.querySelector(".bubble");
      if (typing) {
        bubble.innerHTML = `<div class="typing-dots"><span></span><span></span><span></span></div>`;
      } else if (text) {
        const p = document.createElement("p");
        p.className = "answer-text";
        p.textContent = text;
        bubble.appendChild(p);
      }
      els.messages.appendChild(msg);
      this._scrollToBottom();
      return msg;
    }

    _scrollToBottom() {
      els.messages.scrollTop = els.messages.scrollHeight;
    }

    // -- Sessions ------------------------------------------------------------

    async _startNewSession() {
      try {
        await fetch(`/api/chat/${this.sessionId}`, { method: "DELETE" });
      } catch {
        // Non-fatal: even if the server call fails we still start fresh
        // locally so the user isn't blocked.
      }
      this.sessionId = crypto.randomUUID();
      window.localStorage.setItem(SESSION_STORAGE_KEY, this.sessionId);
      els.messages.innerHTML = "";
      this._appendAssistantMessage(
        "New conversation started. Ask me anything about your uploaded documents."
      );
    }

    // -- Uploads ---------------------------------------------------------------

    async _uploadFiles(fileList) {
      const formData = new FormData();
      for (const file of fileList) formData.append("files", file);

      els.uploadProgress.classList.remove("hidden");
      this._setProgress(0, "Uploading…");

      try {
        const xhr = new XMLHttpRequest();
        const responseText = await new Promise((resolve, reject) => {
          xhr.open("POST", "/api/upload");
          xhr.upload.addEventListener("progress", (evt) => {
            if (evt.lengthComputable) {
              const pct = Math.round((evt.loaded / evt.total) * 100);
              this._setProgress(pct, pct < 100 ? "Uploading…" : "Indexing…");
            }
          });
          xhr.addEventListener("load", () => {
            if (xhr.status >= 200 && xhr.status < 300) {
              resolve(xhr.responseText);
            } else {
              reject(new Error(xhr.responseText || `Upload failed (${xhr.status})`));
            }
          });
          xhr.addEventListener("error", () => reject(new Error("Network error during upload.")));
          xhr.send(formData);
        });

        const data = JSON.parse(responseText);
        this._setProgress(100, "Done");
        for (const doc of data.documents) this._addDocToList(doc, false);
      } catch (err) {
        this._addDocToList({ filename: "Upload failed", chunk_count: 0 }, true, err.message);
      } finally {
        window.setTimeout(() => els.uploadProgress.classList.add("hidden"), 800);
      }
    }

    _setProgress(pct, label) {
      els.progressFill.style.width = `${pct}%`;
      els.progressLabel.textContent = label;
    }

    _addDocToList(doc, isError, errorDetail) {
      const li = document.createElement("li");
      if (isError) li.classList.add("error");
      const name = document.createElement("span");
      name.className = "doc-name";
      name.textContent = isError ? errorDetail || doc.filename : doc.filename;
      const chunks = document.createElement("span");
      chunks.className = "doc-chunks";
      chunks.textContent = isError ? "✕" : `${doc.chunk_count} chunks`;
      li.appendChild(name);
      li.appendChild(chunks);
      els.docList.appendChild(li);
    }
  }

  document.addEventListener("DOMContentLoaded", () => new SupportConsoleApp());
})();
