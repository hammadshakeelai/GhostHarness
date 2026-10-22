import os
from pathlib import Path
from pydantic import BaseModel, Field

class HardwareBudgetConfig(BaseModel):
    max_vram_mb: int = Field(default=5400, description="Max VRAM allocation before offloading (6GB GPU max)")
    max_ram_mb: int = Field(default=26000, description="Max System RAM allocation (32GB system max)")
    vram_safety_margin_mb: int = Field(default=700, description="Headroom for OS desktop window manager")

class ModelConfig(BaseModel):
    fast_model: str = Field(default="qwen2.5-coder-7b-instruct", description="100% VRAM resident model for fast tool loops")
    heavy_model: str = Field(default="qwen2.5-coder-14b-instruct", description="Hybrid GPU+RAM offloaded model for complex architecture")
    context_window: int = Field(default=8192, description="Context window size (tokens)")
    api_base: str = Field(default="http://127.0.0.1:1234/v1", description="OpenAI-compatible inference endpoint (LM Studio / llama-server)")
    api_key: str = Field(default="lm-studio", description="API key (dummy for local)")
    temperature: float = Field(default=0.2, description="Sampling temperature for coding accuracy")

class AgentConfig(BaseModel):
    workspace_root: str = Field(default=str(Path.cwd()))
    require_diff_approval: bool = Field(default=True, description="Prompt user before modifying files on disk")
    require_terminal_approval: bool = Field(default=True, description="Prompt user before executing shell commands")
    max_tool_iterations: int = Field(default=25, description="Max tool execution loop steps")
    auto_switch_models: bool = Field(default=True, description="Automatically escalate complex reasoning to heavy model")

class Settings(BaseModel):
    hardware: HardwareBudgetConfig = HardwareBudgetConfig()
    models: ModelConfig = ModelConfig()
    agent: AgentConfig = AgentConfig()
    web_host: str = "127.0.0.1"
    web_port: int = 8765

settings = Settings()
