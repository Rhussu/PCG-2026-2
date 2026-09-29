from __future__ import annotations

from typing import Any

from agente.base import BaseAgent
from agente.classic_memory_agent import ClassicMemoryAgent
from agente.config import AgentConfig
from agente.rag_memory_agent import RAGMemoryAgent
from agente.random_agent import RandomAgent

AVAILABLE_AGENTS = [
    {
        "id": "random",
        "name": "Agente Aleatorio (Baseline)",
        "badge": "CONTROL",
        "badge_color": "#abb2bf",
        "description": "Selección aleatoria uniforme entre comandos admisibles. Referencia base para benchmarks.",
        "icon": "🎲",
    },
    {
        "id": "classic_memory",
        "name": "Agente Historial Clásico (LangChain)",
        "badge": "HISTORIAL",
        "badge_color": "#61afef",
        "description": "Acumula observaciones y acciones secuenciales en una ventana deslizante de memoria conversacional.",
        "icon": "📜",
    },
    {
        "id": "rag_memory",
        "name": "Agente Memoria Avanzada (RAG LangChain)",
        "badge": "VECTORIAL RAG",
        "badge_color": "#c678dd",
        "description": "Almacén vectorial semántico que fragmenta e indexa recuerdos para recuperar hechos y mapas relevantes.",
        "icon": "🧠",
    },
]


def get_available_agents() -> list[dict[str, Any]]:
    """Retorna la lista de agentes disponibles para ser seleccionados en la interfaz gráfica."""
    return list(AVAILABLE_AGENTS)


def create_agent(agent_type: str = "random", config: AgentConfig | dict[str, Any] | None = None) -> BaseAgent:
    """Fábrica para instanciar cualquier agente soportado en el sistema."""
    cfg: AgentConfig
    if isinstance(config, AgentConfig):
        cfg = config
    elif isinstance(config, dict):
        cfg = AgentConfig.from_dict(config)
    else:
        cfg = AgentConfig()

    agent_type_clean = (agent_type or "random").lower().strip()

    if agent_type_clean in {"classic_memory", "classic", "historial"}:
        return ClassicMemoryAgent(config=cfg)

    elif agent_type_clean in {"rag_memory", "rag", "avanzado"}:
        return RAGMemoryAgent(config=cfg)

    elif agent_type_clean in {"random", "aleatorio", "baseline"}:
        return RandomAgent()

    # Fallback por defecto si no se reconoce
    return RandomAgent()
