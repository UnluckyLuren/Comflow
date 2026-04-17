/**
 * ClawFlow — Dashboard Controller
 * Fetches metrics and renders donut chart + recent executions
 */
class DashboardController {
  constructor() {
    this.chart = null;
    this.refreshInterval = null;
  }

  async init() {
    await this.loadDashboard();
    await this.checkN8nStatus();
    // Auto-refresh every 30s
    this.refreshInterval = setInterval(() => {
      this.loadDashboard();
      this.checkN8nStatus();
    }, 30000);
  }

  async loadDashboard() {
    try {
      const res  = await apiFetch('/api/dashboard/status');
      if (!res) return;
      const data = await res.json();
      this.renderStats(data);
      this.renderDonut(data.active_count ?? 0, data.inactive_count ?? 0);
      this.renderRecentExecutions(data.recent_executions ?? []);
      this.renderRecentCommands(data.recent_commands ?? []);
    } catch (err) {
      console.error('Dashboard load error:', err);
    }
  }

  renderStats(data) {
    this._setText('statTotalFlows',  data.total_count     ?? 0);
    this._setText('statActiveFlows', data.active_count    ?? 0);
    this._setText('statCommands',    data.commands_today  ?? 0);
    this._setText('statErrors',      data.errors_today    ?? 0);
  }

  renderDonut(active, inactive) {
    const canvas = document.getElementById('donutChart');
    if (!canvas) return;

    const total = active + inactive || 1;
    const ctx = canvas.getContext('2d');

    // Simple canvas donut — no external lib needed
    const cx = canvas.width / 2, cy = canvas.height / 2;
    const R = 60, r = 40;
    const activeAngle = (active / total) * Math.PI * 2;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Background circle
    ctx.beginPath();
    ctx.arc(cx, cy, R, 0, Math.PI * 2);
    ctx.arc(cx, cy, r, Math.PI * 2, 0, true);
    ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--bg-elevated').trim();
    ctx.fill();

    if (active > 0) {
      // Active slice
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.arc(cx, cy, R, -Math.PI / 2, -Math.PI / 2 + activeAngle);
      ctx.arc(cx, cy, r, -Math.PI / 2 + activeAngle, -Math.PI / 2, true);
      ctx.closePath();
      ctx.fillStyle = '#00e676';
      ctx.fill();
    }

    if (inactive > 0) {
      // Inactive slice
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.arc(cx, cy, R, -Math.PI / 2 + activeAngle, -Math.PI / 2 + Math.PI * 2);
      ctx.arc(cx, cy, r, -Math.PI / 2 + Math.PI * 2, -Math.PI / 2 + activeAngle, true);
      ctx.closePath();
      ctx.fillStyle = '#1a2130';
      ctx.fill();
    }

    // Center hole (clean)
    ctx.beginPath();
    ctx.arc(cx, cy, r - 2, 0, Math.PI * 2);
    ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--bg-surface').trim() || '#0d1117';
    ctx.fill();

    // Update center text
    this._setText('donutTotal', active + inactive);
    this._setText('legendActive',   active);
    this._setText('legendInactive', inactive);
  }

  renderRecentExecutions(executions) {
    const tbody = document.getElementById('executionsBody');
    if (!tbody) return;

    if (!executions.length) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;color:var(--text-muted);padding:24px">Sin ejecuciones recientes</td></tr>`;
      return;
    }

    tbody.innerHTML = executions.map(e => `
      <tr>
        <td><span class="text-mono" style="color:var(--accent)">${escapeHtml(e.flow_id || '—')}</span></td>
        <td>${escapeHtml(e.name || '—')}</td>
        <td>${formatDate(e.started_at)}</td>
        <td>
          <span class="badge ${e.status === 'success' ? 'badge-active' : 'badge-error'}">
            ${e.status === 'success' ? '✓ Éxito' : '✗ Fallo'}
          </span>
        </td>
        <td style="color:var(--text-muted)">${e.duration_ms ? e.duration_ms + 'ms' : '—'}</td>
      </tr>
    `).join('');
  }

  renderRecentCommands(commands) {
    const list = document.getElementById('commandsList');
    if (!list) return;

    if (!commands.length) {
      list.innerHTML = `<div style="text-align:center;color:var(--text-muted);padding:24px;font-size:13px">Sin comandos recientes</div>`;
      return;
    }

    list.innerHTML = commands.map(c => `
      <div class="log-entry fade-in">
        <span class="log-time">${formatDate(c.created_at)}</span>
        <span class="log-level ${c.estado === 'exito' ? 'info' : c.estado === 'error' ? 'error' : 'warning'}">
          ${c.estado}
        </span>
        <span class="log-message">${escapeHtml(c.texto_transcrito || 'Sin transcripción')}</span>
      </div>
    `).join('');
  }

  async checkN8nStatus() {
    const dot   = document.getElementById('n8nStatusDot');
    const label = document.getElementById('n8nStatusLabel');
    if (!dot || !label) return;

    try {
      const res  = await apiFetch('/api/infrastructure/ping-n8n');
      const data = await res.json();

      if (data.online) {
        dot.className   = 'status-dot online';
        label.textContent = 'n8n Online';
      } else {
        dot.className   = 'status-dot offline';
        label.textContent = 'n8n Offline';
      }
    } catch {
      dot.className   = 'status-dot offline';
      label.textContent = 'n8n Offline';
    }
  }

  _setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  }

  destroy() {
    if (this.refreshInterval) clearInterval(this.refreshInterval);
  }
}

// Make loadDashboard globally callable
function loadDashboard() {
  if (window._dashboard) window._dashboard.loadDashboard();
}
