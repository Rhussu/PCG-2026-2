from __future__ import annotations

import random
import re
import time
from typing import Any

import numpy as np
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.vectorstores.in_memory import InMemoryVectorStore
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from agente.base import BaseAgent
from agente.config import AgentConfig


class LocalFallbackEmbeddings(Embeddings):
    """Embeddings determinísticos ligeros basados en proyección de n-gramas de palabras
    utilizados automáticamente cuando el endpoint de embeddings en las 2x RTX 4090 no esté disponible.
    """

    def __init__(self, size: int = 128) -> None:
        self.size = size

    def _embed(self, text: str) -> list[float]:
        vec = np.zeros(self.size, dtype=np.float32)
        words = re.findall(r"\w+", text.lower())
        if not words:
            return vec.tolist()
        for w in words:
            idx = abs(hash(w)) % self.size
            vec[idx] += 1.0
        norm = float(np.linalg.norm(vec))
        if norm > 0:
            vec /= norm
        return vec.tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


RAG_SYSTEM_PROMPT = """Eres un agente autónomo de élite dotado de una memoria vectorial semántica (RAG) jugando en TextWorld.
A diferencia de un jugador común, posees la capacidad de recuperar selectivamente tus recuerdos y experiencias pasadas más relevantes para la situación actual.

REGLAS DE ACTUACIÓN:
1. Analiza cuidadosamente los 'RECUERDOS RECUPERADOS' (RAG Context) para identificar dónde están las llaves, puertas bloqueadas o tareas pendientes.
2. Debes seleccionar EXACTAMENTE UNA acción de la lista de 'COMANDOS ADMISIBLES'.
3. Responde ÚNICAMENTE con el texto del comando elegido, sin explicaciones ni texto adicional.
4. Si necesitas abrir una puerta con cerradura o un contenedor, revisa en tus recuerdos qué llave corresponde o qué habitación no has terminado de explorar.
"""


class RAGMemoryAgent(BaseAgent):
    """Agente con Memoria Avanzada (RAG - Retrieval-Augmented Generation) utilizando LangChain.
    En lugar de saturar la ventana de contexto linealmente, fragmenta e indexa semánticamente
    las observaciones, habitaciones descubiertas, objetos y acciones previas en un almacén vectorial.
    En cada turno, recupera las memorias más afines al estado actual para enriquecer el razonamiento del LLM.
    """

    def __init__(self, config: AgentConfig | None = None) -> None:
        super().__init__(
            name="Agente Memoria Avanzada (RAG LangChain)",
            agent_type="rag_memory",
            description="Memoria vectorial semántica con LangChain para recuperar experiencias y hechos relevantes.",
        )
        self.config = config or AgentConfig()
        self.vector_store: InMemoryVectorStore | None = None
        self.embeddings: Embeddings | None = None
        self.total_memories_stored: int = 0

        # Métricas computacionales
        self.total_prompt_tokens: int = 0
        self.total_completion_tokens: int = 0
        self.total_latency_ms: float = 0.0
        self.api_calls_count: int = 0
        self.is_offline_fallback: bool = False

        self._llm: ChatOpenAI | None = None
        self._init_components()

    def _init_components(self) -> None:
        # 1. Intentar inicializar embeddings remotos en 2x 4090 o usar fallback
        try:
            self.embeddings = OpenAIEmbeddings(
                base_url=self.config.embedding_base_url,
                api_key=self.config.embedding_api_key,
                model=self.config.embedding_model,
                timeout=10.0,
                max_retries=1,
            )
            self.vector_store = InMemoryVectorStore(self.embeddings)
        except Exception:
            self.embeddings = LocalFallbackEmbeddings()
            self.vector_store = InMemoryVectorStore(self.embeddings)

        # 2. Inicializar cliente LLM
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
        """Limpia el almacén vectorial de memoria al reiniciar la partida."""
        if self.embeddings is None:
            self.embeddings = LocalFallbackEmbeddings()
        self.vector_store = InMemoryVectorStore(self.embeddings)
        self.total_memories_stored = 0
        self.current_step = 0

    def _store_experience(self, text: str, category: str, extra_meta: dict[str, Any] | None = None) -> None:
        """Almacena un fragmento estructurado de conocimiento en la memoria vectorial."""
        if not self.vector_store or not text.strip():
            return

        meta = {
            "step": self.current_step,
            "category": category,
            **(extra_meta or {}),
        }
        doc = Document(page_content=text.strip(), metadata=meta)
        try:
            self.vector_store.add_documents([doc])
            self.total_memories_stored += 1
        except Exception:
            # Si los embeddings remotos fallan dinámicamente, cambiar a fallback local
            self.embeddings = LocalFallbackEmbeddings()
            self.vector_store = InMemoryVectorStore(self.embeddings)
            self.vector_store.add_documents([doc])
            self.total_memories_stored += 1

    def _retrieve_relevant_memories(self, query: str) -> list[str]:
        """Recupera los top-k recuerdos semánticamente más similares a la consulta actual."""
        if not self.vector_store or self.total_memories_stored == 0:
            return []

        try:
            k = max(1, self.config.rag_top_k)
            docs = self.vector_store.similarity_search(query, k=k)
            return [d.page_content for d in docs]
        except Exception:
            return []

    def answer(self, observation: str, valid_commands: list[str]) -> str:
        self.current_step += 1
        t_start = time.time()

        if not valid_commands:
            return "look"

        # 1. Almacenar la nueva observación recibida en la memoria RAG
        self._store_experience(
            text=f"Turno {self.current_step}: {observation}",
            category="observation",
        )

        # 2. Recuperar recuerdos afines usando la observación actual como consulta
        recalled = self._retrieve_relevant_memories(observation)
        if recalled:
            recalled_context = "\n".join(f"- Recuerdo {i+1}: {mem}" for i, mem in enumerate(recalled))
        else:
            recalled_context = "(No hay memorias previas relevantes aún; inicio de exploración)."

        # 3. Formular prompt enriquecido con contexto RAG
        commands_list_str = "\n".join(f"- {cmd}" for cmd in valid_commands)
        user_message_content = (
            f"RECUERDOS RELEVANTES RECUPERADOS (RAG Memory):\n{recalled_context}\n\n"
            f"OBSERVACIÓN ACTUAL DEL ENTORNO:\n{observation}\n\n"
            f"COMANDOS ADMISIBLES:\n{commands_list_str}\n\n"
            f"Basándote en tus recuerdos y la observación actual, ¿cuál es tu siguiente acción exacta?"
        )

        messages: list[BaseMessage] = [
            SystemMessage(content=RAG_SYSTEM_PROMPT),
            HumanMessage(content=user_message_content),
        ]

        raw_action = ""
        prompt_tokens = 0
        completion_tokens = 0

        try:
            if self._llm is None:
                self._init_components()

            if self._llm is not None:
                self.api_calls_count += 1
                response = self._llm.invoke(messages)
                raw_action = str(response.content)

                meta = getattr(response, "response_metadata", {}) or {}
                usage = meta.get("token_usage") or getattr(response, "usage_metadata", None) or {}
                if isinstance(usage, dict):
                    prompt_tokens = usage.get("prompt_tokens") or usage.get("input_tokens") or 0
                    completion_tokens = usage.get("completion_tokens") or usage.get("output_tokens") or 0
                else:
                    prompt_tokens = sum(len(m.content) for m in messages) // 4
                    completion_tokens = len(raw_action) // 4

                self.is_offline_fallback = False
            else:
                raise RuntimeError("LLM client no inicializado")

        except Exception as exc:
            if not self.config.fallback_if_offline:
                raise exc

            self.is_offline_fallback = True
            raw_action = self._heuristic_fallback_choice(observation, valid_commands)

            prompt_tokens = sum(len(m.content) for m in messages) // 4
            completion_tokens = max(1, len(raw_action) // 4)

        elapsed_ms = (time.time() - t_start) * 1000.0
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        self.total_latency_ms += elapsed_ms

        chosen_action = self.clean_and_match_command(raw_action, valid_commands)

        # 4. Almacenar también la acción tomada en el almacén de memoria episódica
        self._store_experience(
            text=f"En el turno {self.current_step}, ejecuté la acción '{chosen_action}' tras observar: {observation[:120]}...",
            category="action_decision",
        )

        return chosen_action

    def _heuristic_fallback_choice(self, observation: str, valid_commands: list[str]) -> str:
        """Selección heurística cuando el servidor 2x RTX 4090 esté offline."""
        priority_keywords = ["take key", "take ", "unlock ", "open ", "go north", "go south", "go east", "go west"]
        for kw in priority_keywords:
            for cmd in valid_commands:
                if cmd.lower().startswith(kw):
                    return cmd
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
            "estimated_cost_usd": 0.0,
            "total_memories_indexed": self.total_memories_stored,
            "status": "offline_fallback" if self.is_offline_fallback else "online",
            "is_mock": self.is_offline_fallback,
        }
