# 🌎 Mejorando la Consistencia Espacio Temporal de LLMs utilizando ABMs

> **Proyecto Computacional Guiado (PCG)**  
> **Autor:** Walter Andrés Zárate Solar  
> **Profesor Guía:** Pedro Pinacho Davidson  
> **Institución:** Universidad de Concepción

---

## 📌 Visión General

El despliegue de **Modelos de Lenguaje (LLMs)** como agentes autónomos en entornos dinámicos e interactivos enfrenta un desafío crítico: la saturación y degradación de la ventana de contexto (*context rot*). Acumular el historial linealmente no solo eleva exponencialmente el consumo de tokens y la latencia, sino que detona alucinaciones severas sobre el estado real del mundo.

Los enfoques tradicionales de **RAG vectorial** suelen ser insuficientes en entornos con causalidad temporal o dependencias espaciales complejas, ya que tratan la memoria como fragmentos estáticos de texto indexados por similitud semántica.

Este proyecto propone, implementa y evalúa una **memoria externa dinámica estructurada como una simulación viva mediante Modelos Basados en Agentes (ABM)**. En vez de depender de un grafo o base vectorial estática, el agente cuenta con un "cerebro simulador" dotado de reglas y estados propios que evolucionan en el tiempo, permitiéndole razonar, consultar y actuar de forma precisa y eficiente frente a un sandbox interactivo como TextWorld.

---

## 📄 Propuesta y Plan de Trabajo

Para profundizar en el marco teórico, backlog detallado y cronograma del proyecto, consulta los documentos de referencia:

* **Documentación local:** Encuentra la propuesta formal en PDF y el desglose del plan de trabajo dentro del directorio [`documents/`](./documents/).
* **Seguimiento en Notion:** Revisa el tablero de tareas, roadmap detallado y notas de investigación en nuestro espacio de trabajo:  
  👉 **[Ver Plan de Trabajo y Backlog en Notion](https://app.notion.com/p/ppinacho/Mejorando-la-Consistencia-Espacio-Temporal-de-LLMs-utilizando-ABMs-3c2671a67c8c80639396f60e9d519320?source=copy_link)** *(Solo podras verlo si estas invitado al Notion)*

---

## 📁 Estructura del Proyecto

Organización del repositorio y componentes clave del sistema:

```text
.
├── agente/           # Lógica central del agente LLM, prompts y toma de decisiones
├── controllers/      # Controladores para representar adecuadamente el agente y el entorno en la interfaz
├── documents/        # Propuesta del PCG, plan de trabajo (backlog/roadmap) e informes
├── interface/        # Interfaz de visualización / interacción con el sistema y la simulación
├── tw/               # Mundos, mapas y escenarios personalizados generados para TextWorld
├── main.py           # Punto de entrada principal para ejecutar los experimentos
└── requirements.txt  # Dependencias y librerías necesarias del proyecto
```

## 🚀 Puesta en Marcha

Clona el repositorio e instala el entorno para ejecutar las pruebas:

```bash
# 1. Clonar el repositorio
git clone [https://github.com/RHussu/PCG-2026-2.git](https://github.com/RHussu/PCG-2026-2.git)
cd PCG-2026-2

# 2. Crear y activar entorno virtual
python -m venv venv
source venv/bin/activate   # En Windows: venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Ejecutar el proyecto
python main.py
```