"""
main.py — NeuralChat API v1
FastAPI backend. engine.py / providers.py / config.py are untouched.

Run:
    uvicorn main:app --reload --port 8000

Environment variables (set on Railway dashboard or in .env):
    DEFAULT_API_KEY   — shared Cohere key used when users don't supply their own
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

from config import (
    APP_NAME, APP_VERSION,
    MODES, PERSONAS, FEW_SHOT_PRESETS, EXAMPLE_PROMPTS,
)
from providers import PROVIDERS, ACTIVE_PROVIDER
from engine import NeuralChatEngine
from schemas import (
    ChatRequest, ChatResponse,
    ResetMemoryRequest, ResetMemoryResponse,
    SettingsResponse, ProviderInfo, ModeInfo, PersonaInfo, FewShotPreset,
    FewShotExample,
    StreamRequest,
    ErrorResponse,
)

# ════════════════════════════════════════════════════════════════
#  SERVER-SIDE CONFIG  (from environment variables)
# ════════════════════════════════════════════════════════════════

# The default shared API key — read from env var, NEVER exposed to the frontend.
# On Railway: set DEFAULT_API_KEY in the Variables tab.
# Locally:    set it in your shell or .env file.
_DEFAULT_API_KEY   = os.getenv("DEFAULT_API_KEY", "").strip()
_DAILY_FREE_LIMIT  = int(os.getenv("DAILY_FREE_LIMIT", "20"))


# ════════════════════════════════════════════════════════════════
#  PATHS
# ════════════════════════════════════════════════════════════════

BACKEND_DIR  = pathlib.Path(__file__).parent
_flat        = BACKEND_DIR / "frontend"
_nested      = BACKEND_DIR.parent / "frontend"
FRONTEND_DIR = _flat if _flat.exists() else _nested


# ════════════════════════════════════════════════════════════════
#  ENGINE
# ════════════════════════════════════════════════════════════════

_engine = NeuralChatEngine()


@asynccontextmanager
async def lifespan(app: FastAPI):
    key_status = "✓ set" if _DEFAULT_API_KEY else "✗ not set (users must supply own key)"
    print(f"🚀 {APP_NAME} API v{APP_VERSION} — http://localhost:8000")
    print(f"   Frontend dir: {FRONTEND_DIR}")
    print(f"   DEFAULT_API_KEY: {key_status}")
    print(f"   Daily free limit: {_DAILY_FREE_LIMIT}")
    yield
    print(f"🛑 {APP_NAME} shutting down.")
    _engine.reset_memory()


# ════════════════════════════════════════════════════════════════
#  APP
# ════════════════════════════════════════════════════════════════

app = FastAPI(
    title=f"{APP_NAME} API",
    version=APP_VERSION,
    description=(
        "LangChain-powered multi-mode chatbot API. "
        "Supports Zero-Shot, Few-Shot, Chain-of-Thought, Memory Chain, Structured Output."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


# ════════════════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════════════════

def _resolve_api_key(provider: str, user_key: str) -> str:
    """
    Return the key to use for the request.
    Priority: user-supplied key > DEFAULT_API_KEY env var.
    Raises 400 if neither is available.
    """
    key = (user_key or "").strip() or _DEFAULT_API_KEY
    if not key:
        raise HTTPException(
            status_code=400,
            detail=(
                f"No API key for {provider}. "
                "Enter your own key in the sidebar, or ask the administrator "
                "to set DEFAULT_API_KEY on the server."
            ),
        )
    return key


def _persona_prompt(persona_name: str, custom: str) -> str:
    if custom.strip():
        return custom.strip()
    p = PERSONAS.get(persona_name)
    if not p:
        raise HTTPException(400, f"Unknown persona: '{persona_name}'")
    return p["prompt"]


def _validate(mode: str, provider: str, model: str) -> None:
    if mode not in MODES:
        raise HTTPException(400, f"Unknown mode '{mode}'. Valid: {list(MODES)}")
    if provider not in PROVIDERS:
        raise HTTPException(400, f"Unknown provider '{provider}'. Valid: {list(PROVIDERS)}")
    if model not in PROVIDERS[provider]["models"]:
        raise HTTPException(
            400,
            f"Model '{model}' not available for {provider}. "
            f"Valid: {PROVIDERS[provider]['models']}",
        )


def _coerce_examples(raw) -> list[dict] | None:
    if not raw:
        return None
    result = []
    for ex in raw:
        if isinstance(ex, FewShotExample):
            result.append({"input": ex.input, "output": ex.output})
        elif isinstance(ex, dict):
            result.append(ex)
    return result or None


def _build_engine_kwargs(req, resolved_key: str) -> dict:
    return dict(
        user_input     = req.user_input,
        mode           = req.mode,
        persona_prompt = _persona_prompt(req.persona, req.custom_system_prompt),
        provider       = req.provider,
        model          = req.model,
        api_key        = resolved_key,
        temperature    = req.temperature,
        max_tokens     = req.max_tokens,
        memory_enabled = req.memory_enabled,
        cot_steps      = req.cot_steps,
        examples       = _coerce_examples(req.examples),
        custom_sys     = req.custom_system_prompt,
        session_id     = req.session_id,
        cost_per_1k    = PROVIDERS[req.provider]["cost_per_1k"],
    )


# ════════════════════════════════════════════════════════════════
#  ROUTES
# ════════════════════════════════════════════════════════════════

# ── Frontend entry ────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_index():
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return HTMLResponse(content=index.read_text(encoding="utf-8"))
    return HTMLResponse(
        "<h2>NeuralChat API running.</h2>"
        "<p>Visit <a href='/docs'>/docs</a> for API reference.</p>"
    )

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    for name in ("favicon.ico", "icon.ico", "icon.png"):
        p = FRONTEND_DIR / name
        if p.exists():
            mt = "image/x-icon" if name.endswith(".ico") else "image/png"
            return Response(content=p.read_bytes(), media_type=mt)
    # Return a minimal transparent 1x1 ICO so browsers stop 404-ing
    ico = bytes([
        0,0,1,0,1,0,1,1,0,0,1,0,24,0,40,0,0,0,22,0,0,0,
        40,0,0,0,1,0,0,0,2,0,0,0,1,0,24,0,0,0,0,0,4,0,0,0,
        0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
        0,0,0,0,0,0,0,0,
    ])
    return Response(content=ico, media_type="image/x-icon")


# ── POST /chat ────────────────────────────────────────────────

@app.post(
    "/chat",
    response_model=ChatResponse,
    summary="Send a message — full response",
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def chat(req: ChatRequest):
    _validate(req.mode, req.provider, req.model)
    resolved_key = _resolve_api_key(req.provider, req.api_key)
    kwargs = _build_engine_kwargs(req, resolved_key)
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


# ── POST /stream ──────────────────────────────────────────────

@app.post("/stream", summary="Stream a response via Server-Sent Events",
          responses={400: {"model": ErrorResponse}})
async def stream_chat(req: StreamRequest):
    _validate(req.mode, req.provider, req.model)
    resolved_key = _resolve_api_key(req.provider, req.api_key)
    kwargs = _build_engine_kwargs(req, resolved_key)

    async def generate() -> AsyncGenerator[str, None]:
        try:
            reply = await asyncio.get_event_loop().run_in_executor(
                None, lambda: _engine.chat(**kwargs)
            )
            words = reply.text.split(" ")
            for i, word in enumerate(words):
                chunk = word + (" " if i < len(words) - 1 else "")
                yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
                await asyncio.sleep(0.010)
            yield f"data: {json.dumps({'type': 'done', 'tokens': reply.tokens, 'latency_ms': reply.latency_ms, 'cost_usd': reply.cost_usd, 'mode': reply.mode, 'provider': reply.provider, 'model': reply.model})}\n\n"
        except ValueError as exc:
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'message': f'Engine error: {exc}'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── POST /reset-memory ────────────────────────────────────────

@app.post("/reset-memory", response_model=ResetMemoryResponse,
          summary="Clear conversation memory")
async def reset_memory(req: ResetMemoryRequest = ResetMemoryRequest()):
    if req.session_id and req.session_id in _engine._store:
        _engine._store.pop(req.session_id)
        return ResetMemoryResponse(
            success=True, message=f"Memory cleared for session '{req.session_id}'.",
            session_id=req.session_id,
        )
    _engine.reset_memory()
    return ResetMemoryResponse(success=True, message="All session memory cleared.")


# ── GET /settings ─────────────────────────────────────────────

@app.get("/settings", response_model=SettingsResponse,
         summary="Get providers, models, modes, personas and server config")
async def get_settings():
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
            "provider":       ACTIVE_PROVIDER,
            "model":          PROVIDERS[ACTIVE_PROVIDER]["default_model"],
            "mode":           "Zero-Shot",
            "persona":        "Assistant",
            "temperature":    0.7,
            "max_tokens":     1024,
            "cot_steps":      3,
            "memory_enabled": True,
        },
        # Tell the frontend whether a default server-side key exists.
        # We never send the key itself — only a boolean.
        has_default_key  = bool(_DEFAULT_API_KEY),
        daily_free_limit = _DAILY_FREE_LIMIT,
    )


# ── GET /health ───────────────────────────────────────────────

@app.get("/health", include_in_schema=False)
async def health():
    return {"status": "ok", "app": APP_NAME, "version": APP_VERSION,
            "has_default_key": bool(_DEFAULT_API_KEY)}
