/* ═══════════════════════════════════════════════════════
   ADAN v3.0 — chat.js (multi-área)
   ═══════════════════════════════════════════════════════ */

/* ─── Estado ─────────────────────────────────────────── */
const state = {
    area: "general",
    config: {},
    mensajeCount: 0,
    pendingTopic: null,
    isLoading: false,
};

/* ─── DOM ────────────────────────────────────────────── */
const $ = id => document.getElementById(id);

const chatMessages     = $("chatMessages");
const chatInput        = $("chatInput");
const sendBtn          = $("sendBtn");
const typingIndicator  = $("typingIndicator");
const sidebar          = document.querySelector(".sidebar");
const areaSelector     = $("areaSelector");
const statEntradas     = $("statEntradas");
const statSinonimos    = $("statSinonimos");
const statMensajes     = $("statMensajes");
const logoIcon         = $("logoIcon");
const logoLetter       = $("logoLetter");
const nombreAsistente  = $("nombreAsistente");
const descAsistente    = $("descAsistente");
const headerNombre     = $("headerNombre");
const headerDesc       = $("headerDesc");
const headerAreaBadge  = $("headerAreaBadge");

// Modals
const modalAprender  = $("modalAprender");
const modalNoSabe    = $("modalNoSabe");
const noSabeTexto    = $("noSabeTexto");


/* ─── Inicialización ─────────────────────────────────── */
document.addEventListener("DOMContentLoaded", async () => {
    // Leer área desde URL
    const params = new URLSearchParams(window.location.search);
    const areaUrl = params.get("area") || "general";

    await cargarAreas();
    await cambiarArea(areaUrl);
    mostrarBienvenida();
    chatInput.focus();
});


/* ─── Áreas ──────────────────────────────────────────── */
async function cargarAreas() {
    try {
        const res = await fetch("/api/areas");
        const areas = await res.json();
        renderAreas(areas);
    } catch {
        areaSelector.innerHTML = '<div class="area-loading">Error cargando áreas</div>';
    }
}

function renderAreas(areas) {
    areaSelector.innerHTML = "";
    areas.forEach(a => {
        const btn = document.createElement("button");
        btn.className = "area-btn";
        btn.dataset.area = a.id;
        btn.style.setProperty("--area-color", a.color_primario);
        btn.innerHTML = `
            <span class="area-btn-emoji">${a.avatar}</span>
            <div class="area-btn-text">
                <span class="area-btn-nombre">${a.nombre}</span>
                <span class="area-btn-desc">${a.descripcion}</span>
            </div>`;
        btn.addEventListener("click", () => cambiarArea(a.id));
        areaSelector.appendChild(btn);
    });
}

async function cambiarArea(areaId) {
    state.area = areaId;

    // Actualizar botones
    document.querySelectorAll(".area-btn").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.area === areaId);
    });

    // Cargar config del área
    try {
        const res = await fetch(`/api/config/${areaId}`);
        state.config = await res.json();
        aplicarTemaArea(state.config);
    } catch {
        state.config = {};
    }

    await cargarStats();

    // Actualizar URL sin recargar
    const url = new URL(window.location);
    url.searchParams.set("area", areaId);
    window.history.replaceState({}, "", url);
}

function aplicarTemaArea(config) {
    const color = config.color_primario || "#7c6af7";
    const nombre = config.nombre || "ADAN";
    const desc = config.descripcion || "Asistente Virtual";
    const avatar = config.avatar || "🤖";

    // CSS variables
    document.documentElement.style.setProperty("--color-primary", color);
    document.documentElement.style.setProperty("--color-primary-2", lightenColor(color, 20));
    document.documentElement.style.setProperty("--color-primary-glow", hexToRgba(color, 0.3));

    // Textos
    nombreAsistente.textContent = nombre;
    descAsistente.textContent = desc;
    headerNombre.textContent = nombre;
    headerDesc.textContent = desc;
    logoLetter.textContent = nombre.charAt(0).toUpperCase();

    // Badge del área
    headerAreaBadge.textContent = `${avatar} ${nombre}`;
    headerAreaBadge.style.color = color;
    headerAreaBadge.style.borderColor = color;
    headerAreaBadge.style.backgroundColor = hexToRgba(color, 0.1);
    headerAreaBadge.classList.add("visible");

    // Título de la página
    document.title = `${nombre} — Asistente Virtual`;
}


/* ─── Stats ──────────────────────────────────────────── */
async function cargarStats() {
    try {
        const res = await fetch(`/api/stats/${state.area}`);
        const data = await res.json();
        statEntradas.textContent = data.total_entradas ?? "—";
        statSinonimos.textContent = data.total_sinonimos ?? "—";
    } catch {
        statEntradas.textContent = statSinonimos.textContent = "—";
    }
}


/* ─── Mensaje de bienvenida ──────────────────────────── */
function mostrarBienvenida() {
    chatMessages.innerHTML = "";
    const nombre = state.config.nombre || "ADAN";
    const desc = state.config.descripcion || "tu asistente virtual";
    renderMensajeAdan(
        `¡Hola! 👋 Soy **${nombre}**, ${desc.toLowerCase()}.\n¿En qué puedo ayudarte hoy?`,
        "local"
    );
}


/* ─── Render mensajes ────────────────────────────────── */
function timeNow() {
    return new Date().toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" });
}

const FUENTE_CONFIG = {
    "local":        { clase: "local",       label: "LOCAL" },
    "Wikipedia":    { clase: "wiki",        label: "WIKI" },
    "DuckDuckGo":   { clase: "ddg",         label: "DDG" },
    "aprendido":    { clase: "aprendido",   label: "NUEVO" },
    "restriccion":  { clase: "restriccion", label: "ÁREA" },
};

function renderMensajeAdan(texto, fuente) {
    const div = document.createElement("div");
    div.className = "message adan-message";

    const fc = FUENTE_CONFIG[fuente] || {};
    const badge = fc.clase ? `<span class="source-badge ${fc.clase}">${fc.label}</span>` : "";
    const esRestriccion = fuente === "restriccion";

    // Parsear **bold** básico
    const html = escapeHtml(texto)
        .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
        .split("\n").filter(l => l.trim())
        .map(l => `<p>${l}</p>`).join("");

    const initial = (state.config.nombre || "ADAN").charAt(0).toUpperCase();
    div.innerHTML = `
        <div class="message-avatar">${initial}</div>
        <div class="message-content">
            <div class="message-bubble ${esRestriccion ? 'restriccion-bubble' : ''}">${html}</div>
            <div class="message-meta">
                <span class="message-time">${timeNow()}</span>
                ${badge}
            </div>
        </div>`;
    chatMessages.appendChild(div);
    scrollToBottom();
}

function renderMensajeUsuario(texto) {
    const div = document.createElement("div");
    div.className = "message user-message";
    div.innerHTML = `
        <div class="message-content">
            <div class="message-bubble">${escapeHtml(texto)}</div>
            <div class="message-meta"><span class="message-time">${timeNow()}</span></div>
        </div>
        <div class="message-avatar">Tú</div>`;
    chatMessages.appendChild(div);
    scrollToBottom();
}

function renderBuscando() {
    const div = document.createElement("div");
    div.className = "message adan-message searching-msg";
    div.id = "searchingMsg";
    const initial = (state.config.nombre || "A").charAt(0).toUpperCase();
    div.innerHTML = `
        <div class="message-avatar">${initial}</div>
        <div class="message-content">
            <div class="message-bubble">
                <div class="searching-spinner"></div>
                Buscando información...
            </div>
        </div>`;
    chatMessages.appendChild(div);
    scrollToBottom();
}

function removeBuscando() { const el = $("searchingMsg"); if (el) el.remove(); }
function scrollToBottom() { chatMessages.scrollTo({ top: chatMessages.scrollHeight, behavior: "smooth" }); }
function escapeHtml(str) {
    return String(str).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}


/* ─── Envío de mensaje ───────────────────────────────── */
async function enviarMensaje() {
    const texto = chatInput.value.trim();
    if (!texto || state.isLoading) return;

    state.isLoading = true;
    state.mensajeCount++;
    statMensajes.textContent = state.mensajeCount;

    chatInput.value = "";
    chatInput.style.height = "auto";
    renderMensajeUsuario(texto);

    typingIndicator.classList.add("visible");
    sendBtn.disabled = true;

    await new Promise(r => setTimeout(r, 350));
    renderBuscando();

    try {
        const res = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ mensaje: texto, area: state.area }),
        });
        const data = await res.json();
        removeBuscando();
        typingIndicator.classList.remove("visible");

        if (!res.ok) {
            renderMensajeAdan("Ocurrió un error. Intenta de nuevo.", "");
        } else if (data.encontrado && data.respuesta) {
            renderMensajeAdan(data.respuesta, data.fuente);
        } else {
            const puedeAprender = state.config.permitir_aprendizaje !== false;
            if (puedeAprender) {
                state.pendingTopic = texto;
                noSabeTexto.textContent = `No tengo información sobre "${texto}". ¿Quieres enseñarme?`;
                showModal(modalNoSabe);
            } else {
                const msg = state.config.mensaje_fuera_area || "No tengo información sobre ese tema.";
                renderMensajeAdan(msg, "restriccion");
            }
        }
    } catch {
        removeBuscando();
        typingIndicator.classList.remove("visible");
        renderMensajeAdan("No se pudo conectar con el servidor. ¿Está activo?", "");
    } finally {
        state.isLoading = false;
        sendBtn.disabled = false;
        chatInput.focus();
    }
}

/* ─── Input events ───────────────────────────────────── */
chatInput.addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); enviarMensaje(); }
});
chatInput.addEventListener("input", () => {
    chatInput.style.height = "auto";
    chatInput.style.height = Math.min(chatInput.scrollHeight, 160) + "px";
});
sendBtn.addEventListener("click", enviarMensaje);

$("sidebarToggle").addEventListener("click", () => sidebar.classList.toggle("collapsed"));


/* ─── Modals ─────────────────────────────────────────── */
function showModal(m) { m.classList.add("active"); }
function hideModal(m) { m.classList.remove("active"); }

document.querySelectorAll(".modal-overlay").forEach(o => {
    o.addEventListener("click", e => { if (e.target === o) hideModal(o); });
});

// Enseñar
$("btnEnsenar").addEventListener("click", () => {
    limpiarForm(); showModal(modalAprender); $("aprClave").focus();
});
$("modalClose").addEventListener("click", () => hideModal(modalAprender));
$("btnCancelarApr").addEventListener("click", () => hideModal(modalAprender));

$("btnGuardarApr").addEventListener("click", async () => {
    const clave    = $("aprClave").value.trim();
    const explica  = $("aprExplica").value.trim();
    const respuesta= $("aprRespuesta").value.trim();
    if (!clave || !explica || !respuesta) {
        [$("aprClave"), $("aprExplica"), $("aprRespuesta")].forEach(f => {
            if (!f.value.trim()) { f.style.borderColor = "var(--color-accent-rose)"; setTimeout(() => f.style.borderColor="",1500); }
        });
        return;
    }
    const btn = $("btnGuardarApr");
    btn.disabled = true; btn.textContent = "Guardando...";
    try {
        const res = await fetch("/api/aprender", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                clave, explica, respuesta,
                otra_pregunta: $("aprOtra").value.trim(),
                sinonimos: $("aprSinonimo").value.trim(),
                area: state.area,
            }),
        });
        const data = await res.json();
        hideModal(modalAprender);
        renderMensajeAdan(data.mensaje || "¡Información guardada!", "aprendido");
        cargarStats();
    } catch {
        renderMensajeAdan("No se pudo guardar. Intenta de nuevo.", "");
        hideModal(modalAprender);
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/></svg> Guardar`;
    }
});

// No sabe
$("btnNoSabeNo").addEventListener("click", () => { hideModal(modalNoSabe); state.pendingTopic = null; });
$("btnNoSabeSi").addEventListener("click", () => {
    hideModal(modalNoSabe);
    limpiarForm();
    if (state.pendingTopic) $("aprClave").value = state.pendingTopic;
    showModal(modalAprender);
    $("aprExplica").focus();
});

// Nueva sesión
$("btnNuevaSesion").addEventListener("click", async () => {
    await fetch("/api/historial/limpiar", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ area: state.area }) });
    state.mensajeCount = 0;
    statMensajes.textContent = 0;
    mostrarBienvenida();
});

function limpiarForm() {
    [$("aprClave"), $("aprExplica"), $("aprRespuesta"), $("aprOtra"), $("aprSinonimo")].forEach(f => f.value = "");
}


/* ─── Utilidades de color ────────────────────────────── */
function hexToRgba(hex, alpha) {
    const r = parseInt(hex.slice(1,3),16);
    const g = parseInt(hex.slice(3,5),16);
    const b = parseInt(hex.slice(5,7),16);
    return `rgba(${r},${g},${b},${alpha})`;
}

function lightenColor(hex, pct) {
    const r = Math.min(255, parseInt(hex.slice(1,3),16) + Math.round(255 * pct/100));
    const g = Math.min(255, parseInt(hex.slice(3,5),16) + Math.round(255 * pct/100));
    const b = Math.min(255, parseInt(hex.slice(5,7),16) + Math.round(255 * pct/100));
    return `#${r.toString(16).padStart(2,'0')}${g.toString(16).padStart(2,'0')}${b.toString(16).padStart(2,'0')}`;
}
