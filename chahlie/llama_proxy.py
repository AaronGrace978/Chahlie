"""
OpenAI-compatible LLM proxy for Chahlie.

Forwards /v1/chat/completions (and /v1/models) to a local Ollama instance
or Ollama Cloud. Run this on a machine with a GPU (or Ollama Cloud key) so
friends can point Chahlie at your proxy instead of needing their own key.

Launch:
    python -m chahlie.llama_proxy
    python -m chahlie.llama_proxy --port 11435 --upstream http://localhost:11434

Environment:
    LLAMA_PROXY_PORT          — listen port (default 11435)
    LLAMA_PROXY_UPSTREAM      — Ollama base URL (default http://localhost:11434)
    LLAMA_PROXY_API_KEY       — optional bearer token clients must send
    OLLAMA_API_KEY            — forwarded to Ollama Cloud when upstream is ollama.com
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Any, Optional

import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn

DEFAULT_PORT = int(os.getenv("LLAMA_PROXY_PORT", "11435"))
DEFAULT_UPSTREAM = os.getenv("LLAMA_PROXY_UPSTREAM", "http://localhost:11434").rstrip("/")
PROXY_API_KEY = os.getenv("LLAMA_PROXY_API_KEY", "").strip()
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "").strip()

app = FastAPI(title="Chahlie Llama Proxy", version="1.0")


def _check_auth(request: Request) -> None:
    if not PROXY_API_KEY:
        return
    auth = request.headers.get("Authorization", "")
    if auth == f"Bearer {PROXY_API_KEY}":
        return
    raise HTTPException(status_code=401, detail="Invalid or missing proxy API key")


def _upstream_headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if OLLAMA_API_KEY and "ollama.com" in DEFAULT_UPSTREAM:
        headers["Authorization"] = f"Bearer {OLLAMA_API_KEY}"
    return headers


def _ollama_chat_url() -> str:
    # Ollama exposes OpenAI-compatible chat at /v1/chat/completions
    if DEFAULT_UPSTREAM.endswith("/v1"):
        return f"{DEFAULT_UPSTREAM}/chat/completions"
    return f"{DEFAULT_UPSTREAM}/v1/chat/completions"


def _ollama_models_url() -> str:
    if DEFAULT_UPSTREAM.endswith("/v1"):
        return f"{DEFAULT_UPSTREAM}/models"
    return f"{DEFAULT_UPSTREAM}/v1/models"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "upstream": DEFAULT_UPSTREAM}


@app.get("/v1/models")
def list_models(request: Request) -> JSONResponse:
    _check_auth(request)
    try:
        resp = requests.get(_ollama_models_url(), headers=_upstream_headers(), timeout=20)
        return JSONResponse(content=resp.json(), status_code=resp.status_code)
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/v1/chat/completions")
async def chat_completions(request: Request) -> StreamingResponse | JSONResponse:
    _check_auth(request)
    body: dict[str, Any] = await request.json()
    stream = bool(body.get("stream", False))

    try:
        resp = requests.post(
            _ollama_chat_url(),
            headers=_upstream_headers(),
            json=body,
            stream=stream,
            timeout=120,
        )
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if stream:
        def _iter():
            for chunk in resp.iter_content(chunk_size=None):
                if chunk:
                    yield chunk

        return StreamingResponse(_iter(), media_type="text/event-stream")

    return JSONResponse(content=resp.json(), status_code=resp.status_code)


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Chahlie OpenAI-compatible Llama proxy")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--upstream", default=DEFAULT_UPSTREAM)
    args = parser.parse_args(argv)

    global DEFAULT_UPSTREAM
    DEFAULT_UPSTREAM = args.upstream.rstrip("/")

    print(f"Chahlie Llama proxy on http://{args.host}:{args.port}")
    print(f"  Upstream: {DEFAULT_UPSTREAM}")
    print(f"  Auth: {'required' if PROXY_API_KEY else 'none'}")
    print()
    print("Point Chahlie at this proxy:")
    print(f"  CHAHLIE_BACKEND=openai-compatible")
    print(f"  OPENAI_COMPATIBLE_URL=http://{args.host}:{args.port}/v1")
    if PROXY_API_KEY:
        print(f"  OPENAI_COMPATIBLE_API_KEY={PROXY_API_KEY}")

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
