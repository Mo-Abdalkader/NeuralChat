"""main.py — NeuralChat v6.3

Run:
    uvicorn main:app --reload --port 8000

Env vars:
    DEFAULT_API_KEY   — shared Cohere key used when users omit their own
    GROQ_API_KEY      — shared Groq key used when users omit their own
    DAILY_FREE_LIMIT  — max free requests per device per provider per day (default: 20)
"""
from __future__ import annotations

import asyncio
import json
import os
import pathlib
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import date
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from config import APP_NAME, APP_VERSION, MODES, PERSONAS, FEW_SHOT_PRESETS, EXAMPLE_PROMPTS
from providers import PROVIDERS, ACTIVE_PROVIDER, DEFAULT_KEYS, get_model_pricing
from engine import NeuralChatEngine
from schemas import (
    ChatRequest, ChatResponse,
    ResetMemoryRequest, ResetMemoryResponse,
    SettingsResponse, ProviderInfo, ModelPricing, ModeInfo, PersonaInfo,
    FewShotPreset, FewShotExample,
    StreamRequest, ErrorResponse,
)

_DAILY_FREE_LIMIT = int(os.getenv("DAILY_FREE_LIMIT", "20"))

BACKEND_DIR  = pathlib.Path(__file__).parent
_flat        = BACKEND_DIR / "frontend"
_nested      = BACKEND_DIR.parent / "frontend"
FRONTEND_DIR = _flat if _flat.exists() else _nested

_engine = NeuralChatEngine()

# ── Per-device, per-provider daily usage counter ───────────────
# Structure: { (device_id, provider, iso_date): request_count }
# Resets automatically because the date is part of the key.
_usage: dict[tuple[str, str, str], int] = defaultdict(int)


def _device_id(request: Request) -> str:
    """
    Best-effort stable device identifier derived from the request.
    Uses X-Device-ID header when the frontend sends one, otherwise
    falls back to the client IP address.
    """
    return (
        request.headers.get("X-Device-ID", "").strip()
        or request.client.host
        or "unknown"
    )


def _check_and_increment_usage(device: str, provider: str) -> None:
    """
    Raise HTTP 429 if the device has exhausted today's free quota for this
    provider, otherwise increment the counter.  Only applies when a server-side
    default key is being used (users with their own key are exempt).
    """
    key = (device, provider, date.today().isoformat())
    if _usage[key] >= _DAILY_FREE_LIMIT:
        raise HTTPException(
            429,
            f"Daily limit of {_DAILY_FREE_LIMIT} free requests reached for {provider}. "
            "Add your own API key in the sidebar to continue.",
        )
    _usage[key] += 1


@asynccontextmanager
async def lifespan(app: FastAPI):
    cohere_status = "set" if DEFAULT_KEYS.get("Cohere") else "not set"
    groq_status   = "set" if DEFAULT_KEYS.get("Groq")   else "not set"
    print(
        f"🚀 {APP_NAME} v{APP_VERSION} — "
        f"Cohere key: {cohere_status} · Groq key: {groq_status} — "
        f"limit: {_DAILY_FREE_LIMIT}/provider/day"
    )
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


def _resolve_key(provider: str, user_key: str, device: str) -> tuple[str, bool]:
    """
    Return (api_key, using_default_key).

    Priority:
      1. User-supplied key  → unlimited, no quota tracking
      2. Server default key for this provider (from env var)  → quota applies
      3. Neither             → 400 error
    """
    explicit = (user_key or "").strip()
    if explicit:
        return explicit, False

    default = DEFAULT_KEYS.get(provider, "")
    if default:
        return default, True

    raise HTTPException(
        400,
        f"No API key for {provider}. Add your key in the sidebar.",
    )


def _resolve_pricing(req) -> tuple[float, float]:
    """
    Return (price_in_1k, price_out_1k) for this request.

    For known models the registry is authoritative.
    For custom models the user-supplied prices are used (defaulting to 0.0
    if omitted, which is a valid choice for providers that are free-tier).
    """
    in_price, out_price = get_model_pricing(req.provider, req.model)
    if in_price == 0.0 and out_price == 0.0:
        # Unknown / custom model — fall back to user-supplied values
        in_price  = req.custom_price_in_1k  or 0.0
        out_price = req.custom_price_out_1k or 0.0
    return in_price, out_price


def _persona_prompt(name: str, custom: str) -> str:
    """Return the effective system prompt for the chosen persona."""
    if custom.strip():
        return custom.strip()
    p = PERSONAS.get(name)
    if not p:
        raise HTTPException(400, f"Unknown persona: '{name}'")
    return p["prompt"]


def _validate(mode: str, provider: str, model: str) -> None:
    """
    Raise 400 if mode or provider is unknown.
    Model validation is intentionally relaxed — any non-empty string is accepted
    so users can supply custom model names not in the preset list.
    """
    if mode not in MODES:
        raise HTTPException(400, f"Unknown mode '{mode}'.")
    if provider not in PROVIDERS:
        raise HTTPException(400, f"Unknown provider '{provider}'.")
    if not model or not model.strip():
        raise HTTPException(400, "Model name cannot be empty.")
    # '__custom__' sentinel must have been replaced by the actual name before reaching here
    if model == "__custom__":
        raise HTTPException(400, "Select 'Custom model…' and enter a model name.")


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
    price_in, price_out = _resolve_pricing(req)
    return dict(
        user_input     = req.user_input,
        mode           = req.mode,
        persona_prompt = _persona_prompt(req.persona, req.custom_system_prompt),
        provider       = req.provider,
        model          = req.model,
        api_key        = key,
        temperature    = req.temperature,
        max_tokens     = req.max_tokens,
        price_in_1k    = price_in,
        price_out_1k   = price_out,
        memory_enabled = req.memory_enabled,
        memory_depth   = req.memory_depth,
        cot_steps      = req.cot_steps,
        examples       = _coerce_examples(req.examples),
        custom_sys     = req.custom_system_prompt,
        session_id     = req.session_id,
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
          responses={400: {"model": ErrorResponse}, 429: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def chat(req: ChatRequest, request: Request):
    """Run a full (non-streaming) chat completion."""
    _validate(req.mode, req.provider, req.model)
    device = _device_id(request)
    key, using_default = _resolve_key(req.provider, req.api_key, device)
    if using_default:
        _check_and_increment_usage(device, req.provider)
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
        text          = reply.text,
        input_tokens  = reply.input_tokens,
        output_tokens = reply.output_tokens,
        tokens        = reply.tokens,
        latency_ms    = reply.latency_ms,
        cost_usd      = reply.cost_usd,
        mode          = reply.mode,
        provider      = reply.provider,
        model         = reply.model,
    )


@app.post("/stream", responses={400: {"model": ErrorResponse}, 429: {"model": ErrorResponse}})
async def stream_chat(req: StreamRequest, request: Request):
    """Stream a chat response token-by-token via Server-Sent Events."""
    _validate(req.mode, req.provider, req.model)
    device = _device_id(request)
    key, using_default = _resolve_key(req.provider, req.api_key, device)
    if using_default:
        _check_and_increment_usage(device, req.provider)
    kwargs = _engine_kwargs(req, key)

    async def generate() -> AsyncGenerator[str, None]:
        try:
            reply = await asyncio.get_event_loop().run_in_executor(
                None, lambda: _engine.chat(**kwargs)
            )
            words = reply.text.split(" ")
            for i, word in enumerate(words):
                chunk = word + (" " if i < len(words) - 1 else "")
                yield f"data: {json.dumps({'type':'token','content':chunk})}\n\n"
                await asyncio.sleep(0.010)
            yield f"data: {json.dumps({'type':'done','input_tokens':reply.input_tokens,'output_tokens':reply.output_tokens,'tokens':reply.tokens,'latency_ms':reply.latency_ms,'cost_usd':reply.cost_usd,'mode':reply.mode,'provider':reply.provider,'model':reply.model})}\n\n"
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
    # Expose preset models only (filter out the __custom__ sentinel)
    def visible_models(models: list[str]) -> list[str]:
        return [m for m in models if m != "__custom__"]

    return SettingsResponse(
        providers={
            name: ProviderInfo(
                label         = p["label"],
                default_model = p["default_model"],
                models        = visible_models(p["models"]),
                pricing       = {
                    model: ModelPricing(in_1k=prices["in_1k"], out_1k=prices["out_1k"])
                    for model, prices in p["pricing"].items()
                },
                docs_url      = p["docs_url"],
                speed_label   = p.get("speed_label", ""),
            )
            for name, p in PROVIDERS.items()
        },
        active_provider=ACTIVE_PROVIDER,
        modes={
            name: ModeInfo(
                icon        = m["icon"],
                description = m["description"],
                when_to_use = m["when_to_use"],
                example     = m["example"],
            )
            for name, m in MODES.items()
        },
        personas={
            name: PersonaInfo(prompt=p["prompt"], tip=p["tip"], icon=p["icon"])
            for name, p in PERSONAS.items()
        },
        few_shot_presets={
            name: FewShotPreset(
                description = pr["description"],
                examples    = [FewShotExample(input=e["input"], output=e["output"]) for e in pr["examples"]],
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
            "memory_depth":   5,
        },
        has_default_key  = bool(DEFAULT_KEYS.get("Cohere") or DEFAULT_KEYS.get("Groq")),
        daily_free_limit = _DAILY_FREE_LIMIT,
    )


@app.get("/usage", include_in_schema=False)
async def usage_status(request: Request):
    """Return today's usage counts for the calling device, per provider."""
    device = _device_id(request)
    today  = date.today().isoformat()
    counts = {
        provider: _usage.get((device, provider, today), 0)
        for provider in PROVIDERS
    }
    return {
        "device":      device,
        "date":        today,
        "limit":       _DAILY_FREE_LIMIT,
        "usage":       counts,
        "has_default": {p: bool(k) for p, k in DEFAULT_KEYS.items()},
    }


@app.get("/health", include_in_schema=False)
async def health():
    """Health check endpoint for Railway."""
    return {
        "status":         "ok",
        "app":            APP_NAME,
        "version":        APP_VERSION,
        "has_cohere_key": bool(DEFAULT_KEYS.get("Cohere")),
        "has_groq_key":   bool(DEFAULT_KEYS.get("Groq")),
    }