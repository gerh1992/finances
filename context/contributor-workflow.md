# Contributor Workflow

## Objective
Permitir que humanos y otras IAs contribuyan sin degradar semántica, trazabilidad ni legibilidad.

## Default workflow
1. `git pull --rebase origin main`
2. entender qué capa estás tocando
3. hacer el cambio más chico que resuelva el problema
4. verificar impacto
5. `git status`
6. commit con contexto suficiente
7. push

## Antes de editar, preguntate
- ¿estoy tocando evidencia (`raw`), trabajo intermedio (`staging`), canon (`normalized`) o contexto (`context`/`logs`)?
- ¿esta edición cambia semántica o solo documentación?
- ¿si otro agente mira esto mañana, va a entender por qué lo hice?
- ¿estoy evitando inventar datos?

## Reglas por capa
### `data/raw/`
- no editar crudos como si fueran datos canónicos
- si hace falta corregir algo, documentar la anomalía; no maquillar el input

### `data/staging/`
- puede regenerarse
- debería reflejar extracción/intermediación, no decisiones económicas finales

### `data/normalized/`
- es la capa más sensible
- cualquier cambio debe preservar trazabilidad
- no mezclar gasto con transferencias o inversión
- no meter reglas implícitas solo en tu cabeza

### `data/manual/`
- sirve para inputs livianos y operativos
- no convertirlo mentalmente en canon estructurado si todavía no se normalizó

### `logs/`
- usarlos para dejar decisiones manuales, supuestos y chequeos relevantes
- si una regla se vuelve estable, moverla luego a docs más estructurados

### `context/`
- mantenerlo legible, corto y accionable
- documentar acá aquello que un tercero necesitaría para contribuir bien

## Cuándo dejar una nota explícita
Dejá nota en `logs/` o `context/` si:
- una clasificación fue dudosa,
- una regla cambió,
- una fuente cambió de formato,
- una excepción humana pasó a ser convención operativa,
- hiciste una migración que un tercero podría malinterpretar.

## Qué NO hacer
- no usar automatización frágil para fingir precisión
- no mezclar cleanup cosmético con reinterpretación económica sin avisar
- no reescribir historia silenciosamente
- no asumir que toda salida bancaria es gasto
- no dejar decisiones importantes solo en el chat

## Definition of done para un cambio bueno
Un cambio está bien hecho si:
- el repo queda más entendible que antes,
- la trazabilidad no empeora,
- la semántica económica sigue consistente,
- otro humano/IA puede seguir desde ahí sin adivinar demasiado.
