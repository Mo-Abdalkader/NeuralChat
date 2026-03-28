"""schemas.py — NeuralChat v6.2"""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field


class FewShotExample(BaseModel):
    input:  str = Field(..., description="Example user input")
    output: str = Field(..., description="Expected model output")


class ChatRequest(BaseModel):
    user_input:           str                            = Field(...,             description="The user's message")
    mode:                 str                            = Field("Zero-Shot",     description="Prompting mode")
    persona:              str                            = Field("Assistant",     description="Persona name")
    provider:             str                            = Field("Cohere",        description="LLM provider")
    model:                str                            = Field("command-a-03-2025", description="Model name")
    api_key:              str                            = Field(...,             description="Provider API key")
    temperature:          float                          = Field(0.7,  ge=0.0, le=1.0)
    max_tokens:           int                            = Field(1024, ge=128, le=4096)
    memory_enabled:       bool                           = Field(True)
    memory_depth:         int                            = Field(5,    ge=1,  le=20,  description="Max message pairs to include in history")
    cot_steps:            int                            = Field(3,    ge=2,  le=8)
    examples:             Optional[List[FewShotExample]] = Field(None)
    custom_system_prompt: str                            = Field("",              description="Override persona system prompt")
    session_id:           str                            = Field("default",       description="Session identifier for memory")


class ChatResponse(BaseModel):
    text:       str
    tokens:     int
    latency_ms: int
    cost_usd:   float
    mode:       str
    provider:   str
    model:      str


class ResetMemoryRequest(BaseModel):
    session_id: Optional[str] = Field(None, description="Session to reset; omit to reset all.")


class ResetMemoryResponse(BaseModel):
    success:    bool
    message:    str
    session_id: Optional[str] = None


class ProviderInfo(BaseModel):
    label:         str
    default_model: str
    models:        List[str]
    cost_per_1k:   float
    docs_url:      str


class ModeInfo(BaseModel):
    icon:        str
    description: str
    when_to_use: str
    example:     str


class PersonaInfo(BaseModel):
    prompt: str
    tip:    str
    icon:   str


class FewShotPreset(BaseModel):
    description: str
    examples:    List[FewShotExample]


class SettingsResponse(BaseModel):
    providers:        dict[str, ProviderInfo]
    active_provider:  str
    modes:            dict[str, ModeInfo]
    personas:         dict[str, PersonaInfo]
    few_shot_presets: dict[str, FewShotPreset]
    example_prompts:  dict[str, List[str]]
    defaults:         dict
    has_default_key:  bool = False
    daily_free_limit: int  = 20


class StreamRequest(BaseModel):
    user_input:           str
    mode:                 str   = "Zero-Shot"
    persona:              str   = "Assistant"
    provider:             str   = "Cohere"
    model:                str   = "command-a-03-2025"
    api_key:              str   = ""
    temperature:          float = Field(0.7,  ge=0.0, le=1.0)
    max_tokens:           int   = Field(1024, ge=128, le=4096)
    memory_enabled:       bool  = True
    memory_depth:         int   = Field(5, ge=1, le=20)
    cot_steps:            int   = Field(3, ge=2, le=8)
    examples:             Optional[List[FewShotExample]] = None
    custom_system_prompt: str   = ""
    session_id:           str   = "default"


class ErrorResponse(BaseModel):
    error:  str
    detail: Optional[str] = None
    code:   int           = 500