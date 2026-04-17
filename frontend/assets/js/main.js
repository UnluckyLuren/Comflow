/**
 * ClawFlow — Main Application Init
 */
document.addEventListener('DOMContentLoaded', () => {
  // Initialize Feather icons
  if (typeof feather !== 'undefined') feather.replace();

  // Sidebar toggle (mobile)
  const toggle  = document.getElementById('sidebarToggle');
  const sidebar = document.getElementById('sidebar');
  toggle?.addEventListener('click', () => sidebar?.classList.toggle('open'));

  // Close sidebar on outside click (mobile)
  document.addEventListener('click', (e) => {
    if (sidebar?.classList.contains('open') &&
        !sidebar.contains(e.target) &&
        e.target !== toggle) {
      sidebar.classList.remove('open');
    }
  });

  // Init Voice Controller (available on all authenticated pages)
  if (document.getElementById('voiceModal')) {
    window._voice = new VoiceController();
  }

  // Init Dashboard Controller if on dashboard page
  if (document.getElementById('donutChart')) {
    window._dashboard = new DashboardController();
    window._dashboard.init();
  }

  // Init Workflows page
  if (document.getElementById('workflowsTable')) {
    window._wf = new WorkflowsController();
    window._wf.init();
  }

  // Init Infrastructure page
  if (document.getElementById('infraGrid')) {
    window._infra = new InfraController();
    window._infra.init();
  }

  // Init Credentials page
  if (document.getElementById('credsList')) {
    window._creds = new CredentialsController();
    window._creds.init();
  }

  // Init Logs page
  if (document.getElementById('logsContainer')) {
    window._logs = new LogsController();
    window._logs.init();
  }
});

/* ─── Workflows Controller ─────────────────────────────────── */
class WorkflowsController {
  async init() {
    await this.loadWorkflows();
    document.getElementById('searchWorkflows')?.addEventListener('input', (e) => {
      this.filterWorkflows(e.target.value);
    });
  }

  async loadWorkflows() {
    try {
      const res  = await apiFetch('/api/workflows/list');
      const data = await res.json();
      this.workflows = data.workflows || [];
      this.renderWorkflows(this.workflows);
    } catch (err) {
      console.error(err);
      showToast('Error cargando flujos', 'error');
    }
  }

  renderWorkflows(wfs) {
    const tbody = document.getElementById('workflowsTableBody');
    if (!tbody) return;

    if (!wfs.length) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;color:var(--text-muted);padding:32px">
        Sin flujos. ¡Dicta tu primer comando! 🎤
      </td></tr>`;
      return;
    }

    tbody.innerHTML = wfs.map(w => `
      <tr data-id="${w.id_flujo_n8n}">
        <td><span class="text-mono text-accent">${escapeHtml(w.id_flujo_n8n)}</span></td>
        <td>${escapeHtml(w.nombre)}</td>
        <td>
          <label class="toggle">
            <input type="checkbox" ${w.activo ? 'checked' : ''}
                   onchange="window._wf.toggleFlow('${w.id_flujo_n8n}', this.checked)">
            <span class="toggle-slider"></span>
          </label>
        </td>
        <td>${this._renderNodes(w.nodos_resumen)}</td>
        <td>${formatDate(w.created_at)}</td>
        <td>
          <div class="flex gap-8">
            <button class="btn btn-ghost btn-sm btn-icon" title="Ver JSON"
                    onclick="window._wf.viewJson('${w.id_flujo_n8n}')">
              <i data-feather="code"></i>
            </button>
            <button class="btn btn-danger btn-sm btn-icon" title="Eliminar"
                    onclick="window._wf.deleteFlow('${w.id_flujo_n8n}')">
              <i data-feather="trash-2"></i>
            </button>
          </div>
        </td>
      </tr>
    `).join('');
    if (typeof feather !== 'undefined') feather.replace();
  }

  _renderNodes(nodes) {
    if (!nodes || !nodes.length) return '<span class="text-muted">—</span>';
    const arr = Array.isArray(nodes) ? nodes : JSON.parse(nodes || '[]');
    return arr.slice(0, 3).map(n =>
      `<span class="badge badge-info" style="margin-right:4px">${escapeHtml(n)}</span>`
    ).join('') + (arr.length > 3 ? `<span class="text-muted">+${arr.length - 3}</span>` : '');
  }

  filterWorkflows(query) {
    if (!this.workflows) return;
    const q = query.toLowerCase();
    const filtered = this.workflows.filter(w =>
      w.nombre.toLowerCase().includes(q) ||
      w.id_flujo_n8n.toLowerCase().includes(q)
    );
    this.renderWorkflows(filtered);
  }

  async toggleFlow(flowId, active) {
    try {
      const res = await apiFetch(`/api/workflows/${flowId}/toggle`, {
        method: 'PUT',
        body: JSON.stringify({ active }),
      });
      const data = await res.json();
      if (!res.ok) { showToast(data.detail || 'Error', 'error'); return; }
      showToast(`Flujo ${active ? 'activado' : 'desactivado'}`, 'success');
    } catch {
      showToast('Error de conexión', 'error');
    }
  }

  async deleteFlow(flowId) {
    if (!confirm('¿Eliminar este flujo de n8n?')) return;
    try {
      const res = await apiFetch(`/api/workflows/${flowId}`, { method: 'DELETE' });
      const data = await res.json();
      if (!res.ok) { showToast(data.detail || 'Error', 'error'); return; }
      showToast('Flujo eliminado', 'success');
      this.loadWorkflows();
    } catch {
      showToast('Error de conexión', 'error');
    }
  }

  async viewJson(flowId) {
    showLoading('Cargando JSON...');
    try {
      const res = await apiFetch(`/api/workflows/${flowId}/json`);
      const data = await res.json();
      hideLoading();
      const pre = document.getElementById('jsonPreviewCode');
      if (pre) pre.textContent = JSON.stringify(data.workflow_json || data, null, 2);
      document.getElementById('nodesPreview').innerHTML = '';
      document.getElementById('previewCommand').textContent = `Flujo ID: ${flowId}`;
      document.getElementById('confirmDeploy').style.display = 'none';
      document.getElementById('previewModal').classList.add('open');
    } catch {
      hideLoading();
      showToast('Error cargando JSON', 'error');
    }
  }
}

function loadWorkflows() {
  window._wf?.loadWorkflows();
}

/* ─── Infrastructure Controller ────────────────────────────── */
class InfraController {
  async init() {
    await this.loadStatus();
    setInterval(() => this.loadStatus(), 15000);

    // Credentials form
    document.getElementById('credForm')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      await this.saveCredential();
    });
  }

  async loadStatus() {
    try {
      const res  = await apiFetch('/api/infrastructure/status');
      const data = await res.json();
      this.renderServices(data.services || []);
    } catch (err) {
      console.error(err);
    }
  }

  renderServices(services) {
    const grid = document.getElementById('infraGrid');
    if (!grid) return;

    const iconMap = { nginx:'globe', fastapi:'cpu', mysql:'database', n8n:'git-merge', cloudflare:'cloud' };

    grid.innerHTML = services.map(s => `
      <div class="service-card">
        <div class="service-icon">
          <i data-feather="${iconMap[s.name.toLowerCase()] || 'box'}"></i>
        </div>
        <div class="service-info">
          <div class="service-name">${escapeHtml(s.name)}</div>
          <div class="service-detail">${escapeHtml(s.detail || '')}</div>
        </div>
        <div class="service-status">
          <span class="status-dot ${s.online ? 'online' : 'offline'}"></span>
          <span style="color:${s.online ? 'var(--green)' : 'var(--red)'};font-size:12px">
            ${s.online ? 'Online' : 'Offline'}
          </span>
        </div>
      </div>
    `).join('');
    if (typeof feather !== 'undefined') feather.replace();
  }

  async saveCredential() {
    const form = document.getElementById('credForm');
    const fd   = new FormData(form);
    showLoading('Validando credencial...');
    try {
      const res = await apiFetch('/api/infrastructure/save-config', {
        method: 'POST',
        body: JSON.stringify(Object.fromEntries(fd)),
      });
      const data = await res.json();
      hideLoading();
      if (!res.ok) { showToast(data.detail || 'Error', 'error'); return; }
      showToast('Credencial guardada correctamente', 'success');
    } catch {
      hideLoading();
      showToast('Error de conexión', 'error');
    }
  }
}

/* ─── Credentials Controller ────────────────────────────────── */
class CredentialsController {
  async init() {
    await this.load();
    document.getElementById('addCredBtn')?.addEventListener('click', () => {
      document.getElementById('credModal')?.classList.add('open');
    });
    document.getElementById('closeCredModal')?.addEventListener('click', () => {
      document.getElementById('credModal')?.classList.remove('open');
    });
    document.getElementById('credSaveForm')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      await this.save();
    });
  }

  async load() {
    const res  = await apiFetch('/api/credentials/list');
    const data = await res.json();
    this.render(data.credentials || []);
  }

  render(creds) {
    const list = document.getElementById('credsList');
    if (!list) return;

    if (!creds.length) {
      list.innerHTML = `<div style="text-align:center;color:var(--text-muted);padding:32px">Sin credenciales guardadas</div>`;
      return;
    }

    list.innerHTML = creds.map(c => `
      <div class="service-card">
        <div class="service-icon">
          <i data-feather="key"></i>
        </div>
        <div class="service-info">
          <div class="service-name">${escapeHtml(c.nombre_app)}</div>
          <div class="service-detail">${c.tipo} · Actualizado ${formatDate(c.updated_at)}</div>
        </div>
        <div class="flex gap-8 items-center">
          <span class="badge ${c.estado_conexion === 'valida' ? 'badge-active' : c.estado_conexion === 'invalida' ? 'badge-error' : 'badge-inactive'}">
            ${c.estado_conexion}
          </span>
          <button class="btn btn-danger btn-sm btn-icon" onclick="window._creds.delete(${c.id_credencial})">
            <i data-feather="trash-2"></i>
          </button>
        </div>
      </div>
    `).join('');
    if (typeof feather !== 'undefined') feather.replace();
  }

  async save() {
    const form = document.getElementById('credSaveForm');
    showLoading('Validando y guardando...');
    try {
      const res = await apiFetch('/api/credentials/add', {
        method: 'POST',
        body: JSON.stringify({
          nombre_app: document.getElementById('credApp').value,
          tipo: document.getElementById('credType').value,
          token: document.getElementById('credToken').value,
        }),
      });
      const data = await res.json();
      hideLoading();
      if (!res.ok) { showToast(data.detail || 'Error', 'error'); return; }
      showToast('Credencial guardada y validada', 'success');
      document.getElementById('credModal')?.classList.remove('open');
      this.load();
    } catch {
      hideLoading();
      showToast('Error de conexión', 'error');
    }
  }

  async delete(id) {
    if (!confirm('¿Eliminar esta credencial?')) return;
    const res = await apiFetch(`/api/credentials/${id}`, { method: 'DELETE' });
    if (res.ok) { showToast('Credencial eliminada', 'success'); this.load(); }
    else showToast('Error al eliminar', 'error');
  }
}

/* ─── Logs Controller ───────────────────────────────────────── */
class LogsController {
  async init() {
    await this.load();
    document.getElementById('logsRefresh')?.addEventListener('click', () => this.load());
    document.getElementById('logsLevelFilter')?.addEventListener('change', (e) => {
      this.load(e.target.value);
    });
  }

  async load(level = '') {
    const url = level ? `/api/logs?level=${level}&limit=100` : '/api/logs?limit=100';
    try {
      const res  = await apiFetch(url);
      const data = await res.json();
      this.render(data.logs || []);
    } catch {
      showToast('Error cargando logs', 'error');
    }
  }

  render(logs) {
    const container = document.getElementById('logsContainer');
    if (!container) return;

    if (!logs.length) {
      container.innerHTML = `<div style="text-align:center;color:var(--text-muted);padding:32px">Sin logs</div>`;
      return;
    }

    container.innerHTML = logs.map(l => `
      <div class="log-entry fade-in">
        <span class="log-time">${formatDate(l.created_at)}</span>
        <span class="log-level ${l.nivel}">${l.nivel}</span>
        <span class="log-module">[${escapeHtml(l.modulo || '?')}]</span>
        <span class="log-message">${escapeHtml(l.mensaje)}</span>
      </div>
    `).join('');
  }
}
