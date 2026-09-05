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

## Cada chat nuevo con un atleta

Arrastra desde `out/<nombre_atleta>/`:

- [ ] `state.md` — siempre
- [ ] `profile.md` — siempre
- [ ] `continuity.md` — solo si ya existe (significa que ya hubo una sesión en este bloque)

No hace falta volver a arrastrar a media conversación — solo al abrir un
chat **nuevo**.

## Consulta a media semana, fuera de calendario

1. `python coach.py prep <id>`
2. ¿Sigues en el mismo chat? No necesitas nada más.
3. ¿Vas a abrir un chat **nuevo**? Antes de cerrar este, pídele al coach:
   *"dame el header de continuidad"*
4. Pega el `#SESSION` que te entregue en `out/<nombre>/continuity.md`

## Cierre de bloque

1. El coach emite automáticamente un `#SESSION` con borde visual al terminar
   la última sesión
2. Cópialo en `out/<nombre>/continuity.md`
3. `python coach.py prep <id>` antes del siguiente chat

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
