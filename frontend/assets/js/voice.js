/**
 * ClawFlow — VoiceController (Anti-Amnesia + Select Fix)
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

    this._bindEvents();
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
    // NUEVO: Oculta la ventana SIN borrar el texto (Evita Error 422)
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
    showLoading('Analizando requerimientos de IA...');
    try {
      const res  = await apiFetch('/api/voice/analyze', {
        method: 'POST',
        body: JSON.stringify({ text }),
      });
      const data = await res.json();
      hideLoading();

      if (!res?.ok) {
        showToast('Procediendo sin credenciales auto-inyectadas.', 'warning');
        return;
      }

      this.analysisData = data;

      if (data.needs_interaction) {
        this.hideVoiceModalSafely(); // <-- AQUÍ SE EVITA EL BORRADO DE TEXTO
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

      if (!res?.ok) { showToast(data?.detail || 'Error de la IA', 'error'); return; }

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
    container.innerHTML = assignments.map((a, idx) => this._renderCredSlot(a, idx)).join('');

    // Prevenir duplicación de eventos de click
    const confirmBtn = document.getElementById('confirmCredSelection');
    if (confirmBtn) {
      confirmBtn.onclick = () => {
        const selections = this._collectCredSelections(container, assignments);
        if (!selections) return; 
        modal.classList.remove('open');
        this.selectedCreds = selections;
        
        // Enviamos el texto que mantuvimos a salvo
        this._generateFlow(
          this.transcriptText || this.manualInput?.value?.trim() || '',
          selections,
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
    const statusIcon = { found: '✅', multiple: '⚡', not_found: '⚠️' }[status] || '❓';
    const statusColor = { found: 'var(--green)', multiple: 'var(--amber)', not_found: 'var(--red)' }[status];

    let contentHtml = '';

    if (status === 'found') {
      contentHtml = `
        <input type="hidden" class="cred-mode" data-idx="${idx}" value="use_stored">
        <input type="hidden" class="cred-db-id" data-idx="${idx}" value="${matches[0].id}">
        <div class="cred-auto-badge">
          <span style="color:var(--green)">✓ Auto-seleccionada:</span>
          <strong>${escapeHtml(matches[0].name)}</strong>
        </div>`;
    } else if (status === 'multiple') {
      const options = matches.map((m, mi) => `<option value="${m.id}" data-name="${escapeHtml(m.name)}" ${mi === 0 ? 'selected' : ''}>${escapeHtml(m.name)}</option>`).join('');
      contentHtml = `
        <input type="hidden" class="cred-mode" data-idx="${idx}" value="use_stored">
        <input type="hidden" class="cred-db-id" data-idx="${idx}" value="${matches[0].id}">
        <input type="hidden" class="cred-name" data-idx="${idx}" value="${escapeHtml(matches[0].name)}">
        <p class="text-muted" style="font-size:12px;margin-bottom:10px">Selecciona qué credencial usar:</p>
        <select class="form-control cred-select" data-idx="${idx}" style="margin-bottom: 10px;">
            ${options}
            <option value="manual">-- Usar nombre manual en n8n --</option>
        </select>
        <div id="credManualWrapper_${idx}" style="display:none; margin-top: 10px;">
          <input type="text" class="form-control cred-manual-input" id="credManual_${idx}" placeholder="Nombre exacto en n8n...">
        </div>`;
    } else {
      contentHtml = `
        <input type="hidden" class="cred-mode" data-idx="${idx}" value="skip">
        <div class="cred-not-found-info">
          <p style="font-size:13px;color:var(--amber);margin-bottom:10px">No tienes esta credencial guardada.</p>
          <div class="cred-option-tabs">
            <button class="cred-opt-btn active" data-opt="skip" data-idx="${idx}">⏭️ Omitir credencial (Añadir en n8n luego)</button>
            <button class="cred-opt-btn" data-opt="manual" data-idx="${idx}">📝 Tengo el nombre en n8n</button>
          </div>
          <div class="cred-opt-panel" id="credOpt_manual_${idx}" style="display:none">
            <input type="text" class="form-control cred-manual-input" id="credManualNotFound_${idx}" placeholder="Nombre en n8n..." data-idx="${idx}" style="margin-top:10px">
          </div>
        </div>`;
    }

    return `
      <div class="cred-slot" data-idx="${idx}" data-cred-type="${escapeHtml(credential_type)}" data-node-type="${escapeHtml(assignment.node_type)}">
        <div class="cred-slot-header">
          <div class="cred-slot-info">
            <span style="font-size:18px">${statusIcon}</span>
            <div>
              <div class="cred-slot-label" style="color:${statusColor}">${escapeHtml(credential_label)}</div>
              <div class="cred-slot-node text-muted">${escapeHtml(node_name)}</div>
            </div>
          </div>
        </div>
        <div class="cred-slot-body">${contentHtml}</div>
      </div>`;
  }

  _collectCredSelections(container, assignments) {
    const result = [];
    for (let idx = 0; idx < assignments.length; idx++) {
      const a = assignments[idx];
      const slot = container.querySelector(`.cred-slot[data-idx="${idx}"]`);
      if (!slot) continue;

      const modeEl = slot.querySelector(`.cred-mode[data-idx="${idx}"]`);
      const dbIdEl = slot.querySelector(`.cred-db-id[data-idx="${idx}"]`);

      if (a.status === 'found') {
        result.push({ node_type: a.node_type, credential_type: a.credential_type, credential_label: a.credential_label, mode: 'use_stored', db_credential_id: parseInt(dbIdEl?.value || '0'), credential_name: a.matches[0].name });
      } else if (a.status === 'multiple') {
        const selectEl = slot.querySelector(`.cred-select[data-idx="${idx}"]`);
        if (selectEl?.value === 'manual') {
          const manualVal = slot.querySelector(`#credManual_${idx}`)?.value?.trim();
          if (!manualVal) { showToast(`Ingresa el nombre manual para ${a.credential_label}`, 'warning'); return null; }
          result.push({ node_type: a.node_type, credential_type: a.credential_type, credential_label: a.credential_label, mode: 'manual_name', manual_name: manualVal, credential_name: manualVal });
        } else {
          const match = a.matches.find(m => String(m.id) === selectEl?.value);
          result.push({ node_type: a.node_type, credential_type: a.credential_type, credential_label: a.credential_label, mode: 'use_stored', db_credential_id: parseInt(selectEl?.value), credential_name: match?.name });
        }
      } else {
        const activeBtn = slot.querySelector('.cred-opt-btn.active');
        const opt = activeBtn?.dataset?.opt || 'skip';
        if (opt === 'manual') {
          const manualVal = slot.querySelector(`#credManualNotFound_${idx}`)?.value?.trim();
          if (manualVal) {
            result.push({ node_type: a.node_type, credential_type: a.credential_type, credential_label: a.credential_label, mode: 'manual_name', manual_name: manualVal, credential_name: manualVal });
          } else {
            result.push({ node_type: a.node_type, credential_type: a.credential_type, credential_label: a.credential_label, mode: 'skip', credential_name: '' });
          }
        } else {
          result.push({ node_type: a.node_type, credential_type: a.credential_type, credential_label: a.credential_label, mode: 'skip', credential_name: '' });
        }
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
    showLoading('Desplegando flujo...');
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
      showToast(`✓ Flujo "${data.name || 'Nuevo'}" desplegado`, 'success', 5000);
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

document.addEventListener('click', e => {
  if (!e.target.matches('.cred-opt-btn')) return;
  const idx = e.target.dataset.idx;
  const opt = e.target.dataset.opt;

  document.querySelectorAll(`.cred-opt-btn[data-idx="${idx}"]`).forEach(b => b.classList.remove('active'));
  e.target.classList.add('active');

  const panel = document.getElementById(`credOpt_manual_${idx}`);
  if (panel) panel.style.display = opt === 'manual' ? 'block' : 'none';

  const slot = e.target.closest('.cred-slot');
  if (slot) {
    const modeEl = slot.querySelector('.cred-mode');
    if (modeEl) modeEl.value = opt;
  }
});

document.addEventListener('change', e => {
  if (!e.target.matches('.cred-select')) return;
  const idx = e.target.dataset.idx;
  const manualWrap = document.getElementById(`credManualWrapper_${idx}`);
  if (manualWrap) manualWrap.style.display = e.target.value === 'manual' ? 'block' : 'none';

  const slot = e.target.closest('.cred-slot');
  if (slot) {
    const modeEl = slot.querySelector('.cred-mode');
    if (e.target.value === 'manual') {
      if (modeEl) modeEl.value = 'manual_name';
    } else {
      if (modeEl) modeEl.value = 'use_stored';
    }
  }
});

function _featherReplace() {
  if (typeof feather !== 'undefined') feather.replace();
}