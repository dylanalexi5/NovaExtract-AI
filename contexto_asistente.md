## Arquitectura Actual
- **Patrón:** Clean Architecture / Modular Monolith.
- **Stack:** Python 3.11+, FastAPI, Pydantic v2, PostgreSQL (Supabase), PyMuPDF, Microsoft Presidio (PII).
- **IA:** OpenAI (gpt-4o-mini) con Structured Outputs / Ollama (SLM). Se utiliza EXCLUSIVAMENTE la librería `instructor` para la orquestación. Cero LangChain.

## Estado Actual
- [x] Planificación y definición del Stack (Fase 0).
- [ ] Fase 1: Setup, configuración base y estructura de carpetas (En progreso).

## Decisiones Arquitectónicas (ADR)
4. **Orquestación de IA:** Se descarta LangChain para evitar sobre-abstracción y código espagueti. Se adopta `instructor` en conjunto con Pydantic para garantizar tipado estricto, control absoluto del flujo y validación nativa de los outputs del LLM.