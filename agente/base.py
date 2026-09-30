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
    def extract_reasoning(raw_text: str) -> str | None:
        """Extrae la traza de razonamiento <think>...</think> si el modelo la incluye (ej. Qwen3 / DeepSeek-R1)."""
        if not raw_text:
            return None
        match = re.search(r"<think>(.*?)</think>", raw_text, flags=re.DOTALL)
        if match:
            return match.group(1).strip()
        return None

    @staticmethod
    def clean_and_match_command(raw_text: str, valid_commands: list[str]) -> str:
        """Limpia la respuesta generada por el LLM y la mapea estrictamente a un comando válido.
        Soporta modelos de razonamiento (como qwen3:32b o deepseek-r1) eliminando bloques <think>...</think>.
        """
        if not valid_commands:
            return "look"

        if not raw_text:
            return valid_commands[0]

        # 0. Eliminar bloques de razonamiento/pensamiento de Qwen3 / DeepSeek
        cleaned = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL).strip()
        if not cleaned:
            # Si el modelo no cerró la etiqueta o sólo emitió think, remover la etiqueta de apertura
            cleaned = re.sub(r"</?think>", "", raw_text, flags=re.IGNORECASE).strip()

        # 1. Limpieza básica de comillas, saltos de línea y puntos
        cleaned = cleaned.strip("'\"`").strip()
        lines = [line.strip().strip("'\"`").strip() for line in cleaned.split("\n") if line.strip()]
        if not lines:
            return valid_commands[0]

        # 2. Revisión de coincidencia directa en cualquiera de las líneas
        # (por si el LLM emitió un saludo o cabecera y el comando en una línea siguiente)
        valid_lower_map = {cmd.lower(): cmd for cmd in valid_commands}
        for line in lines:
            line_clean = re.sub(
                r"^(action|command|comando|i choose|i will|execute|run)\s*:\s*",
                "",
                line,
                flags=re.IGNORECASE,
            ).strip().strip("'\"`").strip()
            if line_clean.endswith("."):
                line_clean = line_clean[:-1].strip()

            if line_clean.lower() in valid_lower_map:
                return valid_lower_map[line_clean.lower()]

        # 3. Analizar la primera línea candidata
        candidate = lines[0]
        candidate = re.sub(
            r"^(action|command|comando|i choose|i will|execute|run)\s*:\s*",
            "",
            candidate,
            flags=re.IGNORECASE,
        ).strip().strip("'\"`").strip()
        if candidate.endswith("."):
            candidate = candidate[:-1].strip()

        candidate_lower = candidate.lower()
        if candidate_lower in valid_lower_map:
            return valid_lower_map[candidate_lower]

        # 4. Coincidencia por contención (ej. si el LLM dijo "take the brass key" y el comando es "take brass key")
        for cmd in valid_commands:
            cmd_lower = cmd.lower()
            if cmd_lower in candidate_lower or candidate_lower in cmd_lower:
                return cmd

        # 5. Coincidencia difusa (difflib)
        matches = difflib.get_close_matches(candidate_lower, [c.lower() for c in valid_commands], n=1, cutoff=0.6)
        if matches:
            best_match = matches[0]
            for cmd in valid_commands:
                if cmd.lower() == best_match:
                    return cmd

        # 6. Fallback seguro al primer comando válido
        return valid_commands[0]
