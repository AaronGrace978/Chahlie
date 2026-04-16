"""
Configuration for Chahlie
Supports both Anthropic and Ollama backends
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Backend Configuration
# Options: "anthropic" or "ollama"
BACKEND = os.getenv("CHAHLIE_BACKEND", "ollama")

# Anthropic Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = "claude-sonnet-4-20250514"

# Ollama Configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")  # Good default for agentic work

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
