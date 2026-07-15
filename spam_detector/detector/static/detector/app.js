/**
 * SpamShield AI — app.js
 * AJAX prediction, file-drop drag & drop, UI state management
 */

(function () {
  'use strict';

  /* ── DOM Refs ──────────────────────────────────────────────────────────── */
  const textarea     = document.getElementById('message-input');
  const btnPredict   = document.getElementById('btn-predict');
  const btnClear     = document.getElementById('btn-clear');
  const resultPanel  = document.getElementById('result-panel');
  const resultVerdict= document.getElementById('result-verdict');
  const confidenceVal= document.getElementById('confidence-val');
  const confidenceFill=document.getElementById('confidence-fill');
  const spamProbVal  = document.getElementById('spam-prob-val');
  const hamProbVal   = document.getElementById('ham-prob-val');
  const fileInput    = document.getElementById('file-input');
  const fileDropZone = document.getElementById('file-drop-zone');
  const fileDropText = document.getElementById('file-drop-text');
  const btnBatch     = document.getElementById('btn-batch-submit');

  /* ── Predict ───────────────────────────────────────────────────────────── */
  if (btnPredict) {
    btnPredict.addEventListener('click', runPredict);
    textarea && textarea.addEventListener('keydown', (e) => {
      if (e.ctrlKey && e.key === 'Enter') runPredict();
    });
  }

  async function runPredict() {
    const text = textarea ? textarea.value.trim() : '';
    if (!text) {
      showError('Please enter some text to analyze.');
      return;
    }
    if (text.length < 5) {
      showError('Text too short. Please enter at least 5 characters.');
      return;
    }

    setLoading(true);

    try {
      const res = await fetch(window.PREDICT_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': window.CSRF_TOKEN,
        },
        body: JSON.stringify({ text }),
      });

      const data = await res.json();

      if (!res.ok || data.error) {
        showError(data.error || 'Prediction failed. Please try again.');
        return;
      }

      displayResult(data);
    } catch (err) {
      showError('Network error. Is the server running?');
      console.error('Predict error:', err);
    } finally {
      setLoading(false);
    }
  }

  function displayResult(data) {
    if (!resultPanel) return;

    const isSpam = data.label === 'spam';

    // Verdict text
    resultVerdict.textContent = isSpam
      ? `🚫 SPAM — Confidence: ${data.confidence}%`
      : `✅ HAM (Clean) — Confidence: ${data.confidence}%`;

    // Panel class
    resultPanel.classList.remove('hidden', 'spam-result', 'ham-result');
    resultPanel.classList.add(isSpam ? 'spam-result' : 'ham-result');

    // Confidence bar (animate after paint)
    if (confidenceVal) confidenceVal.textContent = `${data.confidence}%`;
    if (confidenceFill) {
      confidenceFill.style.width = '0%';
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          confidenceFill.style.width = `${data.confidence}%`;
        });
      });
    }

    // Probabilities
    if (spamProbVal) spamProbVal.textContent = `${data.spam_prob}%`;
    if (hamProbVal)  hamProbVal.textContent  = `${data.ham_prob}%`;

    // Scroll into view
    resultPanel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function setLoading(active) {
    if (!btnPredict) return;
    if (active) {
      btnPredict.classList.add('loading');
      btnPredict.disabled = true;
    } else {
      btnPredict.classList.remove('loading');
      btnPredict.disabled = false;
    }
  }

  /* ── Clear button ──────────────────────────────────────────────────────── */
  if (btnClear) {
    btnClear.addEventListener('click', () => {
      if (textarea) textarea.value = '';
      if (resultPanel) resultPanel.classList.add('hidden');
      const charCount = document.getElementById('char-count');
      if (charCount) charCount.textContent = '0 characters';
      textarea && textarea.focus();
    });
  }

  /* ── File Drop Zone ────────────────────────────────────────────────────── */
  if (fileDropZone && fileInput) {

    fileInput.addEventListener('change', () => {
      const file = fileInput.files[0];
      if (file) {
        if (fileDropText) fileDropText.textContent = `✅ ${file.name} (${formatBytes(file.size)})`;
        if (btnBatch) btnBatch.disabled = false;
      }
    });

    fileDropZone.addEventListener('dragover', (e) => {
      e.preventDefault();
      fileDropZone.classList.add('drag-over');
    });
    fileDropZone.addEventListener('dragleave', () => {
      fileDropZone.classList.remove('drag-over');
    });
    fileDropZone.addEventListener('drop', (e) => {
      e.preventDefault();
      fileDropZone.classList.remove('drag-over');
      const file = e.dataTransfer.files[0];
      if (file && file.name.endsWith('.txt')) {
        const dt = new DataTransfer();
        dt.items.add(file);
        fileInput.files = dt.files;
        if (fileDropText) fileDropText.textContent = `✅ ${file.name} (${formatBytes(file.size)})`;
        if (btnBatch) btnBatch.disabled = false;
      } else {
        showError('Please drop a .txt file.');
      }
    });
  }

  /* ── Auto-dismiss toasts ───────────────────────────────────────────────── */
  document.querySelectorAll('.toast').forEach((toast) => {
    setTimeout(() => toast.remove(), 5000);
  });

  /* ── Helpers ───────────────────────────────────────────────────────────── */
  function showError(msg) {
    const container = document.querySelector('.toast-container') || createToastContainer();
    const toast = document.createElement('div');
    toast.className = 'toast toast-error';
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
      <span class="toast-icon">❌</span>
      <span class="toast-text">${escapeHtml(msg)}</span>
      <button class="toast-close" onclick="this.parentElement.remove()" aria-label="Close">×</button>
    `;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 5000);
  }

  function createToastContainer() {
    const c = document.createElement('div');
    c.className = 'toast-container';
    document.body.appendChild(c);
    return c;
  }

  function escapeHtml(str) {
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function formatBytes(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1048576).toFixed(1)} MB`;
  }

})();
