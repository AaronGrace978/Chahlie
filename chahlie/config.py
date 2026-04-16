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
OLLAMA_CLOUD_HOST = "https://ollama.com"  # Official Ollama Cloud API

# Available Ollama Cloud Models (as of April 2026):
# Top picks for agentic coding:
# - glm-5.1        (SOTA for agentic engineering, SWE-Bench Pro leader)
# - qwen3.5        (6.3M pulls - multimodal, thinking, tools)
# - devstral-small-2 (24B - excels at multi-file editing)
# - gemma4         (3.3M pulls - frontier performance, vision+tools)
# - deepseek-v3.2  (efficient reasoning + agent performance)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "glm-5.1")

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

# Cursor Boston Info
CURSOR_BOSTON = {
    "name": "Cursor Boston",
    "tagline": "Boston's Home for AI-Powered Development",
    "website": "https://cursorboston.com",
    "github": "https://github.com/AaronGrace978/Chahlie",
    "description": "The community for Boston developers building with Cursor IDE",
}

# Credits
CREDITS = {
    "organization": "Cursor Boston",
    "founder": "Robert Hunt",
    "founder_title": "Cursor Boston Ambassador",
    "cmo": "Aaron Grace",
}
