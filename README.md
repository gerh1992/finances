# Financial System V1

Este directorio contiene la primera versión del sistema financiero personal y es la carpeta canónica que se va a versionar en GitHub para el repo `finances`.

## Estructura
- `01_system_design.md` — objetivos, alcance y decisiones de arquitectura
- `02_data_model.md` — modelo de datos y reglas de tablas
- `03_operating_process.md` — ritual semanal/mensual/trimestral
- `04_v1_operational_rules.md` — reglas operativas explícitas
- `05_source_inventory.md` — inventario inicial de cuentas/fuentes V1
- `06_ingestion_spec.md` — contrato de ingestión mensual
- `data/raw/` — archivos crudos por período e institución
- `data/staging/` — extracciones o transformaciones intermedias antes de normalizar
- `data/normalized/` — source of truth en CSV para balances, transacciones, gasto e inversiones
- `data/manual/` — inputs manuales livianos mantenidos fuera del chat, por ejemplo `daily_cash_check.csv`
- `parsers/` — parsers o notas de parsing reutilizables
- `logs/` — notas, validaciones y decisiones manuales

## Source of truth
Los CSVs en `data/normalized/` son el source of truth operativo de V1.

`data/manual/` contiene inputs manuales complementarios; no reemplaza el source of truth normalizado, pero preserva señales operativas útiles para completar cierres y trazabilidad conversacional.

## Moneda base
USD.

## Estado inicial
Sistema bootstrappeado con cuentas iniciales, estructura de carpetas consolidada y CSVs base listos para empezar el primer cierre mensual.
