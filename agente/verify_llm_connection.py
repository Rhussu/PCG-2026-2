#!/usr/bin/env python
"""Script de verificación rápida para el servidor de LLM local en 2x RTX 4090."""

from __future__ import annotations

import sys
import time

from agente.config import AgentConfig


def test_connection() -> int:
    config = AgentConfig()
    print("=" * 65)
    print("🔍 VERIFICACIÓN DE CONEXIÓN A 2x RTX 4090 (vLLM / Ollama API)")
    print("=" * 65)
    print(f"URL Base LLM:      {config.llm_base_url}")
    print(f"Modelo configurado: {config.llm_model}")
    print(f"URL Embeddings:     {config.embedding_base_url}")
    print(f"Modelo Embeddings:  {config.embedding_model}")
    print("-" * 65)

    # 1. Probar LangChain ChatOpenAI
    print("[1/2] Probando inferencia con LangChain ChatOpenAI...")
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            base_url=config.llm_base_url,
            api_key=config.llm_api_key,
            model=config.llm_model,
            temperature=0.0,
            max_tokens=20,
            timeout=10.0,
        )

        t0 = time.time()
        res = llm.invoke([
            SystemMessage(content="Eres un jugador de TextWorld. Responde con un comando."),
            HumanMessage(content="Comandos: look, inventory. Elige uno."),
        ])
        latency_ms = (time.time() - t0) * 1000.0

        print(f"  ✅ ÉXITO - Respuesta: '{res.content.strip()}'")
        print(f"  ⏱️ Latencia: {latency_ms:.1f} ms")

    except Exception as exc:
        print(f"  ❌ FALLO DE CONEXIÓN: {exc}")
        print("  💡 Asegúrate de que vLLM o Ollama esté corriendo en el puerto 8000 con soporte para ambas RTX 4090.")
        print("  ℹ️ Consulta el archivo documents/CONFIGURACION_HARDWARE_2X_RTX4090.md para instrucciones.")
        return 1

    # 2. Probar Embeddings
    print("\n[2/2] Probando generación de embeddings...")
    try:
        from langchain_openai import OpenAIEmbeddings

        embeddings = OpenAIEmbeddings(
            base_url=config.embedding_base_url,
            api_key=config.embedding_api_key,
            model=config.embedding_model,
            timeout=10.0,
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
