# Language Guide — Mexican Spanish (athlete-facing text)

> GENERATED FILE — DO NOT EDIT. Source: `config/language/es_mx.yaml`. Built 2026-10-02 by `python build_zone_tables.py build`.

Applies to `[Focus]`, `[Execution]`, `[Nutrition]` and the cue text in the code block when the athlete's language is Spanish. The vocabulary and phrases are the head coach's own. Tempo, strides, VO2max and neuromuscular are universal and stay as written. Register: professional, direct, *tú*. `verify/validate_block.py` warns on the patterns in **Never write**.

## Class names

| Class | Write |
| :--- | :--- |
| `recovery` | recuperación |
| `endurance` | resistencia aeróbica |
| `tempo` | tempo |
| `sub_threshold` | sub-umbral |
| `threshold` | umbral |
| `supra_threshold` | supra-umbral |
| `vo2max` | VO2max |
| `anaerobic` | anaeróbico |
| `neuromuscular` | neuromuscular |

## Terms and rules of use

| When | Write |
| :--- | :--- |
| endurance class on the sport's long day | fondo aeróbico (never 'trote de fondo aeróbico': on a run it is simply 'fondo aeróbico') |
| endurance class on any other run | trote aeróbico |
| endurance class on any other bike or mixed session | resistencia aeróbica |
| muscular endurance work (e.g. tempo on climbs) | resistencia muscular |
| strides | strides (e.g. '6 strides de 20 s') |
| stride form | zancada fluida (never 'zancada suelta') |
| minutes and seconds in [Focus], [Execution], [Nutrition] | '10 min', '30 s' — never '10m' or '30s' (that is Intervals.icu syntax and reads as metres). Inside the code block the syntax stays '10m', '30s' |
| author zone codes (Friel Zona 3, Daniels E, Koop ER...) | never in athlete text: they go in the coach-only [Zone] field |

## How each field is written

- **`[Focus]`** — A few words in the athlete's terms: what the session trains, using the class names above ("Fondo aeróbico con subidas de resistencia muscular (Tempo)"). It is the workout's name in Intervals.icu, so no author codes and no scheduling logic.
- **`[Zone]`** — Coach-only field, never sent to Intervals.icu: the class and the author's own zone, as the head coach reads them ("Tempo · Friel Zona 3"; several parts separated by " · " or " + ").
- **`[Execution]`** — Three short sentences, at most 60 words, and do not re-list the structure: the athlete sees the steps below. (1) what the session trains, by class, in words; (2) how it should feel and be executed; (3) what to do if it is not going as prescribed. Mention a number only when the athlete needs it to act.
- **`[Nutrition]`** — Before / during / after, only what applies, each with a quantity or a time. When fuelling happens during the session, the timing also goes in the cue of that step.

## The head coach's phrases

Use them as the base and adapt to the step. A phrase may repeat across sessions: consistent wording for the same kind of step is the house style.

**warmup**
- "Trote suave de calentamiento"
- "Trote de calentamiento"
- "Calentamiento progresivo"
- "Trote progresivo"
- "Pedaleo suave"
- "Pedaleo cómodo"
- "Pedaleo con cadencia cómoda autorregulada"

**recovery**
- "Recupera"
- "Afloje"
- "Trote de recuperación"
- "Recupera en las bajadas o planos"

**hold the effort**
- "Ritmo constante"
- "Ritmo controlado"
- "Cadencia controlada"
- "Buena postura"
- "Manteniendo la forma"
- "Mantén la cadencia durante el intervalo"
- "Respeta la cadencia"
- "Respeta la intensidad"
- "Respeta el ritmo"
- "Mismo ritmo que el primer bloque"
- "Misma intensidad"

**raise or lower**
- "Aumenta la intensidad"
- "Aumentando"
- "Sube la potencia sin exagerar"
- "Reduce la intensidad"

**approximate**
- "Aproximadamente"
- "aprox."

## Failure-condition sentences (`[Execution]`, part 3)

`{n}` is an RPE taken from the code block.

- Si el esfuerzo pasa de RPE {n}, reduce la intensidad y conserva la duración.
- Si no logras sostener el ritmo hasta el final del bloque, reduce la intensidad y termina la serie.
- Si la frecuencia cardiaca se dispara pronto, recupera y retoma con menor intensidad.
- Si las piernas se sienten pesadas desde el primer bloque, acorta la sesión y termina en resistencia aeróbica.
- Si el último bloque exige más de lo indicado, mantén el mismo ritmo del primero o termínalo con menor intensidad.

## Never write

| Pattern | Write instead |
| :--- | :--- |
| `se vuelve mayor` | Escribe 'si el esfuerzo pasa de RPE X' o 'si el esfuerzo sube'. |
| `por encima de RPE` | Escribe 'si el esfuerzo pasa de RPE X'. |
| `(?i)\bvan \d` | Escribe 'Incluye 10 min de calentamiento' o 'Empieza con...'. |
| `(?i)\bpaso pareja\b` | Concordancia: 'paso parejo'. |
| `(?i)zancada suelta` | Escribe 'zancada fluida'. |
| `\b(Endurance\|Threshold\|Sub-threshold\|Supra-threshold\|Recovery\|Anaerobic)\b` | En español: resistencia aeróbica (fondo aeróbico en día largo), umbral, sub-umbral, supra-umbral, recuperación, anaeróbico. |
| `(?i)trote de fondo aeróbico` | Escribe 'fondo aeróbico' (día largo) o 'trote aeróbico' (día normal). |
| `\b(\d+m(\d+s)?\|\d+s)\b` | En los campos de texto escribe '10 min' y '30 s'; '10m' y '30s' son sintaxis de Intervals.icu y solo van en el bloque de código. |
| `\b\d+x de \d` | Escribe '6 strides de 20 s' o '6 repeticiones de 20 s', no '6x de 20s'. |
| `\b(Friel\|Daniels\|Coggan\|Carmichael\|Palladino\|Koop\|Olbrich\|Hansons?\|Hudson\|Rosario)\b` | El atleta no usa los códigos de autor: van en el campo [Zone], solo para el coach. |
| `(?i)\brealiza tu\b\|\bprocede a\b\|\basegúrate de\b` | Frase calcada del inglés: usa el imperativo directo ('calienta', 'termina', 'bebe'). |
