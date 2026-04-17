<?php
$pageTitle = 'Flujos de Trabajo';
require_once __DIR__ . '/includes/header.php';
?>

<div class="flex items-center justify-between mb-24">
  <div class="search-bar" style="flex:1;max-width:400px">
    <i data-feather="search"></i>
    <input type="text" id="searchWorkflows" placeholder="Buscar por nombre o nodo...">
  </div>
  <div class="flex gap-8">
    <button class="btn btn-ghost" onclick="window._wf?.loadWorkflows()">
      <i data-feather="refresh-cw"></i> Sincronizar
    </button>
    <button class="btn btn-primary" onclick="document.getElementById('fabMicBtn').click()">
      <i data-feather="mic"></i> Nuevo Flujo por Voz
    </button>
  </div>
</div>

<div class="card">
  <div class="card-header">
    <h3 class="card-title"><i data-feather="git-merge"></i> Flujos en n8n</h3>
  </div>
  <div style="overflow-x:auto">
    <table class="cf-table" id="workflowsTable">
      <thead>
        <tr>
          <th>ID n8n</th>
          <th>Nombre</th>
          <th>Estado</th>
          <th>Nodos</th>
          <th>Creado</th>
          <th>Acciones</th>
        </tr>
      </thead>
      <tbody id="workflowsTableBody">
        <tr><td colspan="6" style="text-align:center;color:var(--text-muted);padding:32px">Cargando flujos...</td></tr>
      </tbody>
    </table>
  </div>
</div>

<!-- JSON View Modal (reuses preview modal, already in footer) -->

<?php require_once __DIR__ . '/includes/footer.php'; ?>
<script>
// Hide deploy button when viewing existing JSON
document.getElementById('confirmDeploy').style.display = '';
</script>
