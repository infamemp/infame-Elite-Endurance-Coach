# Language Guide — Mexican Spanish (athlete-facing text)

> GENERATED FILE — DO NOT EDIT. Source: `config/language/es_mx.yaml`. Built 2026-09-27 by `python build_zone_tables.py build`.

Applies to `[Focus]`, `[Execution]`, `[Nutrition]` and the cue text in the code block when the athlete's language is Spanish. Register: professional, direct, *tú*; natural cycling and running vocabulary; no calques from English. `verify/validate_block.py` warns on the patterns in **Never write**.

## Terms

| Class | Write |
| :--- | :--- |
| `recovery` | recuperación |
| `endurance` | resistencia aeróbica |
| `tempo` | tempo |
| `sub_threshold` | sub-umbral |
| `threshold` | umbral |
| `supra_threshold` | supra-umbral |
| `vo2max` | VO2máx |
| `anaerobic` | anaeróbico |
| `neuromuscular` | neuromuscular |

| English | Spanish |
| :--- | :--- |
| warm-up | calentamiento |
| cool-down | enfriamiento |
| interval / rep | repetición |
| set | serie |
| strides | aceleraciones |
| even pace | paso parejo (running) / potencia pareja (bike) |
| recovery jog | trote de recuperación |
| spin (bike) | girar / pedalear |
| ERG mode | modo ERG |
| cadence | cadencia |
| seated / standing | sentado / de pie |
| minutes / seconds in prose | min / s — never 'm' (it reads as metres) |
| heart rate | frecuencia cardiaca |
| fuelling | alimentación |

## How each field is written

- **`[Focus]`** — A few words: the physiological target, in Spanish, then the author's zone id in parentheses (e.g. resistencia aeróbica (Daniels E)).
- **`[Execution]`** — Three short sentences, at most 60 words, and do not re-list the structure: the athlete sees the steps below. (1) what the session trains, by class and author zone, in words; (2) how it should feel and be executed; (3) what to do if it is not going as prescribed. Mention a number only when the athlete needs it to act (a threshold to hold, a limit not to cross).
- **`[Nutrition]`** — Before / during / after, only what applies, each with a quantity or a time. Vary the wording between sessions; never paste the same sentence into every one.

## Cue bank

Examples of tone and length. Rotate: within one block, no cue is used in more than two sessions. Adapt them to the step; do not paste them.

**warmup**
- "Empieza con paso corto y suelta los hombros"
- "Deja que la respiración se acomode antes de subir el ritmo"
- "Sube poco a poco, todavía sin exigirte"
- "Aquí solo se calienta: cadencia cómoda y postura relajada"
- "Suelta las piernas; el esfuerzo llega después"
- "Aumenta gradualmente hasta el ritmo de la serie"

**recovery**
- "Baja el ritmo y respira hondo"
- "Recupera a tu ritmo, sin prisa"
- "Afloja las piernas y baja las pulsaciones"
- "Trota o camina hasta sentirte listo para la siguiente"
- "Suelta los brazos y toma aire"
- "Pedalea ligero hasta la siguiente repetición"

**cooldown**
- "Baja poco a poco hasta terminar la sesión"
- "Cierra con ritmo corto y respiración tranquila"
- "Termina soltando las piernas"
- "Vuelve a la calma, sin apuro"
- "Últimos minutos ligeros; la sesión ya está hecha"
- "Baja las pulsaciones antes de detenerte"

**effort endurance**
- "Paso parejo y respiración cómoda"
- "Mantén la conversación posible"
- "Constante de principio a fin, sin apretar"
- "Cuida la postura cuando aparezca el cansancio"

**effort tempo threshold**
- "Ritmo firme y controlado; no lo aceleres"
- "Mismo esfuerzo que en la repetición anterior"
- "Sostenible hasta el último minuto"
- "Respira profundo y mantén la cadencia"

**effort high**
- "Fuerte y relajado; no aprietes los hombros"
- "Arranca controlado y termina lo más parejo posible"
- "Todo el esfuerzo va en mantener la técnica"
- "Cadencia alta, zancada suelta"

## Failure-condition sentences (`[Execution]`, part 3)

Vary them; `{n}` is an RPE taken from the code block.

- Si el esfuerzo supera RPE {n}, baja el ritmo y conserva la duración.
- Si no puedes sostener el ritmo hasta el final del bloque, reduce un poco y termina la serie.
- Si la frecuencia cardiaca se dispara antes de la mitad, camina o baja la intensidad y retoma.
- Si las piernas se sienten pesadas desde el primer bloque, acorta la sesión y termina en la zona de recuperación.
- Si el último bloque exige más que RPE {n}, termínalo un escalón abajo.

## Never write

| Pattern | Write instead |
| :--- | :--- |
| `se vuelve mayor` | Escribe 'si el esfuerzo pasa de RPE 3-4' o 'si el esfuerzo sube'. |
| `por encima de RPE` | Escribe 'si el esfuerzo supera RPE X'. |
| `(?i)\bvan \d` | Escribe 'Incluye 10 min de calentamiento' o 'Empieza con...'. |
| `(?i)\bpaso pareja\b` | Concordancia: 'paso parejo'. |
| `\b(Endurance\|Threshold\|Sub-threshold\|Supra-threshold\|Recovery\|Anaerobic)\b` | Usa el término en español: resistencia aeróbica, umbral, sub-umbral, supra-umbral, recuperación, anaeróbico. |
| `(?i)\bstrides?\b` | Usa 'aceleraciones'. |
| `\b\d+x de \d` | Escribe '6 repeticiones de 20 s', no '6x de 20s'. |
| `\b\d+m(\d+s)?\b` | En texto corrido usa 'min' y 's': '10 min', no '10m' (se lee como metros). |
| `(?i)\brealiza tu\b\|\bprocede a\b\|\basegúrate de\b` | Frase calcada del inglés: usa el imperativo directo ('calienta', 'termina', 'bebe'). |
