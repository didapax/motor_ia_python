/* ═══════════════════════════════════════════════════════
   ADAN — chat.js  (lógica del chat)
   ═══════════════════════════════════════════════════════ */

/* ─── Estado ─────────────────────────────────────────── */
const state = {
    mensajeCount: 0,
    pendingTopic: null,      // último tema que ADAN no supo
    isLoading: false,
};

/* ─── Referencias DOM ────────────────────────────────── */
const $ = (id) => document.getElementById(id);

const chatMessages     = $("chatMessages");
const chatInput        = $("chatInput");
const sendBtn          = $("sendBtn");
const typingIndicator  = $("typingIndicator");
const sidebarToggle    = $("sidebarToggle");
const sidebar          = document.querySelector(".sidebar");
const statEntradas     = $("statEntradas");
const statSinonimos    = $("statSinonimos");
const statMensajes     = $("statMensajes");

// Modals
const modalAprender    = $("modalAprender");
const modalNoSabe      = $("modalNoSabe");
const modalClose       = $("modalClose");
const btnCancelar      = $("btnCancelar");
const btnGuardar       = $("btnGuardar");
const btnNoSabeNo      = $("btnNoSabeNo");
const btnNoSabeSi      = $("btnNoSabeSi");
const btnEnsenar       = $("btnEnsenar");
const btnLimpiarHistorial = $("btnLimpiarHistorial");
const noSabeTexto      = $("noSabeTexto");

// Campos del modal
const aprenderClave        = $("aprenderClave");
const aprenderExplica      = $("aprenderExplica");
const aprenderRespuesta    = $("aprenderRespuesta");
const aprenderOtraPregunta = $("aprenderOtraPregunta");
const aprenderSinonimo     = $("aprenderSinonimo");


/* ─── Helpers de tiempo ──────────────────────────────── */
function timeNow() {
    return new Date().toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" });
}


/* ─── Inicialización ─────────────────────────────────── */
document.addEventListener("DOMContentLoaded", () => {
    $("welcomeTime").textContent = timeNow();
    loadStats();
    chatInput.focus();
});


/* ─── Stats ──────────────────────────────────────────── */
async function loadStats() {
    try {
        const res = await fetch("/api/stats");
        if (!res.ok) return;
        const data = await res.json();
        statEntradas.textContent  = data.total_entradas  ?? "—";
        statSinonimos.textContent = data.total_sinonimos ?? "—";
    } catch (_) {
        statEntradas.textContent = statSinonimos.textContent = "—";
    }
}


/* ─── Render de mensajes ─────────────────────────────── */
function badgeClass(fuente) {
    const map = {
        "local":      "local",
        "Wikipedia":  "wiki",
        "DuckDuckGo": "ddg",
        "aprendido":  "aprendido",
    };
    return map[fuente] || "";
}

function badgeLabel(fuente) {
    const map = {
        "local":      "LOCAL",
        "Wikipedia":  "WIKI",
        "DuckDuckGo": "DDG",
        "aprendido":  "NUEVO",
    };
    return map[fuente] || fuente;
}

function renderMensajeAdan(texto, fuente) {
    const div = document.createElement("div");
    div.className = "message adan-message";

    const bClass = badgeClass(fuente);
    const bLabel = badgeLabel(fuente);
    const badgeHtml = bClass
        ? `<span class="source-badge ${bClass}">${bLabel}</span>`
        : "";

    // Convertir saltos de línea en párrafos
    const parrafos = texto.split("\n").filter(l => l.trim()).map(
        l => `<p>${l.trim()}</p>`
    ).join("");

    div.innerHTML = `
        <div class="message-avatar">A</div>
        <div class="message-content">
            <div class="message-bubble">${parrafos}</div>
            <div class="message-meta">
                <span class="message-time">${timeNow()}</span>
                ${badgeHtml}
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
            <div class="message-meta">
                <span class="message-time">${timeNow()}</span>
            </div>
        </div>
        <div class="message-avatar">Tú</div>`;
    chatMessages.appendChild(div);
    scrollToBottom();
}

function renderBuscando() {
    const div = document.createElement("div");
    div.className = "message adan-message searching-msg";
    div.id = "searchingMsg";
    div.innerHTML = `
        <div class="message-avatar">A</div>
        <div class="message-content">
            <div class="message-bubble">
                <div class="searching-spinner"></div>
                Buscando información...
            </div>
        </div>`;
    chatMessages.appendChild(div);
    scrollToBottom();
    return div;
}

function renderError(texto) {
    const div = document.createElement("div");
    div.className = "message adan-message";
    div.innerHTML = `
        <div class="message-avatar">A</div>
        <div class="message-content">
            <div class="message-bubble error-bubble">${escapeHtml(texto)}</div>
            <div class="message-meta">
                <span class="message-time">${timeNow()}</span>
            </div>
        </div>`;
    chatMessages.appendChild(div);
    scrollToBottom();
}

function escapeHtml(str) {
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

function scrollToBottom() {
    chatMessages.scrollTo({ top: chatMessages.scrollHeight, behavior: "smooth" });
}

function removeBuscando() {
    const el = $("searchingMsg");
    if (el) el.remove();
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

    // Mostrar typing + buscando
    typingIndicator.classList.add("visible");
    sendBtn.disabled = true;

    // Pequeño delay para que se vea el typing
    await new Promise(r => setTimeout(r, 400));
    const buscandoEl = renderBuscando();

    try {
        const res = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ mensaje: texto }),
        });

        const data = await res.json();
        removeBuscando();
        typingIndicator.classList.remove("visible");

        if (!res.ok) {
            renderError("Ocurrió un error al procesar tu mensaje. Intenta de nuevo.");
        } else if (data.encontrado && data.respuesta) {
            renderMensajeAdan(data.respuesta, data.fuente);

            // Si es despedida, desactivar input brevemente
            if (data.intencion === "despedida") {
                chatInput.placeholder = "ADAN espera tu regreso... ✨";
            }
        } else {
            // ADAN no supo responder
            state.pendingTopic = texto;
            noSabeTexto.textContent =
                `No tengo información sobre "${texto}". ¿Quieres enseñarme?`;
            showModal(modalNoSabe);
        }
    } catch (err) {
        removeBuscando();
        typingIndicator.classList.remove("visible");
        renderError("No se pudo conectar con ADAN. ¿Está el servidor activo?");
        console.error(err);
    } finally {
        state.isLoading = false;
        sendBtn.disabled = false;
        chatInput.focus();
    }
}


/* ─── Input listeners ────────────────────────────────── */
chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        enviarMensaje();
    }
});

chatInput.addEventListener("input", () => {
    chatInput.style.height = "auto";
    chatInput.style.height = Math.min(chatInput.scrollHeight, 160) + "px";
});

sendBtn.addEventListener("click", enviarMensaje);


/* ─── Sidebar toggle ─────────────────────────────────── */
sidebarToggle.addEventListener("click", () => {
    sidebar.classList.toggle("collapsed");
});


/* ─── Modal helpers ──────────────────────────────────── */
function showModal(modal) {
    modal.classList.add("active");
    document.body.style.overflow = "hidden";
}

function hideModal(modal) {
    modal.classList.remove("active");
    document.body.style.overflow = "";
}

// Cerrar modal al hacer clic fuera
document.querySelectorAll(".modal-overlay").forEach(overlay => {
    overlay.addEventListener("click", (e) => {
        if (e.target === overlay) hideModal(overlay);
    });
});


/* ─── Modal: enseñar a ADAN ──────────────────────────── */
btnEnsenar.addEventListener("click", () => {
    limpiarFormModal();
    showModal(modalAprender);
    aprenderClave.focus();
});

modalClose.addEventListener("click", () => hideModal(modalAprender));
btnCancelar.addEventListener("click", () => hideModal(modalAprender));

btnGuardar.addEventListener("click", async () => {
    const clave    = aprenderClave.value.trim();
    const explica  = aprenderExplica.value.trim();
    const respuesta= aprenderRespuesta.value.trim();

    if (!clave || !explica || !respuesta) {
        [aprenderClave, aprenderExplica, aprenderRespuesta].forEach(f => {
            if (!f.value.trim()) {
                f.style.borderColor = "var(--color-accent-rose)";
                setTimeout(() => f.style.borderColor = "", 1500);
            }
        });
        return;
    }

    btnGuardar.disabled = true;
    btnGuardar.textContent = "Guardando...";

    try {
        const res = await fetch("/api/aprender", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                clave,
                explica,
                respuesta,
                otra_pregunta: aprenderOtraPregunta.value.trim(),
                sinonimo: aprenderSinonimo.value.trim(),
            }),
        });

        const data = await res.json();
        hideModal(modalAprender);
        renderMensajeAdan(
            data.mensaje || "¡Información guardada! Gracias por enseñarme.",
            "aprendido"
        );
        loadStats(); // Actualizar contador
    } catch (_) {
        renderError("No se pudo guardar la información. Intenta de nuevo.");
        hideModal(modalAprender);
    } finally {
        btnGuardar.disabled = false;
        btnGuardar.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
                <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
                <polyline points="17 21 17 13 7 13 7 21"/>
            </svg>
            Guardar`;
    }
});

function limpiarFormModal() {
    [aprenderClave, aprenderExplica, aprenderRespuesta, aprenderOtraPregunta, aprenderSinonimo]
        .forEach(f => f.value = "");
}


/* ─── Modal: no sabe ─────────────────────────────────── */
btnNoSabeNo.addEventListener("click", () => {
    hideModal(modalNoSabe);
    renderMensajeAdan(
        "Está bien. Si en algún momento quieres enseñarme, usa el botón '✏️ Enseñar a ADAN' en el panel lateral.",
        ""
    );
    state.pendingTopic = null;
});

btnNoSabeSi.addEventListener("click", () => {
    hideModal(modalNoSabe);
    limpiarFormModal();
    if (state.pendingTopic) {
        aprenderClave.value = state.pendingTopic;
    }
    showModal(modalAprender);
    aprenderExplica.focus();
});


/* ─── Limpiar historial ──────────────────────────────── */
btnLimpiarHistorial.addEventListener("click", async () => {
    try {
        await fetch("/api/limpiar", { method: "POST" });
    } catch (_) {}

    // Limpiar visualmente
    chatMessages.innerHTML = "";
    state.mensajeCount = 0;
    statMensajes.textContent = 0;

    // Mensaje de bienvenida de nuevo
    renderMensajeAdan(
        "¡Sesión reiniciada! Soy ADAN, tu asistente virtual. ¿En qué puedo ayudarte?",
        "local"
    );
});
