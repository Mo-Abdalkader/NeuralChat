# NeuralChat — Run & Deploy Guide

## Answer to your question first

**Railway takes BOTH frontend and backend together — one single deployment.**

FastAPI serves the HTML/CSS/JS files directly as static files. You do not need a separate service
for the frontend. You push one repository, Railway runs one service, and you get one URL that
opens the full working app. That is the architecture already built into this project.

---

## Part 1 — Run on Your PC

### Step 1 — Extract the zip

Unzip `neuralchat_deploy.zip`. You will get this folder:

```
neuralchat_deploy/
├── main.py
├── engine.py
├── providers.py
├── config.py
├── schemas.py
├── requirements.txt
├── Procfile
├── railway.toml
├── runtime.txt
├── .gitignore
├── .env.example
└── frontend/
    ├── index.html
    ├── styles.css
    └── script.js
```

### Step 2 — Create a virtual environment

Open a terminal inside the `neuralchat_deploy` folder.

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

You will see `(.venv)` at the start of your terminal prompt. That means it is active.

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

This installs FastAPI, uvicorn, LangChain, Cohere, and everything else.
It takes about 60 seconds on first run.

To add OpenAI or Groq support, open `requirements.txt` and uncomment:
```
langchain-openai>=0.1.0
langchain-groq>=0.1.0
```
Then run `pip install -r requirements.txt` again.

### Step 4 — Run the server

```bash
uvicorn main:app --reload --port 8000
```

You will see:
```
🚀 NeuralChat API v5.2 — http://localhost:8000
   Frontend served from: /your/path/neuralchat_deploy/frontend
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 5 — Open the app

Open your browser and go to:
```
http://localhost:8000
```

The full app loads. The API docs are at `http://localhost:8000/docs`.

### Step 6 — Enter your API key

1. In the sidebar, select your **Provider** (Cohere, OpenAI, or Groq)
2. Paste your **API key** into the API Key field
3. Start chatting

**Where to get keys:**
- Cohere:  https://dashboard.cohere.com/api-keys  (has a free tier)
- OpenAI:  https://platform.openai.com/api-keys
- Groq:    https://console.groq.com/keys  (free, very fast)

### Stop the server

Press `Ctrl + C` in the terminal.

### Start it again later

```bash
# activate the environment first
source .venv/bin/activate      # macOS/Linux
.venv\Scripts\Activate.ps1     # Windows

# then run
uvicorn main:app --reload --port 8000
```

---

## Part 2 — Deploy to Railway

Railway is the right platform for this project. It:
- Detects Python automatically (no Dockerfile needed)
- Assigns a public HTTPS URL
- Handles the `$PORT` variable automatically
- Has a free trial and a $5/month hobby plan

**You deploy ONCE. Frontend + backend together. One service. One URL.**

---

### Step 1 — Create a GitHub repository

Railway deploys from GitHub. You need to push your code there first.

1. Go to https://github.com and sign in (or create a free account)
2. Click the **+** button → **New repository**
3. Name it `neuralchat` (or anything you want)
4. Set it to **Private** (recommended — your code stays private)
5. Do NOT tick "Add a README" (your folder already has everything)
6. Click **Create repository**

GitHub will show you a page with commands. Follow the next step.

### Step 2 — Push your code to GitHub

Open a terminal inside your `neuralchat_deploy` folder.

```bash
# Initialize git
git init

# Add all files
git add .

# First commit
git commit -m "Initial commit — NeuralChat v5.2"

# Connect to your GitHub repo (replace YOUR_USERNAME and YOUR_REPO_NAME)
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git

# Push
git branch -M main
git push -u origin main
```

**Example** (if your GitHub username is `MohamedAbdalkader`):
```bash
git remote add origin https://github.com/MohamedAbdalkader/neuralchat.git
```

Refresh your GitHub page — you should see all your files there.

### Step 3 — Sign up for Railway

1. Go to https://railway.app
2. Click **Login** → **Login with GitHub**
3. Authorize Railway to access your GitHub account
4. Complete the short onboarding (takes 2 minutes)

### Step 4 — Create a new Railway project

1. On the Railway dashboard, click **New Project**
2. Click **Deploy from GitHub repo**
3. Find and select your `neuralchat` repository
4. Click **Deploy Now**

Railway will start building immediately. You will see build logs.

### Step 5 — Wait for the build

Railway reads your `requirements.txt` and installs everything automatically.
Build takes 2–4 minutes on first run.

You will see in the logs:
```
✓ Installing dependencies from requirements.txt
✓ Build complete
🚀 NeuralChat API v5.2 — http://0.0.0.0:8000
```

### Step 6 — Generate a public URL

After the build succeeds:

1. Click on your service (the box in the Railway dashboard)
2. Click the **Settings** tab
3. Scroll to **Networking** → **Public Networking**
4. Click **Generate Domain**
5. Railway gives you a URL like: `https://neuralchat-production-xxxx.up.railway.app`

**That URL is your live app.** Open it in any browser — it works immediately.

### Step 7 — Verify it is working

Visit these URLs (replace with your actual Railway domain):

| URL | What it should show |
|-----|---------------------|
| `https://your-app.up.railway.app/` | The NeuralChat chat interface |
| `https://your-app.up.railway.app/health` | `{"status":"ok","app":"NeuralChat","version":"5.2.0"}` |
| `https://your-app.up.railway.app/docs` | FastAPI interactive documentation |

If all three work, your deployment is complete.

---

## Part 3 — After Deployment

### How updates work

Every time you push new code to GitHub, Railway redeploys automatically:

```bash
# Make your changes, then:
git add .
git commit -m "Your change description"
git push
```

Railway detects the push and redeploys in about 2 minutes. Zero downtime — the old version
keeps running until the new one is ready.

### Environment variables (optional)

If you want API keys pre-loaded on the server instead of entered by users in the UI,
you can set them as environment variables in Railway:

1. Open your Railway project
2. Click your service → **Variables** tab
3. Click **New Variable** and add:

| Variable name | Value |
|---------------|-------|
| `COHERE_API_KEY` | your Cohere key |
| `OPENAI_API_KEY` | your OpenAI key |
| `GROQ_API_KEY` | your Groq key |

Then update `providers.py` to read from environment variables:

```python
import os

PROVIDERS = {
    "Cohere": {
        ...
        "api_key": os.getenv("COHERE_API_KEY", ""),
        ...
    },
    "OpenAI": {
        ...
        "api_key": os.getenv("OPENAI_API_KEY", ""),
        ...
    },
    "Groq": {
        ...
        "api_key": os.getenv("GROQ_API_KEY", ""),
        ...
    },
}
```

After adding this, users will not need to enter keys — they just open the app and chat.

### Checking logs

In Railway → your service → **Logs** tab. You can see every request, error, and startup message in real time.

### Monitoring memory and CPU

Railway → your service → **Metrics** tab. Shows CPU, memory, and network usage.

---

## Part 4 — Troubleshooting

### "Build failed" on Railway

Most common cause: missing package in `requirements.txt`.
Check the build logs for the exact error line, then add the missing package.

### "Application failed to start"

Check that `Procfile` contains exactly:
```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```
Railway passes `$PORT` at runtime. Do not hardcode `8000` in the Procfile.

### The app opens but shows only the API, not the HTML

This means `frontend/` folder is missing or not found. Make sure your repository
has the `frontend/` folder at the root level (same level as `main.py`).

Correct structure in your GitHub repo:
```
main.py          ← at root
frontend/
  index.html     ← at root/frontend/
  styles.css
  script.js
```

### API key error in the app

The key is entered in the UI and sent with each request — it is never stored on the server.
Make sure you are using the right key for the right provider. The error message in the
chat will say exactly which provider complained.

### "Port already in use" on your PC

```bash
# Find what is using port 8000
lsof -i :8000        # macOS/Linux
netstat -ano | findstr :8000   # Windows

# Run on a different port
uvicorn main:app --reload --port 8001
# then open http://localhost:8001
```

---

## Summary

| Task | Command / Action |
|------|-----------------|
| Run locally | `uvicorn main:app --reload --port 8000` |
| Open locally | http://localhost:8000 |
| Push to GitHub | `git add . && git commit -m "msg" && git push` |
| Deploy to Railway | Connect GitHub repo in Railway dashboard |
| Update live app | `git push` — Railway auto-redeploys |
| View live logs | Railway dashboard → Logs tab |
| API docs | `https://your-app.up.railway.app/docs` |
