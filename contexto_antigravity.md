## Reglas de Estilo y Código
- **Orquestación LLM:** Prohibido usar LangChain o LlamaIndex. Toda interacción con modelos de lenguaje y extracción de datos estructurados debe implementarse utilizando la librería `instructor` parcheando el cliente oficial (ej. OpenAI) y validando con Pydantic v2.
- **Procesamiento de Documentos:** Aislamiento estricto. La lógica de lectura de PDFs (PyMuPDF) o correos debe residir exclusivamente en la capa de `infrastructure`. Los Casos de Uso (`use_cases`) solo deben recibir texto plano estructurado.
- **Seguridad (PII):** Implementar la sanitización de datos de manera agnóstica mediante una interfaz en `domain` y su implementación concreta con Presidio en `infrastructure`.
- **Extracción Híbrida (Fase 3):** Siempre ejecutar primero una capa determinista (Regex) para campos predecibles (fechas, correos, IDs). Solo enviar al LLM (vía `instructor`) el texto restante o los campos semánticamente complejos. Los modelos Pydantic de salida deben incluir validaciones de campo (`Field(..., description="...")`) que sirvan de prompt implícito para el LLM.

## Convenciones de Idioma
- **Código e Infraestructura (100% Inglés):** Todo el código Python, variables, funciones, nombres de clases, módulos, docstrings, comentarios dentro del código, log messages, rutas API (`/api/v1/...`), schemas de BD y commit messages DEBEN estar estrictamente en INGLÉS.
- **Entregables y Justificaciones de Negocio (Español):** Explicaciones en chat, respuestas teóricas, justificaciones arquitectónicas y registros técnicos en `explicacion_tecnica.txt` deben estar en ESPAÑOL.
- **Documentación (`README.md`):** Español técnico, manteniendo términos técnicos estándar (endpoint, deployment, payload, webhook, etc.).