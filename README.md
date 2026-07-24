# DevTalenty AI Extractor 🚀

**DevTalenty AI Extractor** es una solución enterprise backend construida con **FastAPI**, **Clean Architecture** y **Groq LPUs (Llama-3.3-70b)**, diseñada para resolver la automatización de procesos no estructurados (extracción de datos de CVs/documentos) en empresas SaaS B2B que transicionan hacia un modelo *AI-First*.

---

## 🛠️ Instrucciones de Instalación y Despliegue (Zero Friction)

### Requisitos Previos
- **Docker & Docker Compose** (Recomendado).
- **Python 3.11+** (Si se ejecuta en local).
- **Groq API Key** (Obtenible gratuitamente en [console.groq.com](https://console.groq.com/keys)).

### Opción 1: Despliegue Inmediato con Docker Compose 🐳
```bash
# 1. Clonar y configurar variables de entorno
cp .env.example .env
# Reemplazar GROQ_API_KEY en .env con tu API Key real

# 2. Levantar la infraestructura completa (API + PostgreSQL + Migraciones)
docker-compose up --build -d

# 3. Probar la API interactiva en Swagger UI
# Navegar a: http://localhost:8000/docs
```

### Opción 2: Ejecución Local (Poetry / venv) 💻
```bash
cp .env.example .env
poetry install
poetry run python -m spacy download en_core_web_lg
poetry run alembic upgrade head
poetry run uvicorn app.main:app --reload
```

### 🧪 Ejecución de Pruebas Automatizadas (100% Passing)
```bash
poetry run pytest -v
# o en venv: .\.venv\Scripts\python.exe -m pytest -v
```

---

# 🧠 PARTE 1: Priorización y Criterio de Negocio

### 1. Priorización de los 5 Casos de Uso

| Rango | Caso de Uso | Complejidad Técnica | Coste / Riesgo | Impacto en Negocio | Time-to-Value | Justificación |
| :---: | :--- | :---: | :---: | :---: | :---: | :--- |
| **1** | **Extracción de datos (PDFs/Emails)** | Media | Bajo / Medio | **Muy Alto** | **1-2 Semanas** | **(MVP Seleccionado)** Elimina el 80% del trabajo manual de data-entry. Alto volumen actual, impacto operativo inmediato. |
| **2** | **Generación de Reportes** | Media | Bajo / Bajo | Alto | 3-4 Semanas | Automatiza entregables a clientes. Alto valor percibido con bajo riesgo de alucinación si se usa SQL/RAG estructurado. |
| **3** | **Clasificación y Routing de Tickets** | Baja | Muy Bajo / Bajo | Medio | 1-2 Semanas | Rápido de implementar con modelos pequeños (BERT/8B). Descongestiona soporte técnico. |
| **4** | **Asistente Chat (Datos SaaS)** | Alta | Alto / Alto | Medio-Alto | 2-3 Meses | Alto riesgo de alucinación de cara al cliente final. Requiere arquitectura RAG robusta y permisos multi-tenant. |
| **5** | **Validación de Datos (ERP vs CRM)** | Baja | Nulo / Nulo | Alto | 1 Semana | **NO requiere IA Generativa.** Es un problema determinista que se resuelve con reglas e integraciones API directas. |

### 2. Decisión Crítica: ¿Por qué Extracción de Documentos como Punto de Entrada?
Es el caso de uso con la **mayor relación Impacto / Riesgo**:
1. **Fricción Operativa Real:** Los equipos humanos pierden cientas de horas leyendo PDFs e ingresando datos manualmente en el SaaS/CRM.
2. **Entorno Controlado:** La salida es estructurada (JSON) y puede validarse automáticamente con esquemas (Pydantic).
3. **Bajo Riesgo de Cara al Cliente:** Al incluir un flujo *Human-In-The-Loop (HITL)*, los datos con baja confianza son revisados internamente antes de impactar sistemas críticos.

### 3. Filtro Senior: ¿IA, Reglas o Híbrido?

- **Caso 1 (Extracción PDFs/Emails):** **HÍBRIDO**. Reglas/Regex para parsing binario y sanitización local (Presidio), IA (LLM) para entender la semántica no estructurada del texto.
- **Caso 2 (Reportes Clientes):** **HÍBRIDO**. IA para interpretar la consulta en lenguaje natural (Text-to-SQL / RAG), Reglas/Engine SQL para calcular los números exactos sin alucinación.
- **Caso 3 (Routing Tickets):** **IA (Modelos Pequeños / Classifiers)**. Clasificación NLP o LLM 8B enfocado en taxonomía de soporte.
- **Caso 4 (Asistente Chat):** **IA (RAG Avanzado)**. Embeddings + Vector DB + LLM para síntesis conversacional con guardrails.
- **Caso 5 (Validación ERP vs CRM):** **REGLAS (DETERMINISTA)**. 
  - **¿Por qué NO usaría IA aquí?** Validar si el NIT o teléfono en el CRM coincide con el ERP es una comparación de cadenas/números rígida. Usar un LLM aquí añade latencia, costos por token y el riesgo inaceptable de que el LLM "alucine" que dos números distintos son iguales por aproximación estadística.

---

# 🏗️ PARTE 2: Diseño de Solución (El MVP Construido)

### 1. Arquitectura de Solución (Alto Nivel)

```text
[PDF / Email Input]
        │
        ▼
┌────────────────────────┐
│  FastAPI Ingestion     │ ◄── Punto de Entrada REST (API Gateway)
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│  PyMuPDF Text Extractor│ ◄── Extracción determinista de texto plano
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│  Microsoft Presidio    │ ◄── Sanitización local de PII (GDPR/Compliance)
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│  AIExtractor (Groq)    │ ◄── LLM (Llama-3.3-70b) + Instructor (Function Calling)
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│ Confidence & HITL Engine│ ◄── If Score >= 0.85 -> APPROVED | If < 0.85 -> PENDING
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│ PostgreSQL Repository   │ ◄── Persistencia asíncrona (SQLAlchemy 2.0)
└────────────────────────┘
```
- **Dónde vive la IA:** La IA está encapsulada exclusivamente en el módulo `AIExtractor` en la capa de Infraestructura, desacoplada mediante la interfaz de Dominio `BaseExtractor`.
- **Integración con Sistemas:** Expone Webhooks y endpoints REST (`POST /api/v1/extract/pdf`) para integrarse transparentemente con el CRM/SaaS existente.

### 2. Uso Estratégico de IA

- **¿Dónde usar LLMs?:** Exclusivamente en la transformación de texto desestructurado sanitizado a la entidad Pydantic `CandidateProfile`.
- **¿Dónde usar Embeddings / Búsqueda Semántica?:** **NO se usan en el pipeline de extracción de 1 documento**. Se utilizarían en una etapa posterior del SaaS para permitir al equipo buscar candidatos por habilidades conceptuales (ej: "experto en microservicios cloud") usando `pgvector` o Qdrant.
- **¿Usaría RAG?:** **NO para la extracción puntual de CVs**. RAG se requiere cuando el modelo necesita consultar una base de conocimiento externa. En la extracción de CVs, todo el contexto necesario reside dentro del propio documento.
- **¿Dónde NO usar IA?:** 
  - Extracción binaria de texto del PDF (usamos `PyMuPDF`).
  - Detección y enmascaramiento de datos personales PII (usamos `Presidio` con SpaCy NLP local).
  - Persistencia y validación de tipos de datos (usamos `Pydantic v2` y `SQLAlchemy`).

### 3. Estrategia para Datos

- **Procesamiento de Inputs:** PyMuPDF para archivos PDF; BeautifulSoup + Regex para correos HTML/texto plano.
- **Calidad antes de IA:** 
  - Validación de integridad binaria del archivo.
  - Verificación de longitud mínima de texto (evita PDFs escaneados vacíos sin OCR).
  - Sanitización estricta de caracteres de control nulos.
- **Prevención de Errores Críticos:** Reglas heurísticas de respaldo para campos clave (email/teléfono) que verifican el resultado del LLM mediante Expresiones Regulares deterministas.

### 4. Control de Outputs y Prevención de Alucinaciones

- **Prevención de Alucinaciones:** Uso estricto de la librería **`instructor`** aprovechando *Function Calling / Structured Outputs* del LLM. El modelo no responde texto libre, sino que genera argumentos para un esquema JSON predefinido.
- **Estructura Estricta:** Validación mediante modelos `Pydantic v2`. Si el LLM intenta inventar un campo o tipo de dato, Pydantic dispara un `ValidationError`.
- **Consistencia & Resiliencia:** Decoradores con **`tenacity`** para reintentar la llamada al LLM con *Exponential Backoff* si ocurren errores transitorios o respuestas malformadas.

### 5. Variante de Arquitectura: MVP vs Producción Escalable

- **Versión Low-Cost / MVP (Implementada):**
  - Procesamiento síncrono/directo en FastAPI.
  - Modelo Llama-3.3-70b a través de Groq LPUs (Costo cercano a $0 en volúmenes iniciales).
  - Base de datos PostgreSQL única.
- **Versión Escalable (100k+ docs/día):**
  - **Arquitectura Orientada a Eventos:** Endpoint FastAPI recibe el documento, lo almacena en S3/MinIO y publica un mensaje en **RabbitMQ/Kafka**.
  - **Workers Asíncronos:** Cluster de workers **Celery** consumen la cola, procesan la IA y notifican vía **Webhooks/WebSockets**.
  - **Semantic Caching:** Cache de prompts idénticos en **Redis** usando hashes del documento para evitar re-procesar archivos repetidos.

---

# 🛡️ PARTE 3: Coste, Riesgos y Producción

### 1. Control de Costes de LLM en Producción
- **Model Routing:** Usar un modelo ultra-pequeño (Llama-3.1-8B) para documentos simples o cortos, y escalar a Llama-3.3-70B solo si la confianza de extracción es baja.
- **Max Tokens Caps & Truncamiento:** Truncar textos irrelevantes (ej: anexos legales en CVs) antes de enviarlos al LLM.
- **Prompt Caching / Semantic Cache:** Almacenar en Redis las respuestas de documentos con hash idéntico.

### 2. Trade-Offs Explícitos

1. **Calidad vs Costo:** 
   * *Decisión:* Elegimos **Llama-3.3-70B en Groq** sobre GPT-4o. Ofrece un 95%+ de la calidad de GPT-4o para extracción de entidades a una fracción de su costo ($0.59 vs $5.00 por millón de tokens).
2. **Latencia vs Precisión:** 
   * *Decisión:* Priorizamos la **Precisión** incluyendo sanitización PII previa y validación Pydantic posterior, aceptando un overhead de ~300ms local a cambio de 0% alucinaciones estructurales.
3. **Modelo Grande vs Modelo Pequeño:** 
   * *Decisión:* Usamos un **Modelo Grande (70B)** para el MVP porque los modelos pequeños (8B) sufren al extraer esquemas JSON complejos con campos anidados.

### 3. Escalabilidad (Crecimiento 10x)
- Inserción de capas de colas asíncronas (**RabbitMQ + Celery Workers**).
- Desacoplamiento de la base de datos con **Connection Pooling (PgBouncer)** y réplicas de lectura.
- Autoscale horizontal de contenedores FastAPI en Kubernetes / AWS ECS basado en uso de CPU y profundidad de cola.

### 4. Seguridad, Riesgos y Compliance

- **Datos Sensibles (PII):** Ingesta filtrada localmente con **Microsoft Presidio** (SpaCy) *antes* de que cualquier dato salga a la API del proveedor de LLM.
- **Multi-Tenant (Aislamiento de Clientes):**
  - Filtrado a nivel de Base de Datos usando `tenant_id` obligatorio en todas las consultas del Repositorio.
  - Implementación de **Row Level Security (RLS)** en PostgreSQL para prevenir fuga de datos entre inquilinos.
- **Prompt Injection (en sistemas RAG/LLM):**
  - Sanitización de caracteres de escape e instrucciones de control en el input del usuario.
  - Separación estricta entre el *System Prompt* (instrucciones inmuta bles del sistema) y el *User Content* dentro de la estructura de mensajes del API.
- **Trazabilidad:** Registro estructurado (JSON Logs) de cada solicitud incluyendo `document_id`, `confidence_score`, latencia del proveedor y versión del modelo LLM utilizado.

---

# 🚀 PARTE 4: Implementación, Adopción y Métricas

### 1. De Idea a Producción (Roadmap)
1. **Prototipo (Días 1-3):** Script en Python procesando PDFs locales con Instructor y mostrando JSONs en consola.
2. **MVP (Semanas 1-2 - *Estado Actual*):** API FastAPI con Clean Architecture, sanitización PII, base de datos PostgreSQL, suite de tests y Docker Compose.
3. **Producción (Meses 1-2):** Despliegue de colas asíncronas (Celery), métricas en Prometheus/Grafana, arquitectura multi-tenant con RLS y pipelines CI/CD.

### 2. Colaboración con Equipos Internos
- **Ingeniería:** Entrega de contratos OpenAPI (`openapi.json`) estrictos y SDKs/Webhooks para que los desarrolladores consuman la API sin fricción.
- **Producto:** Definición conjunta del umbral de confianza (0.85) para la bandeja de revisión humana (HITL) y diseño de la interfaz de aprobación.
- **Negocio:** Reportes de métricas de ahorro de tiempo y costo por documento procesado para justificar el ROI.

### 3. Estrategia de Adopción
- **Cero Fricción en el Workflow:** No obligar a los usuarios a usar un nuevo software; los datos procesados por la IA se inyectan automáticamente en el SaaS/CRM existente.
- **Confianza Progresiva (HITL):** En la fase inicial, el 100% de las extracciones pasan por revisión humana rápida. A medida que los usuarios comprueban la precisión de la IA, la bandeja HITL solo recibe los casos borde (<85% confianza).

### 4. Métricas de Éxito (KPIs)

#### 2 Métricas Técnicas:
1. **Latencia del Pipeline (p95):** `< 2.5 segundos` por documento end-to-end.
2. **Tasa de Extracción Estructurada Exitosa:** `> 98%` de procesamientos sin `ValidationError` o fallos de esquema.

#### 2 Métricas de Negocio:
1. **Reducción de Tiempo Operativo:** `> 80%` de reducción en el tiempo que los empleados dedican al ingreso manual de datos.
2. **Retorno de Inversión (ROI):** Lograr un ROI positivo en `< 3 meses`, comparando el costo de infraestructura contra las horas-hombre ahorradas.

---
*Desarrollado para la Evaluación Técnica de Dev Talenty.*
