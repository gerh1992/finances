# Sistema Financiero Personal V1 — Diseño

## Objetivo
Construir un sistema financiero personal simple, portable y auditable cuyo source of truth sea un conjunto pequeño de CSVs normalizados, gestionados por Hermes a partir de extractos mensuales y revisión conversacional semanal.

La meta de V1 no es hacer contabilidad perfecta ni análisis fiscal. La meta es responder bien estas preguntas:
- ¿Dónde está la plata?
- ¿Cuánta liquidez real tengo?
- ¿Cuánto gasté este mes?
- ¿Cómo evolucionan mis inversiones tradicionales?
- ¿Qué decisiones financieras concretas conviene tomar ahora?

## Alcance de V1
Incluye:
- cash y saldos en bancos/billeteras/cuentas personales,
- gastos mensuales agregados en buckets genéricos,
- inversiones tradicionales (no crypto),
- snapshots de balances y posiciones,
- eventos de inversión básicos (aportes, retiros, compras, ventas, fees, dividendos si aparecen),
- consolidación en USD como moneda base,
- revisiones semanal, mensual y trimestral.

No incluye en V1:
- crypto,
- impuestos,
- APIs bancarias,
- análisis item por item de consumos,
- automatizaciones frágiles,
- pricing engine externo complejo,
- performance attribution avanzada.

## Principios de diseño
1. **Source of truth simple**: los datos consolidados viven en CSVs legibles y portables.
2. **Hermes opera por detrás**: el usuario entrega extractos; Hermes parsea, normaliza, resume y propone decisiones.
3. **USD como moneda base**: todos los reportes consolidados se expresan en USD, preservando siempre el monto y moneda original.
4. **Robustez > automatización**: si un parser o automatización es frágil, se marca revisión manual en vez de fingir precisión.
5. **Detalle solo si cambia una decisión**: se guarda granularidad cuando aporta a decisiones; si no, se agrega.
6. **Separación de capas**: no mezclar cuentas, snapshots, transacciones, gastos agregados y posiciones de inversión en un solo archivo.
7. **Auditable y migrable**: cada fila consolidada debe poder rastrearse a un extracto, archivo o nota manual.
8. **Sistema educativo**: los reportes no solo dicen “qué pasó”; explican por qué importa y cómo pensar la decisión.

## Decisiones de arquitectura

### 1. Archivos crudos vs datos normalizados
Los PDFs/CSVs originales de bancos y brokers son **inputs**. No son el source of truth.

El source of truth son los CSVs normalizados que Hermes mantiene después de parsear los extractos.

### 2. Separar snapshots de eventos
El sistema distingue entre:
- estado de una cuenta a una fecha (`balance snapshot`),
- movimientos o eventos (`transactions`),
- posiciones de inversión (`positions snapshot`),
- flujos de inversión (`investment cashflows`).

Esto evita mezclar una foto de cierre con la historia de cómo se llegó ahí.

### 3. Definición económica de gasto
No toda salida es gasto.

**Gasto** = salida que reduce patrimonio neto sin crear otro activo propio.

Entonces:
- comida, alquiler, salud, fees: sí son gasto,
- transferencia entre cuentas propias: no,
- compra de USD con ARS propio: no,
- fondeo de broker propio: no,
- compra de activo financiero: no,
- pago de tarjeta: no si ya se tomó el resumen/consumo como gasto; sí solo si el sistema decidiera usar caja bruta, cosa que V1 no hace.

### 4. Gasto agregado por buckets
No se busca analizar cada compra. Se busca una lectura útil del mes.

Los gastos se agrupan en buckets amplios:
- `housing`
- `food`
- `transport`
- `health`
- `social`
- `shopping`
- `hobbies`
- `other`

Estos buckets son modificables, pero V1 empieza deliberadamente genérico.

### 5. Liquidez explícita
Cada saldo o posición debe caer en un tier de liquidez para que el sistema no confunda patrimonio total con disponibilidad real.

V1 usa:
- `immediate` → disponible ya (caja, banco, billetera operativa),
- `short_term` → accesible en pocos días,
- `invested` → capital invertido o menos disponible.

### 6. Instituciones y parsers reusables
Cada banco/broker/plataforma tendrá un parser reusable por formato.

La lógica no será “leer todo desde cero cada mes”, sino:
- detectar institución y formato,
- correr parser correspondiente,
- normalizar a esquema común,
- marcar casos dudosos para revisión.

### 7. Evolución de inversiones: nivel 1 + 2
V1 cubre:
- qué tenés,
- cuánto vale,
- cuánto costó,
- aportes/retiros,
- compras/ventas,
- evolución histórica por snapshots sucesivos.

No cubre todavía métricas avanzadas como TWR/MWR o benchmark formal.

## Entidades V1 contempladas
### Instituciones/cuentas conocidas al momento del diseño
- Galicia ARS
- Galicia USD
- BNA ARS
- BOFA USD
- MercadoPago ARS
- Wise USD
- Payoneer USD
- Citibank USD
- Invertir Online ARS/USD
- Charles Schwab (cuenta/broker con cash y posiciones; se modela por holdings y saldos, no como “moneda mezclada”)
- efectivo manual

### Monedas V1
- ARS
- USD

### Fuera de V1
- USDT, BTC, ETH y otras crypto.

## Rituales del sistema
### Semanal
No es un cierre contable. Es una conversación corta orientada a:
- liquidez percibida,
- gasto fuera de lo normal,
- necesidad de mover fondos o cambiar ARS/USD,
- dudas de inversión o cash idle,
- preparación del cierre mensual.

### Mensual
Es el ritual operativo principal. El usuario entrega extractos y Hermes:
1. identifica formato e institución,
2. parsea,
3. normaliza,
4. consolida balances,
5. resume gasto mensual,
6. actualiza inversiones,
7. genera reporte y recomendaciones.

### Trimestral
Es revisión estructural/estratégica:
- evolución patrimonial,
- evolución de gasto mensual,
- concentración por institución/moneda,
- liquidez ociosa,
- drift de estilo de vida,
- decisiones estratégicas y educativas.

## Qué responde el sistema cuando funciona bien
- patrimonio líquido actual en USD,
- distribución por institución y moneda,
- cash inmediato vs invertido,
- gasto del último mes y cambio contra el mes previo,
- qué inversiones tenés y cómo evolucionaron,
- si hay demasiada plata quieta,
- si la liquidez está corta o sobrada,
- si el gasto cambió de forma relevante,
- qué decisiones concretas conviene evaluar.

## Qué se posterga a V2 o después
- crypto,
- APIs,
- OCR complejo para PDFs muy malos,
- conciliación bancaria más fina,
- performance avanzada de cartera,
- impuestos,
- dashboard dedicado si no hace falta.
