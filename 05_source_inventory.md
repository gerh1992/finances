# Sistema Financiero Personal V1 — Inventario Inicial de Fuentes

## Propósito
Dejar explícito qué cuentas, plataformas y fuentes forman parte de V1, cómo se nombran y cómo deben interpretarse dentro del sistema.

Este documento baja el diseño abstracto a un inventario operativo real.

---

## Convenciones de naming
### Reglas generales
- `account_id` en minúsculas, con `_`
- usar nombre corto + moneda o función cuando haga falta
- evitar nombres ambiguos como `banco1` o `broker2`
- si una institución tiene más de una cuenta relevante, separar por cuenta/moneda

### Formato recomendado
`institucion_tipo_moneda` o `institucion_moneda`

Ejemplos:
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

---

## Alcance V1
### Incluido en V1
- cash y saldos personales
- bancos
- billeteras
- brokers e inversiones tradicionales
- gasto mensual agregado
- efectivo manual

### Explícitamente fuera de V1
- crypto (USDT, BTC, ETH, etc.)
- impuestos
- APIs bancarias
- trabajo/empresa/shared finances

---

## Inventario inicial de cuentas y fuentes

## 1. Bancos y cuentas de cash
### `galicia_ars`
- `institution`: Galicia
- `country`: AR
- `account_type`: bank
- `default_currency`: ARS
- `liquidity_tier` esperado: `immediate`
- `included_in_v1`: yes
- `notes`: cuenta bancaria personal en ARS

### `galicia_usd`
- `institution`: Galicia
- `country`: AR
- `account_type`: bank
- `default_currency`: USD
- `liquidity_tier` esperado: `immediate`
- `included_in_v1`: yes
- `notes`: cuenta bancaria personal en USD

### `bna_ars`
- `institution`: Banco Nación
- `country`: AR
- `account_type`: bank
- `default_currency`: ARS
- `liquidity_tier` esperado: `immediate`
- `included_in_v1`: yes

### `bofa_usd`
- `institution`: Bank of America
- `country`: US
- `account_type`: bank
- `default_currency`: USD
- `liquidity_tier` esperado: `immediate`
- `included_in_v1`: yes

### `citibank_usd`
- `institution`: Citibank
- `country`: US
- `account_type`: bank
- `default_currency`: USD
- `liquidity_tier` esperado: `immediate`
- `included_in_v1`: yes

---

## 2. Billeteras / plataformas de saldo
### `mercadopago_ars`
- `institution`: MercadoPago
- `country`: AR
- `account_type`: wallet
- `default_currency`: ARS
- `liquidity_tier` esperado: `immediate`
- `included_in_v1`: yes
- `notes`: fuente importante para gasto y movimientos cotidianos

### `wise_usd`
- `institution`: Wise
- `country`: US/global
- `account_type`: wallet
- `default_currency`: USD
- `liquidity_tier` esperado: `immediate`
- `included_in_v1`: yes

### `payoneer_usd`
- `institution`: Payoneer
- `country`: US/global
- `account_type`: platform_balance
- `default_currency`: USD
- `liquidity_tier` esperado: `short_term`
- `included_in_v1`: yes
- `notes`: puede requerir interpretación distinta si opera más como saldo de plataforma que como banco tradicional

---

## 3. Brokers / inversiones tradicionales
### `iol_broker`
- `institution`: Invertir Online
- `country`: AR
- `account_type`: broker
- `default_currency`: ARS
- `liquidity_tier` esperado: `invested`
- `included_in_v1`: yes
- `notes`: modelar cash y posiciones por separado en snapshots/positions

### `schwab_broker`
- `institution`: Charles Schwab
- `country`: US
- `account_type`: broker
- `default_currency`: USD
- `liquidity_tier` esperado: `invested`
- `included_in_v1`: yes
- `notes`: modelar cash y posiciones por separado; no tratar como “cuenta mezclada” sin estructura

### `binance_crypto`
- `institution`: Binance
- `country`: global
- `account_type`: broker
- `default_currency`: USD
- `liquidity_tier` esperado: `invested`
- `included_in_v1`: yes
- `notes`: exchange de criptomonedas (Spot, Simple Earn Flexible y ETH 2.0 Staking / BETH)

---

## 4. Efectivo manual
### `cash_manual`
- `institution`: manual
- `country`: mixed/physical
- `account_type`: cash
- `default_currency`: variable
- `liquidity_tier` esperado: `immediate`
- `included_in_v1`: yes
- `notes`: snapshot manual al cierre mensual; sin feed transaccional fino en V1

---

## Monedas V1
- `ARS`
- `USD`

## Monedas conocidas pero fuera de V1
- `USDT`
- `BTC`
- `ETH`
- otras crypto futuras

---

## Qué esperamos de cada fuente en V1
### Bancos/billeteras
Idealmente:
- saldo de cierre,
- movimientos del período,
- fecha efectiva,
- moneda,
- descripción de movimientos.

### Brokers
Idealmente:
- posición o valuación de cierre,
- cash disponible,
- compras/ventas/aportes/retiros si el archivo lo permite,
- market value o valuación equivalente.

### Efectivo manual
Idealmente:
- fecha,
- moneda,
- monto,
- nota libre si hace falta.

---

## Decisiones explícitas del inventario
1. Todo el scope V1 es **personal**.
2. Crypto queda fuera para simplificar arranque.
3. Cada fuente debe mapear a una cuenta o broker explícito, no quedar “difusa”.
4. Los brokers se modelan como plataforma + snapshots de cash/posiciones, no como un único saldo opaco.
5. Si una fuente nueva aparece, primero se agrega al inventario y recién después se parsea de forma estable.
