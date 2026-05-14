/* GesturePlay — Frontend Logic (5-gesture version) */

let isActive = false;
let pollTimer = null;
let lastLogTimestamp = 0;
let availableActions = {};

const ICONS = {
    fist:      "✊",
    index_up:  "☝️",
    peace:     "✌️",
    three_up:  "🤟",
    open_palm: "✋",
};

const LABELS = {
    fist:      "Fist",
    index_up:  "One Finger",
    peace:     "Two Fingers",
    three_up:  "Three Fingers",
    open_palm: "Open Palm",
};

// Finger-count to dot ID
const COUNT_DOT = { 0: "fd-0", 1: "fd-1", 2: "fd-2", 3: "fd-3", 4: "fd-4" };

// ── Init ───────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", loadConfig);

// ── Toggle Detection ────────────────────────────────────────

async function toggleDetection() {
    const btn = document.getElementById("btn-toggle");
    btn.disabled = true;

    try {
        const res  = await fetch("/api/toggle", { method: "POST" });
        const data = await res.json();
        isActive   = data.active;

        const pill    = document.getElementById("status-pill");
        const txt     = document.getElementById("status-text");
        const feed    = document.getElementById("camera-feed");
        const holder  = document.getElementById("cam-placeholder");

        if (isActive) {
            btn.textContent = "Stop Detection";
            btn.classList.add("active");
            pill.classList.add("active");
            txt.textContent = "Live";

            feed.src = "/video_feed?" + Date.now();
            feed.classList.remove("hidden");
            holder.classList.add("hidden");

            pollTimer = setInterval(pollStatus, 400);
            toast("Detection started — switch to your media player", "ok");
        } else {
            btn.textContent = "Start Detection";
            btn.classList.remove("active");
            pill.classList.remove("active");
            txt.textContent = "Offline";

            feed.src = "";
            feed.classList.add("hidden");
            holder.classList.remove("hidden");

            clearInterval(pollTimer);
            resetReadout();
            document.getElementById("fps-display").textContent = "-- FPS";
            document.getElementById("fps-display").classList.remove("live");
            toast("Detection stopped", "ok");
        }
    } catch (e) {
        toast("Error: " + e.message, "err");
    }

    btn.disabled = false;
}

// ── Poll Status ─────────────────────────────────────────────

async function pollStatus() {
    try {
        const res  = await fetch("/api/status");
        const data = await res.json();

        // FPS
        const fpsEl = document.getElementById("fps-display");
        fpsEl.textContent = (data.fps || 0) + " FPS";
        fpsEl.classList.toggle("live", !!data.fps);

        // Gesture readout
        updateReadout(data.gesture, data.finger_count);

        // Log — compare newest entry timestamp, not count
        if (data.recent_actions && data.recent_actions.length > 0) {
            const newestTime = data.recent_actions[0].time || 0;
            if (newestTime !== lastLogTimestamp) {
                renderLog(data.recent_actions);
                lastLogTimestamp = newestTime;
            }
        } else if (lastLogTimestamp !== 0) {
            renderLog([]);
            lastLogTimestamp = 0;
        }
    } catch (_) { /* silent fail */ }
}

// ── Readout ─────────────────────────────────────────────────

function updateReadout(gesture, count) {
    const emoji   = document.getElementById("readout-emoji");
    const label   = document.getElementById("readout-gesture");
    const action  = document.getElementById("readout-action");

    // Finger dots
    Object.entries(COUNT_DOT).forEach(([c, id]) => {
        document.getElementById(id)?.classList.toggle("active", parseInt(c) === count && gesture !== null);
    });

    if (gesture) {
        const newEmoji = ICONS[gesture] || "🤚";
        if (emoji.textContent !== newEmoji) {
            emoji.textContent = newEmoji;
            emoji.classList.remove("pop");
            void emoji.offsetWidth; // reflow
            emoji.classList.add("pop");
        }
        label.textContent  = LABELS[gesture] || gesture;
        action.textContent = "Gesture detected";
    } else {
        emoji.textContent  = "—";
        label.textContent  = "No hand detected";
        action.textContent = count > 0 ? "Unrecognized gesture" : "Show your hand to the camera";
        Object.values(COUNT_DOT).forEach(id => document.getElementById(id)?.classList.remove("active"));
    }
}

function resetReadout() {
    document.getElementById("readout-emoji").textContent  = "—";
    document.getElementById("readout-gesture").textContent = "No hand detected";
    document.getElementById("readout-action").textContent  = "Waiting...";
    Object.values(COUNT_DOT).forEach(id => document.getElementById(id)?.classList.remove("active"));
}

// ── Log ─────────────────────────────────────────────────────

function renderLog(actions) {
    const body = document.getElementById("log-body");
    if (!actions.length) {
        body.innerHTML = '<div class="log-empty">No actions yet</div>';
        return;
    }
    body.innerHTML = actions.map(a => `
        <div class="log-row">
            <span class="log-icon">${ICONS[a.gesture] || "◈"}</span>
            <span class="log-desc">${a.description || a.action}</span>
            <span class="log-from">${LABELS[a.gesture] || a.gesture}</span>
            <span class="log-time">${a.timestamp || ""}</span>
        </div>
    `).join("");
}

async function clearLog() {
    document.getElementById("log-body").innerHTML = '<div class="log-empty">No actions yet</div>';
    lastLogTimestamp = 0;
    try {
        await fetch("/api/clear_log", { method: "POST" });
    } catch (_) { /* silent fail */ }
}

// ── Config ──────────────────────────────────────────────────

async function loadConfig() {
    try {
        const res    = await fetch("/api/config");
        const config = await res.json();
        availableActions = config.available_actions || {};
        renderGestureTable(config.gestures || {});
    } catch (e) {
        console.error("Config load failed:", e);
    }
}

function renderGestureTable(gestures) {
    const table = document.getElementById("gesture-table");
    table.innerHTML = Object.entries(gestures).map(([name, info]) => {
        const opts = Object.entries(availableActions).map(([actKey, actInfo]) =>
            `<option value="${actKey}" ${actKey === info.action ? "selected" : ""}>${actInfo.label}</option>`
        ).join("");

        return `
            <div class="g-row">
                <span class="g-emoji">${info.emoji || ICONS[name] || "🤚"}</span>
                <div class="g-info">
                    <div class="g-name">${info.label}</div>
                    <div class="g-fingers">${info.fingers}</div>
                </div>
                <select class="g-select" onchange="saveMapping('${name}', this.value)">${opts}</select>
            </div>
        `;
    }).join("");
}

async function saveMapping(gesture, action) {
    try {
        const res  = await fetch("/api/config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ gesture, action }),
        });
        const data = await res.json();
        if (data.success) {
            toast(`${LABELS[gesture] || gesture} → ${action}`, "ok");
            loadConfig();
        } else {
            toast("Failed: " + (data.error || "unknown error"), "err");
        }
    } catch (e) {
        toast("Error: " + e.message, "err");
    }
}

// ── Toast ────────────────────────────────────────────────────

function toast(msg, type = "ok") {
    const root = document.getElementById("toast-root");
    const el   = document.createElement("div");
    el.className = `toast ${type}`;
    el.textContent = msg;
    root.appendChild(el);
    setTimeout(() => {
        el.style.opacity = "0";
        el.style.transition = "opacity 0.3s";
        setTimeout(() => el.remove(), 300);
    }, 2800);
}
