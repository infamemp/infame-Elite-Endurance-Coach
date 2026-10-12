# Language Guide — Mexican Spanish (athlete-facing text)

> GENERATED FILE — DO NOT EDIT. Source: `config/language/es_mx.yaml`. Built 2026-10-12 by `python build_zone_tables.py build`.

Applies to `[Focus]`, `[Why]`, `[Execution]`, `[Nutrition]` and the cue text in the code block when the athlete's language is Spanish. The vocabulary and phrases are the head coach's own. Tempo, strides, openers, sweet spot, sprints, VO2max, FTP and neuromuscular are universal and stay as written; so does any other technical term this guide gives no translation for. Register: professional, direct, *tú*. **A cycling session never uses running words and a running session never uses cycling words: the validator BLOCKS the week (`HC-SPORT`) until it is corrected.** `verify/validate_block.py` warns on the patterns in **Never write**.

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

| Sport | When | Write |
| :--- | :--- | :--- |
| running | endurance class on the sport's long day | fondo aeróbico (never 'trote de fondo aeróbico': on a run it is simply 'fondo aeróbico') |
| running | endurance class on any other run | trote aeróbico |
| cycling | endurance class on any bike or mixed session | resistencia aeróbica (fondo aeróbico on the long day) |
| both | muscular endurance work (e.g. tempo on climbs) | resistencia muscular |
| both | terms that stay in English | Tempo, strides, openers, sweet spot, sprints, VO2max, FTP, neuromuscular. Any other technical term with no translation agreed in this guide also stays in English |
| both | strides | always plural, never 'stride' ('6 strides de 20 s') |
| both | short efforts that wake the legs before a key session | openers (never 'aperturas', never 'piernas abiertas') |
| both | harder minutes inside a session (touches) | toques (e.g. 'Fondo aeróbico con toques de tempo', 'Tempo con arranques'); the session keeps its own class name |
| cycling | short bursts on the bike | arranques |
| running | pick-ups on a run | cambios de ritmo |
| both | rolling aerobic / fartlek session | fartlek, or 'terreno ondulado' when the terrain sets it |
| both | technique drill session | técnica de pedaleo / técnica de carrera (drills keep their own names: spin-ups, pierna aislada, skipping) |
| running | stride form | zancada fluida (never 'zancada suelta') |
| cycling | pedalling form | pedaleo fluido. 'Zancada', 'trote' and 'strides' are running words: never in a bike session |
| running | holding the effort | ritmo ('sostener el ritmo'). Cycling words (pedaleo, rodillo, vatios) never appear in a run |
| cycling | holding the effort | potencia when the step has a power target ('mantener la potencia'), intensidad when it is guided by RPE or heart rate ('mantener la intensidad'). Not 'ritmo' |
| both | a steady effort | constante ('potencia constante', 'esfuerzo constante'). 'Parejo' only for the splits of a run ('paso parejo'), never the default |
| both | to set a pace or power from the start | establecer (never 'asentar') |
| both | easy aerobic effort described by talking | 'esfuerzo en el que puedes hablar con frases completas' (never 'ritmo conversable' or 'conversacional') |
| both | carbohydrates | always plural, 'carbohidratos' (never 'carbohidrato'). 'CHO' is a valid abbreviation ('6-7 g CHO/kg') |
| both | carbohydrates taken during the session | 'carbohidratos durante la sesión' (never 'fuel' or 'intra-entrenamiento') |
| both | repetitions of a set | repeticiones (never 'repeats') |
| both | a percentage in [Focus], [Why], [Execution], [Nutrition] | always with its reference: '60-68% del FTP', '95% del umbral', '85% de la FC máx'. A text line never starts with '- ' (Intervals.icu reads those lines as workout steps) |
| both | minutes and seconds in [Focus], [Execution], [Nutrition] | '10 min', '30 s' — never '10m' or '30s' (that is Intervals.icu syntax and reads as metres). Inside the code block the syntax stays '10m', '30s' |
| both | accents | write correct Spanish with accents. The upload removes the vowel accents (á é í ó ú ü) before the text reaches Intervals.icu; ñ, ¿ and ¡ stay as they are |
| both | author zone codes (Friel Zona 3, Daniels E, Koop ER...) | never in athlete text: they go in the coach-only [Zone] field |

## How each field is written

- **`[Focus]`** — A few words in the athlete's terms: what the session trains, using the class names above ("Fondo aeróbico con subidas de resistencia muscular (Tempo)"). It is the workout's name in Intervals.icu, so no author codes and no scheduling logic.
- **`[Zone]`** — Coach-only field, never sent to Intervals.icu: the class and the author's own zone, as the head coach reads them ("Tempo · Friel Zona 3"; several parts separated by " · " or " + ").
- **`[Execution]`** — Three short sentences, at most 60 words, and do not re-list the structure: the athlete sees the steps below. (1) what the session trains, by class, in words; (2) how it should feel and be executed; (3) what to do if it is not going as prescribed. Mention a number only when the athlete needs it to act, and give every percentage its reference.
- **`[Nutrition]`** — Before / during / after, only what applies, each with a quantity or a time. When fuelling happens during the session, the timing also goes in the cue of that step.

## The head coach's phrases

Use them as the base and adapt to the step. Take the phrases of the session's sport and the ones marked *both*. A phrase may repeat across sessions: consistent wording for the same kind of step is the house style.

**warmup**
- (both) "Calentamiento progresivo"
- (cycling) "Pedaleo suave"
- (cycling) "Pedaleo cómodo"
- (cycling) "Pedaleo con cadencia cómoda"
- (running) "Trote suave de calentamiento"
- (running) "Trote de calentamiento"
- (running) "Trote progresivo"

**recovery**
- (both) "Recupera"
- (both) "Afloje"
- (both) "Recupera en las bajadas o planos"
- (cycling) "Pedaleo suave"
- (running) "Trote de recuperación"

**hold the effort**
- (both) "Cadencia controlada"
- (both) "Buena postura"
- (both) "Manteniendo la forma"
- (both) "Mantén la cadencia durante el intervalo"
- (both) "Respeta la cadencia"
- (both) "Respeta la intensidad"
- (both) "Misma intensidad"
- (cycling) "Potencia constante"
- (cycling) "Potencia controlada"
- (cycling) "Respeta la potencia"
- (cycling) "Misma potencia que el primer bloque"
- (running) "Ritmo constante"
- (running) "Ritmo controlado"
- (running) "Respeta el ritmo"
- (running) "Mismo ritmo que el primer bloque"

**raise or lower**
- (both) "Aumenta la intensidad"
- (both) "Aumentando"
- (both) "Reduce la intensidad"
- (cycling) "Sube la potencia sin exagerar"

**approximate**
- (both) "Aproximadamente"
- (both) "aprox."

## Failure-condition sentences (`[Execution]`, part 3)

`{n}` is an RPE taken from the code block. Pick the one that fits the session's sport and structure.

- (both) Si el esfuerzo pasa de RPE {n}, reduce la intensidad y conserva la duración.
- (both) Si la frecuencia cardiaca se dispara pronto, recupera y retoma con menor intensidad.
- (both) Si las piernas se sienten pesadas desde el primer bloque, acorta la sesión y termina en resistencia aeróbica.
- (both) Si las piernas se sienten pesadas desde el primer esfuerzo, acorta la sesión y termina en resistencia aeróbica.
- (cycling) Si no logras mantener la potencia hasta el final del bloque, reduce la intensidad y termina la serie.
- (cycling) Si el último bloque exige más de lo indicado, mantén la misma potencia del primero o termínalo con menor intensidad.
- (running) Si no logras sostener el ritmo hasta el final del bloque, reduce la intensidad y termina la serie.
- (running) Si el último bloque exige más de lo indicado, mantén el mismo ritmo del primero o termínalo con menor intensidad.

## Words of the other sport (the week is BLOCKED, `HC-SPORT`)

| Session sport | Pattern | Write instead |
| :--- | :--- | :--- |
| cycling | `(?i)\b(?:trot(?:e\|es\|ar\|a\|an\|ando)\|zancadas?\|strides?\|caminat(?:a\|as)\|corre\|corres\|correr\|corriendo)\b` | Es vocabulario de carrera en una sesión de ciclismo. Usa pedaleo (pedaleo fluido, pedaleo suave) y potencia o intensidad; openers en lugar de strides. |
| running | `(?i)\b(?:pedale(?:o\|os\|ar\|a\|an\|ando)\|pedalada\|rodillo\|vatios\|watts\|bicicleta\|bici)\b` | Es vocabulario de ciclismo en una sesión de carrera. Usa trote, zancada, strides y ritmo. |

## Never write

| Pattern | Sport | Write instead |
| :--- | :--- | :--- |
| `se vuelve mayor` | both | Escribe 'si el esfuerzo pasa de RPE X' o 'si el esfuerzo sube'. |
| `por encima de RPE` | both | Escribe 'si el esfuerzo pasa de RPE X'. |
| `(?i)\bvan \d` | both | Escribe 'Incluye 10 min de calentamiento' o 'Empieza con...'. |
| `(?i)\bpaso pareja\b` | both | Concordancia: 'paso parejo'. |
| `(?i)\b(?:potencia\|ritmo\|esfuerzo\|intensidad)\s+parej[oa]\b` | both | Escribe 'constante' ('potencia constante'). 'Parejo' solo para el paso de una carrera. |
| `(?i)zancada suelta` | both | Escribe 'zancada fluida'. |
| `\b(Endurance\|Threshold\|Sub-threshold\|Supra-threshold\|Recovery\|Anaerobic)\b` | both | En español: resistencia aeróbica (fondo aeróbico en día largo), umbral, sub-umbral, supra-umbral, recuperación, anaeróbico. |
| `(?i)trote de fondo aeróbico` | both | Escribe 'fondo aeróbico' (día largo) o 'trote aeróbico' (día normal). |
| `\b(\d+m(\d+s)?\|\d+s)\b` | both | En los campos de texto escribe '10 min' y '30 s'; '10m' y '30s' son sintaxis de Intervals.icu y solo van en el bloque de código. |
| `\b\d+x de \d` | both | Escribe '6 strides de 20 s' o '6 repeticiones de 20 s', no '6x de 20s'. |
| `\b(Friel\|Daniels\|Coggan\|Carmichael\|Palladino\|Koop\|Olbrich\|Hansons?\|Hudson\|Rosario)\b` | both | El atleta no usa los códigos de autor: van en el campo [Zone], solo para el coach. |
| `(?i)\brealiza tu\b\|\bprocede a\b\|\basegúrate de\b` | both | Frase calcada del inglés: usa el imperativo directo ('calienta', 'termina', 'bebe'). |
| `(?i)\bapertura(?:s)?\b` | both | Escribe 'openers', tal cual. |
| `(?i)piernas abiertas\|abre(?:r)? las piernas` | both | Escribe 'activación de piernas' o 'openers'. |
| `(?i)\b(?:asent(?:ar\|ad[oa]s?)\|asienta(?:n)?)\b` | both | Escribe 'establecer'. |
| `(?i)\bconversa(?:ble\|cional)\b\|conversaci[oó]n fluida` | both | Escribe 'esfuerzo en el que puedes hablar con frases completas'. |
| `(?i)\bstride\b` | both | Escribe 'strides', siempre en plural. |
| `(?i)\bcarbohidrato\b` | both | Escribe 'carbohidratos', siempre en plural. |
| `(?i)\brepeats?\b` | both | Escribe 'repeticiones'. |
| `(?i)\bfuel(?:l?ing)?\b\|intra-?entrenamiento` | both | Escribe 'carbohidratos durante la sesión'. |
| `(?i)\britmo\b` | cycling | En ciclismo escribe 'potencia' (paso con meta de potencia) o 'intensidad' (paso por RPE o frecuencia cardiaca). |
| `\d+(?:\s?[-–]\s?\d+)?\s?%(?!\s*(?:del?\b\|de la\b\|FTP\|LTHR\|FC\b\|umbral))` | both | Todo porcentaje lleva su referencia: '60-68% del FTP', '95% del umbral', '85% de la FC máx'. |
