<?php
$pageTitle = 'Dashboard';
require_once __DIR__ . '/includes/header.php';
?>

<!-- Stats Grid -->
<div class="stats-grid">
  <div class="stat-card">
    <div class="stat-label">Total Flujos</div>
    <div class="stat-value" id="statTotalFlows">—</div>
    <div class="stat-sub">En la instancia n8n</div>
  </div>
  <div class="stat-card green">
    <div class="stat-label">Flujos Activos</div>
    <div class="stat-value green" id="statActiveFlows">—</div>
    <div class="stat-sub">Corriendo ahora</div>
  </div>
  <div class="stat-card amber">
    <div class="stat-label">Comandos Hoy</div>
    <div class="stat-value amber" id="statCommands">—</div>
    <div class="stat-sub">Comandos de voz dictados</div>
  </div>
  <div class="stat-card red">
    <div class="stat-label">Errores Hoy</div>
    <div class="stat-value red" id="statErrors">—</div>
    <div class="stat-sub">Fallos de LLM/red</div>
  </div>
</div>

<div class="two-col">
  <!-- Donut Chart -->
  <div class="card card-accent">
    <div class="card-header">
      <h3 class="card-title">
        <i data-feather="pie-chart"></i> Estado de Automatizaciones
      </h3>
    </div>
    <div class="donut-wrap">
      <div class="donut-chart-container">
        <canvas id="donutChart" width="160" height="160"></canvas>
        <div class="donut-center">
          <div class="donut-center-val" id="donutTotal">—</div>
          <div class="donut-center-lbl">Total</div>
        </div>
      </div>
      <div class="donut-legend">
        <div class="legend-item">
          <span class="legend-dot" style="background:var(--green);box-shadow:0 0 6px var(--green)"></span>
          <span style="color:var(--text-secondary)">Activos:</span>
          <strong id="legendActive" style="color:var(--green)">—</strong>
        </div>
        <div class="legend-item">
          <span class="legend-dot" style="background:var(--bg-elevated);border:1px solid var(--border-bright)"></span>
          <span style="color:var(--text-secondary)">Inactivos:</span>
          <strong id="legendInactive" style="color:var(--text-muted)">—</strong>
        </div>
      </div>
    </div>
  </div>

  <!-- Recent Voice Commands -->
  <div class="card">
    <div class="card-header">
      <h3 class="card-title">
        <i data-feather="mic"></i> Comandos Recientes
      </h3>
      <a href="/workflows.php" class="btn btn-ghost btn-sm">Ver todos</a>
    </div>
    <div id="commandsList">
      <div style="text-align:center;color:var(--text-muted);padding:24px;font-size:13px">Cargando...</div>
    </div>
  </div>
</div>

<!-- Recent Executions -->
<div class="card mt-24">
  <div class="card-header">
    <h3 class="card-title">
      <i data-feather="activity"></i> Últimas Ejecuciones n8n
    </h3>
    <button class="btn btn-ghost btn-sm" onclick="loadDashboard()">
      <i data-feather="refresh-cw"></i> Actualizar
    </button>
  </div>
  <div style="overflow-x:auto">
    <table class="cf-table">
      <thead>
        <tr>
          <th>ID Flujo</th>
          <th>Nombre</th>
          <th>Iniciado</th>
          <th>Estado</th>
          <th>Duración</th>
        </tr>
      </thead>
      <tbody id="executionsBody">
        <tr><td colspan="5" style="text-align:center;color:var(--text-muted);padding:24px">Cargando...</td></tr>
      </tbody>
    </table>
  </div>
</div>

<?php require_once __DIR__ . '/includes/footer.php'; ?>
