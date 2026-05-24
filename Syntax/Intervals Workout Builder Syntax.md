Intervals Workout Builder Syntax

1) Basic line format
Most steps follow this pattern:

- [duration OR distance] [target] [optional cadence] [RPE]

Examples:

- 5m30s 60% 90rpm [RPE 1-2]
- 1km 70% LTHR [RPE 2-3]
- 500mtr 70-80% Pace [RPE 3-4]

2) Duration and distance
Time
Hours: 1h
Minutes: 10m, 5m
Seconds: 30s, 90s
Combined: 1h2m30s, 5m30s
Distance
Metric: 500mtr, 2km, 10km

Important

m means minutes (not meters).
For meters, use mtr.

3) Targets
Power
FTP percentage: 75%, 95-105%

Heart rate
Percent of max HR: 70% HR, 75-80% HR
Percent of threshold HR: 95% LTHR, 90-95% LTHR

Pace
Percent of threshold pace: 60% Pace, 78-82% Pace

4) Cadence (cycling)
Add cadence after the target:

- 10m 75% 90rpm
- 12m 85% 90-100rpm

5) Ramps and freeride
Use ramp for gradual change (not case-sensitive):

- 10m ramp 50%-75%
- 15m ramp 60%-90% 85rpm
- 10m ramp 70%-50%

Special:

- 20m freeride = ERG off

6) Repeats
Two ways:

In a header/title line: Main Set 5x
As a standalone line before steps: 5x
Examples:

Main Set 4x
- 2m 90-95%
- 2m 50-55%

5x
- 30s 110-120%
- 30s 40-50%

- 5m 40-50%

Note

Leave one empty line before and after every repeat block (Main Set 5x or 5x).
Nested repeats are not supported.

7) Formatting Text Inside Workout Steps
You can add simple text formatting to make your workout script clearer and easier to read. Intervals.icu ignores these elements when parsing the workout, but they help you organize notes, highlight important parts, or add structure.

Use standard Markdown:

Titles:

# Title H1
### Title H3
###### Title H6
Bold and italic emphasis:

**bold**
*italic*
***bold italic***


8) Correct examples

Warmup

- 1m 50-58% [RPE 1-2]
- 1m 58-64% [RPE 1-2]
- 1m 64-69% [RPE 2-3]
- 1m 69-74% [RPE 2-3]
- 1m 74-78% [RPE 3-4]

- 2m 65-74% [RPE 2-3]

Main Set

- 7m 70-74% [RPE 2-3]
- 7m 74-77% [RPE 3-4]
- 4m 77-79% [RPE 3-4]

4x
- 20s 106-115% [RPE 9-10]
- 40s 50-64% [RPE 1-2]

- 3m 65-74% [RPE 2-3]

Cooldown

- 3m 50-64% [RPE 1-2]

-------------------------

Warmup

- 10m ramp 45-75% [RPE 1-3]

- 2m 65-74% [RPE 2-3]

Main Set

- 7m 70-74% [RPE 2-3]

4x
- 20s 106-115% [RPE 10-10]
- 40s 50-64% [RPE 1-2]

- 7m 74-77% [RPE 3-4]

- 3m 65-74% [RPE 2-3]

Cooldown

- 3m ramp 60-40% [RPE 1-3]

-------------------------

Warmup

- 1m 63-67% pace [RPE 1-1]
- 2m 65-69% pace [RPE 1-2]
- 2m 67-71% pace [RPE 2-3]

Main Set

6x
  - 3m 72-78% pace [RPE 2-3]
  - 1m 30s 70-76% pace [RPE 2-3]

Cooldown

- 3m 65-71% pace [RPE 1-2]

-------------------------

Warmup

- 1m 63-67% lthr [RPE 1-1]
- 2m 65-69% lthr [RPE 1-2]
- 2m 67-71% lthr [RPE 2-3]

Main Set

3x
  - 6m 80-86% lthr [RPE 3-4]
  - 4m 40s 70-76% lthr [RPE 2-3]

Cooldown

- 3m 65-71% lthr [RPE 1-2]