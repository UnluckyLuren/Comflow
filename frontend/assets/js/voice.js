
/**
 * ClawFlow — VoiceController (Rediseñado desde 0 - Unified Select & Scroll Fix)
 */
class VoiceController {
  constructor() {
    this.mediaRecorder  = null;
    this.audioChunks    = [];
    this.isRecording    = false;
    this.transcriptText = '';
    this.generatedJson  = null;
    this.selectedCreds  = [];
    this.pendingCmdId   = null;
    this.stream         = null;
    this.allUserCreds   = []; // Almacenará todas tus credenciales de la bóveda

    this.voiceModal    = document.getElementById('voiceModal');
    this.previewModal  = document.getElementById('previewModal');
    this.credModal     = document.getElementById('credSelectionModal');

    this.voiceVisualizer = document.getElementById('voiceVisualizer');
    this.voiceStatus     = document.getElementById('voiceStatus');
    this.voiceTranscript = document.getElementById('voiceTranscript');
    this.transcriptEl    = document.getElementById('transcriptText');
    this.manualGroup     = document.getElementById('manualInputGroup');
    this.manualInput     = document.getElementById('manualCommand');
    this.micBtn          = document.getElementById('micBtn');
    this.processBtn      = document.getElementById('processVoiceBtn');
    this.toggleManual    = document.getElementById('toggleManualInput');
    this.fabMic          = document.getElementById('fabMicBtn');

    this._injectStyles(); // Inyecta CSS para arreglar el scroll y el select
    this._bindEvents();
  }

  _injectStyles() {
    if (document.getElementById('voiceControllerStyles')) return;
    const style = document.createElement('style');
    style.id = 'voiceControllerStyles';
    style.textContent = `
      /* Arreglo del Modal para permitir Scroll y no salirse de pantalla */
      #credSelectionModal .modal { 
        display: flex !important; 
        flex-direction: column !important; 
        max-height: 85vh !important; 
        overflow: hidden !important; 
        padding: 0 !important;
      }
      .cred-modal-header, .cred-modal-footer { flex-shrink: 0; padding: 24px; background: var(--bg-surface); z-index: 10; }
      #credSlotsContainer { 
        overflow-y: auto !important; 
        flex: 1 1 auto !important; 
        padding: 0 24px 24px 24px !important; 
      }
      /* Arreglo para forzar la apariencia visual de un Select nativo */
      .cred-select {
        appearance: auto !important;
        -webkit-appearance: auto !important;
        background-color: var(--bg-elevated) !important;
        color: var(--text-primary) !important;
        padding: 10px 14px !important;
        border: 1px solid var(--border-bright) !important;
        cursor: pointer !important;
      }
      .cred-select optgroup { color: var(--accent); font-weight: bold; background: var(--bg-surface); }
      .cred-select option { color: var(--text-primary); background: var(--bg-base); }
    `;
    document.head.appendChild(style);
  }

  _bindEvents() {
    this.fabMic?.addEventListener('click', () => this.openVoiceModal());
    document.getElementById('closeVoiceModal')?.addEventListener('click', () => this.cancelVoiceFlow());
    this.micBtn?.addEventListener('click', () => this.toggleRecording());
    this.toggleManual?.addEventListener('click', () => this.toggleManualMode());
    this.processBtn?.addEventListener('click', () => this.processCommand());
    
    document.getElementById('closePreviewModal')?.addEventListener('click', () => this.closePreviewModal());
    document.getElementById('cancelDeploy')?.addEventListener('click', () => this.closePreviewModal());
    document.getElementById('confirmDeploy')?.addEventListener('click', () => this.deployFlow());

    [this.voiceModal, this.previewModal, this.credModal].forEach(m => {
      m?.addEventListener('click', e => { 
        if (e.target === m) {
          m.classList.remove('open');
          if (m === this.voiceModal) this.cancelVoiceFlow();
        }
      });
    });

    // Escuchador global para el menú desplegable (Select)
    document.addEventListener('change', e => {
      if (!e.target.matches('.cred-select')) return;
      const idx = e.target.dataset.idx;
      const selectedOpt = e.target.options[e.target.selectedIndex];
      const manualWrap = document.getElementById(`credManualWrapper_${idx}`);
      
      if (manualWrap) {
        manualWrap.style.display = selectedOpt.dataset.type === 'manual' ? 'block' : 'none';
      }
    });
  }

  openVoiceModal() {
    this._resetVoiceUI();
    this.voiceModal?.classList.add('open');
  }

  cancelVoiceFlow() {
    if (this.isRecording) this.stopRecording();
    this.voiceModal?.classList.remove('open');
    this._releaseStream();
    this._resetVoiceUI();
  }

  hideVoiceModalSafely() {
    if (this.isRecording) this.stopRecording();
    this.voiceModal?.classList.remove('open');
    this._releaseStream();
  }

  closePreviewModal() {
    this.previewModal?.classList.remove('open');
  }

  _resetVoiceUI() {
    this.audioChunks    = [];
    this.transcriptText = '';
    this.generatedJson  = null;
    this.selectedCreds  = [];
    this.pendingCmdId   = null;
    this.isRecording    = false;
    this.voiceVisualizer?.classList.remove('is-recording');
    this._setStatus('Presiona para hablar', '');
    if (this.voiceTranscript) this.voiceTranscript.style.display = 'none';
    if (this.processBtn)      this.processBtn.style.display = 'none';
    if (this.manualGroup)     this.manualGroup.style.display = 'none';
    if (this.manualInput)     this.manualInput.value = '';
    _featherReplace();
  }

  async toggleRecording() {
    this.isRecording ? this.stopRecording() : await this.startRecording();
  }

  async startRecording() {
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.mediaRecorder = new MediaRecorder(this.stream);
      this.audioChunks   = [];
      this.mediaRecorder.ondataavailable = e => { if (e.data.size > 0) this.audioChunks.push(e.data); };
      this.mediaRecorder.onstop = () => this._onRecordingStop();
      this.mediaRecorder.start(250);
      this.isRecording = true;
      this.voiceVisualizer?.classList.add('is-recording');
      this._setStatus('Escuchando... (presiona para detener)', 'recording');
    } catch {
      this._setStatus('Permisos de micrófono denegados', '');
      if (this.manualGroup) this.manualGroup.style.display = 'block';
      if (this.processBtn)  this.processBtn.style.display = 'inline-flex';
      showToast('Micrófono no disponible.', 'warning');
      _featherReplace();
    }
  }

  stopRecording() {
    if (this.mediaRecorder?.state !== 'inactive') this.mediaRecorder?.stop();
    this.isRecording = false;
    this.voiceVisualizer?.classList.remove('is-recording');
    this._setStatus('Procesando audio...', 'processing');
  }

  async _onRecordingStop() {
    if (!this.audioChunks.length) return;
    const blob = new Blob(this.audioChunks, { type: 'audio/webm' });
    this._releaseStream();
    await this._transcribeAudio(blob);
  }

  _releaseStream() {
    this.stream?.getTracks().forEach(t => t.stop());
    this.stream = null;
  }

  async _transcribeAudio(blob) {
    showLoading('Transcribiendo audio con Whisper...');
    try {
      const fd = new FormData();
      fd.append('audio', blob, 'command.webm');
      const res  = await apiFetch('/api/voice/transcribe', { method: 'POST', body: fd });
      const data = await res.json();
      hideLoading();

      if (!res?.ok || !data.text) {
        showToast(data?.detail || 'Error en transcripción', 'error');
        return;
      }

      this.transcriptText = data.text;
      this.pendingCmdId   = data.command_id;
      if (this.transcriptEl) this.transcriptEl.textContent = data.text;
      if (this.voiceTranscript) this.voiceTranscript.style.display = 'block';
      if (this.processBtn) this.processBtn.style.display = 'inline-flex';
      this._setStatus('Transcripción lista. Analizando...', '');
      _featherReplace();

      await this._analyzeCredentials(data.text);
    } catch (err) {
      hideLoading();
      showToast('Error al transcribir', 'error');
    }
  }

  async _analyzeCredentials(text) {
    showLoading('Analizando y buscando en tu Bóveda...');
    try {
      // Pedimos el análisis de IA y la lista de TODAS tus credenciales al mismo tiempo
      const [analysisRes, credsRes] = await Promise.all([
        apiFetch('/api/voice/analyze', { method: 'POST', body: JSON.stringify({ text }) }),
        apiFetch('/api/credentials/list')
      ]);
      
      const data = await analysisRes.json();
      
      if (credsRes && credsRes.ok) {
        const credsData = await credsRes.json();
        this.allUserCreds = credsData.credentials || [];
      } else {
        this.allUserCreds = [];
      }

      hideLoading();

      if (!analysisRes?.ok) {
        showToast('Procediendo sin credenciales auto-inyectadas.', 'warning');
        return;
      }

      this.analysisData = data;

      if (data.needs_interaction) {
        this.hideVoiceModalSafely(); 
        this._openCredModal(data);
      } else {
        this.selectedCreds = data.auto_selected || [];
        this._setStatus('Listo para generar ✓', '');
      }
    } catch (err) {
      hideLoading();
    }
  }

  async processCommand() {
    const text = this.transcriptText || this.manualInput?.value?.trim();
    if (!text) { showToast('Ingresa un comando primero', 'warning'); return; }

    if (!this.analysisData && !this.transcriptText) {
      this.transcriptText = text;
      await this._analyzeCredentials(text);
      if (this.analysisData?.needs_interaction) return; 
    }

    await this._generateFlow(text, this.selectedCreds);
  }

  async _generateFlow(text, selectedCreds = []) {
    showLoading('Generando estructura en n8n...');
    this.hideVoiceModalSafely(); 
    try {
      const res  = await apiFetch('/api/voice/generate-flow', {
        method: 'POST',
        body: JSON.stringify({
          text: text,
          selected_credentials: selectedCreds,
          command_id: this.pendingCmdId,
        }),
      });
      const data = await res.json();
      hideLoading();

      if (!res?.ok) { showToast(data?.detail || 'Error de la IA al crear JSON', 'error'); return; }

      this.generatedJson = data.workflow_json;
      this.selectedCreds = data.selected_credentials || selectedCreds;
      this._openPreviewModal(text, data);
    } catch (err) {
      hideLoading();
      showToast('Error de conexión', 'error');
    }
  }

  _openCredModal(analysisData) {
    const modal = this.credModal;
    if (!modal) return;

    const container = document.getElementById('credSlotsContainer');
    const assignments = analysisData.credential_assignments || [];
    
    // Inyectamos el HTML construido desde cero
    container.innerHTML = assignments.map((a, idx) => this._renderCredSlot(a, idx)).join('');

    const confirmBtn = document.getElementById('confirmCredSelection');
    if (confirmBtn) {
      confirmBtn.onclick = () => {
        const selections = this._collectCredSelections(container, assignments);
        if (!selections) return; // Validación falló
        
        modal.classList.remove('open');
        this.selectedCreds = selections;
        this._generateFlow(
          this.transcriptText || this.manualInput?.value?.trim() || '',
          selections
        );
      };
    }

    document.getElementById('cancelCredSelection').onclick = () => modal.classList.remove('open');
    document.getElementById('cancelCredSelection2').onclick = () => modal.classList.remove('open');

    modal.classList.add('open');
    _featherReplace();
  }

  _renderCredSlot(assignment, idx) {
    const { credential_type, credential_label, node_name, purpose, status, matches } = assignment;
    const statusIcon = status === 'found' ? '✅' : (status === 'multiple' ? '⚡' : '⚠️');
    const statusColor = status === 'found' ? 'var(--green)' : (status === 'multiple' ? 'var(--amber)' : 'var(--red)');

    // 1. Opciones sugeridas por la IA
    const suggestedOpts = (matches || []).map(m => 
      `<option value="${m.id}" data-type="stored" data-name="${escapeHtml(m.name)}">⭐ Detectada: ${escapeHtml(m.name)}</option>`
    ).join('');

    // 2. TODAS tus demás opciones guardadas en la bóveda (Filtramos para no duplicar las sugeridas)
    const suggestedIds = (matches || []).map(m => String(m.id));
    const otherOpts = this.allUserCreds
      .filter(c => !suggestedIds.includes(String(c.id_credencial)))
      .map(c => `<option value="${c.id_credencial}" data-type="stored" data-name="${escapeHtml(c.nombre_app)}">🔑 ${escapeHtml(c.nombre_app)} (${c.origen})</option>`)
      .join('');

    return `
      <div class="cred-slot" style="margin-bottom:16px; background:var(--bg-elevated); border:1px solid var(--border-bright); border-radius:var(--radius-lg); padding:16px;">
        
        <!-- Cabecera de la credencial -->
        <div style="display:flex; gap:12px; margin-bottom:16px;">
          <div style="font-size:20px;">${statusIcon}</div>
          <div>
            <div style="color:${statusColor}; font-weight:bold; font-family:var(--font-display); font-size:15px;">${escapeHtml(credential_label)}</div>
            <div style="font-size:12px; color:var(--text-muted); margin-top:2px;">${escapeHtml(node_name)} · ${escapeHtml(purpose)}</div>
          </div>
        </div>
        
        <!-- EL SELECTOR UNIVERSAL -->
        <label style="font-size:12px; color:var(--text-secondary); display:block; margin-bottom:8px;">Selecciona qué credencial conectar:</label>
        <select class="form-control cred-select" data-idx="${idx}">
          ${suggestedOpts ? `<optgroup label="Sugerencias de la IA">${suggestedOpts}</optgroup>` : ''}
          ${otherOpts ? `<optgroup label="Tu Bóveda de Credenciales">${otherOpts}</optgroup>` : ''}
          <optgroup label="Opciones manuales">
            <option value="skip" data-type="skip" ${!suggestedOpts ? 'selected' : ''}>⏭️ Omitir (Crear nodo sin credencial por ahora)</option>
            <option value="manual" data-type="manual">📝 Quiero escribir el nombre exacto de n8n</option>
          </optgroup>
        </select>
        
        <!-- Input de texto que solo sale si escoges "Escribir nombre exacto" -->
        <div id="credManualWrapper_${idx}" style="display:none; margin-top:12px; padding:12px; background:rgba(0,0,0,0.2); border-radius:var(--radius); border:1px dashed var(--border-bright);">
          <label style="font-size:11px; color:var(--text-muted); margin-bottom:6px; display:block;">Nombre exacto configurado en n8n:</label>
          <input type="text" class="form-control cred-manual-input" id="credManual_${idx}" placeholder="Ej. Mi Telegram Bot">
        </div>

      </div>
    `;
  }

  _collectCredSelections(container, assignments) {
    const result = [];
    
    for (let idx = 0; idx < assignments.length; idx++) {
      const a = assignments[idx];
      const selectEl = container.querySelector(`.cred-select[data-idx="${idx}"]`);
      if (!selectEl) continue;

      const selectedOpt = selectEl.options[selectEl.selectedIndex];
      const dataType = selectedOpt.dataset.type;
      const val = selectEl.value;

      if (dataType === 'stored') {
        result.push({
          node_type: a.node_type,
          credential_type: a.credential_type,
          credential_label: a.credential_label,
          mode: 'use_stored',
          db_credential_id: parseInt(val),
          credential_name: selectedOpt.dataset.name
        });
      } else if (dataType === 'manual') {
        const manualVal = document.getElementById(`credManual_${idx}`)?.value?.trim();
        if (!manualVal) {
          showToast(`Ingresa el nombre manual para ${a.credential_label}`, 'warning');
          return null; // Detenemos la recolección si faltan datos
        }
        result.push({
          node_type: a.node_type,
          credential_type: a.credential_type,
          credential_label: a.credential_label,
          mode: 'manual_name',
          manual_name: manualVal,
          credential_name: manualVal
        });
      } else {
        result.push({
          node_type: a.node_type,
          credential_type: a.credential_type,
          credential_label: a.credential_label,
          mode: 'skip',
          credential_name: ''
        });
      }
    }
    return result;
  }

  _openPreviewModal(command, data) {
    document.getElementById('previewCommand').textContent = `"${command.substring(0, 120)}${command.length > 120 ? '…' : ''}"`;
    const nodesWrap = document.getElementById('nodesPreview');
    nodesWrap.innerHTML = '';
    (data.nodes || []).forEach(n => {
      const chip = document.createElement('div');
      chip.className = 'node-chip';
      chip.innerHTML = `<div class="node-chip-icon">${(n.name || 'N')[0].toUpperCase()}</div><span>${escapeHtml(n.name || n.type || 'Nodo')}</span>`;
      nodesWrap.appendChild(chip);
    });

    document.getElementById('jsonPreviewCode').textContent = JSON.stringify(this.generatedJson, null, 2);
    document.getElementById('confirmDeploy').style.display = '';
    this.previewModal?.classList.add('open');
    _featherReplace();
  }

  async deployFlow() {
    if (!this.generatedJson) return;
    showLoading('Desplegando flujo en n8n...');
    this.previewModal?.classList.remove('open');
    try {
      const res  = await apiFetch('/api/workflows/deploy', {
        method: 'POST',
        body: JSON.stringify({
          workflow_json: this.generatedJson,
          selected_credentials: this.selectedCreds,
        }),
      });
      const data = await res.json();
      hideLoading();

      if (!res?.ok) { showToast(data?.detail || 'Error al desplegar', 'error'); return; }
      showToast(`✓ Flujo "${data.name || 'Nuevo'}" desplegado con éxito`, 'success', 5000);
      if (typeof loadWorkflows  === 'function') loadWorkflows();
    } catch {
      hideLoading();
      showToast('Error de conexión', 'error');
    }
  }

  toggleManualMode() {
    const visible = this.manualGroup?.style.display !== 'none';
    if (this.manualGroup) this.manualGroup.style.display = visible ? 'none' : 'block';
    if (this.processBtn)  this.processBtn.style.display  = visible ? 'none' : 'inline-flex';
    _featherReplace();
  }

  _setStatus(msg, cls) {
    if (!this.voiceStatus) return;
    this.voiceStatus.textContent = msg;
    this.voiceStatus.className   = `voice-status ${cls}`;
  }
}

function _featherReplace() {
  if (typeof feather !== 'undefined') feather.replace();
}