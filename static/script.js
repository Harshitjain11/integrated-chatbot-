const input = document.getElementById("user-input");
const btn = document.getElementById("send-btn");
const micBtn = document.getElementById("mic-btn");
const messages = document.getElementById("chat-messages");

// Append message bubble
function appendMessage(sender, text) {
  const msg = document.createElement("div");
  msg.className = sender === "user" ? "user-msg" : "bot-msg";
  msg.textContent = text;
  messages.appendChild(msg);
  messages.scrollTop = messages.scrollHeight;
}

// Sending lock to avoid duplicate/concurrent sends
let isSending = false;

// Send message to backend
// if forceAppend true -> append user bubble before sending (used rarely)
async function sendMessage(customText = null, forceAppend = false) {
  const text = String(customText ?? input.value).trim();
  if (!text) return;
  if (isSending) {
    // optionally ignore or queue; here we ignore duplicates while sending
    console.warn("Send blocked: already sending");
    return;
  }
  isSending = true;

  // Append only if called from input (customText==null) or forceAppend true
  if (customText == null || forceAppend) {
    appendMessage("user", text);
  }

  // clear input if it was typed
  if (customText == null) input.value = "";

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: "harshit", message: text })
    });

    if (!res.ok) throw new Error("Network response not OK");

    const data = await res.json();
    const botReply = data.reply || "Sorry, I didn’t get that.";
    appendMessage("bot", botReply);
    speak(botReply);
  } catch (err) {
    console.error("Send error:", err);
    appendMessage("bot", "⚠️ Connection problem, please try again.");
  } finally {
    // release lock after a tiny delay so UI doesn't block too long
    setTimeout(() => { isSending = false; }, 300);
  }
}

// Voice output
function speak(text) {
  if (!text) return;
  const u = new SpeechSynthesisUtterance(text);
  u.lang = "en-IN";
  window.speechSynthesis.speak(u);
}

// ===== Voice Recognition (debounced + no duplicate bubbles) =====
let recognition;
let autoSend = true;
let lastTranscript = "";
let lastTime = 0;

// Create small toggle button (if not already present)
let toggleBtn = document.getElementById("auto-toggle");
if (!toggleBtn) {
  toggleBtn = document.createElement("button");
  toggleBtn.id = "auto-toggle";
  toggleBtn.textContent = "🎙️ Auto Send ON";
  toggleBtn.className = "toggle-btn";
  document.querySelector(".chat-input").appendChild(toggleBtn);
}
toggleBtn.addEventListener("click", () => {
  autoSend = !autoSend;
  toggleBtn.textContent = autoSend ? "🎙️ Auto Send ON" : "🎙️ Manual Mode";
  toggleBtn.classList.toggle("off", !autoSend);
});

if ("webkitSpeechRecognition" in window) {
  recognition = new webkitSpeechRecognition();
  recognition.lang = "en-IN";
  recognition.interimResults = false;
  recognition.continuous = false;

  recognition.onstart = () => (micBtn.textContent = "🎙️");
  recognition.onend = () => (micBtn.textContent = "🎤");

  recognition.onresult = (e) => {
    const transcript = String(e.results[0][0].transcript || "").trim();
    if (!transcript) return;

    const now = Date.now();
    // ignore repeated same transcript within 2 seconds
    if (transcript.toLowerCase() === lastTranscript.toLowerCase() && (now - lastTime) < 2000) {
      return;
    }
    lastTranscript = transcript;
    lastTime = now;

    // If autoSend -> directly send via sendMessage(transcript)
    if (autoSend) {
      // ensure we don't append here; sendMessage will append once
      // small delay to let recognition settle and avoid race
      setTimeout(() => {
        sendMessage(transcript, true); // pass forceAppend=true so user bubble appends exactly once
      }, 600);
    } else {
      // Manual: place text in input for user to inspect/send
      input.value = transcript;
    }
  };

  recognition.onerror = (err) => {
    console.error("Speech error:", err);
    micBtn.textContent = "🎤";
  };
} else {
  micBtn.addEventListener("click", () => alert("Speech recognition not supported in this browser."));
}

micBtn.addEventListener("click", () => {
  if (!recognition) return;
  try {
    recognition.start();
  } catch (e) {
    // sometimes start() throws if recognition already active; ignore
    console.warn("Recognition start error (ignored):", e);
  }
});

// UI event listeners
btn.addEventListener("click", () => sendMessage());
input.addEventListener("keypress", (e) => { if (e.key === "Enter") sendMessage(); });