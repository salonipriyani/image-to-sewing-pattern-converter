const uploadZone = document.getElementById('uploadZone');
const fileInput  = document.getElementById('fileInput');
const previewWrap = document.getElementById('previewWrap');
const previewImg  = document.getElementById('previewImg');
const btnRemove   = document.getElementById('btnRemove');
const btnGenerate = document.getElementById('btnGenerate');
const btnPDF      = document.getElementById('btnPDF');
const loadingState = document.getElementById('loadingState');
const loadingText  = document.getElementById('loadingText');
const loadingSub   = document.getElementById('loadingSub');
const results      = document.getElementById('results');
const errorBox     = document.getElementById('errorBox');

let selectedFile = null;
let pdfFilename  = null;

const LOADING_MESSAGES = [
  ["Analysing your garment...",       "Reading seams, silhouette & construction details"],
  ["Calculating pattern pieces...",   "Applying ease allowances to your measurements"],
  ["Drafting the pattern...",         "Adding markings, notches & grain lines"],
  ["Writing sewing instructions...",  "Ordering steps for your skill level"],
];

// ── File handling ─────────────────────────────────────────────────────────────

uploadZone.addEventListener('dragover', e => {
  e.preventDefault();
  uploadZone.classList.add('drag-over');
});

uploadZone.addEventListener('dragleave', () => {
  uploadZone.classList.remove('drag-over');
});

uploadZone.addEventListener('drop', e => {
  e.preventDefault();
  uploadZone.classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file) loadFile(file);
});

fileInput.addEventListener('change', e => {
  if (e.target.files[0]) loadFile(e.target.files[0]);
});

function loadFile(file) {
  selectedFile = file;
  const reader = new FileReader();
  reader.onload = e => {
    previewImg.src = e.target.result;
    previewWrap.classList.add('visible');
    uploadZone.style.display = 'none';
  };
  reader.readAsDataURL(file);
}

btnRemove.addEventListener('click', () => {
  selectedFile = null;
  pdfFilename  = null;
  previewImg.src = '';
  previewWrap.classList.remove('visible');
  uploadZone.style.display = '';
  fileInput.value = '';
  results.classList.remove('visible');
  errorBox.classList.remove('visible');
});

// ── Generate ──────────────────────────────────────────────────────────────────

btnGenerate.addEventListener('click', generate);

async function generate() {
  if (!selectedFile) {
    showError('Please upload a garment image or sketch first.');
    return;
  }

  const measurements = ['bust', 'waist', 'hips', 'height', 'shoulder_width'];
  for (const m of measurements) {
    if (!document.getElementById(m).value) {
      showError(`Please enter your ${m.replace('_', ' ')} measurement.`);
      return;
    }
  }

  errorBox.classList.remove('visible');
  results.classList.remove('visible');
  loadingState.classList.add('visible');
  btnGenerate.disabled = true;

  // Cycle loading messages
  let msgIdx = 0;
  const msgInterval = setInterval(() => {
    msgIdx = (msgIdx + 1) % LOADING_MESSAGES.length;
    loadingText.textContent = LOADING_MESSAGES[msgIdx][0];
    loadingSub.textContent  = LOADING_MESSAGES[msgIdx][1];
  }, 3000);

  // Build multipart form data
  const formData = new FormData();
  formData.append('image', selectedFile);
  formData.append('bust',           document.getElementById('bust').value);
  formData.append('waist',          document.getElementById('waist').value);
  formData.append('hips',           document.getElementById('hips').value);
  formData.append('height',         document.getElementById('height').value);
  formData.append('shoulder_width', document.getElementById('shoulder_width').value);
  formData.append('skill_level',    document.getElementById('skill_level').value);

  try {
    const response = await fetch('/api/v1/generate', {
      method: 'POST',
      body: formData,
    });

    clearInterval(msgInterval);

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || 'Generation failed');
    }

    const data = await response.json();
    renderResults(data);

  } catch (err) {
    clearInterval(msgInterval);
    loadingState.classList.remove('visible');
    btnGenerate.disabled = false;
    showError(`Something went wrong: ${err.message}`);
  }
}

// ── Render results ────────────────────────────────────────────────────────────

function renderResults(data) {
  loadingState.classList.remove('visible');
  btnGenerate.disabled = false;

  // Analysis
  document.getElementById('analysisBody').innerHTML = `
    <p>${data.fabric_recommendation}</p>
    <div class="meta-row">
      <div class="meta-item">
        <span class="meta-label">Garment</span>
        <span class="meta-value">${data.garment_type}</span>
      </div>
      <div class="meta-item">
        <span class="meta-label">Silhouette</span>
        <span class="meta-value">${data.silhouette}</span>
      </div>
      <div class="meta-item">
        <span class="meta-label">Difficulty</span>
        <span class="meta-value">${data.estimated_difficulty}</span>
      </div>
    </div>
    <div style="margin-top:14px;display:flex;flex-wrap:wrap;gap:6px;">
      ${data.construction_details.map(d =>
        `<span style="font-size:10px;background:var(--sepia-faint);padding:3px 8px;border-radius:2px;color:#6b5a3e;">${d}</span>`
      ).join('')}
    </div>
  `;

  // Pattern pieces
  document.getElementById('piecesBody').innerHTML = data.pattern_pieces.map(p => `
    <div class="pattern-piece">
      <span class="piece-num">${p.id}</span>
      <div>
        <div class="piece-name">${p.name} <span style="color:var(--sepia);font-weight:300;">× ${p.quantity}</span></div>
        <div class="piece-meta">${p.width_cm} × ${p.height_cm} cm &nbsp;·&nbsp; SA: ${p.seam_allowance_cm} cm &nbsp;·&nbsp; ${p.notes}</div>
        ${p.markings.length ? `<ul class="piece-markings">${p.markings.map(m => `<li>${m}</li>`).join('')}</ul>` : ''}
      </div>
    </div>
  `).join('');

  // Steps
  document.getElementById('instructionsBody').innerHTML = data.sewing_steps.map(s => `
    <div class="step">
      <span class="step-num">${s.step_number}</span>
      <div>
        <div class="step-title">${s.title}</div>
        <div>${s.instruction}</div>
        ${s.tip ? `<div class="step-tip">✦ ${s.tip}</div>` : ''}
      </div>
    </div>
  `).join('');

  // Materials
  document.getElementById('materialsBody').innerHTML = `
    <ul class="materials-list">
      ${data.materials_list.map(m => `<li>${m}</li>`).join('')}
    </ul>
  `;

  // Store PDF filename for download
  pdfFilename = data.pdf_path.split('/').pop();

  results.classList.add('visible');
  results.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ── PDF download ──────────────────────────────────────────────────────────────

btnPDF.addEventListener('click', () => {
  if (!pdfFilename) return;
  window.location.href = `/api/v1/download/${pdfFilename}`;
});

// ── Helpers ───────────────────────────────────────────────────────────────────

function showError(message) {
  errorBox.textContent = message;
  errorBox.classList.add('visible');
  errorBox.scrollIntoView({ behavior: 'smooth' });
}