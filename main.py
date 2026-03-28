"""main.py — NeuralChat v6.2

Run:
    uvicorn main:app --reload --port 8000

Env vars:
    DEFAULT_API_KEY   — shared key used when users omit their own
    DAILY_FREE_LIMIT  — max free requests per device per day (default: 20)
"""
from __future__ import annotations

import asyncio
import json
import os
import pathlib
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from config import APP_NAME, APP_VERSION, MODES, PERSONAS, FEW_SHOT_PRESETS, EXAMPLE_PROMPTS
from providers import PROVIDERS, ACTIVE_PROVIDER
from engine import NeuralChatEngine
from schemas import (
    ChatRequest, ChatResponse,
    ResetMemoryRequest, ResetMemoryResponse,
    SettingsResponse, ProviderInfo, ModeInfo, PersonaInfo, FewShotPreset, FewShotExample,
    StreamRequest, ErrorResponse,
)

_DEFAULT_API_KEY  = os.getenv("DEFAULT_API_KEY", "").strip()
_DAILY_FREE_LIMIT = int(os.getenv("DAILY_FREE_LIMIT", "20"))

BACKEND_DIR  = pathlib.Path(__file__).parent
_flat        = BACKEND_DIR / "frontend"
_nested      = BACKEND_DIR.parent / "frontend"
FRONTEND_DIR = _flat if _flat.exists() else _nested

_engine = NeuralChatEngine()


@asynccontextmanager
async def lifespan(app: FastAPI):
    key_status = "set" if _DEFAULT_API_KEY else "not set"
    print(f"🚀 {APP_NAME} v{APP_VERSION} — DEFAULT_API_KEY: {key_status} — limit: {_DAILY_FREE_LIMIT}/day")
    yield
    _engine.reset_memory()


app = FastAPI(
    title=f"{APP_NAME} API",
    version=APP_VERSION,
    description="LangChain-powered multi-mode chatbot. Zero-Shot · Few-Shot · Chain-of-Thought · Structured Output.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


def _resolve_key(provider: str, user_key: str) -> str:
    """Return the API key to use, preferring the user-supplied one."""
    key = (user_key or "").strip() or _DEFAULT_API_KEY
    if not key:
        raise HTTPException(400, f"No API key for {provider}. Add your key in the sidebar.")
    return key


def _persona_prompt(name: str, custom: str) -> str:
    """Return the effective system prompt for the chosen persona."""
    if custom.strip():
        return custom.strip()
    p = PERSONAS.get(name)
    if not p:
        raise HTTPException(400, f"Unknown persona: '{name}'")
    return p["prompt"]


def _validate(mode: str, provider: str, model: str) -> None:
    """Raise 400 if mode, provider, or model is not recognised."""
    if mode not in MODES:
        raise HTTPException(400, f"Unknown mode '{mode}'.")
    if provider not in PROVIDERS:
        raise HTTPException(400, f"Unknown provider '{provider}'.")
    if model not in PROVIDERS[provider]["models"]:
        raise HTTPException(400, f"Model '{model}' not available for {provider}.")


def _coerce_examples(raw) -> list[dict] | None:
    """Convert FewShotExample objects or dicts into plain dicts."""
    if not raw:
        return None
    result = []
    for ex in raw:
        if isinstance(ex, FewShotExample):
            result.append({"input": ex.input, "output": ex.output})
        elif isinstance(ex, dict):
            result.append(ex)
    return result or None


def _engine_kwargs(req, key: str) -> dict:
    """Build the kwargs dict for engine.chat()."""
    return dict(
        user_input     = req.user_input,
        mode           = req.mode,
        persona_prompt = _persona_prompt(req.persona, req.custom_system_prompt),
        provider       = req.provider,
        model          = req.model,
        api_key        = key,
        temperature    = req.temperature,
        max_tokens     = req.max_tokens,
        memory_enabled = req.memory_enabled,
        memory_depth   = req.memory_depth,
        cot_steps      = req.cot_steps,
        examples       = _coerce_examples(req.examples),
        custom_sys     = req.custom_system_prompt,
        session_id     = req.session_id,
        cost_per_1k    = PROVIDERS[req.provider]["cost_per_1k"],
    )


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_index():
    """Serve the frontend HTML."""
    idx = FRONTEND_DIR / "index.html"
    if idx.exists():
        return HTMLResponse(content=idx.read_text(encoding="utf-8"))
    return HTMLResponse("<h2>NeuralChat API running.</h2><p><a href='/docs'>/docs</a></p>")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Serve the favicon or a transparent 1×1 fallback."""
    for name in ("favicon.ico", "icon.ico", "icon.png"):
        p = FRONTEND_DIR / name
        if p.exists():
            mt = "image/x-icon" if name.endswith(".ico") else "image/png"
            return Response(content=p.read_bytes(), media_type=mt)
    ico = bytes([
        0,0,1,0,1,0,1,1,0,0,1,0,24,0,40,0,0,0,22,0,0,0,
        40,0,0,0,1,0,0,0,2,0,0,0,1,0,24,0,0,0,0,0,4,0,0,0,
        0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
        0,0,0,0,0,0,0,0,
    ])
    return Response(content=ico, media_type="image/x-icon")


@app.post("/chat", response_model=ChatResponse,
          responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def chat(req: ChatRequest):
    """Run a full (non-streaming) chat completion."""
    _validate(req.mode, req.provider, req.model)
    key    = _resolve_key(req.provider, req.api_key)
    kwargs = _engine_kwargs(req, key)
    try:
        reply = await asyncio.get_event_loop().run_in_executor(
            None, lambda: _engine.chat(**kwargs)
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        raise HTTPException(500, f"Engine error: {exc}")
    return ChatResponse(
        text=reply.text, tokens=reply.tokens, latency_ms=reply.latency_ms,
        cost_usd=reply.cost_usd, mode=reply.mode, provider=reply.provider, model=reply.model,
    )


@app.post("/stream", responses={400: {"model": ErrorResponse}})
async def stream_chat(req: StreamRequest):
    """Stream a chat response token-by-token via Server-Sent Events."""
    _validate(req.mode, req.provider, req.model)
    key    = _resolve_key(req.provider, req.api_key)
    kwargs = _engine_kwargs(req, key)

    async def generate() -> AsyncGenerator[str, None]:
        try:
            reply = await asyncio.get_event_loop().run_in_executor(
                None, lambda: _engine.chat(**kwargs)
            )
            for i, word in enumerate(reply.text.split(" ")):
                chunk = word + (" " if i < len(reply.text.split(" ")) - 1 else "")
                yield f"data: {json.dumps({'type':'token','content':chunk})}\n\n"
                await asyncio.sleep(0.010)
            yield f"data: {json.dumps({'type':'done','tokens':reply.tokens,'latency_ms':reply.latency_ms,'cost_usd':reply.cost_usd,'mode':reply.mode,'provider':reply.provider,'model':reply.model})}\n\n"
        except ValueError as exc:
            yield f"data: {json.dumps({'type':'error','message':str(exc)})}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type':'error','message':f'Engine error: {exc}'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/reset-memory", response_model=ResetMemoryResponse)
async def reset_memory(req: ResetMemoryRequest = ResetMemoryRequest()):
    """Clear conversation memory for one session or all sessions."""
    if req.session_id and req.session_id in _engine._store:
        _engine._store.pop(req.session_id)
        return ResetMemoryResponse(success=True, message=f"Memory cleared for '{req.session_id}'.", session_id=req.session_id)
    _engine.reset_memory()
    return ResetMemoryResponse(success=True, message="All session memory cleared.")


@app.get("/settings", response_model=SettingsResponse)
async def get_settings():
    """Return all provider, mode, persona, and server configuration to the frontend."""
    return SettingsResponse(
        providers={
            name: ProviderInfo(
                label=p["label"], default_model=p["default_model"],
                models=p["models"], cost_per_1k=p["cost_per_1k"], docs_url=p["docs_url"],
            )
            for name, p in PROVIDERS.items()
        },
        active_provider=ACTIVE_PROVIDER,
        modes={
            name: ModeInfo(
                icon=m["icon"], description=m["description"],
                when_to_use=m["when_to_use"], example=m["example"],
            )
            for name, m in MODES.items()
        },
        personas={
            name: PersonaInfo(prompt=p["prompt"], tip=p["tip"], icon=p["icon"])
            for name, p in PERSONAS.items()
        },
        few_shot_presets={
            name: FewShotPreset(
                description=pr["description"],
                examples=[FewShotExample(input=e["input"], output=e["output"]) for e in pr["examples"]],
            )
            for name, pr in FEW_SHOT_PRESETS.items()
        },
        example_prompts=EXAMPLE_PROMPTS,
        defaults={
            "provider": ACTIVE_PROVIDER,
            "model":    PROVIDERS[ACTIVE_PROVIDER]["default_model"],
            "mode":     "Zero-Shot", "persona": "Assistant",
            "temperature": 0.7, "max_tokens": 1024,
            "cot_steps": 3, "memory_enabled": True, "memory_depth": 5,
        },
        has_default_key  = bool(_DEFAULT_API_KEY),
        daily_free_limit = _DAILY_FREE_LIMIT,
    )


@app.get("/health", include_in_schema=False)
async def health():
    """Health check endpoint for Railway."""
    return {"status": "ok", "app": APP_NAME, "version": APP_VERSION,
            "has_default_key": bool(_DEFAULT_API_KEY)}