/**
 * ClawFlow — VoiceController
 * Handles microphone capture, STT, LLM JSON generation, and deployment
 */
class VoiceController {
  constructor() {
    this.mediaRecorder  = null;
    this.audioChunks    = [];
    this.isRecording    = false;
    this.transcriptText = '';
    this.generatedJson  = null;
    this.stream         = null;

    this.voiceModal    = document.getElementById('voiceModal');
    this.previewModal  = document.getElementById('previewModal');
    this.voiceVisualizer = document.getElementById('voiceVisualizer');
    this.voiceStatus   = document.getElementById('voiceStatus');
    this.voiceTranscript = document.getElementById('voiceTranscript');
    this.transcriptEl  = document.getElementById('transcriptText');
    this.manualGroup   = document.getElementById('manualInputGroup');
    this.manualInput   = document.getElementById('manualCommand');
    this.micBtn        = document.getElementById('micBtn');
    this.processBtn    = document.getElementById('processVoiceBtn');
    this.toggleManual  = document.getElementById('toggleManualInput');
    this.fabMic        = document.getElementById('fabMicBtn');
    this.closeVoice    = document.getElementById('closeVoiceModal');
    this.closePreview  = document.getElementById('closePreviewModal');
    this.confirmDeploy = document.getElementById('confirmDeploy');
    this.cancelDeploy  = document.getElementById('cancelDeploy');

    this._bindEvents();
  }

  _bindEvents() {
    this.fabMic?.addEventListener('click', () => this.openVoiceModal());
    this.closeVoice?.addEventListener('click', () => this.closeVoiceModal());
    this.micBtn?.addEventListener('click', () => this.toggleRecording());
    this.toggleManual?.addEventListener('click', () => this.toggleManualMode());
    this.processBtn?.addEventListener('click', () => this.processCommand());
    this.closePreview?.addEventListener('click', () => this.closePreviewModal());
    this.cancelDeploy?.addEventListener('click', () => this.closePreviewModal());
    this.confirmDeploy?.addEventListener('click', () => this.deployFlow());

    // Close on overlay click
    this.voiceModal?.addEventListener('click', (e) => {
      if (e.target === this.voiceModal) this.closeVoiceModal();
    });
    this.previewModal?.addEventListener('click', (e) => {
      if (e.target === this.previewModal) this.closePreviewModal();
    });
  }

  openVoiceModal() {
    this.voiceModal.classList.add('open');
    this._resetVoiceUI();
  }

  closeVoiceModal() {
    if (this.isRecording) this.stopRecording();
    this.voiceModal.classList.remove('open');
    this._releaseStream();
    this._resetVoiceUI();
  }

  closePreviewModal() {
    this.previewModal.classList.remove('open');
  }

  _resetVoiceUI() {
    this.audioChunks    = [];
    this.transcriptText = '';
    this.generatedJson  = null;
    this.isRecording    = false;
    this.voiceVisualizer.classList.remove('is-recording');
    this._setVoiceStatus('Presiona para hablar', '');
    this.voiceTranscript.style.display = 'none';
    this.processBtn.style.display = 'none';
    this.manualGroup.style.display = 'none';
    if (this.manualInput) this.manualInput.value = '';
    if (typeof feather !== 'undefined') feather.replace();
  }

  async toggleRecording() {
    if (this.isRecording) {
      this.stopRecording();
    } else {
      await this.startRecording();
    }
  }

  async startRecording() {
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
      this.mediaRecorder = new MediaRecorder(this.stream);
      this.audioChunks   = [];

      this.mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) this.audioChunks.push(e.data);
      };
      this.mediaRecorder.onstop = () => this._onRecordingStop();

      this.mediaRecorder.start(250);
      this.isRecording = true;
      this.voiceVisualizer.classList.add('is-recording');
      this._setVoiceStatus('Escuchando... (presiona para detener)', 'recording');
    } catch (err) {
      console.error('Mic error:', err);
      this._setVoiceStatus('Permisos de micrófono denegados', '');
      // Fallback: show manual input
      this.manualGroup.style.display = 'block';
      this.processBtn.style.display  = 'inline-flex';
      showToast('Micrófono no disponible. Usa la entrada manual.', 'warning');
    }
  }

  stopRecording() {
    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      this.mediaRecorder.stop();
    }
    this.isRecording = false;
    this.voiceVisualizer.classList.remove('is-recording');
    this._setVoiceStatus('Procesando audio...', 'processing');
  }

  async _onRecordingStop() {
    if (this.audioChunks.length === 0) return;
    const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
    this._releaseStream();
    await this._transcribeAudio(audioBlob);
  }

  _releaseStream() {
    if (this.stream) {
      this.stream.getTracks().forEach(t => t.stop());
      this.stream = null;
    }
  }

  async _transcribeAudio(audioBlob) {
    showLoading('Transcribiendo audio con Whisper...');
    try {
      const formData = new FormData();
      formData.append('audio', audioBlob, 'command.webm');

      const res = await fetch('/api/voice/transcribe', {
        method: 'POST',
        credentials: 'include',
        body: formData,
      });

      const data = await res.json();
      hideLoading();

      if (!res.ok || !data.text) {
        this._setVoiceStatus('No se reconoció voz. Intenta de nuevo.', '');
        showToast(data.detail || 'Error en transcripción', 'error');
        return;
      }

      this.transcriptText = data.text;
      this.transcriptEl.textContent = data.text;
      this.voiceTranscript.style.display = 'block';
      this.processBtn.style.display = 'inline-flex';
      this._setVoiceStatus('Transcripción lista ✓', '');
      if (typeof feather !== 'undefined') feather.replace();
    } catch (err) {
      hideLoading();
      console.error(err);
      showToast('Error de red al transcribir', 'error');
      this._setVoiceStatus('Error de conexión', '');
    }
  }

  toggleManualMode() {
    const visible = this.manualGroup.style.display !== 'none';
    this.manualGroup.style.display = visible ? 'none' : 'block';
    this.processBtn.style.display  = visible ? 'none' : 'inline-flex';
    if (typeof feather !== 'undefined') feather.replace();
  }

  async processCommand() {
    const text = this.transcriptText || this.manualInput?.value?.trim();
    if (!text) {
      showToast('Ingresa o dicta un comando primero', 'warning');
      return;
    }

    showLoading('Generando flujo con IA...');
    try {
      const res = await apiFetch('/api/voice/generate-flow', {
        method: 'POST',
        body: JSON.stringify({ text }),
      });
      const data = await res.json();
      hideLoading();

      if (!res.ok) {
        showToast(data.detail || 'Error al generar JSON', 'error');
        return;
      }

      this.closeVoiceModal(); // Primero cerramos y reseteamos
      this.generatedJson = data.workflow_json; // LUEGO guardamos el JSON a salvo
      this._openPreviewModal(text, data); // Y abrimos la vista previa
    } catch (err) {
      hideLoading();
      console.error(err);
      showToast('Error de conexión con el backend', 'error');
    }
  }

  _openPreviewModal(command, data) {
    document.getElementById('previewCommand').textContent =
      `"${command.substring(0, 120)}${command.length > 120 ? '...' : ''}"`;

    // Render node chips
    const nodesWrap = document.getElementById('nodesPreview');
    nodesWrap.innerHTML = '';
    const nodes = data.nodes || [];
    nodes.forEach(n => {
      const chip = document.createElement('div');
      chip.className = 'node-chip';
      chip.innerHTML = `
        <div class="node-chip-icon">${(n.type || 'N')[0].toUpperCase()}</div>
        <span>${escapeHtml(n.name || n.type || 'Nodo')}</span>
      `;
      nodesWrap.appendChild(chip);
    });

    document.getElementById('jsonPreviewCode').textContent =
      JSON.stringify(this.generatedJson, null, 2);

    this.previewModal.classList.add('open');
    if (typeof feather !== 'undefined') feather.replace();
  }

  async deployFlow() {
    if (!this.generatedJson) return;
    showLoading('Desplegando flujo en n8n...');
    this.previewModal.classList.remove('open');
    try {
      const res = await apiFetch('/api/workflows/deploy', {
        method: 'POST',
        body: JSON.stringify({ workflow_json: this.generatedJson }),
      });
      const data = await res.json();
      hideLoading();

      if (!res.ok) {
        showToast(data.detail || 'Error al desplegar flujo', 'error');
        return;
      }
      showToast(`✓ Flujo "${data.name || 'Nuevo'}" desplegado y activo`, 'success', 5000);

      // Refresh dashboard if on that page
      if (typeof loadDashboard === 'function') loadDashboard();
      if (typeof loadWorkflows === 'function') loadWorkflows();
    } catch (err) {
      hideLoading();
      showToast('Error de conexión al desplegar', 'error');
    }
  }

  _setVoiceStatus(msg, cls) {
    if (!this.voiceStatus) return;
    this.voiceStatus.textContent = msg;
    this.voiceStatus.className = `voice-status ${cls}`;
  }
}
