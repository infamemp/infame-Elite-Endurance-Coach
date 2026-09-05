# Manual Operativo — Infame Elite Endurance Coach v6.1

Guía paso a paso del flujo diario, después del rediseño de septiembre 2026
(motor extendido + `coach.py` unificado + continuidad como archivo).

Este manual cubre el **uso operativo** del sistema. Para arquitectura interna,
consulta `ARCHITECTURE_v6.md`, `WORKFLOW_CHECKLIST.md` e `IMPROVEMENT_BACKLOG.md`
en la raíz del repo — este documento no los reemplaza, los complementa.

---

## 0. Antes de empezar — requisitos por máquina

Esto debe estar listo en **las dos máquinas** (laptop y PC) antes de usar
cualquier comando de este manual:

1. `ICU_API_KEY` configurada como variable de entorno
2. Python instalado, con `pip install -r requirements.txt` corrido (o al menos
   `requests`, `pyyaml`, `openpyxl`)
3. El repo actualizado — mismo commit en ambas máquinas. Si acabas de recibir
   un archivo corregido en un chat con Claude, ese archivo tiene que llegar a
   **ambas** rutas antes de seguir:
   ```
   C:\Dev\Github\infame_elite _endurance_coach\
   E:\Dev\github\infame_elite_endurance_coach\
   ```
   (nota el espacio en el nombre de carpeta de la laptop — es real, no un typo)

**Regla de oro:** si corriges algo en un chat con Claude, ese archivo no está
"instalado" hasta que existe en las dos máquinas y está comiteado en GitHub.
Un archivo corregido que solo vive en la descarga del chat no cuenta.

---

## 1. Dar de alta un atleta nuevo

**Comando:**
```
python coach.py new i123456
```

**Qué hace:**
- Confirma que el ID existe de verdad en tu cuenta de Intervals.icu (detecta
  typos antes de crear nada)
- Si el atleta ya tiene perfil (`config/athletes/i123456.yaml` ya existe), se
  detiene sin tocar nada — nunca sobrescribe un perfil real
- Si no existe, copia la plantilla y crea `config/athletes/i123456.yaml`

**Qué haces tú después:**
1. Abre un chat nuevo en el Proyecto de Claude
2. Sigue la conversación de intake usando `config/athletes/ATHLETE_INTAKE.md`
   como guion — el coach la conduce en el idioma del atleta
3. El coach te entrega un perfil completo al final de la intake — cópialo y
   pégalo dentro de `config/athletes/i123456.yaml`, reemplazando la plantilla
4. Guarda el archivo. El atleta ya está listo para su primer `prep`

No hace falta correr `prep` como parte del alta — el intake no depende de
datos de Intervals.icu, solo de lo que el atleta declara.

---

## 2. Preparar a un atleta para trabajar con él (uso diario, uno por uno)

**Comando:**
```
python coach.py prep i123456
```

**Qué hace, en orden:**
1. Descarga datos frescos de Intervals.icu (`fetch_athlete_data.py`)
2. Resuelve su estado de entrenamiento (`build_state.py`) → `state.md`
3. Renderiza su contexto crudo (`build_profile.py`) → `profile.md`
4. Copia ambos a `out/<nombre_del_atleta>/`
5. Te avisa si `continuity.md` existe en esa carpeta y de cuántos días es
6. Actualiza `out/roster.md` con la fecha de este fetch

**Salida esperada en pantalla:**
```
Ready — drag out/elias_caballero/ (state.md, profile.md) into the Claude Project
continuity.md last updated 3 day(s) ago
```

Si ves `note: no continuity.md here yet`, es normal en la primera semana de
un atleta o de un bloque nuevo — no es un error.

---

## 3. Preparar a todos los atletas de una vez

**Comando:**
```
python coach.py prep --all
```

Corre el paso 2 para cada atleta con datos en la cuenta. Al final:
```
Done. 21/23 athletes ready in out/
```

Si algún atleta falla (por ejemplo, cuenta sin actividad reciente), el
resumen te dice cuántos de cuántos quedaron listos — revisa el detalle de
cada fallo más arriba en la misma salida.

**Para ver quién es quién sin descargar nada:**
```
python coach.py prep --list
```
Lista todos los atletas (id + nombre) y regenera `out/roster.md` con la
fecha de su último fetch real — útil para saber, sin correr nada pesado,
quién lleva tiempo sin actualizarse.

---

## 4. Qué arrastrar al Proyecto de Claude, y cuándo

Al abrir un chat nuevo para trabajar con un atleta, arrastras **la carpeta
completa** `out/<nombre_del_atleta>/`, o los archivos sueltos que tenga
dentro:

| Archivo | ¿Siempre presente? | Qué es |
|---|---|---|
| `state.md` | Sí | Estado autoritativo — CTL/ATL/TSB, ACWR, longitudinal, testing |
| `profile.md` | Sí | Contexto crudo — perfil, config deportiva, calendario, historial |
| `continuity.md` | Solo si ya hubo una sesión previa en este bloque | El `#SESSION` — dónde va el macrociclo |

**No hace falta volver a arrastrar nada a media conversación** — una vez que
el chat tiene los archivos, el coach los conserva en su contexto para el
resto de esa sesión. Solo se vuelve a arrastrar al abrir un chat **nuevo**.

---

## 5. Generar un plan o dar seguimiento (dentro del chat)

Una vez arrastrados los archivos, simplemente conversas con el coach en
lenguaje natural. El sistema es una máquina de estados de 6 fases (Fase 0
a Fase 6) que se conduce sola:

- **Atleta sin `#SESSION` previo** → arranca en Fase 1 (verificación e
  intake si hace falta), construye el macrociclo, y llega a Fase 4
  (generación de bloque)
- **Atleta con `continuity.md`** → el coach lee el `#SESSION`, reconstruye
  dónde iban, y continúa directo desde ahí

En cada fase el coach se detiene y espera tu confirmación explícita antes de
avanzar (por ejemplo, antes de generar código de Intervals.icu en Fase 4).
Eso es intencional — revisa lo que propone antes de aprobar.

---

## 6. Validar y subir un bloque a Intervals.icu

Cuando el coach entrega un bloque de código (sintaxis de Intervals.icu),
antes de subirlo:

**Comando:**
```
python coach.py check ruta\al\bloque.txt
```

Esto corre el validador determinístico: revisa sintaxis, pisos de
prescripción, elegibilidad de rampas, y **calcula el TSS real** (rellenando
el que el coach dejó en `pending`). Si falla, corrígelo y vuelve a correr el
comando — no subas un bloque que no pasó.

Si el bloque necesita una metodología o disciplina distinta a la que trae en
su encabezado:
```
python coach.py check bloque.txt --methodology daniels --discipline running
```

---

## 7. Consulta extra a media semana (ajuste fuera de calendario)

Este es el caso que motivó buena parte del rediseño: necesitas resolver algo
puntual con un atleta sin esperar a que termine el bloque.

**Paso a paso:**
1. Corre `python coach.py prep i123456` para tener datos frescos
2. Abre el chat **existente** de esa semana (si sigues en el mismo hilo, no
   necesitas nada más — el coach ya tiene el contexto)
3. Si vas a abrir un chat **nuevo** para esta consulta puntual: antes de
   cerrarlo, pídele al coach *"dame el header de continuidad"*
4. El coach entrega un `#SESSION` con `Active Phase: 4` (no una transición),
   la semana real del bloque en la que van, y una nota de lo que acaban de
   resolver
5. Copia ese bloque completo y pégalo en `out\i123456\continuity.md`
   (o `out\<nombre>\continuity.md`), reemplazando el anterior
6. La próxima vez que abras un chat para ese atleta, arrastra los tres
   archivos — el ajuste de esta consulta ya quedó capturado en las notas

---

## 8. Cierre de bloque y recalibración (Fase 5)

Al entregar la última sesión de un bloque, el coach emite automáticamente
el `#SESSION` de cierre, con un borde visual y la instrucción de copiarlo.

**Paso a paso:**
1. Copia ese bloque a `out\<atleta>\continuity.md`
2. Antes de la siguiente conversación con este atleta, corre
   `python coach.py prep <id>` para refrescar `state.md`
3. Abre un chat nuevo, arrastra los tres archivos
4. El coach recalibra el siguiente bloque **solo a partir de `#STATE`** — no
   te va a pedir cómo se sintió el atleta ni su cumplimiento; si tú quieres
   aportar eso, es información adicional, nunca un requisito

---

## 9. Cierre de macrociclo / debrief de carrera (Fase 6)

Cuando el bloque final del macrociclo termina (normalmente después de la
carrera A), el coach entra en Fase 6:

1. Si hubo carrera: comparte el resultado en el chat — el coach lo evalúa
   contra `#STATE` y te dice si conviene volver a testear umbrales
2. Si el macrociclo terminó sin carrera (cambio de objetivo, plan
   interrumpido): el coach resume la adaptación lograda
3. Para arrancar el siguiente macrociclo: corre `prep` de nuevo y confirma
   que quieres empezar uno nuevo — el coach vuelve a Fase 1

---

## 10. Mantenimiento — sincronizar máquinas y correr pruebas

**Cada vez que edites algo en `config/` o en `engine/`:**
```
python tests/run_tests.py
```
Corre las 67 pruebas (unitarias, validación de bloques, comparación golden
del motor de estado). Si algo falla, no subas el cambio hasta entenderlo.

**Cada vez que Claude te entregue un archivo corregido en un chat:**
1. Descárgalo
2. Cópialo a las **dos** rutas de máquina
3. Confírmalo corriendo el comando correspondiente una vez en cada máquina
4. Sube el commit a GitHub desde la máquina donde lo probaste primero
5. En la otra máquina, haz pull antes de tu próxima sesión de trabajo ahí

Este último punto es exactamente lo que falló con `intervals_export.py` y
causó semanas de Avg Power vacío — vale la pena hacerlo checklist, no
memoria.

**Repo público vs. privado:** si alguna vez lo pones en público para que
Claude lo revise directamente (como hicimos para la cross-reference de esta
sesión), vuelve a ponerlo en privado apenas termines. GitHub → Settings →
Danger Zone → Change visibility.

---

## 11. Solución de problemas comunes

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| `Missing environment variable ICU_API_KEY` | No configurada en esta terminal/máquina | `setx ICU_API_KEY "tu_key"`, abre una terminal nueva |
| `Athlete 'iXXXXXX' not found` | Typo en el ID, o no es coach de ese atleta | `python coach.py prep --list` para ver los IDs reales |
| `config/athletes/iXXXXXX.yaml already exists` | Ya diste de alta a este atleta antes | Edita el YAML existente, no uses `new` de nuevo |
| Avg Power en `—` para actividades con medidor | Copia local desincronizada con el repo | Repite el paso 10 (sincronizar máquinas) |
| `PROFILE BUILD FAILED (non-blocking)` | Fallo en `build_profile.py`, pero `state.md` se entregó igual | Revisa el error impreso; el chat puede seguir con solo `state.md` mientras lo arreglas |
| `note: no continuity.md here yet` | Primera semana de un atleta/bloque, o se te olvidó guardarlo | Normal en el primer caso; en el segundo, pide el header al coach (paso 7) |
| `#STATE` con más de 7 días | No corriste `prep` recientemente | `python coach.py prep <id>` antes de continuar — el coach se va a negar a avanzar con un estado viejo |

---

## 12. Referencia rápida de archivos y carpetas

```
infame_elite_endurance_coach/
├── coach.py                      punto de entrada único: prep / new / check
├── engine/
│   ├── fetch_athlete_data.py     descarga de Intervals.icu → athlete_data.json
│   ├── build_state.py            resuelve #STATE → state.md / state.json
│   ├── build_profile.py          renderiza profile.md
│   ├── longitudinal.py           módulo de tendencia/curvas (usado por build_state)
│   └── power_profile.py          módulo de perfil de potencia (usado por build_state)
├── verify/
│   └── validate_block.py         gate determinístico — lo llama coach.py check
├── config/
│   ├── athletes/
│   │   ├── _template.yaml        plantilla para coach.py new
│   │   ├── ATHLETE_INTAKE.md     guion de la conversación de alta
│   │   └── <id>.yaml             un archivo por atleta — lo declarado, no lo medido
│   ├── authors/*.yaml            zonas por metodología (Coggan, Daniels, etc.)
│   ├── tss_classes.yaml          multiplicadores de TSS por clase fisiológica
│   └── decision_thresholds.yaml  bandas de decisión — ninguna cifra vive en el código
├── generated/                    tablas de zonas — nunca se editan a mano
├── data/<id>/                    capa interna del motor — no navegar a mano
│   ├── athlete_data.json
│   ├── state.md / state.json
│   └── profile.md
├── out/<nombre_atleta>/          lo que arrastras al Proyecto de Claude
│   ├── state.md
│   ├── profile.md
│   └── continuity.md             el único archivo que tú escribes a mano
├── out/roster.md                 tabla nombre ↔ ID ↔ última actualización
├── tests/
│   ├── run_tests.py               67 pruebas — correr tras cualquier cambio a config/engine
│   └── make_fixtures.py
└── Prompt/
    └── infame_elite_endurance_coach.md   el prompt — vive también en el Proyecto de Claude
```

---

## Ideas para el futuro

Ninguna de estas es necesaria para operar el sistema tal como quedó — son
posibles mejoras a considerar cuando el flujo actual esté probado en la
práctica real con tus 16–23 atletas.

1. **Verificar la regla de `eW'`/`ePmax` contra varios atletas.** Quedó
   fuera de `profile.md` a propósito porque solo se confirmó contra un caso
   (Elías). Si se confirma el patrón (modelo `FFT_CURVES`, ventana 90d) con
   3–4 atletas más, se puede agregar con confianza.

2. **Alerta automática de atletas con datos viejos.** `roster.md` ya
   muestra la fecha de último fetch — un paso más sería que `coach.py
   prep --list` resalte en la salida a cualquier atleta con más de N días
   sin actualizarse, sin que tengas que leer la tabla entera.

3. **Detección de mensajes de calendario sin `type`.** El caso de "🚗 Viaje
   🚗" / "DESCANSO" mostrando `Type: —` reveló que Intervals.icu no siempre
   llena ese campo para entradas genéricas. Vale la pena revisar si hay más
   casos similares (por ejemplo, notas del atleta) que merezcan el mismo
   tratamiento de valor por defecto.

4. **Umbral configurable para la advertencia de `continuity.md` viejo.**
   Hoy está fijo en 10 días dentro de `coach.py`. Podría vivir en
   `decision_thresholds.yaml` junto con el resto de los umbrales, para no
   tener números sueltos en el código de orquestación.

5. **Un modo `coach.py prep --stale` que solo refresque a los atletas con
   datos de más de N días,** en vez de `--all` corriendo contra los 23 cada
   vez — útil según crezca la cuenta.

6. **Registro de qué atletas tienen `continuity.md` faltante o viejo, en el
   propio `roster.md`.** Ahora mismo esa información solo aparece en pantalla
   al correr `prep` para un atleta puntual — centralizarla en el roster daría
   una vista de todos los atletas de un vistazo.

7. **Autores pendientes identificados en el backlog** (Seiler, Pfitzinger,
   Hansons, Skiba) — trabajo de contenido, no de infraestructura, pero sigue
   abierto y vale la pena retomarlo cuando el flujo operativo esté estable.

8. **Golden test específico para `build_profile.py`.** Los otros dos scripts
   del motor (`fetch_athlete_data.py`, `build_state.py`) están cubiertos por
   la suite de 67 pruebas; `build_profile.py` se verificó a mano en esta
   sesión pero no tiene un fixture propio en `tests/`. Agregarlo evitaría
   una regresión silenciosa si se vuelve a tocar.

9. **Script de verificación de sincronización entre máquinas.** Algo tan
   simple como comparar un hash de los archivos de `engine/` en ambas rutas
   habría detectado el desfase de `intervals_export.py` antes de que
   afectara datos reales de un atleta.

10. **Revisar si conviene retirar `intervals_export.py` y `convert.py` del
    repo por completo** (o moverlos a una carpeta `legacy/`) una vez que el
    flujo nuevo lleve unas semanas probado en producción real — hoy siguen
    ahí como referencia histórica, pero ya no son parte del camino diario.
