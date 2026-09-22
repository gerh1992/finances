# Personal Finance System V1

Este repo es el sistema financiero personal canónico de trabajo.

Está diseñado para que **humanos y otras IAs** puedan entender el sistema sin depender del chat, contribuir sin romper semántica, y auditar cómo se interpreta cada fuente.

## Qué resuelve
La meta de V1 no es hacer contabilidad perfecta ni análisis fiscal. La meta es responder bien estas preguntas:
- dónde está la plata,
- cuánta liquidez real hay,
- cuánto se gastó en el mes,
- cómo evolucionan las inversiones tradicionales,
- qué decisiones financieras concretas conviene tomar ahora.

## Orden de lectura recomendado
Si entrás por primera vez, leé en este orden:

1. `context/finance-brief.md`
2. `context/current-state.md`
3. `context/decision-rules.md`
4. `01_system_design.md`
5. `02_data_model.md`
6. `03_operating_process.md`
7. `04_v1_operational_rules.md`
8. `05_source_inventory.md`
9. `06_ingestion_spec.md`
10. `07_financial_dashboard_spec.md`

## Estructura
- `context/` — onboarding, contexto operativo y reglas de interpretación
- `01_system_design.md` — objetivos, alcance y decisiones de arquitectura
- `02_data_model.md` — modelo de datos y reglas de tablas
- `03_operating_process.md` — ritual semanal/mensual/trimestral
- `04_v1_operational_rules.md` — reglas operativas explícitas
- `05_source_inventory.md` — inventario inicial de cuentas/fuentes V1
- `06_ingestion_spec.md` — contrato de ingestión mensual
- `07_financial_dashboard_spec.md` — especificación técnica y de producto del dashboard financiero (alojado y ejecutado centralmente en `utils/visualizer/`)
- `data/raw/` — archivos crudos por período e institución
- `data/staging/` — extracciones o transformaciones intermedias antes de normalizar
- `data/normalized/` — source of truth en CSV para balances, transacciones, gasto e inversiones
- `data/manual/` — inputs manuales complementarios, por ejemplo `daily_cash_check.csv`
- `parsers/` — parsers o notas de parsing reutilizables
- `logs/` — notas, validaciones y decisiones manuales

## Qué es source of truth y qué no
### Sí es source of truth
Los CSVs en `data/normalized/`.

### No es source of truth principal
- `data/raw/` — evidencia de entrada
- `data/staging/` — trabajo intermedio
- `data/manual/` — señales manuales u operativas complementarias
- `logs/` — decisiones, inspecciones, trazabilidad narrativa

`data/manual/` no reemplaza la capa normalizada. Sirve para preservar inputs útiles mientras el sistema todavía no tiene toda la automatización o el modelado final.

## Workflow de contribución
Este repo se mantiene con una disciplina simple:

1. `git pull --rebase origin main`
2. editar
3. verificar
4. `git status`
5. commit con contexto suficiente
6. push a `main`

### Verificar significa, como mínimo
- no romper estructura de carpetas,
- no sobrescribir crudos a ciegas,
- no inventar datos faltantes,
- preservar trazabilidad a fuente o nota manual,
- revisar que las reglas económicas sigan consistentes.

## Guardrails de contribución
Antes de cambiar algo, asumí estas reglas:
- no toda salida es gasto,
- transferencias entre cuentas propias no son gasto,
- compra de USD con ARS propio no es gasto,
- fondeo de broker propio no es gasto,
- compra de activos no es gasto,
- pago de tarjeta no debe duplicar gasto ya reconocido por resumen,
- si algo es ambiguo, documentar incertidumbre y pedir o dejar revisión; no inventar.

## Estado del repo hoy
El repo ya tiene:
- diseño y modelo V1 definidos,
- inventario inicial de cuentas,
- estructura canónica de carpetas,
- primer material piloto de abril 2026 en `raw/`, `staging/` y `logs/`,
- CSVs normalizados bootstrappeados,
- una capa manual mínima para seguimiento diario de cash.

Todavía no es un sistema completamente poblado ni completamente automatizado. Está en una fase donde **la arquitectura y las reglas ya existen**, pero la cobertura de datos y parsers todavía está creciendo.

## Ruta canónica local
- repo root: `/home/ubuntu/.hermes/data/finances`

Compatibilidad legada:
- `/home/ubuntu/.hermes/cache/documents/financial-system-v1` -> symlink al repo canónico
- `/home/ubuntu/.hermes/data/finance/daily_cash_check.csv` -> symlink a `data/manual/daily_cash_check.csv`

## Intención de diseño
Este sistema prioriza:
- claridad,
- trazabilidad,
- robustez,
- utilidad para decidir,
- y legibilidad por terceros.

Si una contribución agrega complejidad, tiene que comprar una mejora real en decisión, trazabilidad o reutilización. Si no, probablemente no conviene.
