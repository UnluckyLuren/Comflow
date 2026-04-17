<?php
$pageTitle = 'Logs del Sistema';
require_once __DIR__ . '/includes/header.php';
?>

<div class="flex items-center justify-between mb-24">
  <div class="flex gap-8 items-center">
    <label class="form-label" style="margin:0">Nivel:</label>
    <select class="form-control" id="logsLevelFilter" style="width:auto;padding:6px 12px">
      <option value="">Todos</option>
      <option value="info">Info</option>
      <option value="warning">Warning</option>
      <option value="error">Error</option>
      <option value="critical">Critical</option>
    </select>
  </div>
  <button class="btn btn-ghost" id="logsRefresh">
    <i data-feather="refresh-cw"></i> Actualizar
  </button>
</div>

<div class="card" style="padding:0;overflow:hidden">
  <div class="card-header" style="padding:16px 20px;border-bottom:1px solid var(--border)">
    <h3 class="card-title"><i data-feather="terminal"></i> Registro de Eventos</h3>
    <span class="text-muted" style="font-size:12px">Últimas 100 entradas</span>
  </div>
  <div id="logsContainer" style="max-height:600px;overflow-y:auto;font-family:var(--font-mono)">
    <div style="text-align:center;color:var(--text-muted);padding:32px">Cargando logs...</div>
  </div>
</div>

<?php require_once __DIR__ . '/includes/footer.php'; ?>
