"""
Configuration for Chahlie
Supports Ollama Cloud and local Ollama backends
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Backend Configuration
# Options: "ollama-cloud" (default), "ollama-local", or "anthropic"
BACKEND = os.getenv("CHAHLIE_BACKEND", "ollama-cloud")

# Ollama Cloud Configuration (https://ollama.com/search?c=cloud)
OLLAMA_CLOUD_API_KEY = os.getenv("OLLAMA_API_KEY")
OLLAMA_CLOUD_HOST = "https://api.ollama.com"

# Available Ollama Cloud Models (as of April 2026):
# - qwen3.5 (6.3M pulls - multimodal, great all-around)
# - qwen3-coder-next (1.1M pulls - optimized for agentic coding)
# - devstral-small-2 (24B - excels at codebases and multi-file editing)
# - glm-5.1 (newest - SOTA for agentic engineering)
# - gemma4 (3.3M pulls - frontier performance)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3-coder-next")

# Local Ollama Configuration (for self-hosted)
OLLAMA_LOCAL_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# Anthropic Configuration (legacy)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = "claude-sonnet-4-20250514"

MAX_TOKENS = 8192

# UI Theme - Fenway Green
THEME = {
    "primary": "#0C2340",      # Navy Blue
    "secondary": "#BD3039",    # Red Sox Red
    "accent": "#1E5631",       # Fenway Green
    "success": "#2ECC71",      # Success Green
    "warning": "#F39C12",      # Warning Orange
    "error": "#E74C3C",        # Error Red
    "text": "#FFFFFF",         # White text
    "muted": "#7F8C8D",        # Muted gray
}

# App Info
APP_NAME = "Chahlie"
APP_TAGLINE = "The Boston Coding Agent"
APP_VERSION = "1.0.0"
APP_CODENAME = "Green Monstah"

# Credits
CREDITS = {
    "organization": "Cursor Boston",
    "founder": "Robert Hunt",
    "cmo": "Aaron Grace",
}
