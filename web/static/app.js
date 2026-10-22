let activeTab = 'diff_viewer';
let currentDiff = null;
let isRecording = false;
let recognition = null;

// Initialize Web Speech Dictation if supported by browser
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
    if (isRecording) {
      btn.style.backgroundColor = 'var(--danger)';
      btn.innerText = '● Listening...';
    } else {
      btn.style.backgroundColor = 'var(--bg-card)';
      btn.innerText = '🎤 Voice';
    }
  }
}

// Telemetry Polling (every 2.5 seconds)
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
      if (vramPct > 88) {
        vramFill.style.backgroundColor = 'var(--danger)';
      } else if (vramPct > 70) {
        vramFill.style.backgroundColor = 'var(--warning)';
      } else {
        vramFill.style.backgroundColor = 'var(--success)';
      }
    }

    // RAM Bar
    const ramPct = Math.min(100, Math.round(data.ram_percent));
    const ramFill = document.getElementById('ram-fill');
    const ramText = document.getElementById('ram-text');
    if (ramFill && ramText) {
      ramFill.style.width = `${ramPct}%`;
      ramText.innerText = `${(data.ram_used_mb / 1024).toFixed(1)} / ${(data.ram_total_mb / 1024).toFixed(1)} GB`;
    }

    // Status Pill
    const statusPill = document.getElementById('headroom-status');
    if (statusPill) {
      statusPill.innerText = data.status_message;
    }
  } catch (err) {
    console.error('Telemetry poll failed:', err);
  }
}

// Check Backend Health
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
    console.warn('Backend check failed:', e);
  }
}

// Trigger Undo Checkpoint
async function triggerUndo() {
  try {
    const res = await fetch('/api/undo', { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      alert(`Reverted checkpoint: ${data.description}\nRestored: ${data.restored_files.join(', ') || 'No files modified'}`);
      currentDiff = null;
      loadPlugins();
    } else {
      alert(data.error || 'No checkpoints to undo.');
    }
  } catch (e) {
    alert(`Undo failed: ${e.message}`);
  }
}

// Change Model Selection
async function onModelChange(sel) {
  const val = sel.value === 'auto' ? null : sel.value;
  await fetch('/api/model/override', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model: val })
  });
}

// Fetch Dynamic Tabs
async function loadPlugins() {
  try {
    const res = await fetch('/api/plugins');
    const plugins = await res.json();
    const tabsContainer = document.getElementById('workspace-tabs');
    tabsContainer.innerHTML = '';

    plugins.forEach(p => {
      const btn = document.createElement('button');
      btn.className = `tab-btn ${p.id === activeTab ? 'active' : ''}`;
      btn.innerText = p.title;
      btn.onclick = () => {
        activeTab = p.id;
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        renderTabContent(p);
      };
      tabsContainer.appendChild(btn);
    });

    const curr = plugins.find(p => p.id === activeTab) || plugins[0];
    if (curr) renderTabContent(curr);
  } catch (e) {
    console.error('Failed loading plugins:', e);
  }
}

async function renderTabContent(plugin) {
  const container = document.getElementById('workspace-content');
  if (plugin.id === 'diff_viewer') {
    if (!currentDiff) {
      container.innerHTML = `
        <div style="text-align: center; color: var(--text-muted); margin-top: 80px;">
          <h3>No Pending File Diffs</h3>
          <p style="font-size: 0.9rem; margin-top: 8px;">When GhostHarness edits a file, unified line diffs appear here for live review.</p>
        </div>
      `;
    } else {
      renderDiffCard(currentDiff);
    }
  } else if (plugin.id === 'repo_explorer') {
    container.innerHTML = `<div style="color: var(--text-muted);">Generating semantic symbol tree...</div>`;
    const res = await fetch('/api/repomap');
    const data = await res.json();
    container.innerHTML = `
      <div style="background: var(--bg-card); padding: 18px; border-radius: 8px; border: 1px solid var(--border); font-family: var(--mono-font); font-size: 0.85rem; white-space: pre-wrap;">
        <h4 style="color: var(--accent); margin-bottom: 12px;">Semantic Codebase AST Map (Aider-Style Token Budgeted)</h4>
        ${escapeHtml(data.map)}
      </div>
    `;
  } else if (plugin.id === 'checkpoints') {
    const res = await fetch('/api/checkpoints');
    const data = await res.json();
    let html = `<div style="background: var(--bg-card); padding: 20px; border-radius: 8px; border: 1px solid var(--border);">
      <h3>Atomic Modification Checkpoints</h3>
      <p style="color: var(--text-muted); margin: 6px 0 16px 0;">Snapshots taken before each tool mutation:</p>
      <ul style="line-height: 2; list-style-position: inside;">`;
    if (!data.checkpoints || data.checkpoints.length === 0) {
      html += `<li>No snapshots yet recorded.</li>`;
    } else {
      data.checkpoints.forEach(c => {
        html += `<li><b>[${c.time}]</b> ${escapeHtml(c.description)} (${c.files.join(', ') || 'No files'})</li>`;
      });
    }
    html += `</ul><button onclick="triggerUndo()" style="margin-top: 14px; background: var(--accent); color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer;">Rollback Most Recent</button></div>`;
    container.innerHTML = html;
  } else if (plugin.id === 'vram_monitor') {
    container.innerHTML = `
      <div style="background: var(--bg-card); padding: 24px; border-radius: 12px; border: 1px solid var(--border);">
        <h3>Hardware Budget & Optimization</h3>
        <p style="color: var(--text-muted); margin: 12px 0 20px 0;">University Lab Machine Profile (6GB Discrete VRAM + 32GB RAM)</p>
        <ul style="line-height: 2; color: #cbd5e1; list-style-position: inside;">
          <li><b>Dedicated VRAM Ceiling:</b> 5,400 MB (Preserves 744 MB for Windows/X11 Desktop compositor)</li>
          <li><b>Fast Model Residency:</b> Qwen 2.5 Coder 7B (Q4_K_M) takes ~4.3 GB + 0.8 GB KV cache = 100% in VRAM</li>
          <li><b>Hybrid Offloading:</b> Qwen 2.5 Coder 14B offloads 26 layers into VRAM, remainder into 32GB RAM</li>
          <li><b>Zero GPU Spill Guard:</b> Active memory manager dynamically limits context length if headroom drops</li>
        </ul>
      </div>
    `;
  } else if (plugin.html_template) {
    container.innerHTML = plugin.html_template;
  } else {
    container.innerHTML = `<div style="padding: 20px;"><h3>${plugin.title}</h3><p>${plugin.description}</p></div>`;
  }
}

function renderDiffCard(diffText) {
  const container = document.getElementById('workspace-content');
  const lines = diffText.split('\n');
  let html = `<div class="diff-card"><div class="diff-header"><span>Surgical Code Patch</span><span style="color: var(--accent);">Modified File</span></div>`;
  lines.forEach(l => {
    let cls = '';
    if (l.startsWith('+') && !l.startsWith('+++')) cls = 'diff-add';
    else if (l.startsWith('-') && !l.startsWith('---')) cls = 'diff-del';
    html += `<div class="diff-line ${cls}">${escapeHtml(l)}</div>`;
  });
  html += `</div>`;
  container.innerHTML = html;
}

function escapeHtml(str) {
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// Send Chat Message
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
            handleAgentEvent(evt, assistantCard);
          } catch (e) {}
        }
      }
    }
  } catch (err) {
    assistantCard.innerHTML += `<div style="color: var(--danger); margin-top: 8px;">Error: ${err.message}</div>`;
  }
}

function appendUserMessage(text) {
  const list = document.getElementById('message-list');
  const div = document.createElement('div');
  div.className = 'msg-card msg-user';
  div.innerText = text;
  list.appendChild(div);
  list.scrollTop = list.scrollHeight;
}

function createAssistantMessageCard() {
  const list = document.getElementById('message-list');
  const div = document.createElement('div');
  div.className = 'msg-card msg-assistant';
  list.appendChild(div);
  list.scrollTop = list.scrollHeight;
  return div;
}

function handleAgentEvent(evt, card) {
  if (evt.type === 'routing') {
    const badge = document.createElement('div');
    badge.style.fontSize = '0.8rem';
    badge.style.color = 'var(--text-muted)';
    badge.style.marginBottom = '6px';
    badge.innerText = `[Engine: ${evt.model} | Tier: ${evt.tier.toUpperCase()}]`;
    card.appendChild(badge);
  } else if (evt.type === 'token') {
    card.innerHTML += escapeHtml(evt.content);
  } else if (evt.type === 'tool_start') {
    const tb = document.createElement('div');
    tb.className = 'tool-badge';
    tb.innerText = `⚙ Executing Tool: ${evt.tool}(${JSON.stringify(evt.arguments)})`;
    card.appendChild(tb);
  } else if (evt.type === 'tool_end') {
    if (evt.tool === 'edit_file' && evt.result.diff) {
      currentDiff = evt.result.diff;
      activeTab = 'diff_viewer';
      loadPlugins();
    }
  }
  const list = document.getElementById('message-list');
  list.scrollTop = list.scrollHeight;
}

window.addEventListener('DOMContentLoaded', () => {
  updateTelemetry();
  setInterval(updateTelemetry, 2500);
  checkBackend();
  setInterval(checkBackend, 10000);
  loadPlugins();

  const input = document.getElementById('prompt-input');
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
});
