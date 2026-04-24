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

  const links = [
    { key: 'cotizaciones', label: 'Cotizaciones', href: '/cotizaciones' },
    { key: 'clientes',     label: 'Clientes',     href: '/clientes' },
    { key: 'productos',    label: 'Productos',     href: '/productos',  adminOnly: true },
    { key: 'usuarios',     label: 'Usuarios',      href: '/usuarios',   adminOnly: true },
  ].filter(l => !l.adminOnly || isAdmin);

  return `
    <aside class="sidebar">
      <div class="sidebar-logo">Cotizaciones</div>
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
