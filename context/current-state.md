# Current State

## Canonical repo
- local root: `/home/ubuntu/.hermes/data/finances`
- remote: `git@github.com:gerh1992/finances.git`
- default branch: `main`

## Legacy compatibility
Para no romper rutas viejas, existen estas compatibilidades:
- `/home/ubuntu/.hermes/cache/documents/financial-system-v1` -> symlink al repo canónico
- `/home/ubuntu/.hermes/data/finance/daily_cash_check.csv` -> symlink a `data/manual/daily_cash_check.csv`

## Nivel de madurez actual
Este repo está en una etapa de **arquitectura ya definida + población todavía parcial**.

Eso significa:
- la estructura conceptual ya está bastante clara,
- la semántica principal ya está decidida,
- pero la cobertura de datos y automatización todavía no está completa.

## Qué contenido real hay hoy
### Diseño y reglas
- diseño del sistema V1
- modelo de datos V1
- proceso operativo semanal/mensual/trimestral
- reglas operativas V1
- inventario inicial de fuentes
- especificación de ingestión

### Datos / evidencia ya presentes
- `data/normalized/accounts.csv` ya tiene el catálogo inicial de cuentas
- los otros CSVs normalizados están inicializados pero todavía casi vacíos
- `data/raw/` tiene material piloto de abril 2026
- `data/staging/` tiene extracciones intermedias de abril 2026
- `logs/` contiene notas de interpretación preliminar de abril 2026
- `data/manual/daily_cash_check.csv` guarda seguimiento manual liviano para cash/gasto diario

## Fuentes y entidades relevantes conocidas
El sistema ya contempla, entre otras:
- Galicia ARS / USD
- BNA ARS
- BOFA USD
- Mercado Pago ARS
- Wise USD
- Payoneer USD
- Citibank USD
- Invertir Online
- Charles Schwab
- efectivo manual

## Lectura correcta del estado actual
No asumir que porque existe el esquema, todos los cierres están cargados.

La lectura correcta hoy es:
- el repo ya define cómo debería funcionar el sistema,
- hay evidencia y material piloto útil,
- pero todavía hay trabajo por hacer para poblarlo y endurecerlo.

## Qué debe hacer alguien nuevo antes de tocar datos
1. leer `context/decision-rules.md`
2. revisar `01_system_design.md` y `02_data_model.md`
3. entender si está tocando crudos, staging, canon normalizado o notas
4. no mezclar una mejora de arquitectura con una migración de datos silenciosa
