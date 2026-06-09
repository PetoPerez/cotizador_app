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
  if (user.rol !== 'admin') window.location.href = '/cotizaciones';
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
  const isAdmin = user.rol === 'admin';
  const isSDL   = user.empresa_codigo === 'servicios_lavanderia';

  const links = [
    { key: 'cotizaciones', label: 'Cotizaciones', href: '/cotizaciones' },
    { key: 'clientes',     label: 'Clientes',     href: '/clientes' },
    { key: 'productos',    label: 'Productos',     href: '/productos',  adminOnly: true },
    { key: 'servicios',    label: 'Servicios',     href: '/servicios',  show: isAdmin || isSDL },
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
                onclick="logout()"
                style="margin-top:12px;width:100%">
          Cerrar sesión
        </button>
      </div>
    </aside>`;
}

function logout() {
  localStorage.removeItem('token');
  localStorage.removeItem('user');
  window.location.href = '/login';
}
