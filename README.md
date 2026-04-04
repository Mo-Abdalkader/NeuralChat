# NeuralChat

**A full-stack AI chatbot supporting multiple LLM providers, 4 prompting strategies, streaming responses, and per-session memory — deployed as a single service on Railway.**

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Railway-7c3aed?style=flat&logo=railway)](https://neuralchat-production.up.railway.app)
[![GitHub](https://img.shields.io/badge/GitHub-NeuralChat-181717?style=flat&logo=github)](https://github.com/Mo-Abdalkader/NeuralChat)
[![Python](https://img.shields.io/badge/Python-3.11-3776ab?style=flat&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![LangChain](https://img.shields.io/badge/LangChain-0.3+-1c3c3c?style=flat)](https://langchain.com)

---

## What it does

NeuralChat lets you chat with AI models from Cohere, OpenAI, Groq, and Gemini — switching providers and models from the UI with no code changes. It goes beyond a basic API wrapper by letting you control *how* the AI reasons, not just *what* you ask.

---

## Features

| Feature | Details |
|---|---|
| **4 AI providers** | Cohere · OpenAI · Groq · Gemini |
| **14+ models** | command-a-03-2025, GPT-4.1, Llama 3.3 70B, Gemini 2.0 Flash and more |
| **Custom model name** | Type any model ID not in the preset list |
| **4 prompting modes** | Zero-Shot, Few-Shot, Chain-of-Thought, Structured Output |
| **6 personas** | Assistant, Engineer, Analyst, Writer, Teacher, Data Scientist |
| **Streaming** | Word-by-word SSE responses with live typing indicator |
| **Memory** | Per-session history with configurable depth (1–20 message pairs) |
| **Markdown** | Full markdown + syntax-highlighted code blocks with copy button |
| **Cost tracking** | Token count, latency, and USD cost shown per message |
| **Free shared key** | 20 requests/day — bring your own key for unlimited use |

---

## Prompting modes

| Mode | What it does | Best for |
|---|---|---|
| **Zero-Shot** | Direct question, no extras | General Q&A, code help, summaries |
| **Few-Shot** | Show 2–5 examples first; AI learns the pattern | Classification, SQL, email rewriting |
| **Chain-of-Thought** | Forces numbered step-by-step reasoning | Math, logic, debugging |
| **Structured Output** | Returns answer + confidence score + key points + follow-up | Research, analysis, reports |

> **Memory** is a sidebar toggle that works across all modes. When ON, the AI sees your previous messages (up to the configured depth). When OFF, every message is treated as a fresh question.

---

## Project structure

```
neuralchat/
├── main.py          # FastAPI routes, SSE streaming, static file serving
├── engine.py        # LangChain engine — runner dispatch, memory management
├── providers.py     # LLM builder — Cohere, OpenAI, Groq, Gemini abstraction + instance cache
├── config.py        # All constants — modes, personas, presets, prompts
├── schemas.py       # Pydantic request/response models
├── requirements.txt
├── Procfile         # Railway start command
├── railway.toml     # Railway deployment config
└── frontend/
    ├── index.html
    ├── styles.css
    └── script.js
```

---

## Run locally

```bash
git clone https://github.com/Mo-Abdalkader/NeuralChat.git
cd NeuralChat
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Open `http://localhost:8000`. Enter your API key in the sidebar.

**Get free keys:**
- Cohere → https://dashboard.cohere.com/api-keys
- OpenAI → https://platform.openai.com/api-keys
- Groq   → https://console.groq.com/keys *(free, extremely fast)*
- Gemini → https://aistudio.google.com/app/apikey *(free tier available)*

---

## Deploy to Railway

```bash
git init && git add . && git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/NeuralChat.git
git push -u origin main
```

Railway dashboard → **New Project → Deploy from GitHub repo → Generate Domain.**

**Optional environment variables** (Railway → Variables tab):

| Variable | Description |
|---|---|
| `DEFAULT_API_KEY` | Shared key for users without their own |
| `DAILY_FREE_LIMIT` | Max free requests per device per day (default: `20`) |

---

## Adding a new provider

The codebase is designed so that adding a provider touches exactly **two places**.

**Step 1 — Install the LangChain package**

```bash
pip install langchain-mistralai        # example: Mistral
```

Add it to `requirements.txt`:

```
langchain-mistralai>=0.1.0
```

**Step 2 — Register the provider in `providers.py`**

Add an entry to the `PROVIDERS` dict:

```python
"Mistral": {
    "label":         "Mistral",
    "default_model": "mistral-large-latest",
    "models": [
        "mistral-large-latest",
        "mistral-small-latest",
        "codestral-latest",
        "__custom__",               # keep this to allow custom model names
    ],
    "api_key":     "",
    "cost_per_1k": 0.002,
    "docs_url":    "https://docs.mistral.ai/getting-started/models/",
    "speed_label": "⚡ Fast",
},
```

Then add a branch in `build_llm()` (in the same file):

```python
if provider_name == "Mistral":
    from langchain_mistralai import ChatMistralAI
    return ChatMistralAI(
        api_key=api_key,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
```

**Step 3 — Add the provider to the frontend fallback in `script.js`**

In `CFG.PROVIDERS_FALLBACK`:

```javascript
Mistral: {
  models:  ["mistral-large-latest","mistral-small-latest","codestral-latest"],
  default: "mistral-large-latest",
  cost:    0.002,
  docs:    "https://docs.mistral.ai/getting-started/models/",
  tier:    '<span class="tier-pay">⚡ Pay-as-you-go</span>',
  speed:   '<span class="tier-fast">⚡ Fast</span>',
},
```

**Step 4 — Add the provider option to `index.html`**

```html
<option value="Mistral">Mistral</option>
```

**Step 5 — (Optional) Add short model display names in `script.js`**

In `CFG.MODEL_SHORT`:

```javascript
"mistral-large-latest":  "Mistral Large",
"mistral-small-latest":  "Mistral Small · fast",
"codestral-latest":      "Codestral · code",
```

That's it. `engine.py`, `main.py`, and `schemas.py` require no changes.

---

## API endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Chat UI |
| `POST` | `/chat` | Full JSON response |
| `POST` | `/stream` | SSE word-by-word stream |
| `GET` | `/settings` | Providers, models, modes, personas |
| `POST` | `/reset-memory` | Clear session memory |
| `GET` | `/health` | Health check |
| `GET` | `/docs` | Swagger interactive API docs |

---

## Tech stack

- **Backend** — FastAPI, LangChain Core, Pydantic v2, Uvicorn
- **Providers** — `langchain-cohere`, `langchain-openai`, `langchain-groq`, `langchain-google-genai`
- **Frontend** — Vanilla HTML/CSS/JS, marked.js, highlight.js
- **Deployment** — Railway (Nixpacks, no Docker needed)

---

## Built by

**Mohamed Abdalkader** — AI Engineer
[GitHub](https://github.com/Mo-Abdalkader) · [LinkedIn](https://linkedin.com/in/MohamedAbdalkader) · [Portfolio](https://mo-abdalkader.github.io/Portfolio)
