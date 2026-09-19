# Context Layer

Esta carpeta existe para que una persona o IA nueva pueda entender rápido:
- qué problema resuelve el sistema,
- en qué estado está,
- qué reglas no se deben romper,
- dónde mirar primero,
- y cómo contribuir sin depender de contexto implícito del chat.

## Orden de lectura recomendado
1. `finance-brief.md` — brief ejecutivo del sistema
2. `current-state.md` — estado operativo y madurez actual
3. `decision-rules.md` — reglas económicas y de interpretación que no conviene violar
4. `principles.md` — principios estratégicos de inversión, asignación de capital y liquidez
5. `data-sources.yaml` — mapa de fuentes, rol y prioridad
6. `contributor-workflow.md` — cómo editar sin degradar el sistema


## Qué NO debería vivir solo en el chat
Si una regla o decisión cambia cómo se interpreta el sistema, debería terminar documentada acá o en los documentos raíz del repo.

El objetivo es evitar una caja negra donde solo entiende el último agente que tocó el sistema.
