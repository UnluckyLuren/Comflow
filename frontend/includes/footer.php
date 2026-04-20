  </div><!-- .page-body -->
</main><!-- .main-content -->

<!-- Voice Recording Modal -->
<div class="modal-overlay" id="voiceModal" role="dialog" aria-modal="true" aria-label="Grabar comando de voz">
  <div class="modal voice-modal">
    <button class="modal-close" id="closeVoiceModal" aria-label="Cerrar"><i data-feather="x"></i></button>
    <div class="voice-modal-header">
      <h2>Dictar Comando</h2>
      <p>Describe el flujo de automatización que deseas crear</p>
    </div>

    <div class="voice-visualizer" id="voiceVisualizer">
      <div class="voice-ring ring-1"></div>
      <div class="voice-ring ring-2"></div>
      <div class="voice-ring ring-3"></div>
      <button class="mic-btn" id="micBtn" aria-label="Iniciar grabación">
        <i data-feather="mic" id="micIcon"></i>
      </button>
    </div>

    <div class="voice-status" id="voiceStatus">Presiona para hablar</div>

    <div class="voice-transcript" id="voiceTranscript" style="display:none">
      <label>Transcripción</label>
      <p id="transcriptText"></p>
    </div>

    <div class="manual-input-group" id="manualInputGroup" style="display:none">
      <label for="manualCommand">Entrada manual de comando</label>
      <textarea id="manualCommand" placeholder="Ej: Crea un flujo que lea correos de Gmail y guarde los adjuntos en Google Drive..." rows="3"></textarea>
    </div>

    <div class="voice-actions">
      <button class="btn btn-ghost" id="toggleManualInput">
        <i data-feather="edit-3"></i> Modo texto
      </button>
      <button class="btn btn-primary" id="processVoiceBtn" style="display:none">
        <i data-feather="zap"></i> Generar Flujo
      </button>
    </div>
  </div>
</div>

<!-- JSON Preview Modal -->
<div class="modal-overlay" id="previewModal" role="dialog" aria-modal="true">
  <div class="modal preview-modal">
    <button class="modal-close" id="closePreviewModal"><i data-feather="x"></i></button>
    <div class="preview-header">
      <h2><i data-feather="git-branch"></i> Vista Previa del Flujo</h2>
      <p id="previewCommand"></p>
    </div>

    <div class="nodes-preview" id="nodesPreview"></div>

    <div class="json-preview">
      <label>Estructura JSON generada</label>
      <pre id="jsonPreviewCode"></pre>
    </div>

    <div class="preview-actions">
      <button class="btn btn-ghost" id="cancelDeploy">
        <i data-feather="x"></i> Cancelar
      </button>
      <button class="btn btn-primary btn-glow" id="confirmDeploy">
        <i data-feather="upload-cloud"></i> Confirmar Despliegue
      </button>
    </div>
  </div>
</div>

<!-- Toast Notifications -->
<div class="toast-container" id="toastContainer" aria-live="polite"></div>

<!-- Floating Mic Button (always visible) -->
<button class="fab-mic" id="fabMicBtn" title="Dictar comando de voz">
  <i data-feather="mic"></i>
</button>

<!-- Loading Overlay -->
<div class="loading-overlay" id="loadingOverlay" style="display:none">
  <div class="loading-content">
    <div class="loading-spinner"></div>
    <p id="loadingMessage">Procesando...</p>
  </div>
</div>

<script src="https://unpkg.com/feather-icons"></script>

<script src="/assets/js/utils.js"></script>
<script src="/assets/js/voice.js?v=2"></script> 
<script src="/assets/js/dashboard.js"></script>
<script src="/assets/js/main.js"></script>
<script>
  feather.replace();
</script>
</body>
</html>
