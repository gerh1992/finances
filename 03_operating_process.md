# Sistema Financiero Personal V1 — Proceso Operativo

## Objetivo del proceso
Definir cómo se alimenta, mantiene y usa el sistema financiero personal con mínima fricción para el usuario y máxima reutilización para Hermes.

La intención es que el trabajo scheduleado del usuario sea corto:
- interacción semanal breve,
- entrega mensual de extractos,
- conversación mensual/trimestral de decisiones.

## Roles
### Usuario
Aporta:
- extractos mensuales (CSV/PDF) de bancos, billeteras y brokers,
- monto manual de efectivo si hace falta,
- aclaraciones cuando haya movimientos ambiguos,
- validación final de decisiones si algo tiene impacto real.

### Hermes
Hace:
- detección de institución/formato,
- parsing reusable por fuente,
- normalización,
- consolidación en USD,
- resumen de gasto mensual,
- actualización de balances e inversiones,
- generación de reportes,
- explicación educativa y recomendaciones.

---

## Cadencia del sistema

## 1. Ritual semanal (ligero)
### Objetivo
Mantener awareness y contexto sin exigir cierre contable.

### Qué se revisa
- sensación de liquidez,
- gasto fuera de lo normal,
- si hay que mover fondos,
- si hay demasiada plata quieta,
- si hay cambios relevantes desde la última conversación,
- si hay dudas o decisiones por pensar.

### Input esperado
Solo conversación breve. No hace falta subir reportes semanales.

### Output esperado
- mini resumen cualitativo,
- flags para mirar a fin de mes,
- posibles acciones tácticas.

### Qué NO hace
- no reconcilia cuentas,
- no cierra gasto del mes,
- no intenta precisión que todavía no existe.

---

## 2. Ritual mensual (principal)
### Objetivo
Cerrar el mes con datos reales y producir el reporte central.

### Input esperado del usuario
Una vez por mes, compartir extractos/archivos de:
- bancos,
- billeteras,
- brokers,
- resumen o información equivalente para gasto,
- efectivo manual si aplica.

### Pipeline mensual de Hermes
#### Paso 1: Ingesta
- recibir archivos,
- archivarlos en carpeta de inputs crudos del período,
- identificar institución y tipo de archivo.

#### Paso 2: Parsing
- ejecutar parser reusable por institución/formato,
- extraer campos útiles,
- detectar limitaciones del archivo,
- marcar registros dudosos.

#### Paso 3: Normalización
- convertir cada archivo a esquema común,
- generar/actualizar `transactions_normalized.csv`,
- generar snapshots de `account_balances.csv`,
- actualizar `investment_positions.csv` y `investment_cashflows.csv` cuando corresponda.

#### Paso 4: Limpieza lógica
- detectar transferencias internas,
- evitar doble conteo,
- separar gasto real de movimientos entre cuentas o inversiones,
- etiquetar buckets de gasto amplios.

#### Paso 5: Consolidación
- convertir a USD con FX explícito,
- producir visión consolidada de cash y cartera,
- calcular gasto total mensual y distribución por buckets,
- comparar contra meses anteriores.

#### Paso 6: Reporte y decisiones
Generar un reporte mensual en 4 bloques.

### Bloque A — Estado actual
- patrimonio líquido,
- cash total,
- inversiones totales,
- distribución por institución,
- distribución por moneda,
- liquidez por tier.

### Bloque B — Gasto del mes
- gasto total del mes,
- variación contra mes anterior,
- buckets principales,
- gastos excepcionalmente altos,
- incertidumbres o cosas a revisar.

### Bloque C — Inversiones
- posiciones actuales,
- costo histórico aproximado,
- valuación actual,
- compras/ventas/aportes/retiros del mes,
- capital ocioso y concentración relevante.

### Bloque D — Decisiones sugeridas
Ejemplos:
- reducir cash idle,
- reforzar liquidez de corto plazo,
- revisar gasto mensual que deriva al alza,
- evaluar concentración por institución o activo,
- decidir si conviene invertir saldo sobrante,
- revisar bucket que cambió demasiado.

### Output final mensual
- CSVs actualizados,
- reporte narrativo,
- lista breve de acciones recomendadas,
- lista de dudas o datos faltantes,
- aprendizaje reusable sobre parsers/nuevos formatos.

---

## 3. Ritual trimestral (estratégico)
### Objetivo
Dejar de mirar solo el último mes y mirar estructura.

### Qué revisa Hermes
- evolución patrimonial trimestral,
- gasto promedio mensual del trimestre,
- drift del estilo de gasto,
- cash idle persistente,
- concentración por institución/moneda,
- calidad de liquidez,
- cambios grandes en cartera,
- oportunidades o riesgos estructurales.

### Capa educativa
Cada revisión trimestral debería explicar conceptos como:
- liquidez real vs patrimonio total,
- concentración,
- costo de oportunidad del dinero quieto,
- diferencia entre gasto, transferencia e inversión,
- cómo pensar cobertura de moneda,
- cuándo un cambio de comportamiento merece atención.

### Output trimestral
- resumen ejecutivo,
- tendencias,
- decisiones estratégicas sugeridas,
- preguntas para redefinir el sistema si hace falta,
- posibles mejoras de V2.

---

## Cómo se agregan nuevas fuentes
### Regla
Una nueva institución no cambia el modelo. Solo agrega:
- una cuenta nueva en `accounts.csv`,
- uno o más parsers reutilizables,
- reglas de mapeo a tipos normalizados.

### Workflow
1. usuario entrega archivo nuevo,
2. Hermes inspecciona formato,
3. Hermes documenta parser/mapeo,
4. el mes siguiente se reutiliza.

Esto hace que el sistema mejore con cada institución aprendida.

---

## Cómo se manejan las incertidumbres
No inventar datos.

Si un archivo no permite inferir algo con suficiente confianza:
- se marca `needs_review`,
- se documenta la incertidumbre,
- se pide confirmación puntual al usuario,
- se conserva la decisión tomada para próximos meses si se vuelve una regla estable.

---

## Criterios de calidad del proceso
El proceso está funcionando bien si:
- el usuario tarda poco en aportar inputs mensuales,
- Hermes no re-aprende formatos cada mes,
- el reporte mensual responde preguntas concretas,
- no hay doble conteo grosero,
- el gasto del mes queda razonablemente claro,
- la liquidez y cartera se entienden mejor que antes,
- las conversaciones semanales sirven para decidir, no para cargar datos.

---

## Roadmap sugerido
### V1
- bancos/billeteras,
- gasto mensual agregado,
- inversiones tradicionales,
- consolidación en USD,
- parsers reusables por institución.

### V1.1
- mejores reglas de bucket,
- deduplicación más fina,
- reportes comparativos más prolijos,
- tracking más robusto de costo base.

### V2
- crypto,
- mayor cobertura de fuentes,
- mejores métricas de cartera,
- tal vez dashboard o vistas más automáticas si realmente aportan.

---

## Filosofía operativa final
Este sistema no busca “hacer bookkeeping por deporte”. Busca aumentar claridad, calidad de decisión y comprensión.

La secuencia correcta es:
1. entender dónde está la plata,
2. medir cuánto sale vivir,
3. entender la estructura de liquidez e inversión,
4. decidir mejor,
5. recién después sofisticar.
