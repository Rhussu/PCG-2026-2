from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentConfig:
    """Configuración global para agentes LLM y memoria, adaptado para servidor local 2x RTX 4090."""

    # Conexión LLM (vLLM / Ollama con OpenAI Compatible API)
    llm_base_url: str = field(
        default_factory=lambda: os.getenv("LLM_BASE_URL", "http://localhost:8000/v1")
    )
    llm_api_key: str = field(
        default_factory=lambda: os.getenv("LLM_API_KEY", "EMPTY")
    )
    llm_model: str = field(
        default_factory=lambda: os.getenv("LLM_MODEL", "meta-llama/Llama-3.1-8B-Instruct")
    )
    temperature: float = field(
        default_factory=lambda: float(os.getenv("LLM_TEMPERATURE", "0.1"))
    )
    max_tokens: int = field(
        default_factory=lambda: int(os.getenv("LLM_MAX_TOKENS", "128"))
    )
    request_timeout: float = field(
        default_factory=lambda: float(os.getenv("LLM_REQUEST_TIMEOUT", "30.0"))
    )

    # Conexión Embeddings para RAG
    embedding_base_url: str = field(
        default_factory=lambda: os.getenv("EMBEDDING_BASE_URL", "http://localhost:8000/v1")
    )
    embedding_api_key: str = field(
        default_factory=lambda: os.getenv("EMBEDDING_API_KEY", "EMPTY")
    )
    embedding_model: str = field(
        default_factory=lambda: os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-en-v1.5")
    )

    # Memoria Clásica (Historial)
    classic_history_window: int = 10  # Número de turnos (pares observación-acción) a retener

    # Memoria RAG Avanzada
    rag_top_k: int = 4  # Número de memorias contextuales a recuperar por decisión
    rag_score_threshold: float = 0.0

    # Tolerancia a fallos y modo offline
    # Si True y el servidor en las 2x RTX 4090 no responde, se usa fallback sin romper la app/test
    fallback_if_offline: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> AgentConfig:
        if not data:
            return cls()
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        filtered = {k: v for k, v in data.items() if k in valid_keys and v is not None}
        return cls(**filtered)

    def to_dict(self) -> dict[str, Any]:
        return {
            "llm_base_url": self.llm_base_url,
            "llm_api_key": self.llm_api_key if self.llm_api_key == "EMPTY" else "***",
            "llm_model": self.llm_model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "classic_history_window": self.classic_history_window,
            "rag_top_k": self.rag_top_k,
            "embedding_model": self.embedding_model,
            "fallback_if_offline": self.fallback_if_offline,
        }
