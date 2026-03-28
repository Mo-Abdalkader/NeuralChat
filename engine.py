from __future__ import annotations

import json
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    FewShotChatMessagePromptTemplate,
    MessagesPlaceholder,
)
from langchain_core.output_parsers import StrOutputParser
from langchain_core.chat_history import InMemoryChatMessageHistory

from providers import build_llm


# ── Reply dataclass ───────────────────────────────────────────

@dataclass
class Reply:
    text:       str
    tokens:     int   = 0
    latency_ms: int   = 0
    cost_usd:   float = 0.0
    mode:       str   = ""
    provider:   str   = ""
    model:      str   = ""


# ── Base runner ───────────────────────────────────────────────

class BaseRunner(ABC):
    def __init__(self, llm):
        self.llm = llm

    @abstractmethod
    def run(self, user_input: str, **kw) -> str: ...

    @staticmethod
    def _sys(custom: str, persona: str) -> str:
        return custom.strip() if custom.strip() else persona

    @staticmethod
    def _history_messages(history: InMemoryChatMessageHistory | None) -> list:
        """Return messages list from history object, safe if None."""
        if history is None:
            return []
        return history.messages or []

    @staticmethod
    def _save_turn(
        history: InMemoryChatMessageHistory | None,
        user_input: str,
        ai_response: str,
    ) -> None:
        """Manually persist the human/AI turn into history."""
        if history is None:
            return
        history.add_message(HumanMessage(content=user_input))
        history.add_message(AIMessage(content=ai_response))


# ── Runners ───────────────────────────────────────────────────

class ZeroShotRunner(BaseRunner):
    def run(self, user_input: str, **kw) -> str:
        sys_text       = self._sys(kw.get("custom_sys", ""), kw.get("persona_prompt", ""))
        mem_on         = kw.get("memory_enabled", True)
        get_hist       = kw.get("get_history")
        session_id     = kw.get("session_id", "default")

        history = get_hist(session_id) if (mem_on and get_hist) else None
        past    = self._history_messages(history)

        # Build message list: system + past history + current input
        messages = [SystemMessage(content=sys_text)] + past + [HumanMessage(content=user_input)]
        response = self.llm.invoke(messages).content

        self._save_turn(history, user_input, response)
        return response


class FewShotRunner(BaseRunner):
    def run(self, user_input: str, **kw) -> str:
        examples = kw.get("examples", [])
        sys_text  = self._sys(kw.get("custom_sys", ""), kw.get("persona_prompt", ""))

        # Fall back to ZeroShot (with memory) if no examples provided
        if not examples:
            return ZeroShotRunner(self.llm).run(user_input, **kw)

        ex_prompt = ChatPromptTemplate.from_messages([
            ("human", "{input}"), ("ai", "{output}"),
        ])
        fs_block = FewShotChatMessagePromptTemplate(
            example_prompt=ex_prompt, examples=examples,
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system", sys_text), fs_block, ("human", "{input}"),
        ])
        return (prompt | self.llm | StrOutputParser()).invoke({"input": user_input})


class ChainOfThoughtRunner(BaseRunner):
    def run(self, user_input: str, **kw) -> str:
        steps    = kw.get("cot_steps", 3)
        steps_md = "\n".join(f"**Step {i}:** <your reasoning here>" for i in range(1, steps + 1))
        sys_text = (
            f"You are a careful reasoning assistant.\n"
            f"Think through the problem in exactly {steps} numbered markdown-bold steps, "
            f"then state your Final Answer clearly.\n\n"
            f"{steps_md}\n\n"
            f"✅ **Final Answer:** <concise answer>"
        )
        return self.llm.invoke([
            SystemMessage(content=sys_text),
            HumanMessage(content=user_input),
        ]).content


class MemoryChainRunner(BaseRunner):
    def run(self, user_input: str, **kw) -> str:
        sys_text   = self._sys(kw.get("custom_sys", ""), kw.get("persona_prompt", ""))
        get_hist   = kw.get("get_history")
        session_id = kw.get("session_id", "default")

        # Memory Chain always uses history regardless of memory_enabled toggle
        history = get_hist(session_id) if get_hist else None
        past    = self._history_messages(history)

        messages  = [SystemMessage(content=sys_text)] + past + [HumanMessage(content=user_input)]
        response  = self.llm.invoke(messages).content

        self._save_turn(history, user_input, response)
        return response


class StructuredOutputRunner(BaseRunner):
    _SCHEMA = """{
  "answer":     "<full markdown answer>",
  "confidence": "<High | Medium | Low>",
  "key_points": ["point 1", "point 2", "point 3"],
  "follow_up":  "<one relevant follow-up question>"
}"""

    def run(self, user_input: str, **kw) -> str:
        sys_text = (
            "Reply ONLY with a valid JSON object matching the schema below. "
            "No markdown fences. No preamble. No extra keys.\n\n"
            f"Schema:\n{self._SCHEMA}"
        )
        raw   = self.llm.invoke([
            SystemMessage(content=sys_text),
            HumanMessage(content=user_input),
        ]).content.strip()

        clean = re.sub(r"```json|```", "", raw).strip()
        try:
            d    = json.loads(clean)
            conf = d.get("confidence", "")
            mark = {"High": "●", "Medium": "◑", "Low": "○"}.get(conf, "·")
            pts  = "\n".join(f"- {p}" for p in d.get("key_points", []))
            return (
                f"{d.get('answer', '')}\n\n"
                f"---\n"
                f"**Confidence** {mark} {conf}  ·  **Key Points**\n{pts}\n\n"
                f"> 💡 {d.get('follow_up', '')}"
            )
        except Exception:
            return raw


# ── Engine ────────────────────────────────────────────────────

class NeuralChatEngine:
    """
    Public API — completely UI-agnostic.

    Memory is managed manually per session_id.
    Each session has its own InMemoryChatMessageHistory.
    History is passed directly to the LLM call and updated after each turn.
    """

    _RUNNERS: dict[str, type[BaseRunner]] = {
        "Zero-Shot":         ZeroShotRunner,
        "Few-Shot":          FewShotRunner,
        "Chain-of-Thought":  ChainOfThoughtRunner,
        "Memory Chain":      MemoryChainRunner,
        "Structured Output": StructuredOutputRunner,
    }

    def __init__(self):
        self._store: dict[str, InMemoryChatMessageHistory] = {}

    def get_history(self, session_id: str) -> InMemoryChatMessageHistory:
        if session_id not in self._store:
            self._store[session_id] = InMemoryChatMessageHistory()
        return self._store[session_id]

    def reset_memory(self, session_id: str | None = None) -> None:
        if session_id and session_id in self._store:
            self._store[session_id].clear()
        else:
            self._store.clear()

    def chat(
        self,
        user_input:     str,
        mode:           str,
        persona_prompt: str,
        provider:       str,
        model:          str,
        api_key:        str,
        temperature:    float,
        max_tokens:     int,
        memory_enabled: bool  = True,
        cot_steps:      int   = 3,
        examples:       list  | None = None,
        custom_sys:     str   = "",
        session_id:     str   = "default",
        cost_per_1k:    float = 0.003,
    ) -> Reply:
        llm    = build_llm(provider, model, temperature, max_tokens, api_key)
        runner = self._RUNNERS.get(mode, ZeroShotRunner)(llm)

        t0 = time.monotonic()
        try:
            text = runner.run(
                user_input,
                persona_prompt  = persona_prompt,
                custom_sys      = custom_sys,
                memory_enabled  = memory_enabled,
                cot_steps       = cot_steps,
                examples        = examples or [],
                get_history     = self.get_history,
                session_id      = session_id,
            )
        except Exception as exc:
            text = f"**Error:** `{exc}`"

        latency_ms = int((time.monotonic() - t0) * 1000)
        tokens     = int(len(text.split()) * 1.35)
        cost_usd   = (tokens / 1000) * cost_per_1k

        return Reply(
            text       = text,
            tokens     = tokens,
            latency_ms = latency_ms,
            cost_usd   = cost_usd,
            mode       = mode,
            provider   = provider,
            model      = model,
        )
