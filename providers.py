"""
providers.py — NeuralChat v6.3

To add a new provider:
  1. Add an entry to PROVIDERS dict below.
  2. Add a branch in build_llm().
  3. Done — nothing else changes.
"""

from __future__ import annotations
import hashlib

# ── LLM instance cache ────────────────────────────────────────
# Key: (provider, model, api_key_hash, temperature, max_tokens)
# Reusing instances avoids re-establishing HTTPS connections on every request.
_LLM_CACHE: dict[tuple, object] = {}


def _cache_key(provider: str, model: str, api_key: str, temperature: float, max_tokens: int) -> tuple:
    """Build a cache key that never stores the raw API key."""
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
    return (provider, model, key_hash, temperature, max_tokens)


# ── Provider registry ─────────────────────────────────────────
PROVIDERS: dict[str, dict] = {
    "Cohere": {
        "label": "Cohere",
        "default_model": "command-r7b-12-2024",
        "models": [
            "command-r7b-12-2024",
            "command-a-03-2025",
            "command-r-plus-08-2024",
            "command-r-08-2024",
            "__custom__",
        ],
        "api_key": "",
        "cost_per_1k": 0.0000,
        "docs_url": "https://docs.cohere.com/docs/models",
        "speed_label": "",  # 🔵 Balanced
    },
    "OpenAI": {
        "label": "OpenAI",
        "default_model": "gpt-4o-mini",
        "models": [
            "gpt-4.1",
            "gpt-4.1-mini",
            "gpt-4o",
            "gpt-4o-mini",
            "__custom__",
        ],
        "api_key": "",
        "cost_per_1k": 0.0000,
        "docs_url": "https://platform.openai.com/docs/models",
        "speed_label": "",  # ⚡ Fast
    },
    "Groq": {
        "label": "Groq",
        "default_model": "llama-3.1-8b-instant",
        "models": [
            "llama-3.1-8b-instant",
            "llama-3.3-70b-versatile",
            "groq/compound",
            "groq/compound-mini",
            "__custom__",
        ],
        "api_key": "",
        "cost_per_1k": 0.0000,
        "docs_url": "https://console.groq.com/docs/models",
        "speed_label": "",  # ⚡⚡ Ultra-fast
    },
    "Gemini": {
        "label": "Gemini",
        "default_model": "gemini-3.1-pro-preview",
        "models": [
            "gemini-3.1-pro-preview",
            "gemini-3-flash-preview",
            "gemini-3.1-flash-lite-preview",
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "__custom__",
        ],
        "api_key": "",
        "cost_per_1k": 0.0000,
        "docs_url": "https://ai.google.dev/gemini-api/docs/models/gemini",
        "speed_label": "",  # ⚡ Fast
    },
}

ACTIVE_PROVIDER = "Cohere"


def get_provider(name: str | None = None) -> dict:
    return PROVIDERS[name or ACTIVE_PROVIDER]


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
