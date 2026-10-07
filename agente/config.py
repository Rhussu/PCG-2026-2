from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from dotenv import load_dotenv

# Cargar automáticamente variables de entorno desde .env si existe
load_dotenv()


@dataclass
class AgentConfig:
    """Configuración global para agentes LLM y memoria, adaptado para servidor local 2x RTX 4090."""

    # Conexión LLM (Ollama / vLLM con OpenAI Compatible API en 2x RTX 4090)
    llm_base_url: str = field(
        default_factory=lambda: os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
    )
    llm_api_key: str = field(
        default_factory=lambda: os.getenv("LLM_API_KEY", "EMPTY")
    )
    llm_model: str = field(
        default_factory=lambda: os.getenv("LLM_MODEL", "qwen3:32b")
    )
    temperature: float = field(
        default_factory=lambda: float(os.getenv("LLM_TEMPERATURE", "0.1"))
    )
    max_tokens: int = field(
        default_factory=lambda: int(os.getenv("LLM_MAX_TOKENS", "512"))
    )
    request_timeout: float = field(
        default_factory=lambda: float(os.getenv("LLM_REQUEST_TIMEOUT", "60.0"))
    )

    # Conexión Embeddings para RAG
    embedding_base_url: str = field(
        default_factory=lambda: os.getenv("EMBEDDING_BASE_URL", "http://localhost:11434/v1")
    )
    embedding_api_key: str = field(
        default_factory=lambda: os.getenv("EMBEDDING_API_KEY", "EMPTY")
    )
    embedding_model: str = field(
        default_factory=lambda: os.getenv("EMBEDDING_MODEL", "bge-m3:latest")
    )

    # Memoria Clásica (Historial)
    classic_history_window: int = 10  # Número de turnos (pares observación-acción) a retener

    # Memoria RAG Avanzada
    rag_top_k: int = 4  # Número de memorias contextuales a recuperar por decisión
    rag_score_threshold: float = 0.0

    # Tolerancia a fallos y modo offline (deshabilitado: fallos en el modelo levantan error para detener el test)
    fallback_if_offline: bool = False

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


def get_installed_ollama_models(base_url: str = "http://localhost:11434", timeout: float = 3.0) -> list[str]:
    """Consulta la API de Ollama (/api/tags) y retorna la lista ordenada de modelos descargados."""
    import json
    import urllib.request

    clean_url = (base_url or "http://localhost:11434").rstrip("/")
    if clean_url.endswith("/v1"):
        clean_url = clean_url[:-3]
    tags_url = f"{clean_url}/api/tags"
    try:
        req = urllib.request.Request(tags_url, headers={"User-Agent": "PCG-Agent"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = [m["name"] for m in data.get("models", []) if isinstance(m, dict) and "name" in m]
            return sorted(models)
    except Exception:
        return []

