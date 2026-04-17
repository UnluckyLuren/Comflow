<?php
$pageTitle = 'Bóveda de Credenciales';
require_once __DIR__ . '/includes/header.php';
?>

<div class="flex items-center justify-between mb-24">
  <p class="text-muted">Gestiona las credenciales de terceros usadas por los flujos de n8n</p>
  <button class="btn btn-primary" id="addCredBtn">
    <i data-feather="plus"></i> Añadir Nueva Llave
  </button>
</div>

<!-- Credentials List -->
<div class="card">
  <div class="card-header">
    <h3 class="card-title"><i data-feather="key"></i> Credenciales Almacenadas</h3>
  </div>
  <div id="credsList" style="display:flex;flex-direction:column;gap:12px;padding:4px 0">
    <div style="text-align:center;color:var(--text-muted);padding:32px">Cargando...</div>
  </div>
</div>

<!-- Add Credential Modal -->
<div class="modal-overlay" id="credModal" role="dialog" aria-modal="true">
  <div class="modal" style="padding:28px">
    <button class="modal-close" id="closeCredModal"><i data-feather="x"></i></button>
    <h2 style="font-family:var(--font-display);font-size:18px;margin-bottom:6px;color:var(--text-primary)">
      Añadir Nueva Llave
    </h2>
    <p class="text-muted mb-16">La credencial se cifrará con AES-256 antes de guardarse</p>

    <form id="credSaveForm">
      <div class="form-group">
        <label class="form-label">Aplicación destino</label>
        <select class="form-control" id="credApp" name="nombre_app" required>
          <option value="">Selecciona una aplicación...</option>
          <option value="Gmail_OAuth">Gmail (OAuth2)</option>
          <option value="Google_Drive">Google Drive</option>
          <option value="Google_Sheets">Google Sheets</option>
          <option value="Slack">Slack</option>
          <option value="GitHub">GitHub</option>
          <option value="Notion">Notion</option>
          <option value="Airtable">Airtable</option>
          <option value="Telegram">Telegram Bot</option>
          <option value="Discord">Discord Webhook</option>
          <option value="Custom">Personalizado...</option>
        </select>
      </div>
      <div class="form-group" id="customAppGroup" style="display:none">
        <label class="form-label">Nombre de la aplicación</label>
        <input type="text" class="form-control" id="customAppName" placeholder="Mi Servicio Personalizado">
      </div>
      <div class="form-group">
        <label class="form-label">Tipo de credencial</label>
        <select class="form-control" id="credType" name="tipo">
          <option value="api_key">API Key</option>
          <option value="oauth2">OAuth2 Token</option>
          <option value="token">Bearer Token</option>
          <option value="basic">Basic Auth</option>
        </select>
      </div>
      <div class="form-group">
        <label class="form-label">Token / Client ID / API Key</label>
        <textarea id="credToken" name="token" class="form-control"
                  placeholder="Pega aquí tu credencial en texto plano. Se cifrará automáticamente."
                  rows="3" required></textarea>
      </div>

      <div style="background:var(--amber-dim);border:1px solid rgba(255,179,0,0.3);border-radius:var(--radius);
                  padding:10px 14px;font-size:12px;color:var(--amber);margin-bottom:16px;display:flex;gap:8px;align-items:flex-start">
        <i data-feather="alert-triangle" style="width:14px;height:14px;flex-shrink:0;margin-top:1px"></i>
        Se realizará un test de conexión antes de guardar. La credencial no se almacenará si el test falla.
      </div>

      <div class="flex gap-8" style="justify-content:flex-end">
        <button type="button" class="btn btn-ghost" id="closeCredModal2">Cancelar</button>
        <button type="submit" class="btn btn-primary btn-glow">
          <i data-feather="shield"></i> Guardar y Validar
        </button>
      </div>
    </form>
  </div>
</div>

<?php require_once __DIR__ . '/includes/footer.php'; ?>
<script>
// Handle custom app name
document.getElementById('credApp').addEventListener('change', function() {
  document.getElementById('customAppGroup').style.display =
    this.value === 'Custom' ? 'block' : 'none';
});
document.getElementById('closeCredModal2')?.addEventListener('click', () => {
  document.getElementById('credModal')?.classList.remove('open');
});
</script>
