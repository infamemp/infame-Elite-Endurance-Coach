# Intervals.icu Workout Builder — Syntax Reference

This file defines **syntax only**: how a line is written so Intervals.icu reads it and the verification engine (`coach.py check`) can cost it. It contains no sessions and no session shapes — what a session contains is decided in the design table, never here.

The session card around the code block (header fields, languages, delivery) is defined in the prompt's `<output_contract>`. This file covers only what goes inside the ` ```text ` block.

---

## 1. Lines allowed inside the code block

Only four kinds of line exist. Anything else — comments, titles, markdown, bold, notes — is not allowed.

| Line | Form |
|:---|:---|
| Section header | `Warmup` · `Main Set` · `Cooldown` — alone on the line, in English |
| Repeat header | `Main Set <N>x` or `<N>x` — alone on the line |
| Step | `- <duration> <target> [<cadence>] [<RPE>] ["<cue>"]` |
| Blank line | Separates sections and surrounds every repeat |

---

## 2. Step line

```
- <duration> <target> [<cadence>] [<RPE>] ["<cue>"]
```

- Starts with `- ` (hyphen and space). No indentation.
- Tokens in this order. `<duration>` and `<target>` are required; the rest are optional.
- One step per line.

### Duration

| Unit | Token | Notes |
|:---|:---|:---|
| Seconds | `30s` | |
| Minutes | `5m` | `m` is **minutes**, never metres |
| Hours | `1h` | |
| Combined | `1m30s` · `1h10m` · `1h2m30s` | Written joined, no spaces |
| Metres | `400mtr` | Distance — see below |
| Kilometres | `2km` | Distance — see below |

**Distance steps** have no fixed duration until pace is known, so the engine **cannot cost them**: their load is missing from the session TSS and the Duration is marked approximate. Use distance only when the methodology or the event genuinely requires it.

### Target — one per step, always

| Metric | Token | Intervals.icu reads it as |
|:---|:---|:---|
| Power | `<a>-<b>%` · `<a>%` | % of FTP |
| Heart rate | `<a>-<b>% LTHR` · `<a>% LTHR` | % of threshold HR |
| Pace | `<a>-<b>% Pace` · `<a>% Pace` | % of threshold pace (higher = faster) |

- Ranges low to high, with a hyphen and no spaces: `85-90%`.
- `LTHR` and `Pace` exactly as written, after one space.
- The metric is the one the Metric Map assigns to the discipline.
- Floors: power 25%, `% LTHR` 50%, `% Pace` 40%.

**Never valid**, even though some are valid Intervals.icu syntax:

| Written | Why it is rejected |
|:---|:---|
| `% HR`, `% HRmax` | Intervals.icu reads `% HR` as % of **maximum** HR — a different anchor from the zone tables |
| `% FTP`, `% CP` | Power takes the bare `%` |
| `250W`, `250 watts` | Absolute values are prohibited |
| `150bpm` | Absolute values are prohibited |
| `5:30/km`, `8:00/mi` | Absolute values are prohibited |
| `Z2`, `Z3 Pace`, `Z4 HR` | Intervals.icu would apply its own zones, not the author's |

### Cadence — cycling only, optional

`90rpm` or a range `85-95rpm`, after the target.

### RPE — optional, required by dual-layer methodologies

`[RPE <a>-<b>]` or `[RPE <a>]`, using the active author's scale from the zone table.

### Cue — optional, required by dual-layer methodologies

`"<text>"` — last on the line, in double quotes, in the athlete's language, with no double quotes inside. Intervals.icu shows it on the device and does not interpret it. No absolute values inside a cue either.

---

## 3. Ramps

```
- <duration> ramp <from>-<to>[<suffix>]
```

- `<from>` is the starting target and `<to>` the ending one; either order (rising or falling).
- The suffix is the metric's: none for power, ` LTHR`, ` Pace`.
- Optional cadence after the ramp target.
- **Only where eligible:** `trainer` with power, and `treadmill` when the athlete profile authorizes it. Everywhere else a ramp is a hard-constraint violation.

---

## 4. Freeride

```
- <duration> freeride
```

ERG off on a smart trainer for that step. `trainer` only. The engine cannot cost it — its load is missing from the session TSS.

---

## 5. Repeats

```
Main Set <N>x
- <step>
- <step>
```

or the same with `<N>x` alone as the header line.

- The repeat's steps follow the header directly, with **no blank line between them** — a blank line ends the repeat.
- **One blank line before and one after** the whole repeat.
- **No nesting**: a repeat never contains another repeat.
- A single-step "repeat" is just a longer step; don't write `1x`.

---

## 6. Section layout

```
Warmup

- <step>

Main Set

- <step>

<N>x
- <step>
- <step>

- <step>

Cooldown

- <step>
```

This shows **layout only** — where headers, blank lines and repeats go. The number of steps, repeats and sections of a real session comes from its design.
