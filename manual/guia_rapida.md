# Guía Rápida — Infame Elite Endurance Coach v6.1

Referencia de una página. El detalle completo está en
`manual_operativo_infame_coach.md`.

## Comandos del día a día

| Comando | Qué hace |
|---|---|
| `python coach.py new <id>` | Dar de alta un atleta nuevo (crea su config desde la plantilla) |
| `python coach.py prep <id>` | Fetch + estado + perfil de un atleta → `out/<nombre>/` |
| `python coach.py prep --all` | Lo mismo, para todos los atletas de la cuenta |
| `python coach.py prep --list` | Lista atletas, refresca `out/roster.md`, no descarga nada |
| `python coach.py check <archivo>` | Valida un bloque y calcula su TSS antes de subirlo |
| `python coach.py review <id> --since <fecha>` | Compara los indicadores de un bloque contra hoy |

## Cada chat nuevo con un atleta

Arrastra desde `out/<nombre_atleta>/`:

- [ ] `state.md` — siempre
- [ ] `profile.md` — siempre
- [ ] `continuity.md` — solo si ya existe (significa que ya hubo una sesión en este bloque)

No hace falta volver a arrastrar a media conversación — solo al abrir un
chat **nuevo**.

## Trabajar vía MCP (solo Claude Desktop, no el navegador)

Instalación única por máquina: `python -m pip install "mcp[cli]" pyyaml
requests`, luego agrega `infame-coach` a `claude_desktop_config.json` con
un bloque `"env": {"ICU_API_KEY": "..."}` (Desktop no siempre hereda las
variables de `setx`). Detalle completo: `manual_operativo_infame_coach.md`
Secciones 0 y 10.

| Herramienta | Reemplaza |
|---|---|
| `get_athlete_state` / `get_athlete_profile` | arrastrar `state.md` / `profile.md` (caché de 1h, di "dame el estado actualizado" para forzar) |
| `list_roster` | `coach.py prep --list` |
| `save_continuity` / `save_race_result` / `save_block` | copiar y pegar en `continuity.md` / `race_notes.md` / un archivo de bloque — el coach las llama solo ahora |
| `validate_block` | `coach.py check <archivo>` — el coach la llama sola justo después de `save_block` |
| `push_block` | pegar en el Workout Builder de Intervals.icu — **nunca automática**; pídela tú, por default hace vista previa |

## Consulta a media semana, fuera de calendario

1. `python coach.py prep <id>`
2. ¿Sigues en el mismo chat? No necesitas nada más.
3. ¿Vas a abrir un chat **nuevo**? Antes de cerrar este, pídele al coach:
   *"dame el header de continuidad"*
4. Pega el `#SESSION` que te entregue en `out/<nombre>/continuity.md`

## Cierre de bloque

1. El coach emite automáticamente un `#SESSION` con borde visual al terminar
   la última sesión
2. Cópialo en `out/<nombre>/continuity.md` — automático si `save_continuity`
   está disponible como herramienta
3. `python coach.py prep <id>` antes del siguiente chat
4. Opcional: `python coach.py review <id> --since <inicio del bloque>` para
   ver qué se movió de verdad (CTL/ATL/TSB, ACWR y durability ya funcionan;
   la progresión de curvas necesita que se acumule historial primero)

## Después de una carrera (Fase 6)

1. El coach emite un bloque `#RACE_RESULT` durante el debrief
2. Agrégalo (nunca reemplaces) a `out/<nombre>/race_notes.md` — automático
   si `save_race_result` está disponible como herramienta
3. `review` lo toma automáticamente para cualquier ventana que incluya esa fecha

## Reglas de oro

- Un fix no está "instalado" hasta que está en **las dos** máquinas y
  comiteado
- Corre `python tests/run_tests.py` después de tocar `config/` o `engine/`
- `#STATE` con más de 7 días → el coach se niega a avanzar; vuelve a correr
  `prep`
- Nunca edites `continuity.md` a mano, solo pegando un `#SESSION` nuevo
- ¿Pusiste el repo en público para una revisión? Vuélvelo privado al terminar

## Errores comunes

| Error | Solución |
|---|---|
| `Missing environment variable ICU_API_KEY` | `setx ICU_API_KEY "..."`, abre una terminal nueva |
| `Athlete not found` | `python coach.py prep --list` para confirmar el ID real |
| `...already exists` (en `new`) | Ese atleta ya está dado de alta — edita el YAML directo |
| Avg Power vacío en actividades con medidor | Máquinas desincronizadas — vuelve a copiar el archivo afectado a ambas |
| `note: no continuity.md here yet` | Normal en la semana 1 de un bloque — no es un error |
| `No data for '<id>'` (en `review`) | Corre `python coach.py prep <id>` primero |
| "No curve history yet" (en `review`) | No es un error — la captura apenas empezó, se resuelve con el tiempo |
| MCP: "Server disconnected" / se queda pensando y expira | Falta `ICU_API_KEY` en el bloque `env` de `claude_desktop_config.json` — revisa `%APPDATA%\Claude\logs\mcp-server-infame-coach.log` |
| Herramienta MCP no aparece tras editar el config | Cierra Desktop desde el ícono de la bandeja (no solo la ventana), vuelve a abrirlo |
