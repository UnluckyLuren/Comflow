<?php
$pageTitle = 'Infraestructura Local';
require_once __DIR__ . '/includes/header.php';
?>

<!-- Services Status -->
<div class="card mb-24">
  <div class="card-header">
    <h3 class="card-title"><i data-feather="server"></i> Estado de Contenedores Docker</h3>
    <button class="btn btn-ghost btn-sm" onclick="window._infra?.loadStatus()">
      <i data-feather="refresh-cw"></i> Actualizar
    </button>
  </div>
  <div class="infra-grid" id="infraGrid">
    <div style="color:var(--text-muted);font-size:13px;padding:16px">Cargando servicios...</div>
  </div>
</div>

<div class="two-col">
  <!-- n8n Config -->
  <div class="card">
    <div class="card-header">
      <h3 class="card-title"><i data-feather="git-merge"></i> Configuración n8n</h3>
    </div>
    <form id="credForm">
      <div class="form-group">
        <label class="form-label">URL del Host de n8n</label>
        <input type="url" name="n8n_url" class="form-control"
               placeholder="http://n8n:5678" value="http://n8n:5678">
      </div>
      <div class="form-group">
        <label class="form-label">n8n API Key</label>
        <input type="password" name="n8n_api_key" class="form-control" placeholder="••••••••••••">
      </div>
      <button type="submit" class="btn btn-primary">
        <i data-feather="save"></i> Guardar y Verificar
      </button>
    </form>
  </div>

  <!-- LLM Config -->
  <div class="card">
    <div class="card-header">
      <h3 class="card-title"><i data-feather="cpu"></i> Configuración LLM</h3>
    </div>
    <form id="llmForm" onsubmit="return false">
      <div class="form-group">
        <label class="form-label">Motor LLM</label>
        <select class="form-control" name="llm_engine" id="llmEngine" onchange="toggleLLMFields()">
          <option value="ollama">Ollama (Local)</option>
          <option value="openai">OpenAI (Nube)</option>
        </select>
      </div>
      <div id="ollamaFields">
        <div class="form-group">
          <label class="form-label">Modelo Ollama</label>
          <input type="text" name="ollama_model" class="form-control" placeholder="llama3:8b" value="llama3:8b">
        </div>
        <div class="form-group">
          <label class="form-label">URL Ollama</label>
          <input type="url" name="ollama_url" class="form-control" placeholder="http://host.docker.internal:11434">
        </div>
      </div>
      <div id="openaiFields" style="display:none">
        <div class="form-group">
          <label class="form-label">OpenAI API Key</label>
          <input type="password" name="openai_key" class="form-control" placeholder="sk-...">
        </div>
        <div class="form-group">
          <label class="form-label">Modelo</label>
          <input type="text" name="openai_model" class="form-control" value="gpt-4o-mini">
        </div>
      </div>
      <button type="button" class="btn btn-primary" onclick="window._infra?.saveCredential()">
        <i data-feather="save"></i> Guardar Configuración LLM
      </button>
    </form>
  </div>
</div>

<!-- Cloudflare Tunnel Status -->
<div class="card mt-24">
  <div class="card-header">
    <h3 class="card-title"><i data-feather="cloud"></i> Cloudflare Tunnel</h3>
  </div>
  <div class="flex items-center gap-16" style="padding:8px 0">
    <div class="service-icon">
      <i data-feather="cloud"></i>
    </div>
    <div>
      <div style="font-size:14px;color:var(--text-primary)">Acceso externo HTTPS</div>
      <div class="text-muted">El tráfico externo se enruta a través del túnel de Cloudflare</div>
    </div>
    <div class="status-indicator" style="margin-left:auto">
      <span class="status-dot" id="cloudflareDot"></span>
      <span id="cloudflareLabel">Verificando...</span>
    </div>
  </div>
</div>

<?php require_once __DIR__ . '/includes/footer.php'; ?>
<script>
function toggleLLMFields() {
  const engine = document.getElementById('llmEngine').value;
  document.getElementById('ollamaFields').style.display = engine === 'ollama' ? 'block' : 'none';
  document.getElementById('openaiFields').style.display = engine === 'openai' ? 'block' : 'none';
}
</script>
