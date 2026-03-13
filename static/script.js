// Fixed script.js - consolidated and cleaned up

const input = document.getElementById("user-input");
const btn = document.getElementById("send-btn");
const micBtn = document.getElementById("mic-btn");
const messages = document.getElementById("chat-messages");
const chatToggle = document.getElementById("chat-toggle");
const chatContainer = document.getElementById("chat-container");
const minimizeBtn = document.getElementById("minimize-btn");
const resetBtn = document.getElementById("reset-btn");

// Sending lock to avoid duplicate/concurrent sends
let isSending = false;

// Append message bubble with timestamp
function appendMessage(sender, text) {
  const wrapper = document.createElement("div");
  wrapper.className = sender === "user" ? "message user-msg" : "message bot-msg";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;

  const time = document.createElement("div");
  time.className = "time";
  time.textContent = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  wrapper.appendChild(bubble);
  wrapper.appendChild(time);
  messages.appendChild(wrapper);
  messages.scrollTop = messages.scrollHeight;
}

// Send message to backend
async function sendMessage(customText = null, forceAppend = false) {
  const text = String(customText ?? input.value).trim();
  if (!text) return;
  if (isSending) {
    console.warn("Send blocked: already sending");
    return;
  }
  isSending = true;

  if (customText == null || forceAppend) {
    appendMessage("user", text);
  }

  if (customText == null) input.value = "";

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: "harshit", message: text }),
    });

    if (!res.ok) throw new Error("Network response not OK");

    const data = await res.json();
    const botReply = data.reply || "Sorry, I didn't get that.";
    appendMessage("bot", botReply);
    speak(botReply);
  } catch (err) {
    console.error("Send error:", err);
    appendMessage("bot", "⚠️ Connection problem, please try again.");
  } finally {
    setTimeout(() => {
      isSending = false;
    }, 300);
  }
}

// Voice output
function speak(text) {
  if (!text) return;
  try {
    window.speechSynthesis.cancel();
  } catch (e) {
    // ignore if not available
  }
  const u = new SpeechSynthesisUtterance(text);
  u.lang = "en-IN";
  window.speechSynthesis.speak(u);
}

// ===== Voice Recognition =====
let recognition = null;
let autoSend = true;
let lastTranscript = "";
let lastTime = 0;

// Auto toggle button
let toggleBtn = document.getElementById("auto-toggle");
if (!toggleBtn) {
  toggleBtn = document.createElement("button");
  toggleBtn.id = "auto-toggle";
  toggleBtn.textContent = "🎙️ Auto Send ON";
  toggleBtn.className = "toggle-btn";
  const chatInputEl = document.querySelector(".chat-input") || document.body;
  chatInputEl.appendChild(toggleBtn);
}

toggleBtn.addEventListener("click", () => {
  autoSend = !autoSend;
  toggleBtn.textContent = autoSend ? "🎙️ Auto Send ON" : "🎙️ Manual Mode";
  toggleBtn.classList.toggle("off", !autoSend);
});

const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition || null;

async function ensureMicPermission() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    console.warn("getUserMedia not supported");
    return false;
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    stream.getTracks().forEach((t) => t.stop());
    return true;
  } catch (err) {
    console.error("Microphone permission denied:", err);
    alert("Please allow microphone access in your browser settings to use voice input.");
    return false;
  }
}

async function createRecognitionInstance() {
  if (!SpeechRec) {
    console.error("SpeechRecognition API not available");
    return null;
  }
  
  const ok = await ensureMicPermission();
  if (!ok) {
    console.error("Microphone permission not granted");
    return null;
  }

  try {
    const r = new SpeechRec();
    r.lang = "en-IN";
    r.interimResults = false;
    r.continuous = false;
    r.maxAlternatives = 1;

    r.onstart = () => {
      console.log("Speech recognition started");
      micBtn.textContent = "🎙️";
      micBtn.classList.add("listening");
      // Show visual feedback
      micBtn.style.backgroundColor = "#ff4444";
    };

    r.onend = () => {
      console.log("Speech recognition ended");
      micBtn.textContent = "🎤";
      micBtn.classList.remove("listening");
      micBtn.style.backgroundColor = "";
    };

    r.onresult = (e) => {
      try {
        const transcript = String(e.results[0][0].transcript || "").trim();
        console.log("Recognized:", transcript);
        if (!transcript) return;

        const now = Date.now();
        if (transcript.toLowerCase() === lastTranscript.toLowerCase() && now - lastTime < 2000) return;
        lastTranscript = transcript;
        lastTime = now;

        if (autoSend) {
          setTimeout(() => sendMessage(transcript, true), 250);
        } else {
          input.value = transcript;
        }
      } catch (err) {
        console.error("Recognition result error:", err);
      }
    };

    r.onerror = (err) => {
      console.error("Speech recognition error:", err);
      micBtn.style.backgroundColor = "";
      if (err?.error === "not-allowed") {
        alert("❌ Microphone access denied! Please enable it in browser settings.");
      } else if (err?.error === "no-speech") {
        console.warn("⚠️ No speech detected - Please speak louder or closer to mic");
        // Don't show alert for no-speech, just log it
      } else if (err?.error === "aborted") {
        console.log("Speech recognition aborted");
      } else {
        console.error(`Speech recognition error: ${err?.error || "Unknown error"}`);
      }
      micBtn.textContent = "🎤";
      micBtn.classList.remove("listening");
    };

    return r;
  } catch (err) {
    console.error("Error creating recognition instance:", err);
    return null;
  }
}

if (!SpeechRec) {
  console.warn("Speech Recognition not supported in this browser");
  micBtn.addEventListener("click", () => {
    alert("❌ Speech recognition not supported in this browser.\n\nPlease use:\n• Google Chrome\n• Microsoft Edge\n• Safari (iOS)\n\nOr simply type your message!");
  });
} else {
  micBtn.addEventListener("click", async () => {
    console.log("Mic button clicked");
    try {
      if (!recognition) {
        console.log("Creating recognition instance...");
        recognition = await createRecognitionInstance();
        if (!recognition) {
          alert("❌ Cannot access microphone. Please:\n1. Allow microphone permission\n2. Use HTTPS (not HTTP)\n3. Check browser settings");
          return;
        }
      }
      try {
        console.log("Starting recognition...");
        recognition.start();
      } catch (e) {
        console.warn("Recognition start error (may already be running):", e);
      }
    } catch (err) {
      console.error("Mic init error:", err);
      alert("❌ Speech recognition failed. Please reload the page and try again.");
    }
  });
}

// ===== CHAT TOGGLE FUNCTIONALITY =====
chatToggle.addEventListener("click", () => {
  chatContainer.classList.toggle("open");
  chatToggle.classList.toggle("active");
});

minimizeBtn.addEventListener("click", () => {
  chatContainer.classList.remove("open");
  chatToggle.classList.remove("active");
});

resetBtn.addEventListener("click", () => {
  messages.innerHTML = "";
  appendMessage("bot", "Hi there! 👋 I'm DineBot, your food ordering assistant. How can I help you today?");
});

// UI event listeners
btn.addEventListener("click", () => sendMessage());
input.addEventListener("keypress", (e) => {
  if (e.key === "Enter") sendMessage();
});

// Show welcome message on load
window.addEventListener("DOMContentLoaded", () => {
  appendMessage("bot", "Hi there! 👋 I'm DineBot, your food ordering assistant. How can I help you today?");
});