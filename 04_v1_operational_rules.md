# Sistema Financiero Personal V1 — Reglas Operativas

## Propósito
Bajar el diseño conceptual a reglas concretas de operación para que el sistema sea consistente, auditable y fácil de mantener.

Estas reglas definen cómo Hermes debe interpretar tarjetas, tipos de cambio, cierres mensuales, valuaciones y casos ambiguos.

---

## 1. Regla de tarjetas

### Política V1
Se usa un modelo de **híbrido controlado**.

### Regla principal
1. Si existe **resumen de tarjeta** o **export de consumos** suficientemente confiable, esa es la fuente principal del gasto.
2. Si no existe resumen/export utilizable, se usa el **movimiento de pago** desde la cuenta pagadora como proxy.
3. Nunca se cuentan ambas cosas como gasto al mismo tiempo.

### Asignación temporal del gasto en V1
Cuando existe resumen/consumos, el gasto se asigna al **mes del resumen/cierre de tarjeta**, no al mes exacto de cada consumo individual.

### Tratamiento del pago de tarjeta
- Si el gasto ya fue reconocido por resumen/consumos, el pago posterior de la tarjeta se clasifica como `card_settlement` o equivalente operativo, **no como gasto nuevo**.
- Si no hubo resumen/consumos disponibles y se usa el pago como proxy, ese pago sí puede alimentar el gasto mensual, pero debe quedar marcado con menor calidad/confianza analítica.

### Justificación
Esta política prioriza:
- robustez,
- baja fricción,
- evitar doble conteo,
- utilidad práctica para revisión mensual.

No busca contabilidad perfecta por fecha de consumo en V1.

---

## 2. Regla de FX ARS→USD

## Moneda base
La moneda base del sistema es `USD`.

## Dos usos distintos del FX
### A. FX histórico de cierre
Para cierres mensuales y análisis histórico, se usa el **promedio entre compra y venta del dólar blue de Ámbito** correspondiente a la fecha de cierre del período, o el día hábil más cercano disponible.

Ese valor:
- se guarda,
- no se recalcula retroactivamente por cambios futuros del mercado,
- se usa para consolidar los datos de ese mes.

### B. FX operativo actual
Para conversaciones semanales o decisiones presentes (por ejemplo, si conviene cambiar liquidez hoy), se usa el **FX más reciente disponible**.

Puede ser:
- provisto manualmente por el usuario una vez por semana,
- o tomado de la referencia acordada si luego se automatiza de forma robusta.

## Regla clave
- **Histórico mensual**: FX del cierre de ese mes.
- **Operativo actual**: FX más reciente.

Nunca se debe reescribir la historia usando el tipo de cambio de hoy para meses ya cerrados.

---

## 2. Regla de MercadoPago / billeteras con dos fechas

### Política V1
Cuando una fuente tipo billetera trae tanto `TRANSACTION_DATE` como `SETTLEMENT_DATE`, se usa una separación explícita entre:
- **fecha económica del movimiento**,
- **fecha de liquidación/trazabilidad**.

### Regla principal
- El mes del movimiento en reportes y clasificación mensual se determina por **`TRANSACTION_DATE`**.
- `SETTLEMENT_DATE` se conserva para trazabilidad, conciliación y detección de cruces de mes.
- Un cruce de mes no mueve automáticamente el movimiento al mes siguiente.

### Justificación
Esto prioriza la lectura económica del comportamiento mensual y evita deformar fin de mes por demoras operativas de liquidación.

### Caso piloto confirmado
En MercadoPago abril 2026 apareció un gasto del `2026-04-30` liquidado el `2026-05-01`; se decidió **contarlo en abril**.

---

## 4. Regla de valuaciones ya expresadas en USD

### Política
Si una fuente ya trae un valor confiable expresado en USD, ese valor se usa tal como viene.

### Entonces
- si una cuenta o plataforma informa saldo en `USD`, se usa ese valor con `fx_to_usd = 1.0`;
- si un broker informa `market value` o valuación total en USD, se usa ese valor;
- si una fuente informa montos en `ARS`, se convierten a USD usando el FX de cierre definido.

### Regla de no reconversión innecesaria
No se reconvierte algo que ya vino correctamente valuado en USD.

Esto evita:
- introducir ruido artificial,
- aplicar conversiones dobles,
- inventar pricing donde no hace falta.

---

## 4. Regla de cierre mensual

### Política V1
Se usa un **cierre flexible por fuente**.

### Qué significa
No se exige que todos los bancos, tarjetas, billeteras y brokers cierren el mismo día ni a la misma hora.

Cada fuente aporta su mejor foto disponible del período.

### Regla práctica
- para bancos/billeteras: usar la **última fecha disponible del mes** o la más cercana al cierre;
- para brokers: usar la **última valuación/posición disponible del mes**;
- para tarjetas: usar el **resumen o cierre representativo del mes**;
- para efectivo: usar **snapshot manual declarado por el usuario** al cierre.

### Requisito de trazabilidad
Cada snapshot o consolidación debe preservar su `as_of_date` o fecha efectiva equivalente.

### Justificación
Esta política reduce fricción y refleja mejor cómo existen realmente los datos financieros en distintas instituciones.

---

## 5. Regla de gasto económico

### Definición
**Gasto** = salida que reduce patrimonio neto sin crear otro activo propio.

### Sí cuentan como gasto
- comida,
- alquiler,
- salud,
- transporte,
- fees bancarios,
- hobbies,
- compras de consumo,
- gastos sociales,
- otros consumos finales.

### No cuentan como gasto
- transferencia entre cuentas propias,
- compra de USD con ARS propio,
- fondeo de broker propio,
- compra de activos financieros,
- movimiento entre billetera y banco propios,
- pago de tarjeta ya reconocido por resumen.

### Regla operativa
Si existe duda, el sistema debe preferir:
- marcar `needs_review`,
- documentar el motivo,
- pedir aclaración puntual,
antes que inventar clasificación.

---

## 6. Regla de buckets de gasto en V1

### Política
Los buckets son deliberadamente amplios. V1 prioriza señal útil sobre granularidad excesiva.

### Buckets iniciales
- `housing`
- `food`
- `transport`
- `health`
- `social`
- `shopping`
- `hobbies`
- `other`

### Regla
No analizar item por item salvo que más adelante cambie una decisión o una necesidad concreta del sistema.

---

## 7. Regla de liquidez

### Liquidity tiers V1
- `immediate`
- `short_term`
- `invested`

### Objetivo
Distinguir patrimonio total de disponibilidad real.

### Uso
Todo saldo o posición relevante debe quedar asignado a un tier para que el reporte pueda responder:
- cuánto está disponible ya,
- cuánto requiere algunos días,
- cuánto está invertido.

---

## 8. Regla de calidad y confianza

### Política
Cuando una cifra proviene de una fuente más débil o indirecta, el sistema debe hacerlo explícito.

### Ejemplos
- gasto estimado por pago de tarjeta sin resumen,
- efectivo declarado manualmente,
- clasificación de bucket inferida con baja confianza,
- transferencias internas no resueltas automáticamente.

### Respuesta del sistema
- marcar la incertidumbre,
- conservar trazabilidad al archivo/fuente,
- pedir aclaración mínima solo cuando cambie el resultado o una decisión.

---

## 9. Regla de overrides manuales

### Política
Hermes puede aplicar overrides manuales cuando:
- un parser no alcanza,
- una clasificación automática es incorrecta,
- una institución cambia formato,
- una regla requiere ajuste puntual.

### Requisito
Todo override debe quedar:
- documentado,
- localizable,
- preferentemente reutilizable como regla futura.

El objetivo no es parchear en silencio, sino transformar excepciones repetidas en lógica estable.

---

## 10. Criterio de cierre mensual aceptable

Un cierre mensual V1 se considera suficientemente bueno si:
- las principales cuentas y brokers del período están cargados,
- el gasto total mensual es razonablemente representativo,
- no hay doble conteo grosero,
- la liquidez total se entiende,
- la cartera tradicional quedó actualizada,
- las incertidumbres relevantes quedaron explicitadas.

No se exige perfección contable. Sí se exige claridad útil para decidir.

---

## Regla maestra del sistema
**Robustez, trazabilidad y utilidad para decidir están por encima de la falsa precisión.**

Si hay que elegir entre:
- un sistema supuestamente exacto pero frágil,
- y un sistema simple, explícito y sostenible,

V1 elige lo segundo.