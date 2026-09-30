#!/usr/bin/env python
"""Script de verificación rápida para el servidor de LLM local en 2x RTX 4090."""

from __future__ import annotations

import os
import sys
import time

# Asegurar que el directorio raíz del proyecto esté en sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agente.base import BaseAgent
from agente.config import AgentConfig


def test_connection() -> int:
    config = AgentConfig()
    print("=" * 65)
    print("🔍 VERIFICACIÓN DE CONEXIÓN A 2x RTX 4090 (Ollama / vLLM API)")
    print("=" * 65)
    print(f"URL Base LLM:      {config.llm_base_url}")
    print(f"Modelo configurado: {config.llm_model}")
    print(f"URL Embeddings:     {config.embedding_base_url}")
    print(f"Modelo Embeddings:  {config.embedding_model}")
    print("-" * 65)

    # 1. Probar LangChain ChatOpenAI
    print("[1/3] Probando inferencia con LangChain ChatOpenAI...")
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            base_url=config.llm_base_url,
            api_key=config.llm_api_key,
            model=config.llm_model,
            temperature=0.0,
            max_tokens=config.max_tokens,
            timeout=config.request_timeout,
        )

        t0 = time.time()
        res = llm.invoke([
            SystemMessage(content="Eres un jugador de TextWorld. Responde eligiendo exactamente un comando de la lista."),
            HumanMessage(content="Comandos disponibles: look, inventory. Elige uno."),
        ])
        latency_ms = (time.time() - t0) * 1000.0

        raw_output = str(res.content).strip()
        print(f"  ✅ ÉXITO - Respuesta bruta del modelo:\n{raw_output}")
        print(f"  ⏱️ Latencia: {latency_ms:.1f} ms")

        # 2. Probar extracción de comando y razonamiento
        print("\n[2/3] Probando sanitizador de comandos y razonamiento <think>...")
        matched_cmd = BaseAgent.clean_and_match_command(raw_output, ["look", "inventory"])
        reasoning = BaseAgent.extract_reasoning(raw_output)
        print(f"  🎯 Comando extraído con éxito: '{matched_cmd}'")
        if reasoning:
            res_preview = reasoning[:120] + "..." if len(reasoning) > 120 else reasoning
            print(f"  💭 Razonamiento detectado: '{res_preview}'")

    except Exception as exc:
        print(f"  ❌ FALLO DE CONEXIÓN LLM: {exc}")
        print("  💡 Asegúrate de que Ollama o vLLM esté corriendo con soporte para ambas RTX 4090.")
        print("  ℹ️ Consulta el archivo documents/CONFIGURACION_HARDWARE_2X_RTX4090.md para instrucciones.")
        return 1

    # 3. Probar Embeddings
    print("\n[3/3] Probando generación de embeddings...")
    try:
        from langchain_openai import OpenAIEmbeddings

        embeddings = OpenAIEmbeddings(
            base_url=config.embedding_base_url,
            api_key=config.embedding_api_key,
            model=config.embedding_model,
            timeout=15.0,
            check_embedding_ctx_length=False,
        )

        t0 = time.time()
        vec = embeddings.embed_query("In the kitchen there is an apple.")
        latency_ms = (time.time() - t0) * 1000.0

        print(f"  ✅ ÉXITO - Vector generado con dimensión: {len(vec)}")
        print(f"  ⏱️ Latencia: {latency_ms:.1f} ms")

    except Exception as exc:
        print(f"  ⚠️ Embeddings no disponibles: {exc}")
        print("  ℹ️ El agente RAG utilizará el fallback determinístico local.")

    print("=" * 65)
    print("🎉 SERVIDOR 2x RTX 4090 LISTO PARA BENCHMARKS TEXTWORLD")
    print("=" * 65)
    return 0


if __name__ == "__main__":
    sys.exit(test_connection())
