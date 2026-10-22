let activeTab = 'diff_viewer';
let currentDiff = null;

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
        badge.innerText = `● Connected (${data.available_models.length} models)`;
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
  } catch (e) {
    console.error('Failed loading plugins:', e);
  }
}

function renderTabContent(plugin) {
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
  let html = `<div class="diff-card"><div class="diff-header"><span>Surgical Code Patch</span><span style="color: var(--accent);">Pending Approval</span></div>`;
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
      renderDiffCard(currentDiff);
    }
  }
  const list = document.getElementById('message-list');
  list.scrollTop = list.scrollHeight;
}

// Initialize on page load
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
