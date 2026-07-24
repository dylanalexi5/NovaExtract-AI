# DevTalenty AI Extractor 🚀

DevTalenty AI Extractor es una API REST backend construida con **FastAPI** y **Arquitectura Limpia**, diseñada para resolver el cuello de botella más crítico en los equipos de reclutamiento: **la extracción estructurada de datos desde currículums (PDFs)**. 

Utilizando un enfoque híbrido que combina reglas deterministas y NLP generativo (Large Language Models), este sistema ingiere binarios, sanitiza datos sensibles (PII) localmente y devuelve perfiles de candidatos estrictamente tipados en JSON listos para integrarse con cualquier ATS (Applicant Tracking System).

---

## 🛠️ Instrucciones de Instalación y Despliegue (Zero Friction)

### Requisitos Previos
- Docker y Docker Compose instalados (Recomendado para evaluación rápida).
- Python 3.11+ si deseas correrlo localmente.
- Obtener una [Groq API Key](https://console.groq.com/keys) (gratuita).

### Opción 1: Despliegue Inmediato (Docker Compose) 🐳
Esta es la manera recomendada para evaluadores técnicos, aislando la base de datos y dependencias en contenedores.

1. **Clonar y configurar credenciales:**
   ```bash
   # Crea tu archivo de entorno a partir de la plantilla segura
   cp .env.example .env
   ```
   *Abre el archivo `.env` recién creado y reemplaza `your_groq_api_key_here` con tu API Key real de Groq.*

2. **Levantar la Arquitectura:**
   ```bash
   docker-compose up --build -d
   ```
   *Nota: La primera ejecución descargará el modelo estadístico de spaCy (~500MB) para Presidio. La base de datos PostgreSQL se autoconfigurará y ejecutará migraciones vía Alembic.*

3. **¡Probar!**
   La API quedará disponible inmediatamente. Abre tu navegador y navega a la documentación interactiva:
   👉 **[http://localhost:8000/docs](http://localhost:8000/docs)**

### Opción 2: Desarrollo Local (Poetry / venv) 💻
Si deseas contribuir al código o correr los tests sin Docker.

1. **Preparar el Entorno:**
   ```bash
   cp .env.example .env
   # Agrega tu GROQ_API_KEY en .env y asegúrate de tener PostgreSQL local corriendo.
   ```
2. **Instalar Dependencias:**
   ```bash
   poetry install
   # Descargar el modelo NLP de spaCy para Presidio
   poetry run python -m spacy download en_core_web_lg
   ```
3. **Migraciones e Inicio:**
   ```bash
   poetry run alembic upgrade head
   poetry run uvicorn app.main:app --reload
   ```

### 🧪 Pruebas Automatizadas (QA)
Para validar la suite de pruebas unitarias y mocks de aislamiento (100% Passing):
```bash
poetry run pytest -v
# o si usas el venv clásico: .\.venv\Scripts\python.exe -m pytest -v
```

---

# 🧠 PARTE 1: Priorización y Criterio de Negocio

El CTO planteó 5 posibles casos de uso. Como Principal Engineer, la decisión de priorización no se basa en "qué tecnología está de moda", sino en la intersección entre Impacto Directo y Retorno de Inversión (ROI).

### Matriz de Priorización

| Caso de Uso | Complejidad de Implementación | Costo / Riesgo Técnico | Impacto de Negocio | Time-to-Value | Rango de Prioridad |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **1. Extracción Estructurada de CVs** | Media | Bajo/Medio | **Muy Alto** (Elimina 80% data-entry manual) | Rápido (Semanas) | **Prioridad 1 (MVP)** |
| **2. Reportes (RAG/NLP a SQL)** | Media-Alta | Medio | Alto (Análisis estratégico) | Medio (Meses) | Prioridad 2 |
| **3. Asistente Chat (Candidatos)** | Alta | Alto (Riesgo de alucinación cara al usuario) | Medio (Soporte nivel 1) | Lento | Prioridad 3 |
| **4. Clasificación de Tickets IT** | Baja | Bajo | Bajo (Solo optimiza IT, no Core Business) | Rápido | Prioridad 4 |
| **5. Validación CRM/ERP** | Baja (Reglas puras) | Nulo | Alto (Integridad de datos) | Rápido | **No usar IA Generativa** |

### 🎯 Decisión Crítica: ¿Por qué Extracción de Documentos como MVP?
El proceso de lectura humana de CVs e ingreso manual a un ATS es el cuello de botella más grande en talento (alto costo operativo y fricción manual). Implementar un modelo que automatice esto ofrece un **Impacto Inmediato**.

### 🧐 El Filtro Senior: ¿IA, Reglas, o Híbrido?
No todos los problemas requieren un Large Language Model.
- **Validación CRM/ERP:** NO debería usar IA generativa. Se debe resolver al 100% con Reglas Deterministas (Expresiones Regulares, Type Checkers como Pydantic) ya que un LLM es estadístico y costoso para validar formatos rígidos (como que un NIT tenga 9 dígitos).
- **Extracción de CVs (Este MVP):** Usa un **Enfoque Híbrido**. PyMuPDF (Reglas) para parsear el binario, Presidio (Reglas/NLP Tradicional) para anonimizar nombres y correos, y finalmente un LLM (IA Generativa) exclusivamente para comprender la semántica del historial laboral.

---

# 🏗️ PARTE 2: Diseño de Solución (El MVP Construido)

Para construir la extracción de datos, diseñamos un pipeline resiliente y seguro:

### Arquitectura de Alto Nivel (Flujo de Datos End-to-End)

```text
[PDF Upload]
     │
     ▼
(PyMuPDF Parser) ───> Extrae Texto Plano respetando orden de lectura (Sin IA)
     │
     ▼
(Microsoft Presidio) ───> Detecta y Máscara PII localmente (Ej: "Juan" -> <PERSON>)
     │
     ▼
(Groq Llama-3.3 + Instructor) ───> LLM extrae semántica estructurada en JSON estricto
     │
     ▼
(HitL & Confidence Engine) ───> ¿Score < 0.85? -> PENDING. ¿Score >= 0.85? -> APPROVED.
     │
     ▼
(PostgreSQL + SQLAlchemy 2) ───> Persistencia asíncrona usando Patrón Repositorio
```

### Control de Outputs y Prevención de Alucinaciones
Usamos la librería **`instructor`** sobre el cliente de OpenAI/Groq para forzar al LLM (Llama-3.3-70b) a devolver llamadas a funciones (Function Calling/Structured Outputs) que deben cumplir milimétricamente con el esquema Pydantic `CandidateProfile`. Esto elimina las alucinaciones estructurales.

### Variante de Arquitectura (MVP vs Producción Escalable)
- **MVP Actual (Lite):** FastAPI maneja el endpoint de forma síncrona/esperando al LLM. Base de datos monolítica (PostgreSQL local).
- **Arquitectura Escalable Futura:** Cuando el volumen supere los 10,000 PDFs diarios, extraeríamos la inferencia del LLM a *Workers* asíncronos usando **Celery y RabbitMQ**. El endpoint FastAPI solo recibiría el PDF, lo encolaría y devolvería un `task_id` (Event-Driven Architecture).

---

# 🛡️ PARTE 3: Coste, Riesgos y Producción

Llevar IA Generativa a producción implica 3 riesgos principales que este MVP ya mitiga:

1. **Riesgo de Privacidad (PII):** Enviar datos sensibles (Nombres, Correos, Teléfonos) a APIs de OpenAI o Groq viola políticas GDPR/CCPA.
   * **Mitigación implementada:** Usamos **Microsoft Presidio** ejecutándose localmente en nuestro servidor para anonimizar los datos antes de la red.
2. **Control de Costos y Latencia:** GPT-4o es costoso. 
   * **Mitigación implementada:** Utilizamos el modelo Open Source **Llama-3.3-70b-versatile** alojado en Groq, que ofrece velocidad ultrarrápida (LPUs) a un coste marginal por millón de tokens, manteniendo una precisión comparable en extracción estructurada.
3. **Caídas de Proveedor (Rate Limits):** 
   * **Mitigación implementada:** Usamos la librería **`tenacity`** para inyectar *Exponential Backoff*. Si la cuota del LLM se agota, el sistema reintenta inteligentemente sin crashear. Además, implementamos degradación elegante (Graceful Fallback) en Base de Datos.

---

# 🚀 PARTE 4: Implementación, Adopción y Métricas

### De Prototipo a Producción Continua
El camino para que el equipo de Talento adopte esta herramienta no es reemplazar a los reclutadores, sino potenciar su embudo. Por eso se construyó el módulo **HITL (Human-In-The-Loop)**. Todos los documentos con confianza menor al 85% caen a una bandeja de `PENDING` para revisión humana. A medida que el modelo mejore y gane confianza (Fine-tuning futuro), el umbral se podrá bajar.

### Definición de Métricas (KPIs)

Para asegurar el éxito del proyecto ante los stakeholders, mediremos:

**2 Métricas Técnicas:**
- **Latencia del Pipeline (p95):** Tiempo de respuesta End-to-End < 2.5 segundos por documento (logrado actualmente gracias a Groq LPUs y bases asíncronas).
- **Tasa de Extracción Estructurada Exitosa:** > 98% de solicitudes donde Pydantic no arroja `ValidationError` por alucinaciones estructurales del LLM.

**2 Métricas de Negocio:**
- **Reducción de Tiempo de Procesamiento (Operativa):** Reducción de > 80% en el tiempo empleado por los reclutadores para digitalizar datos de CVs hacia la plataforma ATS.
- **Retorno de Inversión (ROI):** Alcanzar ROI positivo en < 3 meses (calculado por horas-hombre ahorradas vs coste de infraestructura Groq/Cloud).

---
*Desarrollado para la Evaluación Técnica de Talento.*
