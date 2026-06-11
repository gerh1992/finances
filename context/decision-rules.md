# Decision Rules

Este documento resume las reglas que más importan para no romper la semántica del sistema.

## 1. Definición económica de gasto
**Gasto** = salida que reduce patrimonio neto sin crear otro activo propio.

Entonces:
- comida, alquiler, salud, fees, consumo final -> sí son gasto
- transferencia entre cuentas propias -> no
- compra de USD con ARS propio -> no
- fondeo de broker propio -> no
- compra de activos financieros -> no
- pago de tarjeta ya reconocido por resumen -> no

## 2. Moneda base
La moneda base del sistema es `USD`.

Siempre que sea posible hay que preservar:
- monto original,
- moneda original,
- tipo de cambio usado,
- fuente o archivo de origen.

## 3. FX histórico vs FX operativo
- cierres históricos mensuales -> usar FX del cierre de ese período
- decisiones operativas actuales -> usar FX actual o el más reciente acordado

Nunca reescribir cierres históricos con el tipo de cambio de hoy.

## 4. Tarjetas
Regla V1:
- si existe resumen/export confiable, esa es la fuente principal del gasto de tarjeta
- el pago posterior desde cuenta no debe contarse otra vez como gasto
- si no existe resumen utilizable, el pago de tarjeta puede usarse como proxy, pero con menor confianza

## 5. Transferencias internas
Mover plata entre cuentas propias no es gasto.

Esto incluye, según contexto:
- banco <-> billetera propia,
- Galicia <-> Mercado Pago cuando sea fondeo interno,
- compra de USD con fondos propios,
- fondeo de broker propio.

## 6. Mercado Pago con dos fechas
Para Mercado Pago y fuentes parecidas:
- `TRANSACTION_DATE` define el mes económico del movimiento
- `SETTLEMENT_DATE` se conserva para trazabilidad y conciliación
- un cruce de mes no mueve automáticamente el gasto al mes siguiente

## 7. Liquidez
Los tiers de liquidez existen para no confundir patrimonio total con disponibilidad real:
- `immediate`
- `short_term`
- `invested`

## 8. Qué hacer con incertidumbre
Si algo es ambiguo:
- marcar revisión,
- documentar la limitación,
- pedir aclaración mínima solo si cambia una decisión,
- no inventar precisión.

## 9. Reglas contextuales ya conocidas del sistema del usuario
Estas reglas ya aparecieron como importantes y deben preservarse salvo cambio explícito:
- principales fuentes de gasto: Mercado Pago, cash, Galicia y Payoneer
- Payoneer debe contemplarse como fuente USD relevante
- muchas salidas de USD son conversiones a ARS y no gasto real
- el tracking diario manual actual pide: `ARS gasto real / USD gasto real / USD->ARS / ARS recibidos`

## 10. Regla maestra
Si una edición mejora prolijidad técnica pero empeora trazabilidad o claridad económica, probablemente es una mala edición.
