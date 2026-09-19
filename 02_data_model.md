# Sistema Financiero Personal V1 — Modelo de Datos

## Objetivo del modelo
Diseñar un esquema de datos simple, explícito y portable para consolidar información financiera personal sin depender de una app cerrada.

La regla general es:
- los archivos originales son inputs,
- los CSVs normalizados son el source of truth,
- cada tabla cumple una sola responsabilidad.

## Convenciones globales
- Moneda base del sistema: `USD`
- Siempre preservar:
  - monto original,
  - moneda original,
  - tipo de cambio usado si hubo conversión,
  - archivo o fuente de origen.
- Fechas en ISO: `YYYY-MM-DD`
- IDs estables y legibles cuando sea posible.

---

## 1. `accounts.csv`
Catálogo de cuentas, billeteras, brokers y contenedores de saldo.

### Propósito
Resolver: “qué lugares existen en el sistema”.

### Columnas
- `account_id` — identificador único estable
- `account_name` — nombre visible
- `institution` — entidad o plataforma
- `country` — `AR`, `US`, etc.
- `account_type` — `bank`, `wallet`, `broker`, `cash`, `platform_balance`
- `owner_scope` — en V1 siempre `personal`
- `default_currency` — moneda principal de referencia de la cuenta
- `is_active` — `true`/`false`
- `notes`

### Ejemplos
- `galicia_ars`
- `galicia_usd`
- `bna_ars`
- `bofa_usd`
- `mercadopago_ars`
- `wise_usd`
- `payoneer_usd`
- `citibank_usd`
- `iol_broker`
- `schwab_broker`
- `cash_manual`

### Notas de diseño
- Un broker no se modela solo por “moneda”; se modela como cuenta/plataforma y luego se registran sus saldos/posiciones por moneda o activo.
- Si más adelante una plataforma necesita subcuentas, se agregan sin romper el resto del modelo.

---

## 2. `account_balances.csv`
Snapshots de cash/saldos por cuenta y por moneda.

### Propósito
Resolver: “cuánto dinero líquido o cuasi líquido hay a fecha de cierre”.

### Columnas
- `snapshot_date` — mes o corte lógico al que pertenece la fila
- `as_of_date` — fecha efectiva del saldo informado por la fuente
- `account_id`
- `currency`
- `balance_original`
- `fx_to_usd`
- `balance_usd`
- `liquidity_tier` — `immediate`, `short_term`, `invested`
- `source_type` — `csv`, `pdf`, `manual`, `statement`
- `source_file`
- `notes`

### Reglas
- Una cuenta puede tener varias filas en una misma fecha si maneja más de una moneda.
- `snapshot_date` permite agrupar cierres mensuales; `as_of_date` preserva la fecha real de la fuente.
- `balance_usd` se calcula como `balance_original * fx_to_usd`.
- Si el saldo es manual (ej. efectivo), debe quedar explícito en `source_type` y `notes`.
- **Deuda de Tarjeta como Pasivo**: Las deudas acumuladas en tarjetas de crédito al cierre de mes se registran como un balance con valor **negativo** en su cuenta de tarjeta de crédito correspondiente. Esto permite que la agregación del patrimonio neto consolidado refleje la liquidez neta real del usuario.
- **Principio de Tenencia Real**: Los saldos se persisten exactamente en su moneda nativa (ej. pesos en ARS, dólares en USD). La unificación a USD para visualizaciones agregadas se calcula dinámicamente en el visualizador, evitando fijar conversiones estáticas en los datos base de saldos.

---

## 3. `transactions_normalized.csv`
Movimientos normalizados desde bancos, billeteras y eventualmente resúmenes de tarjeta.

### Propósito
Resolver: “qué movimientos hubo y cuáles impactan gasto real”.

### Columnas
- `txn_id`
- `account_id`
- `txn_date`
- `posted_date`
- `description_raw`
- `amount_original`
- `currency`
- `direction` — `inflow` / `outflow`
- `normalized_type`
- `counterparty`
- `is_internal_transfer`
- `expense_bucket`
- `expense_type` — `fixed` (fijo/esencial) / `discretionary` (variable/opcional) / `-` (si no es gasto)
- `needs_review`
- `source_file`
- `notes`

### `normalized_type` inicial
- `expense`
- `income`
- `internal_transfer`
- `investment_funding`
- `asset_purchase`
- `asset_sale`
- `fee`
- `fx_conversion`
- `card_payment`
- `unknown`

### Reglas importantes
1. **Transferencia interna**: mover plata entre cuentas propias no cuenta como gasto.
2. **Fondeo de broker**: no cuenta como gasto.
3. **Compra de activos**: no cuenta como gasto.
4. **Fee**: sí impacta gasto/costo.
5. **Pago de tarjeta**: cuidado con no duplicar consumos ya registrados en el resumen.
6. Cualquier movimiento dudoso debe quedar con `needs_review = true`.

### Observación
No todos los movimientos terminan expuestos al usuario final. Muchos solo sirven para derivar gasto agregado y limpiar duplicaciones.

---

## 4. `monthly_expense_summary.csv`
Resumen mensual de gasto agregado por bucket y tipo de gasto.

### Propósito
Resolver: “cuánto salió vivir ese mes, a grandes rasgos”.

### Columnas
- `month` — `YYYY-MM`
- `bucket`
- `expense_type` — `fixed` / `discretionary`
- `amount_usd`
- `currency_basis`
- `source_method`
- `notes`

### Buckets iniciales V1
- `housing`
- `food`
- `transport`
- `health`
- `social`
- `shopping`
- `hobbies`
- `other`

### Reglas
- Este archivo es agregado, no itemizado.
- Se puede construir a partir de transacciones normalizadas o de resúmenes agregados si eso da un resultado más robusto.
- Si un bucket no aparece en un mes, puede omitirse o registrarse en cero según convención futura.

---

## 5. `investment_positions.csv`
Snapshot de posiciones de inversión tradicionales a fecha de cierre.

### Propósito
Resolver: “qué inversiones tengo y cuánto valen hoy”.

### Columnas
- `snapshot_date`
- `as_of_date`
- `broker_account_id`
- `asset_id`
- `asset_name`
- `asset_class`
- `quantity`
- `currency`
- `cost_basis_original`
- `cost_basis_usd`
- `market_value_original`
- `fx_to_usd`
- `market_value_usd`
- `unrealized_pnl_usd`
- `notes`

### Reglas
- Si el broker ya provee costo y valuación, V1 usa esos datos en vez de inventar pricing externo.
- `cost_basis_original` expresa el costo en la moneda nativa del activo (`currency`: ARS para CEDEARs locales, USD para activos estadounidenses).
- `cost_basis_usd` expresa el costo de adquisición dolarizado (al tipo de cambio histórico al momento de la compra o nativo USD).
- `asset_class` puede empezar simple: `stock`, `etf`, `bond`, `fund`, `cash_equivalent`, `other`.
- Si un dato no existe en el extracto, se deja explícito y no se inventa.

---

## 6. `investment_cashflows.csv`
Eventos de inversión para reconstruir aportes, retiros y cambios de cartera.

### Propósito
Resolver: “qué pasó en inversiones durante el período”.

### Columnas
- `event_date`
- `broker_account_id`
- `asset_id`
- `event_type`
- `quantity`
- `price_original`
- `gross_amount_original`
- `currency`
- `fx_to_usd`
- `gross_amount_usd`
- `fees_original`
- `source_file`
- `notes`

### `event_type` inicial
- `buy`
- `sell`
- `deposit`
- `withdrawal`
- `dividend`
- `fee`
- `interest`
- `unknown`

### Reglas
- La evolución histórica se construye combinando cashflows con snapshots de posiciones.
- Si el broker ya entrega cashflows limpios, se respetan.
- Si no, Hermes deriva lo posible y marca lo ambiguo.

---

## 7. `fx_rates.csv` (opcional pero recomendable)
Tabla de tipos de cambio usados para consolidación.

### Propósito
Evitar que el sistema “olvide” qué FX se usó en cada cierre.

### Columnas
- `rate_date`
- `from_currency`
- `to_currency`
- `fx_rate`
- `source`
- `notes`

### Uso en V1
Puede mantenerse mínima y solo registrar conversiones ARS→USD necesarias para cierres mensuales.

---

## Relaciones lógicas entre archivos
- `accounts.csv` define los contenedores.
- `account_balances.csv` da la foto de cash/saldos por fecha.
- `transactions_normalized.csv` explica movimientos y permite derivar gasto.
- `monthly_expense_summary.csv` es la vista simplificada del gasto mensual.
- `investment_positions.csv` da la foto de cartera por fecha.
- `investment_cashflows.csv` explica cómo evolucionó la cartera.
- `fx_rates.csv` documenta las conversiones a USD.

---

## Casos borde y reglas explícitas
### Transferencias entre cuentas propias
- No son gasto.
- Deben marcarse con `is_internal_transfer = true` o `normalized_type = internal_transfer`.

### Compra de USD con ARS
- No es gasto.
- Es conversión/cambio de composición monetaria.

### Fondeo de broker
- No es gasto.
- Es movimiento entre activos/cuentas propias.

### Pago de tarjeta
- Se debe evitar la duplicación.
- Si el gasto se toma del resumen/consumos, el pago de tarjeta no vuelve a sumar gasto.

### Efectivo
- En V1 se registra por snapshot manual.
- No requiere feed transaccional fino.

### Crypto
- Fuera de V1.
- El modelo deja espacio para agregarla después como una extensión natural de balances/posiciones.

---

## Criterio de calidad del modelo
El modelo está bien diseñado si permite:
- migrar a otra herramienta sin perder semántica,
- regenerar reportes sin tocar los archivos crudos originales,
- explicar por qué cada cifra existe,
- distinguir liquidez, gasto e inversión sin mezclarlos,
- agregar nuevas instituciones/parsers sin romper el sistema.
