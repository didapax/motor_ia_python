/* ═══════════════════════════════════════════════════════
   ADAN Admin — admin.js
   ═══════════════════════════════════════════════════════ */

/* ─── Estado ─────────────────────────────────────────── */
const admin = {
    area: "",
    config: {},
    entradas: [],
    tabActiva: "entradas",
};

const $ = id => document.getElementById(id);

/* ─── Toast ──────────────────────────────────────────── */
let toastTimer;
function toast(msg, tipo = "info") {
    const t = $("toast");
    t.textContent = msg;
    t.className = `toast ${tipo} show`;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove("show"), 3000);
}

/* ─── Inicialización ─────────────────────────────────── */
document.addEventListener("DOMContentLoaded", async () => {
    const params = new URLSearchParams(window.location.search);
    const areaParam = params.get("area") || "";
    await cargarAreasLogin(areaParam);

    // Enter en PIN
    $("loginPin").addEventListener("keydown", e => { if (e.key === "Enter") login(); });
    $("btnLogin").addEventListener("click", login);
});

async function cargarAreasLogin(defaultArea) {
    try {
        const res = await fetch("/api/areas");
        const areas = await res.json();
        const sel = $("loginArea");
        sel.innerHTML = areas.map(a =>
            `<option value="${a.id}" ${a.id === defaultArea ? "selected" : ""}>${a.avatar} ${a.nombre}</option>`
        ).join("");
    } catch {
        $("loginArea").innerHTML = '<option value="general">ADAN General</option>';
    }
}

/* ─── Login ──────────────────────────────────────────── */
async function login() {
    const area = $("loginArea").value;
    const pin  = $("loginPin").value.trim();
    const errEl = $("loginError");

    if (!pin) { errEl.textContent = "Ingresa el PIN"; errEl.style.display="block"; return; }

    $("btnLogin").disabled = true;
    $("btnLogin").textContent = "Verificando...";

    try {
        const res = await fetch("/api/admin/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ area, pin }),
        });
        const data = await res.json();
        if (data.ok) {
            admin.area = area;
            admin.config = data.config;
            errEl.style.display = "none";
            iniciarPanel();
        } else {
            errEl.textContent = "PIN incorrecto. Intenta de nuevo.";
            errEl.style.display = "block";
        }
    } catch {
        errEl.textContent = "Error de conexión.";
        errEl.style.display = "block";
    } finally {
        $("btnLogin").disabled = false;
        $("btnLogin").innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg> Ingresar`;
    }
}

/* ─── Panel ──────────────────────────────────────────── */
function iniciarPanel() {
    $("loginScreen").style.display = "none";
    $("adminPanel").style.display  = "flex";

    // Aplicar config
    $("adminNombre").textContent = admin.config.nombre || "ADAN Admin";
    $("adminAreaTag").textContent = admin.area;
    $("adminLogoLetter").textContent = (admin.config.nombre || "A").charAt(0);
    $("linkChat").href = `/?area=${admin.area}`;

    // Actualizar URL
    const url = new URL(window.location);
    url.searchParams.set("area", admin.area);
    window.history.replaceState({}, "", url);

    // Cargar pestaña inicial
    cargarTab("entradas");

    // Navegación
    document.querySelectorAll(".admin-nav-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".admin-nav-btn").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            cargarTab(btn.dataset.tab);
        });
    });

    $("btnCerrarSesion").addEventListener("click", () => { location.reload(); });
}

function cargarTab(tab) {
    admin.tabActiva = tab;
    document.querySelectorAll(".admin-tab").forEach(t => t.style.display = "none");
    $(`tab-${tab}`).style.display = "block";

    if (tab === "entradas") cargarEntradas();
    if (tab === "historial") cargarHistorial();
    if (tab === "config") cargarFormConfig();
}

/* ─── Entradas ───────────────────────────────────────── */
async function cargarEntradas() {
    try {
        const res = await fetch(`/api/admin/entradas/${admin.area}`);
        admin.entradas = await res.json();
        renderTabla(admin.entradas);
        cargarStatsEntradas();
    } catch {
        toast("Error al cargar entradas", "error");
    }
}

async function cargarStatsEntradas() {
    try {
        const res = await fetch(`/api/stats/${admin.area}`);
        const data = await res.json();
        $("statsEntradas").textContent = `${data.total_entradas} entradas · ${data.total_sinonimos} sinónimos`;
    } catch {}
}

function renderTabla(entradas) {
    const tbody = $("tablaEntradas");
    if (!entradas.length) {
        tbody.innerHTML = '<tr><td colspan="5" class="tabla-vacia">No hay entradas. ¡Agrega la primera!</td></tr>';
        return;
    }
    tbody.innerHTML = entradas.map(e => {
        const respuesta = (e.respuestas?.[0] || "").substring(0, 80);
        const sins = (e.sinonimos || []).map(s => `<span class="sin-tag">${s}</span>`).join(" ") || "—";
        return `<tr>
            <td><span class="clave-badge">${esc(e.clave)}</span></td>
            <td>${esc(respuesta)}${e.respuestas?.[0]?.length > 80 ? "..." : ""}</td>
            <td>${sins}</td>
            <td>${e.intencion || "—"}</td>
            <td>
                <button class="btn-icon" title="Editar" onclick="editarEntrada('${esc(e.clave)}')">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
                </button>
                <button class="btn-icon danger" title="Eliminar" onclick="eliminarEntrada('${esc(e.clave)}')">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>
                </button>
            </td>
        </tr>`;
    }).join("");
}

function esc(str) {
    return String(str || "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}

// Buscar
$("buscarEntrada").addEventListener("input", function() {
    const q = this.value.toLowerCase();
    const filtradas = admin.entradas.filter(e =>
        e.clave.toLowerCase().includes(q) ||
        (e.respuestas?.[0] || "").toLowerCase().includes(q) ||
        (e.sinonimos || []).some(s => s.toLowerCase().includes(q))
    );
    renderTabla(filtradas);
});

// Nueva entrada
$("btnNuevaEntrada").addEventListener("click", () => abrirModalEntrada(null));
$("modalEntradaClose").addEventListener("click", () => hideModal($("modalEntrada")));
$("btnCancelarEntrada").addEventListener("click", () => hideModal($("modalEntrada")));

function abrirModalEntrada(entrada) {
    $("modalEntradaTitulo").textContent = entrada ? "Editar entrada" : "Nueva entrada";
    $("entradaModoEdicion").value = entrada?.clave || "";
    $("entClave").value = entrada?.clave || "";
    $("entClave").disabled = !!entrada; // No editar clave en modo edición
    $("entExplica").value = entrada?.explica || "";
    $("entRespuesta").value = entrada?.respuestas?.[0] || "";
    $("entOtra").value = entrada?.otra_pregunta || "";
    $("entSinonimos").value = (entrada?.sinonimos || []).join("|");
    showModal($("modalEntrada"));
    $("entClave").focus();
}

function editarEntrada(clave) {
    const entrada = admin.entradas.find(e => e.clave === clave);
    if (entrada) abrirModalEntrada(entrada);
}

$("btnGuardarEntrada").addEventListener("click", async () => {
    const clave = $("entClave").value.trim();
    const explica = $("entExplica").value.trim();
    const respuesta = $("entRespuesta").value.trim();
    if (!clave || !explica || !respuesta) {
        toast("Completa los campos obligatorios (*)", "error"); return;
    }
    try {
        const res = await fetch(`/api/admin/entrada/${admin.area}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                clave, explica,
                respuestas: [respuesta],
                otra_pregunta: $("entOtra").value.trim(),
                sinonimos: $("entSinonimos").value.trim(),
            }),
        });
        const data = await res.json();
        if (data.ok) {
            hideModal($("modalEntrada"));
            toast("Entrada guardada correctamente", "success");
            cargarEntradas();
        } else {
            toast("Error al guardar", "error");
        }
    } catch { toast("Error de conexión", "error"); }
});

async function eliminarEntrada(clave) {
    if (!confirm(`¿Eliminar la entrada "${clave}"? Esta acción no se puede deshacer.`)) return;
    try {
        const res = await fetch(`/api/admin/entrada/${admin.area}/${encodeURIComponent(clave)}`, { method: "DELETE" });
        const data = await res.json();
        if (data.ok) {
            toast("Entrada eliminada", "info");
            cargarEntradas();
        } else {
            toast("No se encontró la entrada", "error");
        }
    } catch { toast("Error al eliminar", "error"); }
}

// Exportar
$("btnExportar").addEventListener("click", () => {
    window.location.href = `/api/admin/exportar/${admin.area}`;
});

// Importar CSV
$("fileImportar").addEventListener("change", async function() {
    if (!this.files[0]) return;
    const formData = new FormData();
    formData.append("archivo", this.files[0]);
    try {
        const res = await fetch(`/api/admin/importar/${admin.area}`, { method: "POST", body: formData });
        const data = await res.json();
        if (data.importadas !== undefined) {
            toast(`✅ ${data.importadas} entradas importadas${data.errores?.length ? ` · ${data.errores.length} errores` : ""}`, "success");
            cargarEntradas();
        } else {
            toast(data.error || "Error al importar", "error");
        }
    } catch { toast("Error al importar", "error"); }
    this.value = "";
});

/* ─── Historial ──────────────────────────────────────── */
async function cargarHistorial() {
    $("historialDetalle").style.display = "none";
    try {
        const res = await fetch(`/api/admin/historial/${admin.area}`);
        const historiales = await res.json();
        renderHistorial(historiales);
    } catch { toast("Error al cargar historial", "error"); }
}

function renderHistorial(historiales) {
    const grid = $("historialGrid");
    if (!historiales.length) {
        grid.innerHTML = '<p class="tabla-vacia">No hay conversaciones registradas aún.</p>';
        return;
    }
    grid.innerHTML = historiales.map(h => {
        const inicio = new Date(h.inicio).toLocaleString("es-ES", { dateStyle:"short", timeStyle:"short" });
        const shortId = h.session_id?.substring(0,8) || "—";
        return `<div class="historial-card" onclick="verHistorial('${h.session_id}', '${inicio}')">
            <div class="historial-card-msgs">${h.total_mensajes}</div>
            <div class="historial-card-title">Sesión ${shortId}...</div>
            <div class="historial-card-meta">
                <span>📅 ${inicio}</span>
                <span>💬 ${h.total_mensajes} mensajes</span>
            </div>
        </div>`;
    }).join("");
}

async function verHistorial(sessionId, titulo) {
    try {
        const res = await fetch(`/api/admin/historial/${admin.area}/${sessionId}`);
        const data = await res.json();
        $("historialDetalleTitle").textContent = `Conversación — ${titulo}`;
        $("historialMensajes").innerHTML = data.mensajes.map(m => {
            const hora = new Date(m.timestamp).toLocaleTimeString("es-ES", { hour:"2-digit", minute:"2-digit" });
            const fuente = m.fuente ? `[${m.fuente}]` : "";
            return `<div class="hist-msg ${m.rol}">
                <div>${esc(m.mensaje)}</div>
                <div class="hist-msg-meta">${m.rol === "adan" ? "ADAN" : "Usuario"} · ${hora} ${fuente}</div>
            </div>`;
        }).join("") || '<p class="tabla-vacia">Sin mensajes</p>';
        $("historialDetalle").style.display = "block";
        $("historialDetalle").scrollIntoView({ behavior: "smooth" });
    } catch { toast("Error al cargar conversación", "error"); }
}

$("btnRefreshHistorial").addEventListener("click", cargarHistorial);
$("btnCerrarDetalle").addEventListener("click", () => {
    $("historialDetalle").style.display = "none";
});

/* ─── Config ─────────────────────────────────────────── */
function cargarFormConfig() {
    const c = admin.config;
    $("cfgNombre").value = c.nombre || "";
    $("cfgDesc").value   = c.descripcion || "";
    $("cfgAvatar").value = c.avatar || "";
    $("cfgColor").value  = c.color_primario || "#7c6af7";
    $("cfgColorHex").value = c.color_primario || "#7c6af7";
    $("cfgTema").value   = c.tema_restriccion || "";
    $("cfgMsgFuera").value = c.mensaje_fuera_area || "";
    $("cfgBusquedaWeb").checked  = c.permitir_busqueda_web !== false;
    $("cfgAprendizaje").checked  = c.permitir_aprendizaje  !== false;
    $("cfgPinNuevo").value = "";

    // Sincronizar color picker ↔ hex
    $("cfgColor").addEventListener("input", function() { $("cfgColorHex").value = this.value; });
    $("cfgColorHex").addEventListener("input", function() {
        if (/^#[0-9a-f]{6}$/i.test(this.value)) $("cfgColor").value = this.value;
    });
}

$("btnGuardarConfig").addEventListener("click", async () => {
    const data = {
        nombre: $("cfgNombre").value.trim(),
        descripcion: $("cfgDesc").value.trim(),
        avatar: $("cfgAvatar").value.trim(),
        color_primario: $("cfgColorHex").value.trim() || $("cfgColor").value,
        tema_restriccion: $("cfgTema").value.trim(),
        mensaje_fuera_area: $("cfgMsgFuera").value.trim(),
        permitir_busqueda_web: $("cfgBusquedaWeb").checked,
        permitir_aprendizaje: $("cfgAprendizaje").checked,
    };
    const pinNuevo = $("cfgPinNuevo").value.trim();
    if (pinNuevo) data.pin_nuevo = pinNuevo;

    try {
        const res = await fetch(`/api/admin/config/${admin.area}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data),
        });
        const result = await res.json();
        if (result.ok) {
            admin.config = { ...admin.config, ...data };
            $("adminNombre").textContent = data.nombre || "ADAN Admin";
            toast("Configuración guardada correctamente", "success");
        } else {
            toast("Error al guardar configuración", "error");
        }
    } catch { toast("Error de conexión", "error"); }
});

/* ─── Modal helpers ──────────────────────────────────── */
function showModal(m) { m.classList.add("active"); document.body.style.overflow="hidden"; }
function hideModal(m) { m.classList.remove("active"); document.body.style.overflow=""; }

document.querySelectorAll(".modal-overlay").forEach(o => {
    o.addEventListener("click", e => { if (e.target === o) hideModal(o); });
});
