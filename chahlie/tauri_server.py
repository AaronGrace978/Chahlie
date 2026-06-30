"""
Local HTTP API for the Chahlie Tauri desktop shell.

Launch:  python -m chahlie.tauri_server --port 18765
"""

from __future__ import annotations

import argparse
import json
import os
import threading
from dataclasses import asdict
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import uvicorn

from . import __codename__, __version__
from .agent import ChahlieAgent
from .config import BACKEND, OLLAMA_CLOUD_MODEL, OLLAMA_LOCAL_MODEL, OPENAI_COMPATIBLE_MODEL
from .deck_setup import (
    needs_api_key_setup,
    reload_config,
    save_api_key,
    verify_api_key,
)
from .personality import get_greeting
from .tools import set_approval_hook

app = FastAPI(title="Chahlie Tauri API", version=__version__)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_agent: Optional[ChahlieAgent] = None
_agent_lock = threading.Lock()
_approval_lock = threading.Lock()
_approval_pending: Optional[dict] = None
_approval_event = threading.Event()
_approval_result = False


def _get_agent() -> ChahlieAgent:
    global _agent
    with _agent_lock:
        if _agent is None:
            set_approval_hook(_approval_prompter)
            _agent = ChahlieAgent()
        return _agent


def _reset_agent() -> None:
    global _agent
    with _agent_lock:
        if _agent is not None:
            _agent.reset()
        else:
            set_approval_hook(_approval_prompter)
            _agent = ChahlieAgent()


def _approval_prompter(command: str, reason: str) -> bool:
    global _approval_pending, _approval_result
    with _approval_lock:
        _approval_pending = {"command": command, "reason": reason}
        _approval_result = False
        _approval_event.clear()
    if not _approval_event.wait(timeout=300):
        with _approval_lock:
            _approval_pending = None
        return False
    with _approval_lock:
        result = _approval_result
        _approval_pending = None
        _approval_event.clear()
    return result


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)


class KeyRequest(BaseModel):
    api_key: str = Field(min_length=8)


class ApprovalRequest(BaseModel):
    approved: bool


def _event_to_dict(evt) -> dict:
    data = asdict(evt)
    if data.get("data") is None:
        data.pop("data", None)
    return data


def _sse_stream(message: str):
    agent = _get_agent()
    for evt in agent.process(message):
        payload = json.dumps(_event_to_dict(evt))
        yield f"data: {payload}\n\n"
    yield "data: {\"type\": \"stream_end\", \"content\": \"\"}\n\n"


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/api/status")
def status():
    agent = _get_agent()
    cost = agent.get_cost_summary()
    model = OLLAMA_CLOUD_MODEL if BACKEND == "ollama-cloud" else OLLAMA_LOCAL_MODEL
    if BACKEND == "openai-compatible":
        model = OPENAI_COMPATIBLE_MODEL
    return {
        "version": __version__,
        "codename": __codename__,
        "backend": cost.get("backend", BACKEND),
        "model": model,
        "cost": cost.get("formatted", "$0.00"),
        "needs_api_key": needs_api_key_setup(),
        "greeting": get_greeting(),
    }


@app.post("/api/chat")
def chat(body: ChatRequest):
    msg = body.message.strip()
    if not msg:
        raise HTTPException(status_code=400, detail="Empty message")
    return StreamingResponse(
        _sse_stream(msg),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/key")
def set_key(body: KeyRequest):
    ok, err = verify_api_key(body.api_key)
    if not ok:
        raise HTTPException(status_code=400, detail=err)
    save_api_key(body.api_key)
    reload_config()
    global _agent
    with _agent_lock:
        set_approval_hook(_approval_prompter)
        _agent = ChahlieAgent()
    return {"ok": True}


@app.post("/api/reset")
def reset_chat():
    _reset_agent()
    return {"ok": True}


@app.get("/api/approval/pending")
def approval_pending():
    with _approval_lock:
        return {"pending": _approval_pending}


@app.post("/api/approval/respond")
def approval_respond(body: ApprovalRequest):
    global _approval_result
    with _approval_lock:
        if _approval_pending is None:
            raise HTTPException(status_code=409, detail="No approval pending")
        _approval_result = body.approved
        _approval_event.set()
    return {"ok": True}


def main() -> None:
    parser = argparse.ArgumentParser(description="Chahlie Tauri backend")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18765)
    args = parser.parse_args()
    os.environ.setdefault("CHAHLIE_TAURI_MODE", "true")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
