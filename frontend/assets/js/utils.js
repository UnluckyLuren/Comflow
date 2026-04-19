/**
 * ClawFlow — Utility Functions
 */

/**
 * Show a toast notification
 * @param {string} message
 * @param {'success'|'error'|'info'|'warning'} type
 * @param {number} duration ms
 */
function showToast(message, type = 'info', duration = 4000) {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const icons = {
    success: 'check-circle',
    error:   'alert-circle',
    info:    'info',
    warning: 'alert-triangle',
  };

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
         stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      ${getFeatherPath(icons[type])}
    </svg>
    <span>${escapeHtml(message)}</span>
  `;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(20px)';
    toast.style.transition = 'all 0.3s';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

function showLoading(msg = 'Procesando...') {
  const overlay = document.getElementById('loadingOverlay');
  const msgEl   = document.getElementById('loadingMessage');
  if (overlay) { overlay.style.display = 'flex'; }
  if (msgEl)   { msgEl.textContent = msg; }
}
function hideLoading() {
  const overlay = document.getElementById('loadingOverlay');
  if (overlay) overlay.style.display = 'none';
}

function escapeHtml(str) {
  const d = document.createElement('div');
  d.appendChild(document.createTextNode(str));
  return d.innerHTML;
}

function formatDate(dateStr) {
  if (!dateStr) return '—';
  return new Intl.DateTimeFormat('es-MX', {
    month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit'
  }).format(new Date(dateStr));
}

/**
 * Extrae el valor de una cookie por su nombre
 */
function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return null;
}

/**
 * Función fetch envuelta con inyección de JWT
 */
async function apiFetch(url, options = {}) {
  // 1. Obtener el token generado por PHP
  const token = getCookie('access_token');

  const defaults = {
    headers: { 
      'Content-Type': 'application/json' 
    },
    credentials: 'include',
  };

  // 2. Si existe el token, inyectarlo como cabecera Bearer para FastAPI
  if (token) {
    defaults.headers['Authorization'] = `Bearer ${token}`;
  }

  const merged = { ...defaults, ...options };
  
  // Respetar cabeceras adicionales si se enviaron en los options
  if (merged.headers && options.headers) {
    merged.headers = { ...defaults.headers, ...options.headers };
  }

  const res = await fetch(url, merged);
  
  if (res.status === 401) {
    window.location.href = '/index.php?expired=1';
    return;
  }
  return res;
}

// Minimal Feather icon paths (used in JS-created elements)
function getFeatherPath(name) {
  const paths = {
    'check-circle': '<polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>',
    'alert-circle': '<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>',
    'info':         '<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>',
    'alert-triangle':'<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
    'zap':          '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
    'x-circle':     '<circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>',
  };
  return paths[name] || '';
}
