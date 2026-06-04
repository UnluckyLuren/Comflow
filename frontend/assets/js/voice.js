/**
 * ClawFlow — VoiceController  (v2)
 *
 * Flow:
 *  1. Record / type command
 *  2. Transcribe  (POST /api/voice/transcribe)
 *  3. Analyze     (POST /api/voice/analyze)      ← NEW
 *     a. All found, 1:1 → auto-proceed
 *     b. Multiple or missing → show CredentialSelectionModal
 *  4. Generate    (POST /api/voice/generate-flow) with selected credentials
 *  5. Preview modal
 *  6. Deploy      (POST /api/workflows/deploy)   with selected credentials
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

    // Modal elements
    this.voiceModal    = document.getElementById('voiceModal');
    this.previewModal  = document.getElementById('previewModal');
    this.credModal     = document.getElementById('credSelectionModal');

    // Voice UI elements
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

    // Close buttons
    this.closeVoice   = document.getElementById('closeVoiceModal');
    this.closePreview = document.getElementById('closePreviewModal');
    this.cancelDeploy = document.getElementById('cancelDeploy');
    this.confirmDeploy= document.getElementById('confirmDeploy');

    this._bindEvents();
  }

  _bindEvents() {
    this.fabMic?.addEventListener('click', ()  => this.openVoiceModal());
    this.closeVoice?.addEventListener('click', () => this.closeVoiceModal());
    this.micBtn?.addEventListener('click',    () => this.toggleRecording());
    this.toggleManual?.addEventListener('click',()=> this.toggleManualMode());
    this.processBtn?.addEventListener('click', () => this.processCommand());
    this.closePreview?.addEventListener('click',()=> this.closePreviewModal());
    this.cancelDeploy?.addEventListener('click',()=> this.closePreviewModal());
    this.confirmDeploy?.addEventListener('click',()=> this.deployFlow());

    // Overlay click to close
    [this.voiceModal, this.previewModal, this.credModal].forEach(m => {
      m?.addEventListener('click', e => { if (e.target === m) m.classList.remove('open'); });
    });
  }

  // ── Voice Modal ──────────────────────────────────────────────────────────
  openVoiceModal() {
    this.voiceModal?.classList.add('open');
    this._resetVoiceUI();
  }

  closeVoiceModal() {
    if (this.isRecording) this.stopRecording();
    this.voiceModal?.classList.remove('open');
    this._releaseStream();
    this._resetVoiceUI();
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

  // ── Recording ────────────────────────────────────────────────────────────
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
      showToast('Micrófono no disponible. Usa la entrada manual.', 'warning');
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

  // ── Step 1: Transcribe ────────────────────────────────────────────────────
  async _transcribeAudio(blob) {
    showLoading('Transcribiendo audio con Whisper...');
    try {
      const fd = new FormData();
      fd.append('audio', blob, 'command.webm');
      const res  = await fetch('/api/voice/transcribe', { method: 'POST', credentials: 'include', body: fd });
      const data = await res.json();
      hideLoading();

      if (!res.ok || !data.text) {
        this._setStatus('No se reconoció voz. Intenta de nuevo.', '');
        showToast(data.detail || 'Error en transcripción', 'error');
        return;
      }

      this.transcriptText = data.text;
      this.pendingCmdId   = data.command_id;
      if (this.transcriptEl)          this.transcriptEl.textContent = data.text;
      if (this.voiceTranscript)       this.voiceTranscript.style.display = 'block';
      if (this.processBtn)            this.processBtn.style.display = 'inline-flex';
      this._setStatus('Transcripción lista. Analizando credenciales necesarias...', '');
      _featherReplace();

      // Auto-trigger analysis
      await this._analyzeCredentials(data.text);

    } catch (err) {
      hideLoading();
      showToast('Error de red al transcribir', 'error');
      this._setStatus('Error de conexión', '');
    }
  }

  // ── Step 1.5: Analyze Credentials ────────────────────────────────────────
  async _analyzeCredentials(text) {
    showLoading('Identificando credenciales necesarias con IA...');
    try {
      const res  = await apiFetch('/api/voice/analyze', {
        method: 'POST',
        body: JSON.stringify({ text }),
      });
      const data = await res.json();
      hideLoading();

      if (!res.ok) {
        // Non-fatal: proceed without credential injection
        showToast('No se pudo analizar credenciales. Procediendo sin ellas.', 'warning');
        this._setStatus('Transcripción lista ✓', '');
        return;
      }

      this.analysisData = data;

      if (data.needs_interaction) {
        // Show credential selection modal
        this.closeVoiceModal();
        this._openCredModal(data);
      } else {
        // Auto-proceed: all credentials were matched automatically
        this.selectedCreds = data.auto_selected || [];
        this._setStatus('Transcripción lista ✓', '');
        if (data.auto_message) {
          showToast(data.auto_message, 'info', 6000);
        }
      }
    } catch (err) {
      hideLoading();
      // Non-fatal
      this._setStatus('Transcripción lista ✓', '');
    }
  }

  // ── Step 2 (manual trigger): Process Command ──────────────────────────────
  async processCommand() {
    const text = this.transcriptText || this.manualInput?.value?.trim();
    if (!text) { showToast('Ingresa o dicta un comando primero', 'warning'); return; }

    // If coming from manual input (no analysis yet), run analysis first
    if (!this.analysisData && !this.transcriptText) {
      this.transcriptText = text;
      await this._analyzeCredentials(text);
      if (this.analysisData?.needs_interaction) return; // modal will handle it
    }

    await this._generateFlow(text, this.selectedCreds);
  }

  // ── Step 3: Generate Workflow JSON ────────────────────────────────────────
  async _generateFlow(text, selectedCreds = []) {
    showLoading('Generando flujo de trabajo con IA...');
    this.closeVoiceModal();
    try {
      const res  = await apiFetch('/api/voice/generate-flow', {
        method: 'POST',
        body: JSON.stringify({
          text,
          selected_credentials: selectedCreds,
          command_id: this.pendingCmdId,
        }),
      });
      const data = await res.json();
      hideLoading();

      if (!res.ok) { showToast(data.detail || 'Error al generar JSON', 'error'); return; }

      this.generatedJson = data.workflow_json;
      this.selectedCreds = data.selected_credentials || selectedCreds;
      this._openPreviewModal(text, data);

    } catch (err) {
      hideLoading();
      showToast('Error de conexión con el backend', 'error');
    }
  }

  // ── Credential Selection Modal ────────────────────────────────────────────
  _openCredModal(analysisData) {
    const modal = this.credModal;
    if (!modal) return;

    const container = document.getElementById('credSlotsContainer');
    if (!container) return;

    const assignments = analysisData.credential_assignments || [];
    container.innerHTML = assignments.map((a, idx) => this._renderCredSlot(a, idx)).join('');

    // Guidance toggles
    container.querySelectorAll('.guidance-toggle').forEach(btn => {
      btn.addEventListener('click', () => {
        const target = document.getElementById(btn.dataset.target);
        if (target) {
          const open = target.style.display !== 'none';
          target.style.display = open ? 'none' : 'block';
          btn.textContent = open ? '📖 Ver guía paso a paso' : '🔼 Ocultar guía';
        }
      });
    });

    // Update summary on change
    container.querySelectorAll('select, input[type="radio"], input[type="text"]').forEach(el => {
      el.addEventListener('change', () => this._updateCredSummary(container, assignments));
    });

    // Confirm button
    document.getElementById('confirmCredSelection')?.addEventListener('click', () => {
      const selections = this._collectCredSelections(container, assignments);
      if (!selections) return; // validation failed
      modal.classList.remove('open');
      this.selectedCreds = selections;
      this._generateFlow(
        this.transcriptText || this.manualInput?.value?.trim() || '',
        selections,
      );
    });

    document.getElementById('cancelCredSelection')?.addEventListener('click', () => {
      modal.classList.remove('open');
    });

    modal.classList.add('open');
    _featherReplace();
  }

  _renderCredSlot(assignment, idx) {
    const { credential_type, credential_label, node_name, purpose, status, matches, guidance, is_auto_creatable } = assignment;

    const statusIcon = { found: '✅', multiple: '⚡', not_found: '⚠️' }[status] || '❓';
    const statusColor = { found: 'var(--green)', multiple: 'var(--amber)', not_found: 'var(--red)' }[status];

    let contentHtml = '';

    if (status === 'found') {
      // Single match: auto-selected, show info
      const m = matches[0];
      contentHtml = `
        <input type="hidden" class="cred-mode" data-idx="${idx}" value="use_stored">
        <input type="hidden" class="cred-db-id" data-idx="${idx}" value="${m.id}">
        <input type="hidden" class="cred-name" data-idx="${idx}" value="${escapeHtml(m.name)}">
        <div class="cred-auto-badge">
          <span style="color:var(--green)">✓ Auto-seleccionada:</span>
          <strong>${escapeHtml(m.name)}</strong>
          <span class="badge badge-active" style="margin-left:8px">${m.estado}</span>
        </div>
      `;
    } else if (status === 'multiple') {
      // Multiple matches: radio buttons
      const radios = matches.map((m, mi) => `
        <label class="cred-radio-label">
          <input type="radio" name="cred_radio_${idx}" value="${m.id}" data-name="${escapeHtml(m.name)}"
                 class="cred-radio-btn" data-idx="${idx}" ${mi === 0 ? 'checked' : ''}>
          <span>${escapeHtml(m.name)}</span>
          <span class="badge badge-${m.estado === 'valida' ? 'active' : 'inactive'}">${m.estado}</span>
        </label>
      `).join('');
      contentHtml = `
        <input type="hidden" class="cred-mode" data-idx="${idx}" value="use_stored">
        <input type="hidden" class="cred-db-id" data-idx="${idx}" value="${matches[0].id}">
        <input type="hidden" class="cred-name" data-idx="${idx}" value="${escapeHtml(matches[0].name)}">
        <p class="text-muted" style="font-size:12px;margin-bottom:10px">Selecciona qué credencial usar para este nodo:</p>
        <div class="cred-radio-group">${radios}</div>
        <div style="margin-top:10px">
          <label class="cred-radio-label">
            <input type="radio" name="cred_radio_${idx}" value="manual" data-name="" class="cred-radio-btn" data-idx="${idx}">
            <span>Usar nombre manual de n8n</span>
          </label>
          <input type="text" class="form-control cred-manual-input" id="credManual_${idx}"
                 placeholder="Nombre exacto en n8n..." style="margin-top:6px;display:none">
        </div>
      `;
    } else {
      // Not found: input + guidance
      const guidanceSteps = guidance.map(s => `<li>${s}</li>`).join('');
      contentHtml = `
        <input type="hidden" class="cred-mode" data-idx="${idx}" value="skip">
        <input type="hidden" class="cred-db-id" data-idx="${idx}" value="">
        <input type="hidden" class="cred-name" data-idx="${idx}" value="">
        <div class="cred-not-found-info">
          <p style="font-size:13px;color:var(--amber);margin-bottom:10px">
            No tienes esta credencial en tu Bóveda. Tienes dos opciones:
          </p>
          <div class="cred-option-tabs">
            <button class="cred-opt-btn active" data-opt="manual" data-idx="${idx}">
              📝 Tengo la credencial en n8n
            </button>
            <button class="cred-opt-btn" data-opt="guide" data-idx="${idx}">
              📖 Necesito crearla
            </button>
            <button class="cred-opt-btn" data-opt="skip" data-idx="${idx}">
              ⏭️ Omitir
            </button>
          </div>
          <div class="cred-opt-panel" id="credOpt_manual_${idx}">
            <p class="text-muted" style="font-size:12px;margin:8px 0">
              Escribe el nombre <strong>exacto</strong> de la credencial como aparece en n8n:
            </p>
            <input type="text" class="form-control cred-manual-input" id="credManualNotFound_${idx}"
                   placeholder="Ej: Mi Gmail OAuth2" data-idx="${idx}">
          </div>
          <div class="cred-opt-panel" id="credOpt_guide_${idx}" style="display:none">
            <div class="cred-guidance-box">
              ${is_auto_creatable
                ? '<p class="text-muted" style="font-size:12px;margin-bottom:8px">Puedes agregar el token en la <strong>Bóveda de Credenciales</strong> y ClawFlow lo sincronizará automáticamente con n8n.</p>'
                : ''
              }
              <ol class="cred-guidance-list">${guidanceSteps}</ol>
              <div style="margin-top:10px">
                <label style="font-size:12px;color:var(--text-muted);display:block;margin-bottom:6px">
                  Escribe el nombre que le diste en n8n (después de crearlo):
                </label>
                <input type="text" class="form-control cred-manual-input" id="credManualAfterCreate_${idx}"
                       placeholder="Nombre de la credencial en n8n..." data-idx="${idx}">
              </div>
            </div>
          </div>
          <div class="cred-opt-panel" id="credOpt_skip_${idx}" style="display:none">
            <p style="font-size:12px;color:var(--text-muted);margin-top:8px">
              El nodo se creará sin credencial. Podrás asignarla manualmente en n8n.
            </p>
          </div>
        </div>
      `;
    }

    return `
      <div class="cred-slot" data-idx="${idx}" data-cred-type="${escapeHtml(credential_type)}"
           data-node-type="${escapeHtml(assignment.node_type)}">
        <div class="cred-slot-header">
          <div class="cred-slot-info">
            <span style="font-size:18px">${statusIcon}</span>
            <div>
              <div class="cred-slot-label" style="color:${statusColor}">
                ${escapeHtml(credential_label)}
              </div>
              <div class="cred-slot-node text-muted">${escapeHtml(node_name)} · ${escapeHtml(purpose)}</div>
            </div>
          </div>
        </div>
        <div class="cred-slot-body">${contentHtml}</div>
      </div>
    `;
  }

  _collectCredSelections(container, assignments) {
    const result = [];

    for (let idx = 0; idx < assignments.length; idx++) {
      const a       = assignments[idx];
      const slot    = container.querySelector(`.cred-slot[data-idx="${idx}"]`);
      if (!slot) continue;

      const modeEl  = slot.querySelector(`.cred-mode[data-idx="${idx}"]`);
      const dbIdEl  = slot.querySelector(`.cred-db-id[data-idx="${idx}"]`);
      const nameEl  = slot.querySelector(`.cred-name[data-idx="${idx}"]`);

      if (a.status === 'found') {
        result.push({
          node_type:        a.node_type,
          credential_type:  a.credential_type,
          credential_label: a.credential_label,
          mode:             'use_stored',
          db_credential_id: parseInt(dbIdEl?.value || '0') || null,
          credential_name:  nameEl?.value || a.credential_label,
        });

      } else if (a.status === 'multiple') {
        const checkedRadio = slot.querySelector(`input[name="cred_radio_${idx}"]:checked`);
        const radioVal     = checkedRadio?.value;
        if (radioVal === 'manual') {
          const manualVal = slot.querySelector(`#credManual_${idx}`)?.value?.trim();
          if (!manualVal) { showToast(`Escribe el nombre de la credencial para ${a.credential_label}`, 'warning'); return null; }
          result.push({
            node_type: a.node_type, credential_type: a.credential_type,
            credential_label: a.credential_label, mode: 'manual_name',
            manual_name: manualVal, credential_name: manualVal,
          });
        } else {
          const match = a.matches.find(m => String(m.id) === radioVal);
          result.push({
            node_type: a.node_type, credential_type: a.credential_type,
            credential_label: a.credential_label, mode: 'use_stored',
            db_credential_id: parseInt(radioVal) || null,
            credential_name: match?.name || a.credential_label,
          });
        }

      } else {
        // not_found: check which opt-tab is active
        const activeBtn = slot.querySelector('.cred-opt-btn.active');
        const opt       = activeBtn?.dataset?.opt || 'skip';

        if (opt === 'manual') {
          const manualVal = slot.querySelector(`#credManualNotFound_${idx}`)?.value?.trim();
          if (manualVal) {
            result.push({
              node_type: a.node_type, credential_type: a.credential_type,
              credential_label: a.credential_label, mode: 'manual_name',
              manual_name: manualVal, credential_name: manualVal,
            });
          } else {
            result.push({ node_type: a.node_type, credential_type: a.credential_type,
              credential_label: a.credential_label, mode: 'skip', credential_name: '' });
          }
        } else if (opt === 'guide') {
          const afterCreate = slot.querySelector(`#credManualAfterCreate_${idx}`)?.value?.trim();
          if (afterCreate) {
            result.push({
              node_type: a.node_type, credential_type: a.credential_type,
              credential_label: a.credential_label, mode: 'manual_name',
              manual_name: afterCreate, credential_name: afterCreate,
            });
          } else {
            result.push({ node_type: a.node_type, credential_type: a.credential_type,
              credential_label: a.credential_label, mode: 'skip', credential_name: '' });
          }
        } else {
          result.push({ node_type: a.node_type, credential_type: a.credential_type,
            credential_label: a.credential_label, mode: 'skip', credential_name: '' });
        }
      }
    }
    return result;
  }

  // ── Preview Modal ─────────────────────────────────────────────────────────
  _openPreviewModal(command, data) {
    document.getElementById('previewCommand').textContent =
      `"${command.substring(0, 120)}${command.length > 120 ? '…' : ''}"`;

    const nodesWrap = document.getElementById('nodesPreview');
    nodesWrap.innerHTML = '';
    (data.nodes || []).forEach(n => {
      const chip = document.createElement('div');
      chip.className = 'node-chip';
      chip.innerHTML = `<div class="node-chip-icon">${(n.name || 'N')[0].toUpperCase()}</div>
                        <span>${escapeHtml(n.name || n.type || 'Nodo')}</span>`;
      nodesWrap.appendChild(chip);
    });

    // Show which credentials were embedded
    const credBadges = (data.selected_credentials || [])
      .filter(c => c.mode !== 'skip' && c.credential_name)
      .map(c => `<span class="badge badge-active" style="margin:2px">🔑 ${escapeHtml(c.credential_label)}: ${escapeHtml(c.credential_name)}</span>`)
      .join('');
    const credWrap = document.getElementById('previewCredBadges');
    if (credWrap) credWrap.innerHTML = credBadges || '<span class="text-muted" style="font-size:12px">Sin credenciales asignadas</span>';

    document.getElementById('jsonPreviewCode').textContent =
      JSON.stringify(this.generatedJson, null, 2);

    document.getElementById('confirmDeploy').style.display = '';
    this.previewModal?.classList.add('open');
    _featherReplace();
  }

  // ── Deploy ────────────────────────────────────────────────────────────────
  async deployFlow() {
    if (!this.generatedJson) return;
    showLoading('Sincronizando credenciales y desplegando flujo en n8n...');
    this.previewModal?.classList.remove('open');
    try {
      const res  = await apiFetch('/api/workflows/deploy', {
        method: 'POST',
        body: JSON.stringify({
          workflow_json:        this.generatedJson,
          selected_credentials: this.selectedCreds,
        }),
      });
      const data = await res.json();
      hideLoading();

      if (!res.ok) { showToast(data.detail || 'Error al desplegar', 'error'); return; }
      showToast(`✓ Flujo "${data.name || 'Nuevo'}" desplegado y activo`, 'success', 5000);
      if (typeof loadDashboard  === 'function') loadDashboard();
      if (typeof loadWorkflows  === 'function') loadWorkflows();
    } catch {
      hideLoading();
      showToast('Error de conexión al desplegar', 'error');
    }
  }

  // ── Manual input mode ────────────────────────────────────────────────────
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


// ── Credential option tab switching (delegated) ───────────────────────────────
document.addEventListener('click', e => {
  if (!e.target.matches('.cred-opt-btn')) return;
  const idx = e.target.dataset.idx;
  const opt = e.target.dataset.opt;

  // Update active tab
  document.querySelectorAll(`.cred-opt-btn[data-idx="${idx}"]`).forEach(b => b.classList.remove('active'));
  e.target.classList.add('active');

  // Show/hide panels
  ['manual', 'guide', 'skip'].forEach(o => {
    const panel = document.getElementById(`credOpt_${o}_${idx}`);
    if (panel) panel.style.display = o === opt ? 'block' : 'none';
  });

  // Update hidden mode input
  const slot = e.target.closest('.cred-slot');
  if (slot) {
    const modeEl = slot.querySelector('.cred-mode');
    if (modeEl) modeEl.value = opt;
  }
});

// ── Multiple cred radio → show/hide manual input ──────────────────────────────
document.addEventListener('change', e => {
  if (!e.target.matches('.cred-radio-btn')) return;
  const idx       = e.target.dataset.idx;
  const manualInp = document.getElementById(`credManual_${idx}`);
  if (manualInp) manualInp.style.display = e.target.value === 'manual' ? 'block' : 'none';

  // Update hidden inputs
  const slot = e.target.closest('.cred-slot');
  if (slot) {
    const dbIdEl = slot.querySelector('.cred-db-id');
    const nameEl = slot.querySelector('.cred-name');
    const modeEl = slot.querySelector('.cred-mode');
    if (e.target.value === 'manual') {
      if (modeEl)  modeEl.value  = 'manual_name';
      if (dbIdEl)  dbIdEl.value  = '';
      if (nameEl)  nameEl.value  = '';
    } else {
      if (modeEl)  modeEl.value  = 'use_stored';
      if (dbIdEl)  dbIdEl.value  = e.target.value;
      if (nameEl)  nameEl.value  = e.target.dataset.name || '';
    }
  }
});

function _featherReplace() {
  if (typeof feather !== 'undefined') feather.replace();
}
