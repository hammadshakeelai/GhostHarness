# ⚡ GhostHarness

> **The Sovereign, Self-Contained AI Agent Harness & Portable Lab**  
> Designed for high-speed local agentic development on constrained hardware (**6GB Discrete VRAM + 32GB RAM**) with **Zero Administrator Privileges Required**.

---

## 🌟 Vision & Key Capabilities

**GhostHarness** transforms any university lab computer, restricted workstation, or laptop into an autonomous AI development powerhouse using an abliterated local Qwen model. Carry your entire development environment, agent harness, models, and fine-tuning datasets on a single USB drive.

- 🛡️ **Zero Admin Privileges (No Root / No Sudo):** Runs entirely in user-space via standard Python (3.10–3.14). Nothing is written to system directories.
- 🚀 **Zero GPU Spill Guard:** Specifically calibrated for **6GB VRAM GPUs (e.g. RTX 5060/4050/3050 Laptop/Desktop)**:
  - **Fast Tier (Qwen 2.5 Coder 7B Abliterated Q4_K_M):** Fits **100% inside 6GB VRAM** (4.3 GB weights + 850 MB 8k Flash-Attention KV cache). Delivers blistering **45–60 tokens/sec** with zero memory swapping.
  - **Heavy Tier (Qwen 2.5 Coder 14B/32B):** Offloads 26 layers into VRAM and remainder into 32GB System RAM for deep architectural planning.
  - **Dynamic Auto-Switching:** Automatically routes quick file edits and terminal commands to 7B, and escalates multi-file refactoring to 14B.
- 🗺️ **Aider-Style Semantic Repo Map:** Extracts an AST symbol hierarchy (classes, functions, signatures) into a compressed token budget (~500–1000 tokens), allowing 7B models to understand the entire multi-file project without blowing context.
- ↺ **Atomic Checkpoint & Instant Undo:** Saves pre-modification file snapshots before every tool execution. Revert bad edits or hallucinated changes instantly with one click (`↺ Undo` or `/undo`).
- 🎯 **Fuzzy-Tolerant Code Patching:** If a local 7B model has minor whitespace or indentation discrepancies in an edit target, a sequence matcher identifies candidate blocks ($\ge 85\%$ similarity), preventing loop failures.
- 🔌 **Full Model Context Protocol (MCP) Client:** Native JSON-RPC 2.0 stdio client that spawns any MCP server (Git, Postgres, Filesystem, Puppeteer) and integrates its tools directly.
- 🎙️ **Multi-Modal Sidecars (Voice & Vision):**
  - **Voice Dictation:** Built-in microphone dictation in the Visual Workspace.
  - **Vision Model Support:** Local inspection of UI screenshots and architecture sketches.
- 🎨 **Visual Workspace & Claude Code UX:**
  - Web GUI with side-by-side syntax diff viewer, live VRAM/RAM gauges, and model overrides.
  - Claude Code style terminal TUI (`/gui`, `/undo`, `/map`, `/vram`, `/model`).
  - **Self-Extensible UI:** Ask the agent to inject custom dashboard widgets or charts live.
- 🧬 **On-the-Go Fine-Tuning Pipeline:** Carry datasets on your USB and run 4-bit QLoRA fine-tuning directly on the lab computer's 6GB GPU, including automated harvesting of git commit history (`git log -p`).

---

## 📊 Hardware Budget Math (6GB VRAM + 32GB RAM)

| Component | Allocation | Role |
| :--- | :--- | :--- |
| **OS & Window Manager** | ~700 MB | OS display headroom (Windows DWM / X11) |
| **Dedicated VRAM Ceiling** | **5,400 MB** | Safe limit enforced by GhostHarness `MemoryManager` |
| **Fast Model (7B Q4_K_M)** | ~4,300 MB + ~800 MB KV | **100% in VRAM** (0% Spill, 45-60 tok/s) |
| **Heavy Model (14B Q4_K_M)**| 4,800 MB VRAM + 4,200 MB RAM | **Hybrid Offload** (26 layers on GPU, remainder in 32GB RAM) |
| **Fine-Tuning (4-bit QLoRA)**| ~4,900 MB VRAM | Rank 8, Batch Size 1, Gradient Checkpointing enabled |

---

## 📁 Repository Architecture

```text
GhostHarness/
├── core/
│   ├── agent.py            # Agentic loop with AST RepoMap & Auto-Compaction
│   ├── checkpoint.py       # Atomic snapshot stack & rollback engine (/undo)
│   ├── dynamic_router.py   # Auto-switch between 7B (pure VRAM) and 14B (heavy)
│   ├── engine.py           # Multi-backend runner (LM Studio / llama-server / Ollama)
│   ├── memory_manager.py   # Live VRAM/RAM telemetry & zero-spill guard
│   ├── multimodal.py       # Whisper voice dictation & local vision sidecars
│   ├── repo_map.py         # Compressed AST codebase symbol mapper
│   ├── cli.py              # Claude Code style rich terminal interface
│   └── config.py           # Configuration parameters and hardware thresholds
├── tools/
│   ├── filesystem.py       # Surgical diff patcher with fuzzy matching fallback
│   ├── terminal.py         # Non-root user-space shell execution sandbox
│   ├── search.py           # Fast regex grep and file pattern discovery
│   ├── researcher.py       # AST codebase architecture analyzer & doc fetcher
│   └── mcp_client.py       # Production JSON-RPC 2.0 stdio MCP Client
├── web/                    # Modern Visual Workspace GUI
│   ├── server.py           # FastAPI backend with SSE streaming & undo endpoints
│   └── static/
│       ├── index.html      # Visual workspace with VRAM gauges & voice dictation
│       ├── styles.css      # Dark-mode styling with glassmorphism
│       └── app.js          # Reactive frontend & dynamic UI plugin loader
├── finetune/
│   ├── lora_trainer.py     # 6GB VRAM 4-bit QLoRA trainer
│   ├── dataset_loader.py   # Harvests codebases and git commit logs into ChatML JSONL
│   └── export_gguf.py      # Merges LoRA adapters for immediate deployment
├── scripts/
│   ├── launch.sh           # Linux zero-admin launcher
│   ├── launch.bat          # Windows zero-admin launcher
│   └── setup_usb.py        # USB offline bundler (wheels + models)
├── requirements.txt
└── pyproject.toml
```

---

## 🚀 Quickstart Guide

### 1. Launch with LM Studio (Zero Configuration)
1. Start **LM Studio** on the machine.
2. Load your model (e.g. `qwen2.5-coder-7b-instruct` or abliterated equivalent).
3. Start the local server on `http://127.0.0.1:1234`.
4. Launch GhostHarness:
   ```bash
   # Visual Workspace Web GUI
   ./scripts/launch.sh --gui

   # Or Terminal TUI mode
   ./scripts/launch.sh
   ```

### 2. Windows Lab Computer
Double-click `scripts\launch.bat` (or pass `--gui` in command prompt).

### 3. Setting Up a 100% Offline USB Drive
On your personal computer connected to the internet:
```bash
python scripts/setup_usb.py /path/to/my_usb_drive
```
This downloads all wheels and sets up the offline installer. Plug the USB into the university computer and launch without internet access!

---

## 🧬 On-The-Go Fine-Tuning on 6GB VRAM

Carry your codebase or git histories on your USB drive and fine-tune Qwen right in the lab:

```bash
# 1. Ingest git commit history into training pairs
python -c "from finetune.dataset_loader import USBDatasetLoader; USBDatasetLoader.harvest_git_commits('.', 'commits.jsonl')"

# 2. Run 4-bit QLoRA (Tuned strictly for 6GB VRAM)
python finetune/lora_trainer.py --dataset commits.jsonl --model Qwen/Qwen2.5-Coder-7B-Instruct

# 3. Merge adapter back into base weights
python finetune/export_gguf.py --base Qwen/Qwen2.5-Coder-7B-Instruct --adapter ./lora_adapter --output ./merged_model
```
