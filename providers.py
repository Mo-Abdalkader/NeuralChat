"""
providers.py — NeuralChat v6.3

To add a new provider:
  1. Add an entry to PROVIDERS dict below.
  2. Add a branch in build_llm().
  3. Done — nothing else changes.
"""

from __future__ import annotations
import hashlib
import os

# ── LLM instance cache ────────────────────────────────────────
# Key: (provider, model, api_key_hash, temperature, max_tokens)
# Reusing instances avoids re-establishing HTTPS connections on every request.
_LLM_CACHE: dict[tuple, object] = {}


def _cache_key(provider: str, model: str, api_key: str, temperature: float, max_tokens: int) -> tuple:
    """Build a cache key that never stores the raw API key."""
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
    return (provider, model, key_hash, temperature, max_tokens)


# ── Default server-side API keys (set via Railway env vars) ───
DEFAULT_KEYS: dict[str, str] = {
    "Cohere": os.getenv("DEFAULT_API_KEY", "").strip(),
    "Groq":   os.getenv("GROQ_API_KEY",    "").strip(),
}

# ── Provider registry ─────────────────────────────────────────
# Prices updated as of April 2026 · all figures are USD per 1 000 tokens
PROVIDERS: dict[str, dict] = {
    "Cohere": {
        "label":         "Cohere",
        "default_model": "command-r7b-12-2024",
        "models": [
            "command-r7b-12-2024",     # In: $0.000038/1K | Out: $0.000150/1K
            "command-a-03-2025",       # In: $0.002500/1K | Out: $0.010000/1K
            "command-r-plus-08-2024",  # In: $0.002500/1K | Out: $0.010000/1K
            "command-r-08-2024",       # In: $0.000150/1K | Out: $0.000600/1K
            "__custom__",
        ],
        "pricing": {
            "command-r7b-12-2024":    {"in_1k": 0.000038, "out_1k": 0.000150},
            "command-a-03-2025":      {"in_1k": 0.002500, "out_1k": 0.010000},
            "command-r-plus-08-2024": {"in_1k": 0.002500, "out_1k": 0.010000},
            "command-r-08-2024":      {"in_1k": 0.000150, "out_1k": 0.000600},
        },
        "api_key":     "",
        "docs_url":    "https://docs.cohere.com/docs/models",
        "speed_label": "🔵 Balanced",
    },
    "Groq": {
        "label":         "Groq",
        "default_model": "llama-3.1-8b-instant",
        "models": [
            "llama-3.1-8b-instant",     # In: $0.000050/1K | Out: $0.000080/1K
            "llama-3.3-70b-versatile",  # In: $0.000590/1K | Out: $0.000790/1K
            "groq/compound",            # In: $0.001000/1K | Out: $0.001000/1K  (est.)
            "groq/compound-mini",       # In: $0.000150/1K | Out: $0.000600/1K  (est.)
            "__custom__",
        ],
        "pricing": {
            "llama-3.1-8b-instant":    {"in_1k": 0.000050, "out_1k": 0.000080},
            "llama-3.3-70b-versatile": {"in_1k": 0.000590, "out_1k": 0.000790},
            "groq/compound":           {"in_1k": 0.001000, "out_1k": 0.001000},
            "groq/compound-mini":      {"in_1k": 0.000150, "out_1k": 0.000600},
        },
        "api_key":     "",
        "docs_url":    "https://console.groq.com/docs/models",
        "speed_label": "⚡⚡ Ultra-fast",
    },
    "OpenAI": {
        "label":         "OpenAI",
        "default_model": "gpt-4o-mini",
        "models": [
            "gpt-4.1",      # In: $0.002000/1K | Out: $0.008000/1K
            "gpt-4.1-mini", # In: $0.000400/1K | Out: $0.001600/1K
            "gpt-4o",       # In: $0.002500/1K | Out: $0.010000/1K
            "gpt-4o-mini",  # In: $0.000150/1K | Out: $0.000600/1K
            "__custom__",
        ],
        "pricing": {
            "gpt-4.1":      {"in_1k": 0.002000, "out_1k": 0.008000},
            "gpt-4.1-mini": {"in_1k": 0.000400, "out_1k": 0.001600},
            "gpt-4o":       {"in_1k": 0.002500, "out_1k": 0.010000},
            "gpt-4o-mini":  {"in_1k": 0.000150, "out_1k": 0.000600},
        },
        "api_key":     "",
        "docs_url":    "https://platform.openai.com/docs/models",
        "speed_label": "⚡ Fast",
    },
    "Gemini": {
        "label":         "Gemini",
        "default_model": "gemini-3.1-pro-preview",
        "models": [
            "gemini-3.1-pro-preview",        # In: $0.002000/1K | Out: $0.012000/1K
            "gemini-3-flash-preview",        # In: $0.000500/1K | Out: $0.003000/1K
            "gemini-3.1-flash-lite-preview", # In: $0.000250/1K | Out: $0.001500/1K
            "gemini-2.5-flash",              # In: $0.000300/1K | Out: $0.002500/1K
            "gemini-2.5-flash-lite",         # In: $0.000100/1K | Out: $0.000400/1K
            "__custom__",
        ],
        "pricing": {
            "gemini-3.1-pro-preview":        {"in_1k": 0.002000, "out_1k": 0.012000},
            "gemini-3-flash-preview":        {"in_1k": 0.000500, "out_1k": 0.003000},
            "gemini-3.1-flash-lite-preview": {"in_1k": 0.000250, "out_1k": 0.001500},
            "gemini-2.5-flash":              {"in_1k": 0.000300, "out_1k": 0.002500},
            "gemini-2.5-flash-lite":         {"in_1k": 0.000100, "out_1k": 0.000400},
        },
        "api_key":     "",
        "docs_url":    "https://ai.google.dev/gemini-api/docs/models/gemini",
        "speed_label": "⚡ Fast",
    },
}

ACTIVE_PROVIDER = "Cohere"


def get_provider(name: str | None = None) -> dict:
    return PROVIDERS[name or ACTIVE_PROVIDER]


def get_model_pricing(provider_name: str, model: str) -> tuple[float, float]:
    """
    Return (price_in_per_1k, price_out_per_1k) for a known model.
    Falls back to (0.0, 0.0) for custom or unrecognised models so the
    caller can substitute user-supplied prices.
    """
    pricing = PROVIDERS.get(provider_name, {}).get("pricing", {})
    entry   = pricing.get(model)
    if entry:
        return entry["in_1k"], entry["out_1k"]
    return 0.0, 0.0


def build_llm(provider_name: str, model: str, temperature: float, max_tokens: int, api_key: str):
    """
    Return a cached LLM instance when possible, otherwise build and cache a new one.
    api_key is passed explicitly — no global state.
    """
    if not api_key:
        raise ValueError(
            f"No API key provided for {provider_name}. "
            f"Go to ⚙ Settings → API Keys and enter your key."
        )

    ck = _cache_key(provider_name, model, api_key, temperature, max_tokens)
    if ck in _LLM_CACHE:
        return _LLM_CACHE[ck]

    llm = _build_fresh(provider_name, model, temperature, max_tokens, api_key)
    _LLM_CACHE[ck] = llm
    return llm


def _build_fresh(provider_name: str, model: str, temperature: float, max_tokens: int, api_key: str):
    """Construct a brand-new LLM instance (called only on cache miss)."""

    if provider_name == "Cohere":
        from langchain_cohere import ChatCohere
        return ChatCohere(
            cohere_api_key=api_key,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    if provider_name == "OpenAI":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            openai_api_key=api_key,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    if provider_name == "Groq":
        from langchain_groq import ChatGroq
        return ChatGroq(
            groq_api_key=api_key,
            model_name=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    if provider_name == "Gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            google_api_key=api_key,
            model=model,
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

    raise ValueError(f"Unknown provider: '{provider_name}'. Add it to providers.py.")