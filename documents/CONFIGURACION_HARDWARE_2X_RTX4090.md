# 🚀 Guía de Configuración y Despliegue de LLMs en 2x NVIDIA GeForce RTX 4090

> **Proyecto Computacional Guiado (PCG)**  
> **Tema:** Mejorando la Consistencia Espacio Temporal de LLMs utilizando ABMs  
> **Hardware Objetivo:** 2x GPUs NVIDIA GeForce RTX 4090 (24 GB VRAM c/u = 48 GB VRAM total)  
> **Estado Actual:** 🟡 **CONFIGURACIÓN PENDIENTE DE DESPLIEGUE EN SERVIDOR LOCAL**  
> *(El sistema cuenta con fallback automático y mock seguro, permitiendo pruebas inmediatas en la interfaz y suites de test hasta que el servidor local esté en marcha).*

---

## 📌 1. Visión General de la Arquitectura

Para alimentar los agentes autónomos de **Memoria Clásica (Historial LangChain)** y **Memoria Avanzada (RAG LangChain)**, el sistema se conecta a un servidor de inferencia local que expone una **API compatible con OpenAI** (`/v1/chat/completions` y `/v1/embeddings`).

Al disponer de **2 tarjetas RTX 4090 (48 GB VRAM combinada)**, dispones de potencia suficiente para correr:
- Modelos medianos nativos en 16 bits (ej. **Llama-3.1-8B-Instruct** o **Qwen-2.5-14B-Instruct**) a altísima velocidad.
- Modelos grandes cuantizados en 4 u 8 bits (ej. **Qwen-2.5-32B-Instruct** o **Llama-3.1-70B-Instruct-AWQ**) distribuidos entre ambas GPUs.
- Un modelo de embeddings dedicado (ej. **bge-large-en-v1.5**) para el agente RAG.

```
┌───────────────────────────────────────────────────────────┐
│                   APLICACIÓN TEXTWORLD                     │
│  - Agente Historial Clásico (LangChain Messages)         │
│  - Agente Memoria Avanzada (LangChain InMemory RAG)       │
└──────────────┬────────────────────────────┬───────────────┘
               │ HTTP / JSON API            │ HTTP / Embeddings
               ▼                            ▼
┌───────────────────────────────────────────────────────────┐
│     SERVIDOR DE INFERENCIA LOCAL (2x RTX 4090 - 48GB)      │
│                                                           │
│  GPU 0 (24GB) ──[ Tensor Parallel / Layers ]── GPU 1 (24GB)│
│                                                           │
│  Stack Recomendado: vLLM (tp=2) o Ollama                  │
│  Endpoint Chat: http://localhost:8000/v1                  │
│  Endpoint Embeddings: http://localhost:8000/v1            │
└───────────────────────────────────────────────────────────┘
```

---

## 🛠️ 2. Opción Recomendada: Despliegue con vLLM (Tensor Parallelism = 2)

**vLLM** es el motor de inferencia de código abierto más rápido para entornos de investigación y producción. Soporta paralelismo tensorial nativo (`tensor-parallel-size 2`), dividiendo los pesos del modelo entre ambas RTX 4090 de manera transparente.

### 2.1. Instalación de vLLM
En un entorno Python 3.10-3.12 con soporte CUDA:
```bash
pip install vllm
```

### 2.2. Modelos Recomendados y Comandos de Lanzamiento

#### Opción A: Llama-3.1-8B-Instruct (Máxima Velocidad & Baja Latencia)
Ideal para pruebas rápidas, iteraciones ágiles y benchmarks de muchas vueltas:
```bash
CUDA_VISIBLE_DEVICES=0,1 python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Meta-Llama-3.1-8B-Instruct \
  --tensor-parallel-size 2 \
  --port 8000 \
  --host 0.0.0.0 \
  --gpu-memory-utilization 0.90 \
  --max-model-len 8192 \
  --trust-remote-code
```

#### Opción B: Qwen-2.5-32B-Instruct-AWQ (Equilibrio Sobresaliente Razonamiento / VRAM)
Excelente capacidad de seguimiento de instrucciones complejas en TextWorld:
```bash
CUDA_VISIBLE_DEVICES=0,1 python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-32B-Instruct-AWQ \
  --tensor-parallel-size 2 \
  --port 8000 \
  --host 0.0.0.0 \
  --gpu-memory-utilization 0.92 \
  --max-model-len 8192
```

#### Opción C: Llama-3.1-70B-Instruct-AWQ (Máxima Capacidad de Razonamiento)
Requiere cuantización AWQ de 4 bits para entrar en los 48 GB:
```bash
CUDA_VISIBLE_DEVICES=0,1 python -m vllm.entrypoints.openai.api_server \
  --model hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4 \
  --tensor-parallel-size 2 \
  --port 8000 \
  --host 0.0.0.0 \
  --gpu-memory-utilization 0.95 \
  --max-model-len 4096
```

---

## 🦙 3. Opción Alternativa: Despliegue con Ollama

Si prefieres una configuración rápida sin compilar dependencias CUDA complejas:

1. **Instalar Ollama:**
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ```
2. **Lanzar servidor asegurando visibilidad de ambas GPUs:**
   ```bash
   CUDA_VISIBLE_DEVICES=0,1 ollama serve
   ```
3. **Descargar y ejecutar el modelo deseado:**
   ```bash
   ollama run llama3.1:8b-instruct-q8_0
   # O modelo más grande:
   ollama run qwen2.5:32b
   ```
   *Ollama automáticamente repartirá las capas entre las GPUs 0 y 1.*
   *El endpoint OpenAI compatible estará disponible en `http://localhost:11434/v1`.*

---

## 🔍 4. Servicio de Embeddings para el Agente RAG

Para el **Agente RAG Avanzado**, se requiere generar vectores de similitud semántica.

### Despliegue del Modelo de Embeddings
Puedes correr un servidor vLLM secundario o Text Embeddings Inference (TEI):
```bash
# Ejemplo con vLLM para embeddings:
CUDA_VISIBLE_DEVICES=1 python -m vllm.entrypoints.openai.api_server \
  --model BAAI/bge-large-en-v1.5 \
  --port 8001 \
  --host 0.0.0.0
```
> **Nota de Fallback:** Si no se levanta un servidor de embeddings dedicado, el agente RAG utiliza internamente una clase de proyección vectorial basada en n-gramas (`LocalFallbackEmbeddings`) que garantiza el funcionamiento continuo y sin errores de la aplicación y los tests.

---

## ⚙️ 5. Configuración del Proyecto (.env o agente/config.py)

Crea o edita el archivo `.env` en la raíz del proyecto `/home/rhussu/Projects/MT/.env`:

```bash
# Configuración del servidor local en 2x RTX 4090
LLM_BASE_URL=http://localhost:8000/v1
LLM_API_KEY=EMPTY
LLM_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=128
LLM_REQUEST_TIMEOUT=30.0

# Configuración de Embeddings para RAG
EMBEDDING_BASE_URL=http://localhost:8000/v1
EMBEDDING_API_KEY=EMPTY
EMBEDDING_MODEL=BAAI/bge-large-en-v1.5

# Parámetros de Memoria
CLASSIC_HISTORY_WINDOW=10
RAG_TOP_K=4
FALLBACK_IF_OFFLINE=true
```

---

## 🧪 6. Script de Verificación de Conectividad

Para validar que las 2x RTX 4090 están respondiendo correctamente antes de lanzar una suite de 50 partidas, puedes ejecutar:

```bash
python agente/verify_llm_connection.py
```

Este script comprobará:
1. Conexión HTTP al endpoint `/v1/models`.
2. Generación de un comando de prueba en TextWorld.
3. Latencia promedio por llamada (suele ser < 25ms en una RTX 4090 para 8B).
4. Generación de vectores de embeddings.
