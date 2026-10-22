# ⚡ GhostHarness System Architecture Specification (SPEC-01)

> **Document Version:** 1.2.0  
> **Status:** RATIFIED & IMPLEMENTED  
> **Target Environment:** Windows 10/11 & Linux Workstations (6GB VRAM, 32GB RAM, Zero Administrator Privileges)  
> **Primary Hardware Benchmark:** NVIDIA GeForce RTX 5060 Laptop/Desktop (6GB Discrete GDDR6 VRAM)  

---

## 1. Executive Summary & Design Invariants

GhostHarness is a fully self-contained, portable AI software engineering harness designed for developer sovereignty on restricted host machines (e.g., university computer science labs equipped with Deep Freeze, shared multi-user workstations, or enterprise locked-down laptops). 

### Non-Negotiable System Invariants:
1. **Zero Elevation Invariant:** The system must NEVER execute commands requiring `UAC` elevation, `sudo`, `Set-ExecutionPolicy Unrestricted` system-wide, or Windows Registry modifications.
2. **Zero Spill Invariant:** Discrete GPU memory consumption must strictly remain $\le 5,400\text{ MB}$, leaving $\ge 744\text{ MB}$ dedicated headroom for the OS Desktop Window Manager (DWM / X11). The model must never trigger PCIe bus memory paging into host system RAM during fast-tier operations.
3. **USB Portability Invariant:** No state, cache, model weight, or virtual environment artifact shall be written outside the repository root. `HF_HOME`, `TORCH_HOME`, and `PYTHONPYCACHEPREFIX` are bound strictly to `$PROJECT_ROOT/.cache`.
4. **Non-Destructive Reversibility Invariant:** Every mutating filesystem action must automatically record an in-memory or atomic disk snapshot before disk write. Rollback (`/undo`) must execute in $\mathcal{O}(1)$ time complexity without requiring git working tree cleanliness.

---

## 2. Hardware Budget & Memory Allocations

The memory budget is calibrated for an aggregate hardware profile of **6,144 MB Discrete VRAM + 32,768 MB Host System RAM**:

```
0 MB               4,320 MB            5,170 MB         5,400 MB      6,144 MB
┌─────────────────────┬───────────────────┬────────────────┬──────────────┐
│  Qwen 2.5 Coder 7B  │  8k Flash-Attn    │ Headroom Guard │ OS DWM / X11 │
│  Q4_K_M Weights     │  KV Cache         │ Buffer         │ Display Comp │
└─────────────────────┴───────────────────┴────────────────┴──────────────┘
│◄──────── 100% Discrete GPU Dedicated VRAM Allocation ─────────►│
```

### Exact Memory Breakdown Equations:

$$\text{VRAM}_{\text{total}} = 6,144\text{ MB}$$

$$\text{VRAM}_{\text{weights}} = 4,320\text{ MB} \quad (\text{Qwen 2.5 Coder 7B Instruct Abliterated, Q4\_K\_M})$$

$$\text{VRAM}_{\text{kv}} = 2 \times n_{\text{layers}} \times n_{\text{heads}} \times d_{\text{head}} \times L_{\text{ctx}} \times \text{sizeof}(\text{fp16}) \approx 850\text{ MB} \quad (L_{\text{ctx}} = 8,192)$$

$$\text{VRAM}_{\text{working}} = \text{VRAM}_{\text{weights}} + \text{VRAM}_{\text{kv}} = 5,170\text{ MB}$$

$$\text{Headroom}_{\text{safe}} = 5,400\text{ MB} - 5,170\text{ MB} = 230\text{ MB}$$

$$\text{OS Reserve} = 6,144\text{ MB} - 5,400\text{ MB} = 744\text{ MB}$$

If task complexity warrants multi-file architectural refactoring, `core/dynamic_router.py` automatically escalates to the **Heavy Tier (14B Q4_K_M)**:
- **GPU Layer Offload:** 26 layers assigned to discrete GPU ($4,800\text{ MB}$).
- **Host RAM Offload:** 22 layers offloaded into system RAM ($4,200\text{ MB}$).
- **Working Host Headroom:** $>20,000\text{ MB}$ available in 32GB system RAM.

---

## 3. Protocol & Tool-Calling Specifications

GhostHarness communicates via rigid JSON-RPC tool schemas conforming to OpenAI Function Calling and Anthropic Claude tool specifications.

### Tool Call JSON Schema:
```json
{
  "tool": "edit_file",
  "arguments": {
    "path": "services/queue_manager.py",
    "target": "    async def pop_task(self):\n        if self.queue:\n            return self.queue.pop(0)",
    "replacement": "    async def pop_task(self):\n        async with self._lock:\n            if self.queue:\n                return self.queue.pop(0)\n            return None"
  }
}
```

### Core Tool Contract Inventory:
1. `read_file(path: str, start_line: Optional[int], end_line: Optional[int]) -> Dict[str, Any]`
2. `write_file(path: str, content: str) -> Dict[str, Any]` (Auto-creates directories, records snapshot)
3. `edit_file(path: str, target: str, replacement: str) -> Dict[str, Any]` (Fuzzy SequenceMatcher fallback $\ge 0.85$)
4. `run_terminal(command: str, cwd: str, timeout_seconds: int) -> Dict[str, Any]` (Sandboxed, filter-guarded)
5. `grep_search(pattern: str, path: str, file_pattern: str) -> Dict[str, Any]`
6. `find_files(pattern: str, path: str) -> Dict[str, Any]`
7. `search_knowledge_base(query: str, max_results: int) -> Dict[str, Any]` (FTS5 BM25 ranked)
8. `mcp_call_tool(server_name: str, tool_name: str, arguments: dict) -> Dict[str, Any]`

---

## 4. Lifecycle Hooks Architecture

GhostHarness features a deterministic hook pipeline executing at five lifecycle interception points:

```
User Turn
   │
   ▼
[ pre_user_turn ] ──────► Telemetry snapshot & Context auto-compaction
   │
   ▼
LLM Generation & Tool Selection
   │
   ▼
[ pre_tool_call ] ──────► Security validation & Atomic Checkpoint snapshot
   │
   ▼
Tool Execution (Filesystem / Sandbox / MCP)
   │
   ▼
[ post_tool_call ] ─────► AST syntax parser & Diff registration
   │
   ▼
[ post_user_turn ] ─────► History pruning & Knowledge Base sync
```

---

## 5. Sandboxing & Safety Guards

All terminal commands executed via `tools/terminal.py` are subjected to a multi-tiered sanitization filter:

### Destructive Patterns Rejected across Windows & Linux:
- `rm -rf /`, `rm -rf /*`, `mkfs`, `dd if=`, `:(){ :|:& };:`
- `rd /s /q c:\`, `del /f /s /q c:\`, `format c:`, `diskpart`
- `remove-item -recurse -force c:\`, `del -recurse -force c:\`
- Pipeline evasion: `cmd /c "rd /s /q c:"`, nested backticks, encoded hex strings.

Commands exceeding 60 seconds (customizable) are killed via `process.kill()` with `SIGKILL` / `TerminateProcess`.
