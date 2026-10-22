// GhostHarness Interactive Web Demo Simulator (for GitHub Pages)
let activeTab = 'diff_viewer';
let vramMB = 4320;
let ramMB = 12400;
let isBusy = false;
let checkpoints = [
  { id: 'chk_init', desc: 'Initial repository baseline state', files: ['core/agent.py', 'tools/filesystem.py'] }
];

let activeDiff = `--- a/services/queue_manager.py
+++ b/services/queue_manager.py
@@ -38,5 +38,8 @@
-    async def pop_task(self):
-        if self.queue:
-            return self.queue.pop(0)
+    async def pop_task(self):
+        async with self._lock:
+            if self.queue:
+                return self.queue.pop(0)
+            return None`;

// Hardware Telemetry Simulation
function startTelemetryLoop() {
  setInterval(() => {
    // Gentle natural telemetry jitter (±20 MB)
    const jitter = Math.floor(Math.random() * 41) - 20;
    vramMB = Math.max(4280, Math.min(4480, vramMB + jitter));
    
    const vramPct = ((vramMB / 6144) * 100).toFixed(0);
    const vramFill = document.getElementById('vram-fill');
    const vramText = document.getElementById('vram-text');
    if (vramFill && vramText) {
      vramFill.style.width = `${vramPct}%`;
      vramText.innerText = `${(vramMB / 1024).toFixed(1)} / 6.0 GB`;
    }

    const ramFill = document.getElementById('ram-fill');
    const ramText = document.getElementById('ram-text');
    if (ramFill && ramText) {
      ramFill.style.width = `38%`;
      ramText.innerText = `12.4 / 32.0 GB`;
    }
  }, 2500);
}

// Tab Switching
function switchTab(tabId) {
  activeTab = tabId;
  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
  
  const buttons = document.querySelectorAll('.tab-btn');
  if (tabId === 'diff_viewer') buttons[0]?.classList.add('active');
  if (tabId === 'repomap') buttons[1]?.classList.add('active');
  if (tabId === 'checkpoints') buttons[2]?.classList.add('active');
  if (tabId === 'telemetry') buttons[3]?.classList.add('active');

  renderTabContent();
}

function renderTabContent() {
  const container = document.getElementById('workspace-content');
  if (!container) return;

  if (activeTab === 'diff_viewer') {
    if (!activeDiff) {
      container.innerHTML = `
        <div style="padding: 40px; text-align: center; color: var(--text-dim);">
          <div style="font-size: 2rem; margin-bottom: 10px;">📋</div>
          <b>No active file modifications.</b>
          <p style="font-size: 0.85rem; margin-top: 6px;">Run a prompt like "⚡ Fix queue race condition" to generate surgical diffs.</p>
        </div>`;
      return;
    }

    const lines = activeDiff.split('\n').map(l => {
      let cls = 'diff-line';
      if (l.startsWith('+') && !l.startsWith('+++')) cls += ' diff-add';
      else if (l.startsWith('-') && !l.startsWith('---')) cls += ' diff-del';
      else if (l.startsWith('@@')) cls += ' diff-hunk';
      return `<div class="${cls}">${escapeHtml(l)}</div>`;
    }).join('');

    container.innerHTML = `
      <div class="diff-container">
        <div class="diff-header">
          <span>services/queue_manager.py — Unified Syntax Patch</span>
          <span style="color: var(--success);">✔ Validated via AST parser</span>
        </div>
        ${lines}
      </div>`;
  } else if (activeTab === 'repomap') {
    container.innerHTML = `
      <div style="background: var(--bg-card); padding: 16px; border-radius: 8px; border: 1px solid var(--border);">
        <div style="font-size: 0.85rem; font-weight: 700; color: #fff; margin-bottom: 12px; display: flex; justify-content: space-between;">
          <span>Semantic AST RepoMap (Compressed 820 Tokens)</span>
          <span style="color: var(--cyan); font-family: var(--mono-font);">Ranking: PageRank + Git Recency</span>
        </div>
        <div class="symbol-tree">
          <div class="tree-file">📁 core/</div>
          <div class="tree-sym">├── <b>agent.py</b> : Agent, execute_turn(), stream_turn()</div>
          <div class="tree-sym">├── <b>dynamic_router.py</b> : ModelRouter, classify_task()</div>
          <div class="tree-sym">├── <b>memory_manager.py</b> : MemoryManager, get_headroom(), zero_spill_guard()</div>
          <div class="tree-sym">├── <b>repo_map.py</b> : RepoMap, generate_map(), _extract_py_symbols()</div>
          <div class="tree-sym">└── <b>checkpoint.py</b> : CheckpointManager, rollback(), create_checkpoint()</div>
          <div class="tree-file" style="margin-top: 8px;">📁 tools/</div>
          <div class="tree-sym">├── <b>filesystem.py</b> : read_file(), write_file(), edit_file() [fuzzy 85%]</div>
          <div class="tree-sym">├── <b>terminal.py</b> : run_terminal() [user-space sandbox]</div>
          <div class="tree-sym">└── <b>mcp_client.py</b> : MCPStdioClient, start(), call_tool()</div>
          <div class="tree-file" style="margin-top: 8px;">📁 finetune/</div>
          <div class="tree-sym">├── <b>lora_trainer.py</b> : train_qwen_qlora() [NF4 4-bit 6GB VRAM]</div>
          <div class="tree-sym">└── <b>dataset_loader.py</b> : USBDatasetLoader, harvest_git_commits()</div>
        </div>
      </div>`;
  } else if (activeTab === 'checkpoints') {
    const listHtml = checkpoints.map((chk, i) => `
      <div style="background: #111828; border: 1px solid var(--border); padding: 12px 14px; border-radius: 6px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
        <div>
          <div style="font-size: 0.82rem; font-weight: 700; color: #fff;">#${checkpoints.length - i} — ${chk.desc}</div>
          <div style="font-size: 0.75rem; color: var(--text-dim); margin-top: 2px;">Files: ${chk.files.join(', ')}</div>
        </div>
        <button onclick="triggerUndo()" style="background: #1e263d; border: 1px solid var(--border); color: #cbd5e1; padding: 4px 10px; border-radius: 4px; font-size: 0.75rem; cursor: pointer;">
          ↺ Revert
        </button>
      </div>
    `).join('');

    container.innerHTML = `
      <div style="background: var(--bg-card); padding: 16px; border-radius: 8px; border: 1px solid var(--border);">
        <div style="font-size: 0.85rem; font-weight: 700; color: #fff; margin-bottom: 12px; display: flex; justify-content: space-between;">
          <span>Active Atomic Checkpoints Stack</span>
          <span style="color: var(--text-muted); font-size: 0.75rem;">Cap: 50 items (Memory bounded)</span>
        </div>
        ${listHtml}
      </div>`;
  } else if (activeTab === 'telemetry') {
    container.innerHTML = `
      <div class="telemetry-card">
        <h4 style="color:#fff; margin-bottom: 10px; font-size: 0.9rem;">Discrete GPU Hardware Telemetry</h4>
        <div style="font-size: 0.82rem; line-height: 1.8; color: #cbd5e1; font-family: var(--mono-font);">
          <div>• Device Name: NVIDIA GeForce RTX 5060 Laptop/Desktop</div>
          <div>• Dedicated VRAM Total: 6,144 MB (6.0 GB)</div>
          <div>• VRAM Currently Allocated: ${vramMB} MB (70.3%)</div>
          <div>• Headroom Buffer: 1,824 MB remaining before 5,400 MB safe threshold</div>
          <div>• Zero-Spill Status: <span style="color: var(--success); font-weight:700;">OPTIMAL (Zero memory paging into host RAM)</span></div>
        </div>
      </div>
      <div class="telemetry-card">
        <h4 style="color:#fff; margin-bottom: 10px; font-size: 0.9rem;">Host System RAM Allocation</h4>
        <div style="font-size: 0.82rem; line-height: 1.8; color: #cbd5e1; font-family: var(--mono-font);">
          <div>• Total Physical RAM: 32,768 MB (32.0 GB)</div>
          <div>• Allocated / In Use: 12,400 MB (37.8%)</div>
          <div>• Available Headroom: 20,368 MB (Ready for 14B/32B Hybrid Offload)</div>
        </div>
      </div>`;
  }
}

// Simulated Agent Interaction
async function runDemoPrompt(type) {
  if (isBusy) return;
  const input = document.getElementById('prompt-input');

  if (type === 'queue') {
    if (input) input.value = "Fix the race condition in services/queue_manager.py when popping tasks concurrently.";
    sendMessage();
  } else if (type === 'vram') {
    if (input) input.value = "Inspect GPU memory headroom and evaluate zero-spill safety on 6GB VRAM.";
    sendMessage();
  } else if (type === 'repomap') {
    switchTab('repomap');
    if (input) input.value = "Show semantic AST RepoMap for current project.";
    sendMessage();
  } else if (type === 'benchmark') {
    switchTab('telemetry');
    if (input) input.value = "Run 17-point system diagnostic benchmark.";
    sendMessage();
  }
}

async function sendMessage() {
  const input = document.getElementById('prompt-input');
  if (!input || !input.value.trim() || isBusy) return;
  
  const text = input.value.trim();
  input.value = '';
  isBusy = true;

  // Append User Message
  appendMessage('user', text);

  // Assistant typing container
  const assistantCard = appendMessage('assistant', '<span class="cursor">Thinking...</span>');
  
  await sleep(600);

  if (text.toLowerCase().includes('queue') || text.toLowerCase().includes('race condition')) {
    assistantCard.innerHTML = `
      <div class="agent-header">
        <span class="agent-avatar">⚡</span>
        <b>GhostHarness Agent</b>
      </div>
      <p>I will search for task popping routines in <code>services/queue_manager.py</code> using <code>grep_search</code>.</p>
      
      <div class="tool-invocation-box">
        <div class="tool-tag">⚡ Tool Call: grep_search</div>
        <code>{"path": "services/queue_manager.py", "pattern": "async def pop_task"}</code>
      </div>`;
    
    await sleep(800);

    assistantCard.innerHTML += `
      <p style="margin-top: 10px;">The method <code>pop_task</code> lacks an async lock guard. In concurrent coroutines, multiple tasks can pass <code>if self.queue:</code> simultaneously. I will use <code>edit_file</code> to wrap this with <code>async with self._lock:</code>.</p>
      
      <div class="tool-invocation-box">
        <div class="tool-tag">⚡ Tool Call: edit_file</div>
        <code>{"path": "services/queue_manager.py", "target": "if self.queue:\\n    return self.queue.pop(0)", "replacement": "async with self._lock:\\n    if self.queue:\\n        return self.queue.pop(0)\\n    return None"}</code>
      </div>`;

    activeDiff = `--- a/services/queue_manager.py
+++ b/services/queue_manager.py
@@ -38,5 +38,8 @@
-    async def pop_task(self):
-        if self.queue:
-            return self.queue.pop(0)
+    async def pop_task(self):
+        async with self._lock:
+            if self.queue:
+                return self.queue.pop(0)
+            return None`;

    checkpoints.unshift({
      id: `chk_${Date.now()}`,
      desc: 'Patched concurrency race in pop_task()',
      files: ['services/queue_manager.py']
    });

    switchTab('diff_viewer');
    await sleep(800);

    assistantCard.innerHTML += `
      <div class="tool-invocation-box" style="border-color: #10b981;">
        <div class="tool-tag" style="color: var(--success);">✔ Tool Output: edit_file</div>
        <code>{"success": true, "path": "services/queue_manager.py", "diff_applied": true}</code>
      </div>
      <p style="margin-top: 8px;">The patch has been applied and verified. Notice the unified diff in the right panel and the new checkpoint snapshot recorded in the Checkpoints tab.</p>`;

  } else if (text.toLowerCase().includes('vram') || text.toLowerCase().includes('headroom')) {
    switchTab('telemetry');
    assistantCard.innerHTML = `
      <div class="agent-header">
        <span class="agent-avatar">⚡</span>
        <b>Hardware Memory Manager</b>
      </div>
      <p><b>Discrete GPU Telemetry Evaluation (RTX 5060 6GB):</b></p>
      <div class="tool-invocation-box">
        <div class="tool-tag">⚡ Telemetry Query: get_vram_telemetry()</div>
        <code>{"vram_used_mb": ${vramMB}, "max_threshold_mb": 5400, "status": "OPTIMAL"}</code>
      </div>
      <p style="margin-top: 8px;"><b>Status:</b> Zero GPU spill detected. The model weights (4,320 MB) and 8k KV cache (850 MB) fit 100% inside discrete VRAM, sustaining 55 tokens/second with 0% memory swapping into system RAM.</p>`;

  } else {
    assistantCard.innerHTML = `
      <div class="agent-header">
        <span class="agent-avatar">⚡</span>
        <b>GhostHarness Agent</b>
      </div>
      <p>I have analyzed your request: <i>"${escapeHtml(text)}"</i>.</p>
      <p style="margin-top: 8px;">Using the AST RepoMap symbol index, I have formulated a surgical execution plan in user-space without requiring administrator privileges. To test code patching, click the <b>"⚡ Fix queue race condition"</b> chip above!</p>`;
  }

  isBusy = false;
  scrollChatToBottom();
}

function appendMessage(role, content) {
  const list = document.getElementById('message-list');
  if (!list) return null;
  const card = document.createElement('div');
  card.className = `msg-card msg-${role}`;
  card.innerHTML = content;
  list.appendChild(card);
  scrollChatToBottom();
  return card;
}

function scrollChatToBottom() {
  const list = document.getElementById('message-list');
  if (list) list.scrollTop = list.scrollHeight;
}

function triggerUndo() {
  if (checkpoints.length > 1) {
    const reverted = checkpoints.shift();
    activeDiff = null;
    switchTab('diff_viewer');
    alert(`↺ Rollback Complete!\nReverted checkpoint: "${reverted.desc}"\nRestored files: ${reverted.files.join(', ')}`);
  } else {
    alert("↺ Baseline snapshot reached. No further checkpoints to undo.");
  }
}

function onModelChange(sel) {
  const status = document.getElementById('backend-status');
  if (sel.value === 'qwen2.5-coder-14b-instruct') {
    vramMB = 4800;
    if (status) status.innerText = '● llama-server (Qwen 14B Hybrid Offload)';
    alert("Switched to 14B Heavy Tier: 26 layers on GPU (4.8 GB VRAM) + 22 layers in 32GB host RAM.");
  } else {
    vramMB = 4320;
    if (status) status.innerText = '● llama-server :8080 (Qwen 2.5 Coder 7B)';
  }
  renderTabContent();
}

function toggleDictation() {
  const btn = document.getElementById('mic-btn');
  if (!btn) return;
  if (btn.innerText.includes('Voice')) {
    btn.style.backgroundColor = 'var(--danger)';
    btn.innerText = '● Listening...';
    setTimeout(() => {
      const input = document.getElementById('prompt-input');
      if (input) input.value = "Fix race condition in services/queue_manager.py";
      btn.style.backgroundColor = 'var(--bg-card)';
      btn.innerText = '🎤 Voice';
    }, 2200);
  }
}

function escapeHtml(str) {
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// Initialize on DOM load
window.addEventListener('DOMContentLoaded', () => {
  renderTabContent();
  startTelemetryLoop();
});
