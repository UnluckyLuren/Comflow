<?php
$pageTitle = 'Infraestructura Local';
require_once __DIR__ . '/includes/header.php';
?>

<!-- Status Row -->
<div id="n8nConfigStatusRow" class="config-status-row mb-24" style="display:none">
  <span id="n8nConfigStatusIcon"></span>
  <span id="n8nConfigStatusMsg"></span>
</div>

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
  <!-- n8n Config ─────────────────────────────────────── -->
  <div class="card">
    <div class="card-header">
      <h3 class="card-title"><i data-feather="git-merge"></i> Conexión con n8n</h3>
      <span id="n8nSavedBadge" class="badge badge-info" style="display:none">Guardado en DB</span>
    </div>
    <p class="text-muted mb-16" style="font-size:12px">
      Ingresa la URL de tu instancia n8n y la API Key. ClawFlow verificará la conexión
      antes de guardar. Todos los flujos usarán esta configuración automáticamente.
    </p>

    <!-- Current config display -->
    <div id="currentN8nConfig" style="margin-bottom:16px;display:none">
      <label class="form-label">Configuración actual</label>
      <div style="background:var(--bg-elevated);border:1px solid var(--border-bright);
                  border-radius:var(--radius);padding:10px 14px;font-size:13px">
        <div class="flex gap-8 items-center">
          <i data-feather="link" style="width:14px;height:14px;color:var(--accent)"></i>
          <span id="currentN8nUrl" class="text-accent"></span>
        </div>
        <div class="flex gap-8 items-center" style="margin-top:4px">
          <i data-feather="key" style="width:14px;height:14px;color:var(--text-muted)"></i>
          <span class="text-muted">API Key: configurada ✓</span>
        </div>
      </div>
    </div>

    <form id="n8nConfigForm">
      <div class="form-group">
        <label class="form-label">URL del Host de n8n</label>
        <input type="url" name="n8n_url" id="n8nUrlInput" class="form-control"
               placeholder="http://n8n:5678 (o tu URL pública)">
        <span style="font-size:11px;color:var(--text-muted);margin-top:4px;display:block">
          Ejemplo: http://n8n:5678 &nbsp;|&nbsp; https://n8n.midominio.com
        </span>
      </div>
      <div class="form-group">
        <label class="form-label">n8n API Key</label>
        <input type="password" name="n8n_api_key" id="n8nApiKeyInput" class="form-control"
               placeholder="••••••••••••">
        <span style="font-size:11px;color:var(--text-muted);margin-top:4px;display:block">
          En n8n: <b>Configuración → API → Habilitar API</b> y copia la key generada
        </span>
      </div>

      <div id="n8nSaveError" class="auth-error" style="margin-bottom:12px"></div>
      <div id="n8nSaveSuccess" class="auth-success" style="margin-bottom:12px"></div>

      <button type="submit" class="btn btn-primary btn-glow" id="n8nSaveBtn">
        <i data-feather="shield"></i> Verificar y Guardar Conexión
      </button>
    </form>
  </div>

  <!-- LLM Config ─────────────────────────────────────── -->
  <div class="card">
    <div class="card-header">
      <h3 class="card-title"><i data-feather="cpu"></i> Configuración LLM</h3>
    </div>
    <p class="text-muted mb-16" style="font-size:12px">
      Motor de IA para generar flujos n8n. Groq (recomendado) es gratuito y muy rápido.
    </p>

    <div class="form-group">
      <label class="form-label">Motor LLM activo</label>
      <select class="form-control" id="llmEngine" onchange="toggleLLMFields()">
        <option value="groq">⚡ Groq API (Llama 3.3 70B — recomendado)</option>
        <option value="openai">☁️ OpenAI API</option>
        <option value="ollama">🖥️ Ollama (local)</option>
      </select>
    </div>

    <!-- Groq -->
    <div id="groqFields">
      <div class="form-group">
        <label class="form-label">Groq API Key</label>
        <input type="password" class="form-control" id="groqKeyInput"
               placeholder="gsk_... (obtén una gratis en console.groq.com)">
      </div>
      <div class="form-group">
        <label class="form-label">Modelo Groq</label>
        <select class="form-control" id="groqModel">
          <option value="llama-3.3-70b-versatile">llama-3.3-70b-versatile (recomendado)</option>
          <option value="llama3-8b-8192">llama3-8b-8192 (rápido)</option>
          <option value="mixtral-8x7b-32768">mixtral-8x7b-32768</option>
        </select>
      </div>
    </div>

    <!-- OpenAI -->
    <div id="openaiFields" style="display:none">
      <div class="form-group">
        <label class="form-label">OpenAI API Key</label>
        <input type="password" class="form-control" placeholder="sk-...">
      </div>
    </div>

    <!-- Ollama -->
    <div id="ollamaFields" style="display:none">
      <div class="form-group">
        <label class="form-label">Modelo Ollama</label>
        <input type="text" class="form-control" placeholder="llama3:8b" value="llama3:8b">
      </div>
      <div class="form-group">
        <label class="form-label">URL Ollama</label>
        <input type="url" class="form-control" placeholder="http://host.docker.internal:11434">
      </div>
    </div>

    <button class="btn btn-ghost" onclick="showToast('LLM se configura vía variables de entorno en docker-compose.yml', 'info')">
      <i data-feather="info"></i> Configuración actual es via .env
    </button>
  </div>
</div>

<!-- Cloudflare Tunnel -->
<div class="card mt-24">
  <div class="card-header">
    <h3 class="card-title"><i data-feather="cloud"></i> Cloudflare Tunnel</h3>
  </div>
  <div class="flex items-center gap-16" style="padding:8px 0">
    <div class="service-icon"><i data-feather="cloud"></i></div>
    <div>
      <div style="font-size:14px;color:var(--text-primary)">Acceso externo HTTPS</div>
      <div class="text-muted">Tráfico externo enrutado a través del túnel Cloudflare</div>
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
  const e = document.getElementById('llmEngine').value;
  document.getElementById('groqFields').style.display   = e === 'groq'    ? 'block' : 'none';
  document.getElementById('openaiFields').style.display = e === 'openai'  ? 'block' : 'none';
  document.getElementById('ollamaFields').style.display = e === 'ollama'  ? 'block' : 'none';
}

// ── Load current n8n config ──────────────────────────────────
async function loadN8nConfig() {
  try {
    const res  = await apiFetch('/api/infrastructure/n8n-config');
    const data = await res.json();
    if (data.host_url) {
      document.getElementById('currentN8nUrl').textContent = data.host_url;
      document.getElementById('currentN8nConfig').style.display = 'block';
      document.getElementById('n8nUrlInput').placeholder = data.host_url;
      if (data.source === 'database') {
        document.getElementById('n8nSavedBadge').style.display = 'inline-flex';
      }
    }
  } catch {}
}

// ── n8n Config Form submit ───────────────────────────────────
document.getElementById('n8nConfigForm').addEventListener('submit', async function(e) {
  e.preventDefault();
  const url    = document.getElementById('n8nUrlInput').value.trim();
  const apiKey = document.getElementById('n8nApiKeyInput').value.trim();
  const errDiv = document.getElementById('n8nSaveError');
  const okDiv  = document.getElementById('n8nSaveSuccess');
  const btn    = document.getElementById('n8nSaveBtn');

  errDiv.classList.remove('visible');
  okDiv.classList.remove('visible');

  if (!url && !apiKey) {
    errDiv.textContent = 'Ingresa al menos la URL o la API Key de n8n.';
    errDiv.classList.add('visible');
    return;
  }

  btn.disabled = true;
  btn.innerHTML = '<i data-feather="loader"></i> Verificando...';
  if (typeof feather !== 'undefined') feather.replace();

  try {
    const body = {};
    if (url)    body.n8n_url     = url;
    if (apiKey) body.n8n_api_key = apiKey;

    const res  = await apiFetch('/api/infrastructure/save-config', {
      method: 'POST',
      body: JSON.stringify(body),
    });
    const data = await res.json();

    if (!res.ok) {
      errDiv.textContent = data.detail || 'Error al guardar.';
      errDiv.classList.add('visible');
    } else {
      okDiv.textContent = '✓ ' + data.message;
      okDiv.classList.add('visible');
      document.getElementById('n8nApiKeyInput').value = '';
      showToast('Configuración de n8n guardada y verificada', 'success');
      loadN8nConfig();
      // Refresh infrastructure status
      window._infra?.loadStatus();
    }
  } catch (err) {
    errDiv.textContent = 'Error de conexión al guardar.';
    errDiv.classList.add('visible');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i data-feather="shield"></i> Verificar y Guardar Conexión';
    if (typeof feather !== 'undefined') feather.replace();
  }
});

// Load on page init
loadN8nConfig();
</script>
