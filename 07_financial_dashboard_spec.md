# 07 — Especificación Técnica y de Producto: Dashboard de Inversiones & Portal Financiero Integral

> **Documento de especificación para implementación directa por IA.**  
> Este documento contiene todas las definiciones de arquitectura, contratos de datos, fórmulas financieras, diseño de interfaz y guía de construcción paso a paso para implementar el **Portal Financiero Personal** con el **Módulo de Inversiones (Charles Schwab)** 100% operativo en su Fase 1.

---

## 1. Visión y Alcance del Producto

### 1.1. Objetivo
Construir un dashboard web moderno, interactivo, rápido y estéticamente superior que funcione como **portal único de visualización de finanzas personales**.

El sistema debe resolver de forma inmediata:
- **¿Cómo vengo en mis inversiones?**: Valuación actual, ganancia/pérdida no realizada ($ y %), dividendos cobrados, retenciones impositivas y ponderación de activos.
- **¿Cuál es el histórico de mi cartera?**: Evolución del capital invertido vs. valuación acumulada mes a mes desde 2023, y registro detallado de transacciones.
- **¿Dónde está el dinero y cuánta liquidez real tengo?**: Clasificación en tiers de liquidez (*immediate*, *short_term*, *invested*), métrica de runway y patrimonio neto consolidado.
- **¿Cómo evoluciona mi gasto?**: Consolidación de gasto mensual por buckets y por tipo (*fixed* vs. *discretionary*).

### 1.2. Estrategia de Entrega (Phasing)
- **Fase 1 (Inmediata y 100% Funcional)**:
  - Header Global con Net Worth, P&L total, modo privacidad y switch de moneda.
  - **Módulo de Inversiones (Schwab)** completo: KPIs de rendimiento, curva histórica de valuación vs. aportes, gráficos de Asset Allocation, tracking de dividendos/impuestos NRA, tabla de holdings con ordenamiento/búsqueda y libro de transacciones con filtros.
  - Shell de navegación con pestañas modulares listas para recibir los demás datos normalizados.
- **Fase 2 (Cuentas, Liquidez y Gastos)**:
  - Módulo de Liquidez & Cuentas (lectura de `account_balances.csv` y `accounts.csv`).
  - Módulo de Gastos & Flujo Mensual (lectura de `monthly_expense_summary.csv` y `transactions_normalized.csv`).
  - Módulo de Patrimonio Neto Consolidado (Activos menos deudas de tarjeta).

---

## 2. Fuentes de Datos y Contratos (Source of Truth)

El dashboard consume los archivos CSV ubicados en `data/normalized/`. Ningún dato se inventa; todos provienen de las tablas canónicas:

| Archivo CSV | Propósito | Campos Clave Utilizados |
| :--- | :--- | :--- |
| **`investment_positions.csv`** | Snapshot actual de tenencias de inversión (Schwab e IOL) | `asset_id`, `asset_name`, `asset_class`, `quantity`, `cost_basis_original`, `cost_basis_usd`, `market_value_usd`, `unrealized_pnl_usd`, `as_of_date` |
| **`investment_cashflows.csv`** | 337 transacciones históricas (2023–2026) | `event_date`, `broker_account_id`, `asset_id`, `event_type` (`buy`, `dividend`, `fee`, `deposit`, `interest`), `quantity`, `price_original`, `gross_amount_usd`, `fees_original`, `notes` |
| **`account_balances.csv`** | Saldos de caja y liquidez por cuenta | `account_id`, `currency`, `balance_original`, `balance_usd`, `liquidity_tier` (`immediate`, `short_term`, `invested`), `as_of_date` |
| **`accounts.csv`** | Catálogo maestro de cuentas e instituciones | `account_id`, `account_name`, `institution`, `country`, `account_type`, `default_currency` |
| **`monthly_expense_summary.csv`** | Gasto mensual agregado | `month`, `bucket`, `expense_type` (`fixed`, `discretionary`), `amount_usd` |
| **`fx_rates.csv`** | Tipos de cambio históricos | `rate_date`, `from_currency`, `to_currency`, `fx_rate` |

---

## 3. Fórmulas y Algoritmos Financieros

La IA que implemente el sistema debe programar los siguientes motores de cálculo en Python (Pandas / NumPy):

### 3.1. Métricas de Posición Actual (Holdings)
Para cada activo $i$ en `investment_positions.csv`:
- **Precio Promedio de Compra (Avg Cost)**: $\text{AvgCost}_i = \frac{\text{cost\_basis\_original}_i}{\text{quantity}_i}$
- **Precio Actual de Mercado**: $\text{MarketPrice}_i = \frac{\text{market\_value\_usd}_i}{\text{quantity}_i}$
- **Retorno No Realizado (%)**: $\text{UnrealizedPnL}\%_i = \left(\frac{\text{market\_value\_usd}_i - \text{cost\_basis\_original}_i}{\text{cost\_basis\_original}_i}\right) \times 100$
- **Ponderación en Cartera (%)**: $\text{Weight}\%_i = \left(\frac{\text{market\_value\_usd}_i}{\sum_{j} \text{market\_value\_usd}_j}\right) \times 100$

### 3.2. Clasificación de Asset Allocation
Mapeo determinista según el activo:
- **`SCHB`** (Schwab U.S. Broad Market ETF) $\rightarrow$ **Renta Variable EE.UU. (Broad Market)**
- **`SPY`** (SPDR S&P 500 ETF Trust) $\rightarrow$ **Renta Variable EE.UU. (Large Cap)**
- **`SCHF`** (Schwab International Equity ETF) $\rightarrow$ **Renta Variable Internacional (Desarrollados)**
- **`XLE`** (Energy Select Sector SPDR ETF) $\rightarrow$ **Sectorial Renta Variable (Energía)**
- **`SCHZ`** (Schwab U.S. Aggregate Bond ETF) $\rightarrow$ **Renta Fija / Bonos EE.UU.**
- **`schwab_broker (cash)`** $\rightarrow$ **Caja / Liquidez en Broker**

### 3.3. Reconstrucción de la Curva Histórica de Cartera
A partir de `investment_cashflows.csv`:
1. Agrupar cronológicamente por mes (`YYYY-MM`) desde marzo 2023 hasta la fecha actual.
2. **Aportes Netos de Capital Acumulados ($)**:
   - Suma acumulada de eventos `event_type == 'deposit'` menos retiros `event_type == 'withdrawal'`.
3. **Capital Total Desplegado en Compras ($)**:
   - Suma acumulada del valor bruto de eventos `event_type == 'buy'`.
4. **Flujo de Dividendos y Retenciones Fiscales**:
   - **Dividendos Brutos**: Suma de `gross_amount_usd` de eventos `event_type == 'dividend'`.
   - **Retenciones Fiscales (NRA Tax 30%)**: Suma de montos de eventos `event_type == 'fee'` donde la nota indique `NRA Tax Adj`.
   - **Dividendos Netos**: $\text{Dividendos Brutos} - \text{Retenciones Fiscales}$.
5. **Evolución del Valor Estimado de Cartera**:
   - Para el cierre actual (`2026-09`): valor real de mercado provisto por el snapshot ($164,598.90 USD).
   - Para los meses intermedios: reconstrucción del costo base acumulado y valoración interpolada en base al flujo de compras y reinversiones de dividendos.

### 3.4. Liquidez Consolidada y Runway
- **Liquidez Inmediata ($)**: Suma de `balance_usd` de cuentas con `liquidity_tier == 'immediate'`.
- **Liquidez Corto Plazo ($)**: Suma de `balance_usd` con `liquidity_tier == 'short_term'`.
- **Capital Invertido ($)**: Suma de valuaciones de `investment_positions.csv` + saldo cash en broker.
- **Patrimonio Neto ($)**: $(\text{Liquidez Inmediata} + \text{Liquidez Corto Plazo} + \text{Capital Invertido}) - \text{Deuda de Tarjetas Registrada}$.
- **Runway (Meses de Subsistencia)**:
  $$\text{Runway} = \frac{\text{Liquidez Inmediata USD}}{\text{Gasto Fijo Mensual USD}}$$

---

## 4. Arquitectura Tecnológica (100% Python)

Para garantizar máxima velocidad de desarrollo, consistencia con el repositorio (`pandas`, parsers), portabilidad y facilidad de mantenimiento directo por el usuario:

- **Framework Web**: **Streamlit** (`>=1.35.0`).
- **Librería de Gráficos**: **Plotly** (`plotly.graph_objects` y `plotly.express` con plantilla oscura `plotly_dark`), que ofrece gráficos interactivos con zoom, paneo, hover enriquecido y animaciones.
- **Motor de Datos**: **Pandas** (`>=2.0.0`) para lectura determinista y vectorizada de los CSVs en `data/normalized/`.
- **Caching**: Decorador nativo `@st.cache_data` para carga instantánea y recálculo eficiente al interactuar con filtros.
- **Styling / Tema**: `.streamlit/config.toml` con tema oscuro (`dark mode` nativo, fondo `#0B0F17`, acentos azul/verde esmeralda) complementado con inyección de CSS sutil vía `st.markdown(..., unsafe_allow_html=True)` para tarjetas de métricas elegantes.
- **Estructura del Proyecto**:
  ```text
  finances/
  ├── dashboard/                 # Aplicación Streamlit (Python puro)
  │   ├── app.py                 # Entrypoint principal (`streamlit run dashboard/app.py`)
  │   ├── .streamlit/
  │   │   └── config.toml        # Configuración de tema oscuro, background y layout wide
  │   ├── modules/
  │   │   ├── __init__.py
  │   │   ├── data_loader.py     # Carga de CSVs de data/normalized/ con @st.cache_data
  │   │   ├── financial_math.py  # Cálculos de P&L, curvas históricas, dividendos y tiers
  │   │   ├── investments_view.py# Módulo 1: KPIs, gráficos Plotly, tabla holdings y ledger
  │   │   ├── liquidity_view.py  # Módulo 2: Tiers de liquidez, cuentas y runway
  │   │   ├── expenses_view.py   # Módulo 3: Burn rate y buckets de gasto
  │   │   └── net_worth_view.py  # Módulo 4: Patrimonio neto consolidado
  │   └── utils/
  │       ├── __init__.py
  │       ├── formatting.py      # Formateo monetario y modo privacidad (máscara ••••••)
  │       └── ui_components.py   # Componentes visuales y custom CSS reutilizables
  ```

---

## 5. Diseño de Interfaz y Componentes (UI / UX)

### 5.1. Header Global
- **Logo & Contexto**: Título *"Personal Finance & Investment Portal"*, subtítulo con fecha de último corte (`As of September 16, 2026`).
- **KPI Primario**: **Net Worth Consolidado** destacado con tipografía grande (ej: `$164,774.70 USD`), con variación porcentual total.
- **Acciones Globales**:
  - **Privacy Mode Toggle**: Ícono de ojo que enmascara inmediatamente todos los valores monetarios en pantalla (`$ ••••••`).
  - **Currency Display**: Indicador de moneda base USD con tooltip descriptivo.
  - **Data Status Badge**: Chip verde que indica *"Source: data/normalized (Audited)"*.

### 5.2. Pestañas de Navegación (Tabs)
1. **Inversiones (Activa por defecto)**: Ícono `TrendingUp`.
2. **Liquidez & Cuentas**: Ícono `Wallet`.
3. **Gastos & Flujo**: Ícono `PieChart`.
4. **Patrimonio Neto**: Ícono `Layers`.

---

### 5.3. Módulo 1: Inversiones (Detalle de Componentes)

#### A. Tarjetas de Métricas Principales (KPI Cards)
1. **Valuación de Cartera**: `$164,598.90 USD` (Subtexto: *Costo Base: $118,953.42 USD*).
2. **Ganancia No Realizada (Unrealized P&L)**: `+$45,645.48 USD` en verde vibrante (`+38.37%`).
3. **Dividendos Brutos Acumulados**: Total histórico generado por los ETFs.
4. **Retenciones Fiscales (NRA 30%)**: Total retenido por el IRS en origen.
5. **Caja en Broker**: `$175.80 USD` (Liquidez no invertida lista para compras).

#### B. Gráfico 1: Curva Histórica de Cartera (Area / Line Chart)
- **Eje X**: Fechas mensuales desde marzo 2023 hasta septiembre 2026.
- **Serie 1 (Línea Azul/Índigo)**: Aportes Netos de Capital Acumulados.
- **Serie 2 (Área Verde Esmeralda)**: Valuación Total de Cartera en el tiempo.
- **Tooltip**: Desglose con fecha, capital aportado, valuación y gap de ganancia.

#### C. Gráfico 2: Asset Allocation (Donut Charts Interactivos)
- **Selector de Vista**:
  - *Vista por Activo*: SCHB (33.5%), SCHF (26.8%), SPY (19.4%), XLE (16.8%), SCHZ (3.6%).
  - *Vista por Clase de Activo*: Renta Variable US (52.9%), Renta Variable Internacional (26.8%), Sectorial Energía (16.8%), Renta Fija (3.6%).
- Al hacer hover en cada porción: ticker, nombre completo, monto en USD y porcentaje.

#### D. Gráfico 3: Flujo de Dividendos y Retenciones (Bar Chart)
- Barras agrupadas por período (trimestral o anual):
  - Barra 1: Dividendo Bruto Cobrado.
  - Barra 2: Retención Fiscal NRA Tax (30%).
  - Barra 3: Dividendo Neto Reinvertido.

#### E. Tabla de Posiciones Actuales (Holdings Ledger)
Columnas indispensables:
- **Ticker** (con badge del activo).
- **Nombre del Instrumento**.
- **Clase de Activo**.
- **Cantidad de Títulos** (con formato decimal de 4 dígitos).
- **Precio Promedio de Compra ($)**.
- **Precio de Mercado Actual ($)**.
- **Valuación de Mercado ($)**.
- **Ganancia / Pérdida ($ y %)** con color condicional (verde para positivo, rojo para negativo).
- **Ponderación (% de la Cartera)** con barra de progreso visual.

#### F. Libro Histórico de Movimientos (Transactions Ledger)
- Filtro interactivo por tipo de evento: `Todos`, `Compras (Buy)`, `Dividendos`, `Impuestos (Fees)`, `Fondeos (Deposits)`.
- Búsqueda por texto (filtra por ticker o descripción en las notas).
- Paginación ágil (10 / 25 / 50 filas por página).
- Columnas: Fecha, Tipo de Evento (badge coloreado), Activo, Cantidad, Precio, Monto Bruto USD, Retención Fiscal, Notas de Origen.

---

### 5.4. Módulo 2: Liquidez & Cuentas (Estructura de la Fase 2 integrada en el Shell)
- **Distribución por Tiers**:
  - Barra o Donut de Liquidez: Inmediata vs. Corto Plazo vs. Invertida.
  - Indicador de Runway: Cálculo en meses de subsistencia.
- **Grilla de Cuentas**:
  - Tarjetas individuales por cuenta activa en `accounts.csv`: Galicia, BNA, MercadoPago, BofA, Citi, Wise, Payoneer, Schwab, Efectivo manual.
  - Muestra saldo nativo original y conversión consolidada a USD.

---

### 5.5. Módulo 3: Gastos & Flujo Mensual (Estructura en Shell)
- **Burn Rate**: Tarjeta con gasto total del mes más reciente vs. mes anterior.
- **Estructura de Costo de Vida**: Proporción Fijos (*Fixed/Subsistencia*) vs. Variables (*Discretionary/Estilo de vida*).
- **Desglose por Buckets**: Gráfico de barras horizontales o donut (`housing`, `food`, `health`, `transport`, `social`, etc.).

---

## 6. Instrucciones de Implementación Paso a Paso (Para el Agente IA)

La IA encargada de la ejecución debe seguir estrictamente este procedimiento:

### Paso 1: Instalación y Entorno
1. Asegurarse de tener `streamlit` y `plotly` en el entorno o agregarlos a `requirements.txt`:
   ```bash
   pip install "streamlit>=1.35.0" "plotly>=5.20.0"
   ```
2. Crear la carpeta del dashboard y submódulos:
   ```bash
   mkdir -p dashboard/.streamlit dashboard/modules dashboard/utils
   touch dashboard/modules/__init__.py dashboard/utils/__init__.py
   ```

### Paso 2: Configuración de Tema (.streamlit/config.toml)
Crear `dashboard/.streamlit/config.toml` para fijar el modo oscuro y layout ancho de forma nativa:
```toml
[theme]
base = "dark"
primaryColor = "#38BDF8"
backgroundColor = "#0B0F17"
secondaryBackgroundColor = "#111827"
textColor = "#F3F4F6"
font = "sans serif"

[server]
headless = true
enableCORS = false
```

### Paso 3: Carga de Datos y Lógica Financiera
1. Implementar `dashboard/modules/data_loader.py`:
   - Función `@st.cache_data load_data()` que lea directamente:
     - `data/normalized/investment_positions.csv`
     - `data/normalized/investment_cashflows.csv`
     - `data/normalized/account_balances.csv`
     - `data/normalized/accounts.csv`
     - `data/normalized/monthly_expense_summary.csv`
2. Implementar `dashboard/modules/financial_math.py`:
   - Cálculo de P&L, pesos de cartera, reconstrucción de serie histórica mensual y desglose de dividendos vs. NRA Tax 30% usando Pandas vectorizado.

### Paso 4: Construcción de Vistas Modulares
1. Implementar `dashboard/utils/formatting.py`:
   - Función para formatear moneda (`format_currency(val, privacy_mode=False)`), enmascarando como `$ ••••••` si el modo privacidad está activado en `st.session_state`.
2. Implementar `dashboard/modules/investments_view.py`:
   - Métricas principales con `st.columns` y deltas porcentuales.
   - Gráfico de curva histórica con `go.Figure()` (Aportes netos vs. Valuación de cartera).
   - Donut chart de Asset Allocation con selector por Ticker / Clase de Activo (`px.pie`).
   - Gráfico de barras de dividendos brutos vs. NRA Tax retenido vs. neto.
   - Tabla de posiciones con `st.dataframe` enriquecido con formato de moneda y porcentajes.
   - Libro de transacciones con filtros en barra lateral o cabecera (`st.multiselect`, `st.text_input`).
3. Implementar vistas preliminares de `liquidity_view.py`, `expenses_view.py` y `net_worth_view.py`.
4. Ensamblar en `dashboard/app.py`:
   - Configuración de página: `st.set_page_config(page_title="Personal Finance Portal", layout="wide")`.
   - Header con Net Worth, toggle de privacidad en `st.session_state` y badge de última actualización.
   - Pestañas principales con `tab_inv, tab_liq, tab_exp, tab_nw = st.tabs(...)`.

### Paso 5: Verificación y Validación
1. Ejecutar la aplicación:
   ```bash
   streamlit run dashboard/app.py
   ```
2. Validar que la suma total de posiciones coincida exactamente con `$164,598.90 USD` y la ganancia no realizada con `$45,645.48 USD`.
3. Validar que el contador de transacciones en la tabla muestre exactamente las 337 filas de `investment_cashflows.csv`.
4. Comprobar que al activar el checkbox/toggle de privacidad en el header, todos los importes se oculten como `$ ••••••`.

---

## 7. Criterios de Aceptación (Definition of Done)

- [ ] **100% Python Nativo**: La solución no requiere Node.js, npm ni herramientas externas; corre directo con el Python del repo.
- [ ] **Exactitud Numérica**: Valuación actual de Schwab, costo base y P&L coinciden con el source of truth al centavo.
- [ ] **Reconstrucción Histórica**: El gráfico histórico refleja correctamente los aportes iniciales ($50k) y las compras subsecuentes hasta alcanzar los ~$164.6k actuales.
- [ ] **Transparencia Fiscal**: Las retenciones del 30% NRA Tax están calculadas, documentadas y visualizadas claramente junto a los dividendos brutos.
- [ ] **Asset Allocation Dinámico**: Los pesos porcentuales de SCHB, SCHF, SPY, XLE, SCHZ suman el 100% y se visualizan con paletas armoniosas en Plotly.
- [ ] **Interactividad & Búsqueda**: La tabla de transacciones responde inmediatamente a búsquedas por ticker y filtros por tipo de evento.
- [ ] **Modo Privacidad Funcional**: El toggle oculta todos los importes en pantalla con un clic.
- [ ] **Código Limpio y Modular**: Código Python idiomático (PEP 8), modularizado en `modules/` y con caching eficiente vía `@st.cache_data`.
- [ ] **Fidelidad al Sistema**: No se violan los guardrails de `01_system_design.md` ni `04_v1_operational_rules.md`.
