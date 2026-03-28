"""config.py — NeuralChat v6.2"""

APP_NAME    = "NeuralChat"
APP_VERSION = "6.2.0"

DEVELOPER = {
    "name":       "Mohamed Abdalkader",
    "title":      "Freelance AI Engineer",
    "university": "Zagazig University — B.Sc. Computer Science (2019–2023)",
    "location":   "Egypt",
    "bio": (
        "AI engineer specializing in LLMs, RAG systems, and medical imaging. "
        "Building end-to-end ML pipelines — from fine-tuning large language models "
        "to shipping production APIs. Passionate about LangChain, open-source AI, "
        "and tools that make intelligence accessible."
    ),
    "stack": [
        "Python", "PyTorch", "TensorFlow", "Hugging Face", "LangChain",
        "FastAPI", "Docker", "MLflow", "Azure", "AWS", "FAISS", "Streamlit",
    ],
    "links": {
        "GitHub":   "https://github.com/Mo-Abdalkader",
        "LinkedIn": "https://linkedin.com/in/MohamedAbdalkader",
        "Portfolio":"https://mo-abdalkader.github.io/Portfolio",
        "Email":    "mailto:contact@mohamed-ai.dev",
    },
}

MODES: dict[str, dict] = {
    "Zero-Shot": {
        "icon":        "○",
        "description": "Ask anything directly. The model answers from its training knowledge with no examples.",
        "when_to_use": "General questions, explanations, summaries, brainstorming.",
        "example":     "Explain how transformers work in simple terms.",
    },
    "Few-Shot": {
        "icon":        "◈",
        "description": "Provide 2–5 labelled examples first. The model learns the pattern and applies it.",
        "when_to_use": "Classification, SQL generation, email rewriting, code review.",
        "example":     '"I love this!" → Positive  ·  then ask: "This is terrible."',
    },
    "Chain-of-Thought": {
        "icon":        "◎",
        "description": "Forces numbered step-by-step reasoning before the final answer.",
        "when_to_use": "Math, logic puzzles, multi-step reasoning, Fermi estimation.",
        "example":     "How many piano tuners are there in Chicago?",
    },
    "Structured Output": {
        "icon":        "▣",
        "description": "Returns a structured card: answer, confidence score, key points, and a follow-up question.",
        "when_to_use": "Research summaries, analysis, parseable outputs, dashboards.",
        "example":     "What is Docker and why should I use it?",
    },
}

PERSONAS: dict[str, dict] = {
    "Assistant": {
        "prompt": "You are a helpful AI assistant. Be clear, accurate, and concise. Use markdown formatting.",
        "tip":    "Balanced, general-purpose responses.",
        "icon":   "🤖",
    },
    "Engineer": {
        "prompt": "You are a senior software engineer. Always provide working, production-quality code in properly tagged markdown code blocks. Explain your architectural choices.",
        "tip":    "Returns runnable code with clear explanations.",
        "icon":   "💻",
    },
    "Analyst": {
        "prompt": "You are an expert research analyst. Structure answers with headers, bullet points, and evidence. Cite your reasoning. Be thorough.",
        "tip":    "Deep, structured, evidence-based answers.",
        "icon":   "📊",
    },
    "Writer": {
        "prompt": "You are a creative writing expert. Be vivid, expressive, and imaginative. Prioritize narrative quality and style.",
        "tip":    "Expressive, narrative-driven responses.",
        "icon":   "✍️",
    },
    "Teacher": {
        "prompt": "You are a Socratic teacher. Guide the user toward understanding through carefully chosen questions and hints rather than direct answers.",
        "tip":    "Teaches by asking, not telling.",
        "icon":   "🎓",
    },
    "Data Scientist": {
        "prompt": "You are a data scientist. Prioritize statistical reasoning, data interpretation, and quantitative thinking. Use tables and structured formats where helpful.",
        "tip":    "Analytical and quantitative focus.",
        "icon":   "📈",
    },
}

FEW_SHOT_PRESETS: dict[str, dict] = {
    "Sentiment Analysis": {
        "description": "Classify text as Positive, Negative, or Neutral.",
        "examples": [
            {"input": "I absolutely love this product!",         "output": "Positive"},
            {"input": "The service was terrible and very slow.", "output": "Negative"},
            {"input": "It was okay, nothing special.",           "output": "Neutral"},
        ],
    },
    "SQL Generator": {
        "description": "Convert natural language into SQL queries.",
        "examples": [
            {"input": "All users older than 30",     "output": "SELECT * FROM users WHERE age > 30;"},
            {"input": "Count products per category", "output": "SELECT category, COUNT(*) FROM products GROUP BY category;"},
            {"input": "Top 5 most expensive items",  "output": "SELECT * FROM items ORDER BY price DESC LIMIT 5;"},
        ],
    },
    "Email Rewriter": {
        "description": "Turn casual notes into professional emails.",
        "examples": [
            {"input": "tell john meeting is cancelled",
             "output": "Hi John,\n\nI wanted to let you know that our upcoming meeting has been cancelled.\n\nBest regards"},
            {"input": "ask sarah for the report asap",
             "output": "Hi Sarah,\n\nCould you please share the report at your earliest convenience?\n\nThank you"},
        ],
    },
    "Code Reviewer": {
        "description": "Review Python code and suggest clear improvements.",
        "examples": [
            {"input": "def add(a,b): return a+b",
             "output": "Works. Add type hints:\ndef add(a: int, b: int) -> int:\n    return a + b"},
            {"input": "for i in range(len(lst)): print(lst[i])",
             "output": "Non-Pythonic. Use:\nfor item in lst:\n    print(item)"},
        ],
    },
    "Custom": {
        "description": "Define your own input → output pattern.",
        "examples": [],
    },
}

EXAMPLE_PROMPTS: dict[str, list[str]] = {
    "Zero-Shot": [
        "Explain how attention mechanisms work in transformers",
        "What are the tradeoffs between SQL and NoSQL databases?",
        "Write a Python decorator that measures execution time",
    ],
    "Few-Shot": [
        "This product completely changed my life for the better!",
        "Get all orders placed in the last 7 days",
        "remind the team about the deadline on friday",
    ],
    "Chain-of-Thought": [
        "How many golf balls fit inside a school bus?",
        "If I invest $500/month at 7% annual return for 20 years, what do I end up with?",
        "A bat and ball cost $1.10. The bat costs $1 more than the ball. How much is the ball?",
    ],
    "Structured Output": [
        "What is containerization and why does it matter?",
        "Explain the CAP theorem in distributed systems",
        "What are the SOLID principles in software engineering?",
    ],
}