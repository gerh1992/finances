# Sistema Financiero Personal V1 — Especificación de Ingestión

## Propósito
Definir exactamente cómo entran los datos al sistema cada mes para que el proceso sea repetible, claro y cada vez menos manual.

Este documento define:
- qué archivos se aceptan,
- cómo se organizan,
- cómo se nombran,
- qué debe hacer Hermes con cada fuente,
- y cómo actuar si una fuente viene incompleta o cambia de formato.

---

## Principio general
Los archivos originales son **inputs crudos**.

Hermes debe:
1. archivarlos,
2. identificar fuente y formato,
3. correr parser reusable si existe,
4. producir datos normalizados,
5. marcar revisión manual si algo es ambiguo.

Nunca se debe editar el archivo crudo como si fuera el source of truth.

---

## Tipos de archivo aceptados en V1
### Preferidos
- `CSV`
- `XLSX` / export tabular si aparece
- `PDF` cuando no exista otra opción

### Política de calidad
- si hay CSV y PDF, preferir CSV;
- usar PDF como fallback o soporte;
- si el PDF es difícil de parsear, aceptar extracción/manual review antes que inventar datos.

---

## Estructura de carpetas recomendada
```text
financial-system-v1/
  docs/
  data/
    raw/
      2026-05/
        galicia/
        mercadopago/
        iol/
        schwab/
        ...
      2026-06/
      ...
    normalized/
      accounts.csv
      account_balances.csv
      transactions_normalized.csv
      monthly_expense_summary.csv
      investment_positions.csv
      investment_cashflows.csv
      fx_rates.csv
  parsers/
  logs/
```

### Regla
- `raw/` conserva archivos originales por período y fuente;
- `normalized/` guarda el source of truth consolidado;
- `parsers/` documenta o contiene lógica reusable por institución;
- `logs/` puede guardar notas de parsing, errores o decisiones manuales.

---

## Naming de archivos crudos
### Formato recomendado
`YYYY-MM_institucion_tipo_descripcion.ext`

### Ejemplos
- `2026-05_galicia_statement_ars.csv`
- `2026-05_galicia_statement_usd.pdf`
- `2026-05_mercadopago_movements.csv`
- `2026-05_iol_positions.xlsx`
- `2026-05_iol_transactions.csv`
- `2026-05_schwab_statement.pdf`
- `2026-05_bofa_statement_usd.csv`

### Objetivo
Que Hermes pueda inferir rápido:
- período,
- institución,
- tipo de archivo,
- posible parser aplicable.

---

## Contrato mínimo por tipo de fuente

## 1. Bancos / billeteras
### Idealmente deben traer
- fecha efectiva del movimiento o saldo,
- descripción,
- importe,
- moneda,
- saldo final o snapshot de cierre,
- algún identificador del período.

### Resultado esperado
- movimientos a `transactions_normalized.csv`,
- snapshot de cierre a `account_balances.csv`.

---

## 2. Tarjetas
### Si hay resumen o consumos
Debe permitir identificar:
- período/cierre,
- total consumido o detalle suficiente,
- moneda,
- descripciones si existen.

### Resultado esperado
- derivar gasto mensual,
- no duplicar con el pago posterior desde la cuenta.

### Si NO hay resumen
- el pago desde cuenta pagadora puede usarse como proxy,
- con menor confianza,
- y dejando explícito que es fallback.

---

## 3. Brokers
### Idealmente deben traer
- fecha de valuación o cierre,
- cash disponible,
- posiciones,
- market value o valuación,
- compras/ventas/aportes/retiros si existe historial.

### Resultado esperado
- snapshot de cash a `account_balances.csv` cuando corresponda,
- posiciones a `investment_positions.csv`,
- eventos a `investment_cashflows.csv` si el archivo lo permite.

---

## 4. Efectivo manual
### Input esperado
Puede venir como mensaje simple del usuario:
- fecha,
- moneda,
- monto,
- comentario opcional.

### Resultado esperado
- fila manual en `account_balances.csv`.

---

## Pipeline de ingestión mensual
### Paso 1 — Recepción
El usuario entrega archivos del período.

### Paso 2 — Archivo
Hermes guarda/copía los archivos en:
- `data/raw/YYYY-MM/institucion/`

### Paso 3 — Identificación
Hermes identifica:
- institución,
- tipo de documento,
- moneda,
- período,
- parser potencial.

### Paso 4 — Parsing
Si existe parser reusable:
- usarlo.

Si no existe:
- inspeccionar formato,
- documentar mapeo,
- derivar lógica inicial reusable.

### Paso 5 — Normalización
Escribir o actualizar las tablas normalizadas.

### Paso 6 — Validación
Chequear al menos:
- columnas mínimas presentes,
- moneda coherente,
- fecha usable,
- no duplicación grosera,
- balances razonables,
- movimientos dudosos marcados.

### Paso 7 — Reporte
Con la normalización completa, producir el cierre mensual y sus recomendaciones.

---

## Política de parsers por institución
### Regla
Cada institución debe tender a tener un parser reusable o, como mínimo, una nota de mapping estable.

### Objetivo
Que el costo de ingestión baje con el tiempo.

### Evolución esperada
1. primer archivo = aprendizaje/manual + documentación,
2. segundo archivo = parser más confiable,
3. tercer archivo en adelante = reutilización casi automática.

---

## Manejo de cambios de formato
Si una institución cambia su export:
1. no sobrescribir lógica anterior a ciegas,
2. registrar la diferencia,
3. adaptar parser o crear variante,
4. dejar trazabilidad de qué versión aplicó a qué archivo.

---

## Manejo de incertidumbre y errores
### Cuando falta información
Hermes debe preferir:
- marcar `needs_review`,
- preguntar lo mínimo indispensable,
- documentar la limitación,
antes que inferir demasiado.

### Ejemplos típicos
- transferencia que no se sabe si es interna,
- consumo ambiguo que podría ser inversión o gasto,
- PDF que no trae moneda clara,
- broker que trae valuación pero no costo histórico.

---

## Criterio de ingestión suficiente en V1
Un período mensual está suficientemente ingerido si:
- las principales cuentas activas del período están cargadas,
- hay una foto razonable de cash,
- el gasto total mensual es calculable o estimable con buena señal,
- la cartera tradicional quedó actualizada,
- las principales dudas quedaron explicitadas.

No se exige perfección. Se exige utilidad y trazabilidad.

---

## Próximo nivel de madurez
Cuando V1 funcione bien, esta especificación permite evolucionar a:
- mejor naming automático,
- mejor librería de parsers,
- carpetas por institución más ricas,
- validadores automáticos,
- eventual soporte crypto o nuevas fuentes.
