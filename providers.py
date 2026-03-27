"""
providers.py — NeuralChat v5.2
Isolated provider registry. Models verified as active March 2026.

To add a new provider:
  1. Add an entry to PROVIDERS dict below.
  2. Add a branch in build_llm().
  3. Done — nothing else changes.

Retired models (DO NOT USE):
  Cohere:  command-r-plus, command-r, command-light  (retired Sep 2025)
  Groq:    llama3-70b-8192, llama3-8b-8192           (retired May 2025)
           mixtral-8x7b-32768, gemma-7b-it            (retired 2025)
"""

from __future__ import annotations

# ── Provider registry ─────────────────────────────────────────
PROVIDERS: dict[str, dict] = {
    "Cohere": {
        "label":         "Cohere",
        "default_model": "command-a-03-2025",
        "models": [
            "command-a-03-2025",        # flagship, 256k ctx — recommended
            "command-r-plus-08-2024",   # strong, 128k ctx
            "command-r-08-2024",        # balanced, 128k ctx
            "command-r7b-12-2024",      # fast & cheap, 128k ctx
        ],
        "api_key":     "",              # set via UI
        "cost_per_1k": 0.0025,
        "docs_url":    "https://docs.cohere.com/docs/models",
    },
    "OpenAI": {
        "label":         "OpenAI",
        "default_model": "gpt-4o-mini",
        "models": [
            "gpt-4.1",                  # latest flagship
            "gpt-4.1-mini",             # fast & affordable
            "gpt-4o",                   # vision-capable
            "gpt-4o-mini",              # default — best value
        ],
        "api_key":     "",
        "cost_per_1k": 0.0006,
        "docs_url":    "https://platform.openai.com/docs/models",
    },
    "Groq": {
        "label":         "Groq",
        "default_model": "llama-3.1-8b-instant",
        "models": [
            "llama-3.3-70b-versatile",  # best quality on Groq
            "llama-3.1-70b-versatile",  # strong, 128k ctx
            "llama-3.1-8b-instant",     # default — extremely fast & free
            "gemma2-9b-it",             # Google Gemma 2, 8k ctx
        ],
        "api_key":     "",
        "cost_per_1k": 0.00006,
        "docs_url":    "https://console.groq.com/docs/models",
    },
}

ACTIVE_PROVIDER = "Cohere"


def get_provider(name: str | None = None) -> dict:
    return PROVIDERS[name or ACTIVE_PROVIDER]


def build_llm(provider_name: str, model: str, temperature: float, max_tokens: int, api_key: str):
    """
    Isolated LLM builder.
    api_key is passed explicitly — no global state, no Streamlit imports.
    """
    if not api_key:
        raise ValueError(
            f"No API key provided for {provider_name}. "
            f"Go to ⚙ Settings → API Keys and enter your key."
        )

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

    raise ValueError(f"Unknown provider: '{provider_name}'. Add it to providers.py.")
