# NeuralChat

**A full-stack AI chatbot supporting multiple providers, prompting strategies, and streaming responses — deployed as a single service on Railway.**

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Railway-7c3aed?style=flat&logo=railway)](https://neuralchat.up.railway.app)
[![GitHub](https://img.shields.io/badge/GitHub-NeuralChat-181717?style=flat&logo=github)](https://github.com/Mo-Abdalkader/NeuralChat)
[![Python](https://img.shields.io/badge/Python-3.11-3776ab?style=flat&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)

---

## What it does

NeuralChat lets you chat with AI models from Cohere, OpenAI, and Groq — switching providers and models from the UI with no code changes. It goes beyond a basic wrapper by giving you control over *how* the AI is prompted, not just *what* you ask.

---

## Features

| Feature | Details |
|---|---|
| **3 AI providers** | Cohere · OpenAI · Groq |
| **10+ models** | command-a-03-2025, GPT-4o, Llama 3.3 70B and more |
| **5 prompting modes** | Zero-Shot, Few-Shot, Chain-of-Thought, Memory Chain, Structured Output |
| **6 personas** | Assistant, Engineer, Analyst, Writer, Teacher, Data Scientist |
| **Streaming** | Word-by-word SSE responses |
| **Memory** | Per-session conversation history, toggleable |
| **Cost tracking** | Token count, latency, and USD cost shown per message |
| **Free shared key** | 20 requests/day — bring your own key for unlimited use |

---

## Prompting modes explained

- **Zero-Shot** — Direct question, no extras. Best for general queries.
- **Few-Shot** — Provide 2–5 examples first; the AI learns the pattern. Best for classification or formatting tasks.
- **Chain-of-Thought** — Forces numbered step-by-step reasoning before the final answer. Best for math and logic.
- **Memory Chain** — Maintains full conversation history across turns. Best for long sessions.
- **Structured Output** — Forces a JSON response with `answer`, `confidence`, `key_points`, and `follow_up`.

---

## Project structure

```
neuralchat/
├── main.py          # FastAPI routes, middleware, static file serving
├── engine.py        # LangChain engine — prompting logic, runner dispatch
├── providers.py     # LLM builder — Cohere, OpenAI, Groq abstraction
├── config.py        # All constants — modes, personas, presets
├── schemas.py       # Pydantic request/response models
├── requirements.txt
├── Procfile         # Railway / Heroku start command
├── railway.toml     # Railway deployment config
└── frontend/
    ├── index.html
    ├── styles.css
    └── script.js
```

---

## Run locally

**1. Clone and set up environment**

```bash
git clone https://github.com/Mo-Abdalkader/NeuralChat.git
cd NeuralChat
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**2. Start the server**

```bash
uvicorn main:app --reload --port 8000
```

**3. Open the app**

```
http://localhost:8000
```

Enter your API key in the sidebar. Get free keys at:
- Cohere → https://dashboard.cohere.com/api-keys
- OpenAI → https://platform.openai.com/api-keys
- Groq → https://console.groq.com/keys (free, very fast)

---

## Deploy to Railway

**One command, one service — Railway handles everything.**

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/NeuralChat.git
git push -u origin main
```

Then in Railway: **New Project → Deploy from GitHub repo → select your repo → Generate Domain.**

**Optional environment variables** (set in Railway → Variables tab):

| Variable | Description |
|---|---|
| `DEFAULT_API_KEY` | Shared key for users who don't supply their own |
| `DAILY_FREE_LIMIT` | Max free requests per device per day (default: `20`) |

---

## API endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Chat UI |
| `POST` | `/chat` | Full JSON response |
| `POST` | `/stream` | Word-by-word SSE stream |
| `GET` | `/settings` | Providers, models, modes, personas |
| `POST` | `/reset-memory` | Clear session memory |
| `GET` | `/health` | Health check |
| `GET` | `/docs` | Interactive API docs (Swagger) |

---

## Adding a new provider

Edit `providers.py` only — nothing else changes:

```python
if provider_name == "Mistral":
    from langchain_mistralai import ChatMistralAI
    return ChatMistralAI(api_key=api_key, model=model, temperature=temperature)
```

Then add the provider entry to `PROVIDERS` dict in the same file and you're done.

---

## Tech stack

- **Backend** — FastAPI, LangChain Core, Pydantic v2, Uvicorn
- **Providers** — `langchain-cohere`, `langchain-openai`, `langchain-groq`
- **Frontend** — Vanilla HTML/CSS/JS, marked.js, highlight.js
- **Deployment** — Railway (Nixpacks, no Docker needed)

---

## Built by

**Mohamed Abdalkader** — AI Engineer  
[GitHub](https://github.com/Mo-Abdalkader) · [LinkedIn](https://linkedin.com/in/MohamedAbdalkader) · [Portfolio](https://mo-abdalkader.github.io/Portfolio)
