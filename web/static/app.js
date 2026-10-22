let activeTab = 'diff_viewer';
let currentDiff = null;
let isRecording = false;
let recognition = null;
let pluginsList = [];

// Initialize Web Speech Dictation
if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SpeechRec();
  recognition.continuous = false;
  recognition.interimResults = false;

  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    const input = document.getElementById('prompt-input');
    if (input) {
      input.value = (input.value ? input.value + ' ' : '') + transcript;
    }
  };

  recognition.onend = () => {
    isRecording = false;
    updateMicButtonUI();
  };
}

function toggleDictation() {
  if (!recognition) {
    alert("Speech recognition is not supported in this browser. Please use Chrome/Edge or type directly.");
    return;
  }
  if (isRecording) {
    recognition.stop();
    isRecording = false;
  } else {
    recognition.start();
    isRecording = true;
  }
  updateMicButtonUI();
}

function updateMicButtonUI() {
  const btn = document.getElementById('mic-btn');
  if (btn) {
    btn.style.backgroundColor = isRecording ? 'var(--danger)' : 'transparent';
    btn.innerText = isRecording ? '●' : '🎤';
  }
}

// Telemetry Polling (Every 2.5 seconds)
async function updateTelemetry() {
  try {
    const res = await fetch('/api/telemetry');
    if (!res.ok) return;
    const data = await res.json();

    // VRAM Bar
    const vramPct = Math.min(100, Math.round(data.vram_percent));
    const vramFill = document.getElementById('vram-fill');
    const vramText = document.getElementById('vram-text');
    if (vramFill && vramText) {
      vramFill.style.width = `${vramPct}%`;
      vramText.innerText = `${(data.vram_used_mb / 1024).toFixed(1)} / ${(data.vram_total_mb / 1024).toFixed(1)} GB`;
      if (vramPct > 88) vramFill.style.backgroundColor = 'var(--danger)';
      else if (vramPct > 70) vramFill.style.backgroundColor = 'var(--warning)';
      else vramFill.style.backgroundColor = 'var(--cyan)';
    }

    // RAM Bar
    const ramPct = Math.min(100, Math.round(data.ram_percent));
    const ramFill = document.getElementById('ram-fill');
    const ramText = document.getElementById('ram-text');
    if (ramFill && ramText) {
      ramFill.style.width = `${ramPct}%`;
      ramText.innerText = `${(data.ram_used_mb / 1024).toFixed(1)} / ${(data.ram_total_mb / 1024).toFixed(1)} GB`;
    }

    // Status Badge
    const statusPill = document.getElementById('headroom-status');
    if (statusPill) {
      statusPill.innerText = data.status_message;
    }
  } catch (err) {
    console.debug('Telemetry poll failed:', err);
  }
}

// Backend Health Check
async function checkBackend() {
  try {
    const res = await fetch('/api/health');
    const data = await res.json();
    const badge = document.getElementById('backend-status');
    if (badge) {
      if (data.online) {
        badge.innerText = `● ${data.backend || 'Backend'} (${data.available_models.length} models)`;
        badge.style.color = 'var(--success)';
      } else {
        badge.innerText = `○ Backend Offline`;
        badge.style.color = 'var(--danger)';
      }
    }
  } catch (e) {
    console.debug('Backend check offline');
  }
}

// Mission & LoRA Adapter Status
async function checkMissionStatus() {
  try {
    const res = await fetch('/api/mission');
    if (!res.ok) return;
    const data = await res.json();
    const adapterPill = document.getElementById('adapter-status');
    if (adapterPill) {
      if (data.adapter_present) {
        adapterPill.style.display = 'inline-block';
        adapterPill.innerText = `🎯 LoRA: ${data.adapter_name} (${data.adapter_size_mb} MB)`;
      } else {
        adapterPill.style.display = 'none';
      }
    }
  } catch (e) {
    console.debug('Mission status check failed');
  }
}

// Trigger Undo
async function triggerUndo() {
  try {
    const res = await fetch('/api/undo', { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      alert(`↺ Snapshot Rolled Back!\nDescription: ${data.description}\nRestored: ${data.restored_files.join(', ') || 'Clean state'}`);
      currentDiff = null;
      loadPlugins();
    } else {
      alert(data.error || 'No checkpoints to undo.');
    }
  } catch (e) {
    alert(`Undo failed: ${e.message}`);
  }
}

// Model Selection
async function onModelChange(sel) {
  const val = sel.value === 'auto' ? null : sel.value;
  await fetch('/api/model/override', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model: val })
  });
}

// Workspace Tab Navigation
async function loadPlugins() {
  try {
    const res = await fetch('/api/plugins');
    pluginsList = await res.json();
    const tabsContainer = document.getElementById('workspace-tabs');
    tabsContainer.innerHTML = '';

    pluginsList.forEach(p => {
      const btn = document.createElement('button');
      btn.className = `tab-btn ${p.id === activeTab ? 'active' : ''}`;
      btn.innerText = p.title;
      btn.onclick = () => switchWorkspaceTab(p.id);
      tabsContainer.appendChild(btn);
    });

    const activePlugin = pluginsList.find(p => p.id === activeTab) || pluginsList[0];
    if (activePlugin) renderTabContent(activePlugin);
  } catch (e) {
    console.debug('Failed loading plugins:', e);
  }
}

function switchWorkspaceTab(tabId) {
  activeTab = tabId;
  document.querySelectorAll('.tab-btn').forEach((btn, i) => {
    btn.classList.toggle('active', pluginsList[i] && pluginsList[i].id === tabId);
  });
  const p = pluginsList.find(x => x.id === tabId);
  if (p) renderTabContent(p);
}

async function renderTabContent(plugin) {
  const container = document.getElementById('workspace-content');
  if (!container) return;

  if (plugin.id === 'diff_viewer') {
    if (!currentDiff) {
      container.innerHTML = `
        <div style="padding: 40px; text-align: center; color: var(--text-dim);">
          <div style="font-size: 2.2rem; margin-bottom: 12px;">📝</div>
          <b style="color: var(--text-muted); font-size: 1rem;">No Active Code Modifications</b>
          <p style="font-size: 0.85rem; margin-top: 8px;">Ask GhostHarness to edit a file, and the surgical unified diff will render here in real time.</p>
        </div>`;
    } else {
      renderDiffCard(currentDiff);
    }
  } else if (plugin.id === 'repo_explorer') {
    container.innerHTML = `<div style="color: var(--text-muted); padding: 10px;">Generating AST symbol tree...</div>`;
    const res = await fetch('/api/repomap');
    const data = await res.json();
    container.innerHTML = `
      <div style="background: var(--bg-card); padding: 18px; border-radius: 8px; border: 1px solid var(--border); font-family: var(--mono-font); font-size: 0.82rem; white-space: pre-wrap;">
        <div style="color: var(--cyan); font-weight: 700; margin-bottom: 10px; display: flex; justify-content: space-between;">
          <span>Semantic AST RepoMap</span>
          <span style="color: var(--text-muted);">Compressed Token Budget</span>
        </div>
        ${escapeHtml(data.map)}
      </div>`;
  } else if (plugin.id === 'checkpoints') {
    const res = await fetch('/api/checkpoints');
    const data = await res.json();
    let html = `
      <div style="background: var(--bg-card); padding: 18px; border-radius: 8px; border: 1px solid var(--border);">
        <div style="font-weight: 700; margin-bottom: 8px; color: #fff;">Atomic File Snapshots</div>
        <p style="color: var(--text-muted); font-size: 0.82rem; margin-bottom: 14px;">Instant rollback points created prior to every disk mutation:</p>
        <div style="display: flex; flex-direction: column; gap: 8px;">`;
    if (!data.checkpoints || data.checkpoints.length === 0) {
      html += `<div style="color: var(--text-dim); font-size: 0.85rem;">No checkpoints recorded yet.</div>`;
    } else {
      data.checkpoints.forEach(c => {
        html += `
          <div style="background: #0f1527; border: 1px solid var(--border); padding: 10px 14px; border-radius: 6px; display: flex; justify-content: space-between; align-items: center;">
            <div>
              <div style="font-weight: 600; font-size: 0.85rem; color: #fff;">${escapeHtml(c.description)}</div>
              <div style="font-size: 0.75rem; color: var(--text-dim); margin-top: 2px;">${c.time} • ${c.files.join(', ') || 'No files'}</div>
            </div>
            <button onclick="triggerUndo()" class="undo-mini-btn">↺ Rollback</button>
          </div>`;
      });
    }
    html += `</div></div>`;
    container.innerHTML = html;
  } else if (plugin.id === 'vram_monitor') {
    container.innerHTML = `
      <div style="background: var(--bg-card); padding: 20px; border-radius: 8px; border: 1px solid var(--border); font-size: 0.88rem; line-height: 1.8;">
        <h3 style="color: #fff; margin-bottom: 8px;">6GB VRAM Zero-Spill Architecture</h3>
        <p style="color: var(--text-muted); margin-bottom: 14px; font-size: 0.82rem;">Calibrated for NVIDIA RTX 5060/4050 Discrete GPUs</p>
        <div style="font-family: var(--mono-font); font-size: 0.82rem; color: #cbd5e1;">
          <div>• Dedicated VRAM Ceiling: <span style="color: var(--cyan); font-weight: 700;">5,400 MB</span> (744 MB reserved for Windows DWM)</div>
          <div>• Fast Tier (7B Q4_K_M): <span style="color: var(--success); font-weight: 700;">100% in VRAM</span> (4.3 GB weights + 850 MB KV cache)</div>
          <div>• Heavy Tier (14B Q4_K_M): <span style="color: var(--accent-light);">Hybrid offload</span> (26 layers GPU, remainder 32GB RAM)</div>
          <div>• Zero-Spill Guard: Continuous NVML telemetry dynamically guards KV cache context</div>
        </div>
      </div>`;
  }
}

function renderDiffCard(diffText) {
  const container = document.getElementById('workspace-content');
  const lines = diffText.split('\n');
  let html = `<div class="diff-card"><div class="diff-header"><span>Surgical Code Patch (Live Diff)</span><span style="color: var(--success);">✔ Validated</span></div>`;
  lines.forEach(l => {
    let cls = 'diff-line';
    if (l.startsWith('+') && !l.startsWith('+++')) cls += ' diff-add';
    else if (l.startsWith('-') && !l.startsWith('---')) cls += ' diff-del';
    else if (l.startsWith('@@')) cls += ' diff-hunk';
    html += `<div class="${cls}">${escapeHtml(l)}</div>`;
  });
  html += `</div>`;
  container.innerHTML = html;
}

function fillPrompt(text) {
  const input = document.getElementById('prompt-input');
  if (input) {
    input.value = text;
    sendMessage();
  }
}

// Send Message & Parse SSE Stream
async function sendMessage() {
  const input = document.getElementById('prompt-input');
  const prompt = input.value.trim();
  if (!prompt) return;

  input.value = '';
  appendUserMessage(prompt);
  const assistantCard = createAssistantMessageCard();

  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt: prompt })
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let partialLine = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      const lines = (partialLine + chunk).split('\n\n');
      partialLine = lines.pop();

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const raw = line.slice(6).trim();
          if (raw === '[DONE]') break;
          try {
            const evt = JSON.parse(raw);
            handleStreamEvent(evt, assistantCard);
          } catch (e) {
            // Raw text chunk fallback
            assistantCard.querySelector('.content-body').innerHTML += escapeHtml(raw);
          }
        }
      }
    }
  } catch (err) {
    assistantCard.querySelector('.content-body').innerHTML += `<div style="color: var(--danger); margin-top: 8px;">Error: ${escapeHtml(err.message)}</div>`;
  }
}

function handleStreamEvent(evt, card) {
  const body = card.querySelector('.content-body');
  if (evt.type === 'token') {
    body.innerHTML += escapeHtml(evt.content);
  } else if (evt.type === 'tool_start') {
    let tagCls = 'read';
    if (evt.tool === 'edit_file') tagCls = 'edit';
    if (evt.tool === 'run_terminal') tagCls = 'bash';

    body.innerHTML += `
      <div class="tool-badge ${tagCls}">
        <span>⚙ ${escapeHtml(evt.tool)}</span>
        <span style="color: var(--text-muted);">${escapeHtml(JSON.stringify(evt.arguments))}</span>
      </div><br/>`;
  } else if (evt.type === 'tool_end') {
    if (evt.tool === 'edit_file' && evt.result && evt.result.diff) {
      currentDiff = evt.result.diff;
      switchWorkspaceTab('diff_viewer');

      // Append Claude style Artifact card
      body.innerHTML += `
        <div class="artifact-card">
          <div class="artifact-header">
            <span>📝 Artifact: ${escapeHtml(evt.arguments.path || 'Code Patch')}</span>
            <button onclick="switchWorkspaceTab('diff_viewer')" class="artifact-open-btn">View in Inspector ↗</button>
          </div>
        </div>`;
    }
  }
  scrollChatToBottom();
}

function appendUserMessage(text) {
  const list = document.getElementById('message-list');
  const card = document.createElement('div');
  card.className = 'msg-card msg-user';
  card.innerHTML = `<div style="font-weight: 600;">❯ ${escapeHtml(text)}</div>`;
  list.appendChild(card);
  scrollChatToBottom();
}

function createAssistantMessageCard() {
  const list = document.getElementById('message-list');
  const card = document.createElement('div');
  card.className = 'msg-card msg-assistant';
  card.innerHTML = `
    <div class="agent-header">
      <span class="agent-avatar">⚡</span>
      <span class="agent-title">GhostHarness Agent</span>
    </div>
    <div class="content-body" style="white-space: pre-wrap;"></div>`;
  list.appendChild(card);
  scrollChatToBottom();
  return card;
}

function scrollChatToBottom() {
  const list = document.getElementById('message-list');
  if (list) list.scrollTop = list.scrollHeight;
}

function escapeHtml(str) {
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// Resizable Split Pane Logic
function initResizer() {
  const resizer = document.getElementById('resizer');
  const chatPanel = document.getElementById('chat-panel');
  const workspacePanel = document.getElementById('workspace-panel');
  let isResizing = false;

  resizer.addEventListener('mousedown', (e) => {
    isResizing = true;
    document.body.style.cursor = 'col-resize';
  });

  window.addEventListener('mousemove', (e) => {
    if (!isResizing) return;
    const containerWidth = window.innerWidth;
    const leftWidth = e.clientX;
    const rightWidth = containerWidth - leftWidth;

    if (leftWidth > 350 && rightWidth > 350) {
      chatPanel.style.flex = 'none';
      chatPanel.style.width = `${leftWidth}px`;
      workspacePanel.style.flex = '1';
    }
  });

  window.addEventListener('mouseup', () => {
    isResizing = false;
    document.body.style.cursor = 'default';
  });
}

// Enter to send in textarea
document.addEventListener('DOMContentLoaded', () => {
  const input = document.getElementById('prompt-input');
  if (input) {
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });
  }

  initResizer();
  loadPlugins();
  checkBackend();
  checkMissionStatus();
  updateTelemetry();
  setInterval(updateTelemetry, 2500);
  setInterval(checkMissionStatus, 5000);
});
