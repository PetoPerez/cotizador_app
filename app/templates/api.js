const API_BASE = window.location.origin;
const API_PATH = '/api';

function getToken() {
  return localStorage.getItem('token');
}

function getUser() {
  try {
    return JSON.parse(localStorage.getItem('user') || '{}');
  } catch {
    return {};
  }
}

function requireAuth() {
  if (!getToken()) window.location.href = '/login';
}

function requireAdmin() {
  requireAuth();
  const user = getUser();
  if (user.rol !== 'admin' && user.rol !== 'superadmin') window.location.href = '/cotizaciones';
}

async function apiFetch(path, options = {}) {
  const token = getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };

  const res = await fetch(`${API_BASE}${API_PATH}${path}`, { ...options, headers });

  if (res.status === 401) {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = '/login';
    return;
  }

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Error ${res.status}`);
  }

  if (res.status === 204) return null;
  return res.json();
}

function showAlert(msg, type = 'danger', targetId = 'alert-box') {
  const el = document.getElementById(targetId);
  if (!el) return;
  el.textContent = msg;
  el.className = `alert ${type}`;
  el.classList.remove('hidden');
  if (type === 'success') setTimeout(() => el.classList.add('hidden'), 3500);
}

function formatDate(dateStr) {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleDateString('es-MX', {
    day: '2-digit', month: 'short', year: 'numeric',
  });
}

function formatMXN(amount) {
  return new Intl.NumberFormat('es-MX', {
    style: 'currency', currency: 'MXN',
  }).format(amount || 0);
}

function formatCurrency(amount, moneda = 'MXN', tc = 1) {
  // Precios en BD están en USD, multiplicamos por TC para MXN
  const val = moneda === 'MXN' ? (amount || 0) * tc : (amount || 0);
  return new Intl.NumberFormat(moneda === 'USD' ? 'en-US' : 'es-MX', {
    style: 'currency', currency: moneda,
  }).format(val);
}

let _tcCache = null;

async function loadTipoCambio() {
  try {
    const data = await apiFetch('/cotizaciones/tipo-cambio');
    _tcCache = data.usd_mxn;
    const chip = document.getElementById('tc-chip');
    if (chip) {
      chip.textContent = `1 USD = $${data.usd_mxn.toFixed(2)} MXN`;
      chip.title = 'Tipo de cambio actualizado';
    }
    return data.usd_mxn;
  } catch {
    const chip = document.getElementById('tc-chip');
    if (chip) chip.textContent = 'T.C. no disponible';
    return null;
  }
}

function getTipoCambio() { return _tcCache; }

function estadoBadge(estado) {
  const map = {
    borrador: 'badge-gray',
    enviada:  'badge-blue',
    aceptada: 'badge-green',
    cancelada:'badge-red',
  };
  return `<span class="badge ${map[estado] || 'badge-gray'}">${estado}</span>`;
}

function renderSidebar(active) {
  const user = getUser();
  const isAdmin = user.rol === 'admin' || user.rol === 'superadmin';
  const isSDL   = user.empresa_codigo === 'servicios_lavanderia';

  const links = [
    { key: 'cotizaciones', label: 'Cotizaciones', href: '/cotizaciones' },
    { key: 'clientes',     label: 'Clientes',     href: '/clientes' },
    { key: 'productos',    label: 'Productos',     href: '/productos',  adminOnly: true },
    { key: 'servicios',    label: 'Servicios',     href: '/servicios',  show: isAdmin || isSDL },
    { key: 'reportes',     label: 'Reportes',      href: '/reportes',   adminOnly: true },
    { key: 'usuarios',     label: 'Usuarios',      href: '/usuarios',   adminOnly: true },
  ].filter(l => {
    if (l.adminOnly) return isAdmin;
    if ('show' in l) return l.show;
    return true;
  });

  return `
    <aside class="sidebar">
      <div class="sidebar-logo">Cotizaciones</div>
      <div class="tc-chip" id="tc-chip">Cargando T.C....</div>
      <nav class="sidebar-nav">
        ${links.map(l => `
          <a href="${l.href}" class="nav-link ${active === l.key ? 'active' : ''}">
            ${l.label}
          </a>
        `).join('')}
      </nav>
      <div class="sidebar-footer">
        <div class="sidebar-user">${user.nombre || ''}</div>
        <div class="sidebar-role">${user.rol || ''}</div>
        <button class="btn btn-secondary btn-sm"
                onclick="abrirCambiarPassword()"
                style="margin-top:12px;width:100%">
          Cambiar contraseña
        </button>
        <button class="btn btn-secondary btn-sm"
                onclick="logout()"
                style="margin-top:8px;width:100%">
          Cerrar sesión
        </button>
      </div>
    </aside>` + renderCambiarPasswordModal();
}

function renderCambiarPasswordModal() {
  return `
    <div class="modal-overlay" id="modal-cambiar-password">
      <div class="modal" style="max-width:440px">
        <div class="modal-header">
          <div class="modal-title">Cambiar mi contraseña</div>
          <button class="modal-close" onclick="cerrarCambiarPassword()">×</button>
        </div>
        <div id="cambiar-password-alert" class="alert hidden"></div>
        <div class="form-group">
          <label class="form-label">Contraseña actual *</label>
          <input type="password" class="form-control" id="cp-actual" autocomplete="current-password">
        </div>
        <div class="form-group">
          <label class="form-label">Nueva contraseña *</label>
          <input type="password" class="form-control" id="cp-nueva" autocomplete="new-password" minlength="6">
        </div>
        <div class="form-group">
          <label class="form-label">Confirmar nueva contraseña *</label>
          <input type="password" class="form-control" id="cp-confirm" autocomplete="new-password" minlength="6">
        </div>
        <div class="flex gap-8 mt-16" style="justify-content:flex-end">
          <button class="btn btn-secondary" onclick="cerrarCambiarPassword()">Cancelar</button>
          <button class="btn btn-primary" id="cp-save" onclick="guardarCambiarPassword()">Guardar</button>
        </div>
      </div>
    </div>`;
}

function abrirCambiarPassword() {
  ['cp-actual','cp-nueva','cp-confirm'].forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
  document.getElementById('cambiar-password-alert').classList.add('hidden');
  document.getElementById('modal-cambiar-password').classList.add('open');
}

function cerrarCambiarPassword() {
  document.getElementById('modal-cambiar-password').classList.remove('open');
}

async function guardarCambiarPassword() {
  const actual = document.getElementById('cp-actual').value;
  const nueva = document.getElementById('cp-nueva').value;
  const confirm = document.getElementById('cp-confirm').value;
  const alertEl = document.getElementById('cambiar-password-alert');

  if (!actual || !nueva || !confirm) {
    alertEl.textContent = 'Completa todos los campos';
    alertEl.className = 'alert alert-danger';
    return;
  }
  if (nueva.length < 6) {
    alertEl.textContent = 'La nueva contraseña debe tener al menos 6 caracteres';
    alertEl.className = 'alert alert-danger';
    return;
  }
  if (nueva !== confirm) {
    alertEl.textContent = 'Las contraseñas nuevas no coinciden';
    alertEl.className = 'alert alert-danger';
    return;
  }

  const btn = document.getElementById('cp-save');
  btn.disabled = true;
  try {
    await apiFetch('/usuarios/me/password', {
      method: 'POST',
      body: JSON.stringify({ password_actual: actual, password_nuevo: nueva }),
    });
    cerrarCambiarPassword();
    showAlert('Contraseña actualizada correctamente', 'success');
  } catch (e) {
    alertEl.textContent = e.message;
    alertEl.className = 'alert alert-danger';
  } finally {
    btn.disabled = false;
  }
}

function logout() {
  localStorage.removeItem('token');
  localStorage.removeItem('user');
  window.location.href = '/login';
}

// ─── Vista previa de importación (candado: confirmar antes de escribir) ──────
// Recibe el reporte de la fase 1 (confirmar=false) y devuelve una promesa que
// resuelve true si el usuario confirma. Reutilizable por productos y servicios.
function previewImportModal(data) {
  return new Promise((resolve) => {
    const r = data.resumen || {};
    const hayQueHacer = (r.nuevos || 0) + (r.actualizar || 0) > 0;

    const chip = (label, val, cls) =>
      `<div style="flex:1;min-width:90px;background:var(--bg3);border:1px solid var(--border);border-radius:8px;padding:8px 10px;text-align:center">
         <div style="font-size:20px;font-weight:600;color:${cls}">${val || 0}</div>
         <div style="font-size:11px;color:var(--text3)">${label}</div>
       </div>`;

    const listaNuevos = (data.nuevos || []).length
      ? `<div style="margin-top:12px"><div style="font-size:12px;font-weight:600;color:var(--accent2);margin-bottom:4px">Nuevos</div>
         <div style="max-height:120px;overflow-y:auto;font-size:12px;color:var(--text2)">
           ${data.nuevos.map(x => `<div>• ${x}</div>`).join('')}</div></div>` : '';

    const listaAct = (data.actualizar || []).length
      ? `<div style="margin-top:12px"><div style="font-size:12px;font-weight:600;color:var(--accent);margin-bottom:4px">A actualizar (solo lo que cambió)</div>
         <div style="max-height:150px;overflow-y:auto;font-size:12px;color:var(--text2)">
           ${data.actualizar.map(x => `<div style="margin-bottom:3px">• <strong>${x.item}</strong>: ${x.cambios.join(', ')}</div>`).join('')}</div></div>` : '';

    const listaErr = (data.errores || []).length
      ? `<div style="margin-top:12px"><div style="font-size:12px;font-weight:600;color:var(--danger);margin-bottom:4px">Errores (no se cargarán)</div>
         <div style="max-height:120px;overflow-y:auto;font-size:12px;color:var(--danger)">
           ${data.errores.map(x => `<div>• ${x}</div>`).join('')}</div></div>` : '';

    const nota = hayQueHacer ? '' :
      `<div style="margin-top:12px;font-size:12px;color:var(--text3)">No hay nada nuevo ni cambios que aplicar.</div>`;

    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay open';
    overlay.innerHTML = `
      <div class="modal" style="max-width:560px">
        <div class="modal-header">
          <div class="modal-title">Vista previa de importación</div>
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          ${chip('Nuevos', r.nuevos, 'var(--accent2)')}
          ${chip('A actualizar', r.actualizar, 'var(--accent)')}
          ${chip('Sin cambios', r.sin_cambios, 'var(--text2)')}
          ${chip('Errores', r.errores, 'var(--danger)')}
        </div>
        ${listaErr}${listaAct}${listaNuevos}${nota}
        <div class="flex gap-8 mt-16" style="justify-content:flex-end">
          <button class="btn btn-secondary" id="imp-cancelar">Cancelar</button>
          <button class="btn btn-primary" id="imp-confirmar" ${hayQueHacer ? '' : 'disabled'}>
            Confirmar e importar
          </button>
        </div>
      </div>`;
    document.body.appendChild(overlay);
    const cerrar = (val) => { overlay.remove(); resolve(val); };
    overlay.querySelector('#imp-cancelar').onclick = () => cerrar(false);
    const btn = overlay.querySelector('#imp-confirmar');
    if (hayQueHacer) btn.onclick = () => cerrar(true);
  });
}
