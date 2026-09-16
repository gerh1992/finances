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
    raw/            # [IGNORADA EN GIT] Zona temporal de procesamiento local
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
- `2026-05_schwab_positions.csv` (o export nativo `Individual-Positions-YYYY-MM-DD-*.csv`)
- `2026-05_schwab_transactions.csv` (o export nativo `Individual_XXX_Transactions_YYYYMMDD-*.csv`)
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

## 3. Brokers (Inversiones Tradicionales)

### A. Charles Schwab (CSV Exports nativos o canónicos)
Procesado determinísticamente mediante `parsers/parse_schwab_csv.py`:
1. **Archivo de Posiciones (`Individual-Positions-*.csv` o `YYYY-MM_schwab_positions.csv`)**:
   - **Campos esperados**: `Symbol`, `Description`, `Qty (Quantity)`, `Price`, `Mkt Val (Market Value)`, `Cost Basis`, `Gain $ (Gain/Loss $)`, `Asset Type`.
   - **Fecha de corte (`as_of_date`)**: Extraída de la cabecera del archivo (`Positions for account ... as of ... YYYY/MM/DD`).
   - **Resultado en `investment_positions.csv`**: Se mapean todas las tenencias de activos (`SCHB`, `SCHF`, `SPY`, etc.) con sus cantidades, costo base y valuación de mercado.
   - **Resultado en `account_balances.csv`**: La fila `Cash & Cash Investments` se persiste automáticamente como saldo de liquidez no invertida en la cuenta comitente (`account_id = schwab_broker`, `liquidity_tier = invested`, `currency = USD`).
2. **Archivo de Transacciones (`Individual_*_Transactions_*.csv` o `YYYY-MM_schwab_transactions.csv`)**:
   - **Campos esperados**: `Date`, `Action`, `Symbol`, `Description`, `Quantity`, `Price`, `Fees & Comm`, `Amount`.
   - **Fechas**: Maneja fechas estándar y contables con `"as of"` (asignando la fecha efectiva real al evento).
   - **Mapeo de eventos a `investment_cashflows.csv`**:
     - `Buy`, `Reinvest Shares` → `buy`
     - `Sell` → `sell`
     - `Reinvest Dividend`, `Cash Dividend`, `Pr Yr Cash Div`, `Cash In Lieu` → `dividend`
     - `MoneyLink Transfer`, `Wire Received` → `deposit` (o `withdrawal` si el monto es negativo)
     - `Credit Interest`, `Interest Adj` → `interest`
     - `NRA Tax Adj`, `Pr Yr NRA Tax` → `fee` (retención fiscal en origen)
     - `Stock Split` → `stock_split`

### B. Invertir Online (IOL)
Procesamiento implementado mediante `parsers/parse_iol.py` y orquestado en `parsers/ingest.py`:

1. **Operaciones Finalizadas (`OperacionesFinalizadas*.xls`)**:
   - Boletos oficiales de compra y venta (`BCBA`, `NYSE`).
   - Mapea a `investment_cashflows.csv`: `event_type in ['buy', 'sell']`, activos (`SPY`, `GOOGL`, `AL30`, `XLE`, `XBI`, `AAPL`, etc.), cantidades, precios pactados, comisiones e IVA.
2. **Movimientos Históricos (`MovimientosHistoricos*.xls`)**:
   - Movimientos de caja, dividendos (en ARS y USD), créditos por saldos remunerados (`interest`), retenciones impositivas (`fee`), depósitos y retiros.
   - Mapea a `investment_cashflows.csv`: filtra liquidaciones de boletos para evitar duplicación con `OperacionesFinalizadas`.
3. **Resumen de Cuenta Oficial (`resumen_cuenta_*.pdf`)**:
   - Snapshot de tenencias al corte: `GOOGL`, `SPY`, `XLE`, `ADCGLOA` a `investment_positions.csv`.
   - Saldos líquidos disponibles en ARS y USD a `account_balances.csv`.
   - Conversión dinámica a USD usando cotización implícita CCL/MEP en `fx_rates.csv`.

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

## Control de Idempotencia y Prevención de Duplicados

Para asegurar que un extracto no sea procesado y sumado dos veces a las tablas normalizadas, el orquestador implementa un control por huella digital (hash):

1. **Huella Única:** Cada archivo que ingresa al Inbox se lee y se calcula su hash `SHA-256`.
2. **Registro de Ingestión:** Existe un archivo de control centralizado en `data/normalized/ingested_files.csv`.
3. **Mapeo:** Antes de proceder con el parseo, se busca el hash en el registro. Si ya existe con estado `success`, el archivo se omite del flujo.
4. **Esquema de `ingested_files.csv`:**
   `file_name,file_hash,ingested_at,status,account_id,notes`

---

## Pipeline de Ingestión Automatizado (Headless & API)

El proceso se ejecuta mediante el script `parsers/ingest.py` y opera de la siguiente manera:

### Origen de los Datos (Headless)
El script se conecta a la API de Google Drive utilizando una clave JSON de **Service Account** (`credentials.json`) ubicada en la raíz del repositorio.
- Monitorea una carpeta remota **Inbox** (`DRIVE_INBOX_FOLDER_ID`).
- Tras procesar con éxito cada archivo, lo mueve a una carpeta remota **Archive** (`DRIVE_ARCHIVE_FOLDER_ID`), organizándolos en subcarpetas `YYYY-MM/` o manteniéndolos en la raíz del Archive según configuración.

### Interfaz del Orquestador (`ingest.py`)
Soporta tres modos clave para facilitar la auditoría y depuración:
1. **Modo normal:** `python parsers/ingest.py`
   Procesa de forma desatendida todo el Inbox de Drive, descargando temporalmente, validando el hash, ejecutando los parsers correspondientes, actualizando los CSVs en `data/normalized/` e ingresando los archivos al Archive de Drive tras registrar el hash.
2. **Modo Dry-Run:** `python parsers/ingest.py --dry-run`
   Ejecuta todo el pipeline (descarga temporal, cálculo de hash, parseo local o llamada a Gemini para PDFs), pero **no escribe cambios en los CSVs consolidados ni altera la ubicación de los archivos en Google Drive**. Imprime el resultado estructurado en consola para validación previa rápida.
3. **Modo Archivo Único:** `python parsers/ingest.py --file <path_local_o_id_drive>`
   Dirige el proceso a un único archivo para aislar errores o probar formatos nuevos sin tocar el resto del Inbox.

---

## Política de parsers (Híbrida: PDF y CSV)

### 1. Ingestión de PDFs (Parseador Genérico vía LLM)
Para todos los documentos en formato **PDF** (extractos bancarios de Galicia, BofA, Schwab, etc.):
- **Regla**: Se utiliza un único script centralizado `parsers/parse_pdf.py`.
- **Estrategia**:
  1. Extraer el texto del PDF de manera local preservando el diseño de las columnas (`pdftotext -layout` o `pdfplumber`).
  2. Enviar el texto plano a la API de un LLM (Gemini) utilizando un esquema estructurado (JSON Schema) para mapear transacciones y saldos al formato de la base de datos.
  3. Si el PDF es una imagen/escaneo, se procesa de forma multimodal (visión).
- **Justificación**: Se evita tener que escribir y mantener parsers de código rígidos y frágiles para cada banco, lo cual reduce drásticamente el costo de mantenimiento.

### 2. Ingestión de CSVs (Parsers Locales Deterministas)
Para los documentos tabulares nativos en formato **CSV** o **Excel** (Mercado Pago, Charles Schwab, Invertir Online, Galicia export, Wise export, etc.):
- **Regla**: Se utiliza un script específico por institución en la carpeta `parsers/` (ej. `parsers/parse_mercadopago_csv.py`, `parsers/parse_schwab_csv.py`).
- **Estrategia**: Procesar el archivo de forma puramente determinista y local (usando `pandas` o el módulo `csv` de la librería estándar de Python) mapeando las columnas nativas al esquema normalizado.
- **Justificación**: Rapidez absoluta, 100% de fiabilidad, y costo de tokens cero (0) al procesarse de forma local sin requerir llamadas al LLM.

---

## Manejo de cambios de formato
Si una institución cambia su export:
1. Para **PDFs**: Modificar o refinar el prompt/JSON schema del parseador genérico si el cambio afecta la extracción semántica.
2. Para **CSVs**: Adaptar el mapeo de columnas en el script específico de la institución, documentando en `logs/` la versión del export afectada.

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
