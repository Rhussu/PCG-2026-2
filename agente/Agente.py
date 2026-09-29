from __future__ import annotations

from typing import Any

from agente.factory import create_agent
from agente.random_agent import RandomAgent


class Agente(RandomAgent):
    """Clase puente para retrocompatibilidad con scripts existentes.
    Por defecto hereda el comportamiento del Agente Aleatorio (Baseline).
    Para crear agentes específicos de memoria clásica o RAG, utiliza `agente.factory.create_agent`.
    """

    def __init__(self, agent_type: str = "random", config: dict[str, Any] | None = None) -> None:
        if agent_type != "random":
            # Si se solicita explícitamente otro tipo, delegamos internamente
            self._delegate = create_agent(agent_type, config)
            super().__init__()
            self.name = self._delegate.name
            self.agent_type = self._delegate.agent_type
            self.description = self._delegate.description
        else:
            self._delegate = None
            super().__init__()

    def answer(self, text: str, valid_commands: list[str]) -> str:
        if self._delegate is not None:
            return self._delegate.answer(text, valid_commands)
        return super().answer(text, valid_commands)

    def reset(self) -> None:
        if self._delegate is not None:
            self._delegate.reset()
        super().reset()

    def get_metrics(self) -> dict[str, Any]:
        if self._delegate is not None:
            return self._delegate.get_metrics()
        return super().get_metrics()