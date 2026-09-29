from __future__ import annotations

import random
import time
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from agente.base import BaseAgent
from agente.config import AgentConfig


SYSTEM_PROMPT = """Eres un agente autónomo experto jugando una aventura de texto interactiva en TextWorld.
Tu objetivo es explorar el entorno, recolectar objetos necesarios, resolver acertijos y completar las misiones para maximizar tu puntuación y ganar el juego.

REGLAS CRÍTICAS:
1. Debes elegir EXACTAMENTE UNA acción de la lista proporcionada de 'COMANDOS ADMISIBLES'.
2. Responde ÚNICAMENTE con el texto del comando elegido, sin explicaciones, sin razonamientos, sin comillas y sin punto final.
3. Recuerda las habitaciones por las que has pasado y qué objetos encontraste o dejaste allí.
4. Si hay puertas cerradas, busca llaves o herramientas en otras habitaciones. Si ves objetos útiles (llaves, comida, recipientes), tómalos.
"""


class ClassicMemoryAgent(BaseAgent):
    """Agente con Memoria Clásica (Historial Conversacional / Buffer de Contexto) utilizando LangChain.
    Mantiene un registro secuencial de los turnos previos (observaciones y acciones tomadas)
    y lo envía en el contexto del prompt para que el LLM mantenga la continuidad de la partida.
    """

    def __init__(self, config: AgentConfig | None = None) -> None:
        super().__init__(
            name="Agente Historial Clásico (LangChain)",
            agent_type="classic_memory",
            description="Historial secuencial de observaciones y acciones en ventana deslizante con LangChain.",
        )
        self.config = config or AgentConfig()
        self.history: list[BaseMessage] = []

        # Métricas acumuladas de la sesión
        self.total_prompt_tokens: int = 0
        self.total_completion_tokens: int = 0
        self.total_latency_ms: float = 0.0
        self.api_calls_count: int = 0
        self.is_offline_fallback: bool = False

        self._llm: ChatOpenAI | None = None
        self._init_llm()

    def _init_llm(self) -> None:
        try:
            self._llm = ChatOpenAI(
                base_url=self.config.llm_base_url,
                api_key=self.config.llm_api_key,
                model=self.config.llm_model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                timeout=self.config.request_timeout,
                max_retries=1,
            )
        except Exception:
            self._llm = None

    def reset(self) -> None:
        """Reinicia la memoria episódica al comenzar una nueva partida."""
        self.history.clear()
        self.current_step = 0

    def answer(self, observation: str, valid_commands: list[str]) -> str:
        self.current_step += 1
        t_start = time.time()

        if not valid_commands:
            return "look"

        # Construir opciones de comandos admisibles para el prompt
        commands_list_str = "\n".join(f"- {cmd}" for cmd in valid_commands)
        user_message_content = (
            f"OBSERVACIÓN ACTUAL:\n{observation}\n\n"
            f"COMANDOS ADMISIBLES (debes elegir exactamente uno de estos):\n{commands_list_str}\n\n"
            f"¿Cuál es tu siguiente acción?"
        )

        # Truncar historial a la ventana configurada (cada turno son 2 mensajes: Human + AI)
        window = self.config.classic_history_window * 2
        active_history = self.history[-window:] if window > 0 else []

        messages: list[BaseMessage] = [
            SystemMessage(content=SYSTEM_PROMPT),
            *active_history,
            HumanMessage(content=user_message_content),
        ]

        raw_action = ""
        prompt_tokens = 0
        completion_tokens = 0

        try:
            if self._llm is None:
                self._init_llm()

            if self._llm is not None:
                self.api_calls_count += 1
                response = self._llm.invoke(messages)
                raw_action = str(response.content)

                # Extraer conteo de tokens si el servidor vLLM / OpenAI compatible los envía
                meta = getattr(response, "response_metadata", {}) or {}
                usage = meta.get("token_usage") or getattr(response, "usage_metadata", None) or {}
                if isinstance(usage, dict):
                    prompt_tokens = usage.get("prompt_tokens") or usage.get("input_tokens") or 0
                    completion_tokens = usage.get("completion_tokens") or usage.get("output_tokens") or 0
                else:
                    # Estimación aproximada basada en caracteres si el proveedor no envía uso
                    prompt_tokens = sum(len(m.content) for m in messages) // 4
                    completion_tokens = len(raw_action) // 4

                self.is_offline_fallback = False
            else:
                raise RuntimeError("LLM client no inicializado")

        except Exception as exc:
            # Servidor 2x RTX 4090 offline o error de conexión
            if not self.config.fallback_if_offline:
                raise exc

            self.is_offline_fallback = True
            raw_action = self._heuristic_fallback_choice(observation, valid_commands)

            # Tokens aproximados simulados para el prompt elaborado
            prompt_tokens = sum(len(m.content) for m in messages) // 4
            completion_tokens = max(1, len(raw_action) // 4)

        elapsed_ms = (time.time() - t_start) * 1000.0
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        self.total_latency_ms += elapsed_ms

        chosen_action = self.clean_and_match_command(raw_action, valid_commands)

        # Actualizar historial episódico en memoria
        self.history.append(HumanMessage(content=f"Observación: {observation}"))
        self.history.append(AIMessage(content=chosen_action))

        return chosen_action

    def _heuristic_fallback_choice(self, observation: str, valid_commands: list[str]) -> str:
        """Estrategia de selección informada de respaldo cuando el servidor local 2x 4090 está offline."""
        # Priorizar tomar llaves o ítems clave
        priority_keywords = ["take key", "take ", "unlock ", "open ", "go north", "go south", "go east", "go west"]
        for kw in priority_keywords:
            for cmd in valid_commands:
                if cmd.lower().startswith(kw):
                    return cmd

        # Si no hay comandos prioritarios, elegir al azar
        return random.choice(valid_commands)

    def get_metrics(self) -> dict[str, Any]:
        total_tokens = self.total_prompt_tokens + self.total_completion_tokens
        avg_latency = (
            round(self.total_latency_ms / max(1, self.api_calls_count or self.current_step), 1)
        )
        return {
            "prompt_tokens": self.total_prompt_tokens,
            "completion_tokens": self.total_completion_tokens,
            "total_tokens": total_tokens,
            "avg_inference_latency_ms": avg_latency,
            "api_calls": self.api_calls_count,
            "estimated_cost_usd": 0.0,  # Inferencia local en 2x 4090
            "status": "offline_fallback" if self.is_offline_fallback else "online",
            "is_mock": self.is_offline_fallback,
        }
