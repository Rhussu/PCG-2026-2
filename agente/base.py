from __future__ import annotations

import difflib
import re
from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    """Clase base abstracta para todos los agentes decisores en TextWorld."""

    def __init__(self, name: str, agent_type: str, description: str) -> None:
        self.name = name
        self.agent_type = agent_type
        self.description = description
        self.current_step: int = 0

    @abstractmethod
    def answer(self, observation: str, valid_commands: list[str]) -> str:
        """Dado el texto de observación del entorno y la lista de comandos válidos,
        retorna el comando exacto a ejecutar.
        """
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reinicia la memoria o estado interno del agente al comenzar una nueva partida."""
        pass

    @abstractmethod
    def get_metrics(self) -> dict[str, Any]:
        """Retorna las métricas computacionales acumuladas (tokens, latencias, llamadas API)."""
        pass

    def get_info(self) -> dict[str, Any]:
        """Retorna metadatos identificativos del agente."""
        return {
            "name": self.name,
            "agent_type": self.agent_type,
            "description": self.description,
        }

    @staticmethod
    def clean_and_match_command(raw_text: str, valid_commands: list[str]) -> str:
        """Limpia la respuesta generada por el LLM y la mapea estrictamente a un comando válido."""
        if not valid_commands:
            return "look"

        if not raw_text:
            return valid_commands[0]

        # 1. Limpieza básica de comillas, saltos de línea y puntos
        cleaned = raw_text.strip().strip("'\"`").strip()
        lines = [line.strip().strip("'\"`").strip() for line in cleaned.split("\n") if line.strip()]
        candidate = lines[0] if lines else cleaned

        # Remover prefijos comunes como 'Action:', 'Command:', 'I choose:', 'Comando:'
        candidate = re.sub(
            r"^(action|command|comando|i choose|i will|execute|run)\s*:\s*",
            "",
            candidate,
            flags=re.IGNORECASE,
        ).strip().strip("'\"`").strip()

        # Quitar punto final si vino "take key."
        if candidate.endswith("."):
            candidate = candidate[:-1].strip()

        # 2. Coincidencia exacta (case-insensitive)
        candidate_lower = candidate.lower()
        for cmd in valid_commands:
            if candidate_lower == cmd.lower():
                return cmd

        # 3. Coincidencia por contención (si el LLM dijo "take the brass key" y el comando es "take brass key")
        for cmd in valid_commands:
            cmd_lower = cmd.lower()
            if cmd_lower in candidate_lower or candidate_lower in cmd_lower:
                return cmd

        # 4. Coincidencia difusa (difflib)
        matches = difflib.get_close_matches(candidate_lower, [c.lower() for c in valid_commands], n=1, cutoff=0.6)
        if matches:
            best_match = matches[0]
            for cmd in valid_commands:
                if cmd.lower() == best_match:
                    return cmd

        # 5. Fallback seguro al primer comando válido
        return valid_commands[0]
