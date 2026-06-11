# MercadoPago ARS — Abril 2026

## Archivo crudo archivado
- `data/raw/2026-04/mercadopago/2026-04_mercadopago_movements_ars.csv`

## Decisión de corte temporal
Para MercadoPago en V1, el mes económico del movimiento se determina por `TRANSACTION_DATE`.

`SETTLEMENT_DATE` se conserva como dato de trazabilidad y para detectar cruces de mes, pero no redefine automáticamente el mes del gasto o movimiento.

## Caso detectado en abril 2026
Se detectó 1 movimiento con cruce de mes:
- `TRANSACTION_DATE`: `2026-04-30T22:06:00.000-03:00`
- `SETTLEMENT_DATE`: `2026-05-01T23:51:28.000-03:00`
- `REAL_AMOUNT`: `-40880.00`
- criterio aplicado: **contar en abril 2026**

## Resumen rápido de inspección inicial
- filas totales del archivo: 110
- filas con `TRANSACTION_DATE` en abril 2026: 107
- filas con `TRANSACTION_DATE` en mayo 2026: 2
- filas con `TRANSACTION_DATE` en marzo 2026: 1

## Patrón observado
- muchas entradas `bank_transfer` positivas parecen fondeo/transferencia interna
- muchas salidas `available_money` negativas parecen gasto real
- existen `PAYOUTS` negativas que podrían ser retiros/transferencias y necesitan revisión al normalizar
- existen microcréditos/intereses positivos muy chicos que conviene clasificar aparte

## Estado
Inspección inicial completa. Falta normalización detallada y cruce con Galicia para detectar transferencias internas.
