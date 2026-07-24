# DevTalenty AI Extractor 🚀

DevTalenty AI Extractor es una API REST construida en Python (FastAPI) diseñada para la extracción inteligente de datos estructurados desde currículums (PDFs) o correos electrónicos (Raw Text). Utiliza una arquitectura híbrida que combina reglas deterministas (Expresiones Regulares) y NLP generativo (Large Language Models) para estructurar perfiles de candidatos con precisión y consistencia.

Este proyecto implementa **Clean Architecture** (Arquitectura Limpia) y el Patrón Repositorio, garantizando que la lógica de negocio (Dominio) sea completamente agnóstica a la infraestructura tecnológica subyacente (PostgreSQL, Groq, Presidio, PyMuPDF).

---

## Características Principales ⚙️

1. **Extracción Híbrida Inteligente**: 
   - Parseo de binarios PDF sin dependencias de I/O de disco usando `PyMuPDF`.
   - Uso de `instructor` para forzar a que el LLM (Llama 3.1) responda en formato JSON estrictamente tipado usando validación iterativa de Pydantic.
2. **Seguridad y Privacidad (PII)**: 
   - Anonimización en memoria mediante **Microsoft Presidio**. Nombres, correos electrónicos y teléfonos son enmascarados antes de enviarse al proveedor LLM, protegiendo los datos confidenciales de los candidatos bajo estándares GDPR/CCPA.
3. **Resiliencia (Retry Backoff)**:
   - Uso de `tenacity` para encapsular las llamadas de red externas, proporcionando reintentos exponenciales automáticos contra límites de cuota (Rate Limits) o caídas temporales del proveedor de IA.
4. **Flujo HITL (Human-in-the-Loop)**:
   - El LLM reporta un *confidence score*. Si el puntaje es menor a un umbral configurado (ej. 0.85), el documento persiste en estado `PENDING` para revisión humana obligatoria, evitando el ingreso de alucinaciones (hallucinations) a los sistemas del cliente.
5. **Persistencia Asíncrona Robusta**:
   - SQLAlchemy 2.0 (con la nueva sintaxis `Mapped[T]`) y el driver `asyncpg` para operaciones no bloqueantes de alto rendimiento, ideal para despliegues serverless o escalables.

---

## Tecnologías y Stack 🛠️

- **Backend**: Python 3.11+, FastAPI, Pydantic v2
- **IA & Extracción**: Groq (Llama-3), Instructor (Structured Outputs)
- **Seguridad**: Microsoft Presidio (NLP PII Masking) + spaCy (`en_core_web_lg`)
- **Base de Datos**: PostgreSQL 15, SQLAlchemy 2.0, Asyncpg, Alembic
- **Despliegue**: Docker, Docker Compose

---

## Cómo Ejecutar (Evaluadores y Desarrollo) 🐳

La forma recomendada y más sencilla de evaluar este proyecto en cualquier máquina (sin configurar variables de entorno, entornos virtuales, o instalar modelos de Machine Learning locales) es mediante **Docker Compose**.

### Prerrequisitos
- Tener instalado [Docker](https://docs.docker.com/get-docker/) y Docker Compose.
- Obtener una [Groq API Key](https://console.groq.com/keys) (es gratuita y toma 1 minuto).

### Paso a Paso (Docker Compose)

1. Exporta tu API Key como variable de entorno (Docker Compose la tomará automáticamente de tu entorno local para no subirla al código fuente):
   ```bash
   # En Windows PowerShell
   $env:OPENAI_API_KEY="gsk_TU_API_KEY_AQUI"
   
   # En Linux / Mac
   export OPENAI_API_KEY="gsk_TU_API_KEY_AQUI"
   ```

2. Levanta la infraestructura completa (Base de datos PostgreSQL + API):
   ```bash
   docker-compose up --build -d
   ```
   *Nota: La primera ejecución tomará unos minutos, ya que descarga el modelo estadístico de spaCy (~500MB) para Presidio y las dependencias de Python.*

3. Verifica que la API y la base de datos están corriendo:
   ```bash
   docker ps
   # Deberías ver los contenedores 'devtalenty-api' y 'devtalenty-db' en estado "Up".
   ```

4. Navega a la interfaz interactiva de Swagger:
   - **URL:** [http://localhost:8000/docs](http://localhost:8000/docs)

5. ¡Listo! Puedes probar el endpoint `POST /api/v1/extract/pdf` subiendo un CV y luego revisarlo con el flujo HITL usando `GET /api/v1/documents/pending`.

---

## Cómo Ejecutar (Modo Local / Desarrollo) 💻

Si deseas desarrollar o debugear localmente sin Docker:

1. Instala [Poetry](https://python-poetry.org/).
2. Instala las dependencias y el modelo NLP:
   ```bash
   poetry install
   poetry run python -m spacy download en_core_web_lg
   ```
3. Renombra el archivo `.env.example` a `.env` y configura tus variables (incluyendo una base de datos PostgreSQL corriendo y tu `OPENAI_API_KEY`).
4. Corre las migraciones para crear las tablas:
   ```bash
   poetry run alembic upgrade head
   ```
5. Inicia el servidor:
   ```bash
   poetry run uvicorn app.main:app --reload
   ```

---

## Documentación Técnica Explicativa 📝
Como parte de los lineamientos de la evaluación, las decisiones arquitectónicas (ADRs) clave que respaldan este proyecto están documentadas exhaustivamente en el archivo raíz:
👉 [explicacion_tecnica.txt](./explicacion_tecnica.txt)

En este archivo encontrarás justificaciones técnicas rigurosas (por ejemplo: ¿Por qué usamos Presidio?, ¿Por qué PyMuPDF sobre pdfplumber?, ¿Por qué el Patrón Repositorio y Clean Architecture?, etc).
