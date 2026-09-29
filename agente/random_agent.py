from __future__ import annotations

import random
from typing import Any

from agente.base import BaseAgent


class RandomAgent(BaseAgent):
    """Agente de referencia (Baseline) que elige acciones de forma aleatoria uniforme
    entre los comandos admisibles. Sirve como control para comparar el rendimiento de LLMs.
    """

    def __init__(self) -> None:
        super().__init__(
            name="Agente Aleatorio (Baseline)",
            agent_type="random",
            description="Elige comandos al azar entre las opciones admisibles. Control de referencia.",
        )
        self.decisions_count: int = 0

    def answer(self, observation: str, valid_commands: list[str]) -> str:
        self.current_step += 1
        self.decisions_count += 1

        if not valid_commands:
            return "look"

        comando = random.choice(valid_commands)
        return comando

    def reset(self) -> None:
        self.current_step = 0
        self.decisions_count = 0

    def get_metrics(self) -> dict[str, Any]:
        return {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "avg_inference_latency_ms": 0.0,
            "api_calls": 0,
            "estimated_cost_usd": 0.0,
            "status": "ready",
            "is_mock": False,
        }
