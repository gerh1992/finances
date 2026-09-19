# Finance Brief

## Qué es esto
Un sistema financiero personal versionado en Git para consolidar:
- cuentas y saldos,
- gasto mensual,
- liquidez,
- inversiones tradicionales,
- y decisiones financieras asociadas.

No es una app cerrada. Es un repo auditable con datos legibles, reglas explícitas y espacio para parsers/revisión manual.

## Qué intenta responder
- ¿Dónde está la plata?
- ¿Cuánta liquidez real hay hoy?
- ¿Cuánto salió vivir este mes?
- ¿Qué parte es gasto real vs transferencia o inversión?
- ¿Qué decisiones financieras concretas conviene evaluar?

## Filosofía
- robustez > falsa precisión
- trazabilidad > magia
- datos simples y portables > sistema opaco
- no inventar > completar huecos con confianza artificial
- separar capas lógicas > meter todo en un solo CSV

## Núcleo del modelo
La capa canónica es `data/normalized/`.

Tablas principales:
- `accounts.csv` — catálogo de cuentas/plataformas
- `account_balances.csv` — snapshots de cash/saldos
- `transactions_normalized.csv` — movimientos normalizados
- `monthly_expense_summary.csv` — gasto agregado mensual
- `investment_positions.csv` — snapshot de cartera
- `investment_cashflows.csv` — flujos de inversión
- `fx_rates.csv` — FX usado para consolidación

## Qué ya está decidido
- moneda base: `USD`
- V1 incluye activos cripto (Binance BTC/ETH/BETH) y excluye impuestos complejos
- gasto se mira de forma económica, no meramente como caja bruta
- no se debe duplicar gasto con pagos de tarjeta o transferencias internas
- histórico mensual usa FX de cierre, no FX actual reescribiendo el pasado
- el sistema tiene que ser entendible por terceros sin depender del chat

## Estado actual de madurez
El sistema está bootstrappeado, no completo.

Hoy ya existen:
- diseño V1,
- modelo de datos V1,
- reglas operativas V1,
- inventario inicial de fuentes,
- inputs piloto de abril 2026,
- notas de interpretación inicial,
- catálogo de cuentas cargado,
- capa manual mínima para cash diario.

Todavía faltan, en distinto grado:
- poblar cierres mensuales consistentes,
- expandir parsers reutilizables,
- normalización más completa de transacciones,
- validadores automáticos más fuertes,
- mayor cobertura de fuentes reales.

## Cómo pensar una contribución buena
Una contribución suma si hace al menos una de estas cosas:
- mejora claridad del sistema,
- agrega trazabilidad,
- baja ambigüedad de una regla,
- mejora reutilización de parsers o mappings,
- incorpora una fuente real sin romper semántica,
- mejora la capacidad de responder preguntas de liquidez/gasto/inversión.

## Cómo pensar una contribución mala
Una contribución probablemente degrada el sistema si:
- mezcla gasto con transferencias,
- mete lógica implícita no documentada,
- sobreescribe crudos como si fueran canon,
- inventa datos faltantes,
- agrega automatización frágil sin trazabilidad,
- cambia semántica histórica sin dejar nota o justificación.
