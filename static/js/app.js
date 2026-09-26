/**
 * AI Business Card Studio - Frontend Application
 */

const state = {
  sessionId: null,
  currentCard: null,
  attachedFile: null,
  currentView: 'both',
  isFlipped: false,
  apiKeyConfigured: false,
  activeCodeTab: 'css'
};

// DOM References
const chatForm = document.getElementById('chatForm');
const promptInput = document.getElementById('promptInput');
const sendBtn = document.getElementById('sendBtn');
const chatMessages = document.getElementById('chatMessages');
const attachImageBtn = document.getElementById('attachImageBtn');
const referenceImageInput = document.getElementById('referenceImageInput');
const imagePreviewBar = document.getElementById('imagePreviewBar');
const imagePreviewImg = document.getElementById('imagePreviewImg');
const previewFilename = document.getElementById('previewFilename');
const removeImageBtn = document.getElementById('removeImageBtn');

const sessionStatusText = document.getElementById('sessionStatusText');
const sessionIdPill = document.getElementById('sessionIdPill');
const newSessionBtn = document.getElementById('newSessionBtn');
const clearChatBtn = document.getElementById('clearChatBtn');

const frontSideCard = document.getElementById('frontSideCard');
const backSideCard = document.getElementById('backSideCard');
const flipFront = document.getElementById('flipFront');
const flipBack = document.getElementById('flipBack');
const flipInner = document.getElementById('flipInner');
const flipCardBtn = document.getElementById('flipCardBtn');
const dynamicCardStyles = document.getElementById('dynamicCardStyles');
const cardDisplayWrapper = document.getElementById('cardDisplayWrapper');

const cardTitleMeta = document.getElementById('cardTitleMeta');
const cardPaletteMeta = document.getElementById('cardPaletteMeta');

const downloadPngBtn = document.getElementById('downloadPngBtn');
const downloadPdfBtn = document.getElementById('downloadPdfBtn');
const copyCodeBtn = document.getElementById('copyCodeBtn');

// Key Modal References
const keyModal = document.getElementById('keyModal');
const openKeyModalBtn = document.getElementById('openKeyModalBtn');
const closeKeyModalBtn = document.getElementById('closeKeyModalBtn');
const cancelKeyModalBtn = document.getElementById('cancelKeyModalBtn');
const keyConfigForm = document.getElementById('keyConfigForm');
const apiKeyInput = document.getElementById('apiKeyInput');
const providerSelect = document.getElementById('providerSelect');
const navKeyStatus = document.getElementById('navKeyStatus');
const keyStatusBanner = document.getElementById('keyStatusBanner');
const keyStatusMsg = document.getElementById('keyStatusMsg');
const togglePwBtn = document.getElementById('togglePwBtn');

// Code Modal References
const codeModal = document.getElementById('codeModal');
const closeCodeModalBtn = document.getElementById('closeCodeModalBtn');
const codeViewArea = document.getElementById('codeViewArea');
const copyModalCodeBtn = document.getElementById('copyModalCodeBtn');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  setupEventListeners();
  checkApiKeyStatus();
  showEmptyCanvasState();
});

function setupEventListeners() {
  // Form submission
  chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    submitPrompt();
  });

  // Auto-resize prompt textarea & submit on Enter (without Shift)
  promptInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submitPrompt();
    }
  });

  promptInput.addEventListener('input', () => {
    promptInput.style.height = 'auto';
    promptInput.style.height = Math.min(promptInput.scrollHeight, 160) + 'px';
  });

  // File attachment
  attachImageBtn.addEventListener('click', () => referenceImageInput.click());
  referenceImageInput.addEventListener('change', handleFileSelected);
  removeImageBtn.addEventListener('click', clearAttachedFile);

  // New session & clear
  newSessionBtn.addEventListener('click', startNewSession);
  clearChatBtn.addEventListener('click', () => {
    chatMessages.innerHTML = '';
  });

  // Prompt chips
  document.querySelectorAll('.prompt-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      promptInput.value = chip.getAttribute('data-prompt');
      promptInput.focus();
      promptInput.style.height = Math.min(promptInput.scrollHeight, 160) + 'px';
    });
  });

  // View toggle tabs
  document.querySelectorAll('.view-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.view-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      setViewMode(tab.getAttribute('data-view'));
    });
  });

  // 3D Flip
  flipCardBtn.addEventListener('click', toggle3DFlip);

  // Downloads & Code
  downloadPngBtn.addEventListener('click', exportCardsAsPng);
  downloadPdfBtn.addEventListener('click', exportCardsAsPdf);
  copyCodeBtn.addEventListener('click', openCodeModal);

  // Session ID click to copy
  sessionIdPill.addEventListener('click', () => {
    if (state.sessionId) {
      navigator.clipboard.writeText(state.sessionId);
      alert('Session ID copied to clipboard: ' + state.sessionId);
    }
  });

  // Key Modal events
  openKeyModalBtn.addEventListener('click', openKeyModal);
  closeKeyModalBtn.addEventListener('click', () => keyModal.style.display = 'none');
  cancelKeyModalBtn.addEventListener('click', () => keyModal.style.display = 'none');
  keyConfigForm.addEventListener('submit', handleSaveKey);
  togglePwBtn.addEventListener('click', () => {
    const isPw = apiKeyInput.type === 'password';
    apiKeyInput.type = isPw ? 'text' : 'password';
    togglePwBtn.innerHTML = isPw ? '<i class="fa-solid fa-eye-slash"></i>' : '<i class="fa-solid fa-eye"></i>';
  });

  // Code Modal events
  closeCodeModalBtn.addEventListener('click', () => codeModal.style.display = 'none');
  document.querySelectorAll('.code-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.code-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      state.activeCodeTab = tab.getAttribute('data-tab');
      updateCodeViewContent();
    });
  });
  copyModalCodeBtn.addEventListener('click', () => {
    navigator.clipboard.writeText(codeViewArea.value);
    alert('Code copied to clipboard!');
  });
}

// ========================================================
// API KEY CHECK & CONFIGURATION
// ========================================================
async function checkApiKeyStatus() {
  try {
    const res = await fetch('/api/config/openai-key/');
    if (res.ok) {
      const data = await res.json();
      state.apiKeyConfigured = data.is_configured;
      if (data.is_configured) {
        navKeyStatus.textContent = `${data.provider.toUpperCase()} (${data.masked_key})`;
        keyStatusBanner.style.background = 'rgba(16, 185, 129, 0.15)';
        keyStatusBanner.style.borderColor = 'rgba(16, 185, 129, 0.4)';
        keyStatusMsg.textContent = `Active Key Configured: ${data.provider.toUpperCase()} (${data.masked_key})`;
      } else {
        navKeyStatus.textContent = 'Configure Key';
        keyStatusBanner.style.background = 'rgba(239, 68, 68, 0.15)';
        keyStatusBanner.style.borderColor = 'rgba(239, 68, 68, 0.4)';
        keyStatusBanner.style.color = '#f87171';
        keyStatusMsg.textContent = 'No custom API key active. (Using default executive engine).';
      }
    }
  } catch (err) {
    console.error('Error checking key status:', err);
  }
}

function openKeyModal() {
  keyModal.style.display = 'flex';
  checkApiKeyStatus();
}

async function handleSaveKey(e) {
  e.preventDefault();
  const key = apiKeyInput.value.trim();
  const provider = providerSelect.value;
  if (!key) return;

  try {
    const res = await fetch('/api/config/openai-key/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ api_key: key, provider: provider })
    });
    const data = await res.json();
    if (res.ok) {
      alert('AI Key configured successfully!');
      keyModal.style.display = 'none';
      checkApiKeyStatus();
    } else {
      alert('Error: ' + (data.error || 'Failed to save key'));
    }
  } catch (err) {
    alert('Failed to connect to server: ' + err.message);
  }
}

// ========================================================
// FILE ATTACHMENT HANDLER
// ========================================================
function handleFileSelected(e) {
  const file = e.target.files[0];
  if (!file) return;

  state.attachedFile = file;
  previewFilename.textContent = file.name;
  attachImageBtn.classList.add('has-file');

  const reader = new FileReader();
  reader.onload = (event) => {
    imagePreviewImg.src = event.target.result;
    imagePreviewBar.style.display = 'flex';
  };
  reader.readAsDataURL(file);
}

function clearAttachedFile() {
  state.attachedFile = null;
  referenceImageInput.value = '';
  imagePreviewBar.style.display = 'none';
  attachImageBtn.classList.remove('has-file');
}

// ========================================================
// CHAT & REDESIGN WORKFLOW
// ========================================================
async function submitPrompt() {
  const promptText = promptInput.value.trim();
  const file = state.attachedFile;

  if (!promptText && !file) return;

  // Render User Message
  appendUserMessage(promptText, file);

  // Clear inputs
  promptInput.value = '';
  promptInput.style.height = 'auto';
  clearAttachedFile();

  // Show typing indicator
  const typingIndicator = appendTypingIndicator();
  sendBtn.disabled = true;

  try {
    const isNew = isNewCardPrompt(promptText);
    if (isNew) {
      state.sessionId = null;
      sessionIdPill.style.display = 'none';
      sessionStatusText.textContent = 'New Card';
    }

    const formData = new FormData();
    if (promptText) formData.append('prompt', promptText);
    if (file) formData.append('reference_image', file);
    if (state.sessionId && !isNew) formData.append('session_id', state.sessionId);

    // If new card request or no active session, start fresh with /api/generate-card/
    const endpoint = (state.sessionId && !isNew) 
      ? `/api/generate-card/${state.sessionId}/` 
      : `/api/generate-card/`;

    const res = await fetch(endpoint, {
      method: 'POST',
      body: formData
    });


    const data = await res.json();
    typingIndicator.remove();

    if (res.ok) {
      // Update session state
      state.sessionId = data.session_id;
      sessionStatusText.textContent = 'Active Session';
      sessionIdPill.textContent = data.session_id.substring(0, 8) + '...';
      sessionIdPill.style.display = 'inline-block';

      // Render Assistant Message
      appendAssistantMessage(data.assistant_message || data.bot_reply || 'Card ready.');

      // Render Card (Prioritize live HTML/CSS Front & Back sides)
      if (data.card && (data.card.front_html || data.card.css)) {
        renderCard(data.card, data.title);
      } else if (data.image_base64 || data.image_url) {
        renderCardImage(data.image_base64 || data.image_url, data.card_data);
      }
    } else {
      appendAssistantMessage('❌ Error: ' + (data.error || 'Failed to process request.'));
    }
  } catch (err) {
    typingIndicator.remove();
    appendAssistantMessage('❌ Network Error: ' + err.message);
  } finally {
    sendBtn.disabled = false;
  }
}

function appendUserMessage(text, file) {
  const msgDiv = document.createElement('div');
  msgDiv.className = 'message user-msg';

  let attachmentHtml = '';
  if (file) {
    const blobUrl = URL.createObjectURL(file);
    attachmentHtml = `
      <div class="msg-attachment-thumb">
        <img src="${blobUrl}" alt="Reference">
      </div>
    `;
  }

  msgDiv.innerHTML = `
    <div class="msg-avatar"><i class="fa-solid fa-user"></i></div>
    <div class="msg-content">
      ${text ? `<p>${escapeHtml(text).replace(/\n/g, '<br>')}</p>` : ''}
      ${attachmentHtml}
    </div>
  `;
  chatMessages.appendChild(msgDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function appendAssistantMessage(text) {
  const msgDiv = document.createElement('div');
  msgDiv.className = 'message assistant-msg';
  msgDiv.innerHTML = `
    <div class="msg-avatar"><i class="fa-solid fa-robot"></i></div>
    <div class="msg-content">
      <p>${escapeHtml(text).replace(/\n/g, '<br>')}</p>
    </div>
  `;
  chatMessages.appendChild(msgDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function appendTypingIndicator() {
  const msgDiv = document.createElement('div');
  msgDiv.className = 'message assistant-msg';
  msgDiv.id = 'typingIndicator';
  msgDiv.innerHTML = `
    <div class="msg-avatar"><i class="fa-solid fa-wand-sparkles"></i></div>
    <div class="msg-content">
      <p><i class="fa-solid fa-spinner fa-spin"></i> Analyzing design & crafting executive card...</p>
    </div>
  `;
  chatMessages.appendChild(msgDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return msgDiv;
}

// ========================================================
// CARD RENDERER & 3D FLIP
// ========================================================
function renderCard(card, title) {
  state.currentCard = card;

  // Inject Scoped CSS
  if (card.css) {
    dynamicCardStyles.innerHTML = card.css;
  }

  // Render Front & Back in side-by-side mode
  frontSideCard.innerHTML = card.front_html || '';
  backSideCard.innerHTML = card.back_html || '';

  // Also render inside 3D Flip faces
  flipFront.innerHTML = card.front_html || '';
  flipBack.innerHTML = card.back_html || '';

  // Meta update
  if (title) {
    cardTitleMeta.textContent = title;
  } else if (card.card_data && card.card_data.name) {
    cardTitleMeta.textContent = `${card.card_data.name} - ${card.card_data.company || 'Card'}`;
  }

  if (card.card_data && card.card_data.primary_color) {
    cardPaletteMeta.textContent = `Colors: ${card.card_data.primary_color} / ${card.card_data.accent_color || '#d4af37'}`;
  }
}

function renderCardImage(imgSrc, cardData) {
  state.currentCard = {
    image_base64: imgSrc,
    image_url: imgSrc,
    card_data: cardData
  };
  const imgHtml = `<img src="${imgSrc}" style="width:100%;height:100%;object-fit:cover;border-radius:12px;display:block;" alt="Business Card">`;
  frontSideCard.innerHTML = imgHtml;
  backSideCard.innerHTML = imgHtml;
  flipFront.innerHTML = imgHtml;
  flipBack.innerHTML = imgHtml;

  if (cardData && cardData.name) {
    const org = cardData.company_name || cardData.company || 'Visiting Card';
    const role = cardData.designation || cardData.title || '';
    cardTitleMeta.textContent = `${cardData.name} - ${role ? role + ' at ' : ''}${org}`;
  }
  if (cardData && cardData.primary_color) {
    cardPaletteMeta.textContent = `Colors: ${cardData.primary_color} / ${cardData.accent_color || '#d4af37'}`;
  }
}

function setViewMode(mode) {
  state.currentView = mode;
  cardDisplayWrapper.className = 'card-display-wrapper';

  if (mode === 'both') {
    cardDisplayWrapper.classList.add('view-both');
  } else if (mode === 'front') {
    cardDisplayWrapper.classList.add('view-front-only');
  } else if (mode === 'back') {
    cardDisplayWrapper.classList.add('view-back-only');
  } else if (mode === 'flip') {
    cardDisplayWrapper.classList.add('view-flip-mode');
  }
}

function toggle3DFlip() {
  state.isFlipped = !state.isFlipped;
  if (state.currentView !== 'flip') {
    // switch tab to flip
    document.querySelectorAll('.view-tab').forEach(t => t.classList.remove('active'));
    document.querySelector('.view-tab[data-view="flip"]').classList.add('active');
    setViewMode('flip');
  }
  flipInner.classList.toggle('flipped', state.isFlipped);
}

function startNewSession() {
  state.sessionId = null;
  state.currentCard = null;
  sessionStatusText.textContent = 'Ready for New Card';
  sessionIdPill.style.display = 'none';
  sessionIdPill.textContent = '';
  chatMessages.innerHTML = '';
  showEmptyCanvasState();
  alert('New Card Session started! Type your card details or upload a reference design.');
}

function showEmptyCanvasState() {
  state.sessionId = null;
  state.currentCard = null;
  sessionStatusText.textContent = 'Ready for New Card';
  sessionIdPill.style.display = 'none';
  sessionIdPill.textContent = '';

  const emptyHtml = `
    <div style="height:100%;min-height:300px;display:flex;flex-direction:column;align-items:center;justify-content:center;color:#64748b;text-align:center;padding:24px;">
      <i class="fa-solid fa-id-card" style="font-size:46px;margin-bottom:14px;opacity:0.4;"></i>
      <p style="font-size:15px;font-weight:600;margin:0 0 6px 0;color:#94a3b8;">No Card Generated Yet</p>
      <span style="font-size:13px;opacity:0.75;">Type your card prompt or click a sample to generate your design</span>
    </div>
  `;
  if (frontSideCard) frontSideCard.innerHTML = emptyHtml;
  if (backSideCard) backSideCard.innerHTML = emptyHtml;
  if (flipFront) flipFront.innerHTML = emptyHtml;
  if (flipBack) flipBack.innerHTML = emptyHtml;
}


// ========================================================
// HIGH-RES EXPORT (PNG & PDF)
// ========================================================
async function exportSingleCard(elementId, filename) {
  const el = document.getElementById(elementId);
  if (!el) return;

  try {
    const canvas = await html2canvas(el, {
      scale: 3, // High DPI for crisp printing
      useCORS: true,
      backgroundColor: null
    });
    const link = document.createElement('a');
    link.download = filename;
    link.href = canvas.toDataURL('image/png');
    link.click();
  } catch (err) {
    alert('Export error: ' + err.message);
  }
}

async function exportCardsAsPng() {
  if (state.currentCard && state.currentCard.front_html) {
    await exportSingleCard('frontSideCard', 'business-card-front.png');
    setTimeout(async () => {
      await exportSingleCard('backSideCard', 'business-card-back.png');
    }, 400);
    return;
  }
  if (state.currentCard && (state.currentCard.image_base64 || state.currentCard.image_url)) {
    const link = document.createElement('a');
    link.download = 'business-card.png';
    link.href = state.currentCard.image_base64 || state.currentCard.image_url;
    link.click();
    return;
  }
  await exportSingleCard('frontSideCard', 'business-card-front.png');
  setTimeout(async () => {
    await exportSingleCard('backSideCard', 'business-card-back.png');
  }, 400);
}

async function exportCardsAsPdf() {
  try {
    const { jsPDF } = window.jspdf;
    // Standard business card size: 3.5in x 2in landscape
    const pdf = new jsPDF({
      orientation: 'landscape',
      unit: 'in',
      format: [3.5, 2]
    });

    const frontCanvas = await html2canvas(frontSideCard, { scale: 3, useCORS: true });
    const frontImgData = frontCanvas.toDataURL('image/jpeg', 1.0);
    pdf.addImage(frontImgData, 'JPEG', 0, 0, 3.5, 2);

    // Page 2 (Back)
    pdf.addPage([3.5, 2], 'landscape');
    const backCanvas = await html2canvas(backSideCard, { scale: 3, useCORS: true });
    const backImgData = backCanvas.toDataURL('image/jpeg', 1.0);
    pdf.addImage(backImgData, 'JPEG', 0, 0, 3.5, 2);

    pdf.save('business-card-print-ready.pdf');
  } catch (err) {
    alert('PDF Generation failed: ' + err.message);
  }
}

// ========================================================
// CODE MODAL
// ========================================================
function openCodeModal() {
  if (!state.currentCard) return;
  codeModal.style.display = 'flex';
  updateCodeViewContent();
}

function updateCodeViewContent() {
  if (!state.currentCard) return;
  if (state.activeCodeTab === 'css') {
    codeViewArea.value = state.currentCard.css || '/* No CSS */';
  } else if (state.activeCodeTab === 'front') {
    codeViewArea.value = state.currentCard.front_html || '<!-- No Front HTML -->';
  } else if (state.activeCodeTab === 'back') {
    codeViewArea.value = state.currentCard.back_html || '<!-- No Back HTML -->';
  }
}

function escapeHtml(text) {
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
  return String(text).replace(/[&<>"']/g, m => map[m]);
}

function isNewCardPrompt(text) {
  if (!text) return false;
  const lower = text.toLowerCase().trim().replace(/^["']|["']$/g, '');
  return /\b(make|create|design|generate)\s+(a\s+)?(new\s+)?(visiting|business)?\s*card\b/i.test(lower) ||
         /\b(card\s+for|visiting\s+card\s+for|business\s+card\s+for)\b/i.test(lower) ||
         /\b(নতুন কার্ড|কার্ড বানাও|ভিজিটিং কার্ড বানাও)\b/i.test(lower);
}

