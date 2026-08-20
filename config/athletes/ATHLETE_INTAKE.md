# Athlete Intake

**How this works.** This form collects only what the coach cannot read from your
training platform. Everything measurable — your fitness numbers, past sessions,
heart rate history — is pulled automatically. What is asked here is what only you know.

**How long it takes.** Ten minutes. If you have never trained before, less — most
of the later sections will not apply to you.

**If you don't know an answer, write "I don't know."** That is a real answer and it
is more useful than a guess. Nothing here is a test.

---

## Part 1 — Who you are

**1.1 Name**

**1.2 Age**

**1.3 What language do you want your training written in?**

**1.4 Kilometres or miles?**

---

## Part 2 — What you want

**2.1 What do you want to achieve?**
Write it however it comes out. Any of these are complete answers:
- "Finish my first 10K without walking"
- "Break 3:15 in the marathon"
- "Get back in shape after two years off"
- "Ride the Gran Fondo in October and not suffer the whole way"
- "Be healthier. I don't have a specific event."

**2.2 Do you have a date?**
An event, a trip, a deadline of any kind. If there is no date, say so — training
without a target date is perfectly valid.

**2.3 If you have more than one goal, which matters most?**
Goals compete for the same training time. Knowing the priority lets the coach
protect the one that matters.

**2.4 Have you done anything like this before?**
- Never
- Yes, a while ago
- Yes, recently

---

## Part 3 — Injuries and limitations

**3.1 Are you currently injured, or recovering from an injury?**
If yes: what, when it started, and what you can and cannot do right now.

**3.2 Any injury that comes back when you train harder?**
The knee that complains, the achilles that flares, the back that goes out. Recurring
problems shape the plan more than past ones do.

**3.3 Anything else that affects how you can train?**
Medication that changes heart rate, poor heat tolerance, recent surgery, pregnancy,
a joint that limits range of motion. Anything that would change what the coach
prescribes.

---

## Part 4 — Your week

This is the single most important section. A plan built on hours you do not have
will fail, no matter how well designed it is.

**4.1 Which days can you train?**
Mark the realistic ones, not the ideal ones.

| Mon | Tue | Wed | Thu | Fri | Sat | Sun |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
|     |     |     |     |     |     |     |

**4.2 How long can each of those days be?**
A rough number per day is enough — "45 min weekdays, 2h Saturday."

**4.3 Which days can be long?**
Most plans need one or two longer sessions. Which days can absorb them?

**4.4 What time of day do you usually train?**
Morning, midday, evening, varies. This affects fuelling advice and how sessions
are sequenced.

**4.5 Is there anything coming that will disrupt this?**
Travel, work seasons, exams, a new baby, surgery. Say when and how long.

**4.6 Be honest: is the week you just described sustainable for the next three months?**
If it is your best week rather than your normal week, say so.

---

## Part 5 — Where and how you train

**5.1 What sport or sports?**
Running, cycling, both, something else.

**5.2 Where do you actually train?**
Roads, trails, a track, an indoor trainer, a treadmill, a gym, a mix.

**5.3 If you train indoors, how often?**
And is it by choice — weather, safety, schedule — or all you have available?

**5.4 What is the terrain like?**
Flat, rolling, mountainous. If you run trails: technical or smooth? How much
elevation on a typical outing?

**5.5 What is the weather like where you train?**
Especially heat, humidity, or altitude. These change what a given effort costs you.

---

## Part 6 — Your training history

> **New to training? Skip this whole section.** Write "starting from zero" and move on.

**6.1 What have you been doing for the last three months?**
Roughly: how many sessions a week, how long, how hard.

**6.2 What is the most you have trained consistently?**
Your biggest sustained week or month, and when that was.

**6.3 What is your longest session in the last year?**

**6.4 Have you followed a structured plan before?**
If yes: whose, and did it work for you?

**6.5 What kind of training do you enjoy?**
And what do you hate? A plan you dread is a plan you skip.

---

## Part 7 — Devices and data

> **No watch, no bike computer? Skip this section.** You can train perfectly well
> by effort, and the coach will prescribe that way.

**7.1 What do you wear or use?**
Watch, heart rate strap, bike computer, smart trainer, power meter, phone app.

**7.2 Do you have a power meter?**
- Bike: yes / no / smart trainer only (indoor)
- Run: yes / no

**7.3 Does your device control your indoor trainer automatically?**
This is what allows ramped targets that change gradually during a session.

**7.4 Do you know any of your numbers?**
FTP, threshold pace, max or resting heart rate, recent test results. If you have
never tested, say so — the coach can work it out from your training data or
prescribe a test.

**7.5 Do you track sleep, resting heart rate, or HRV?**

---

## Part 8 — Preferences

All optional. Skip anything you have no opinion about.

**8.1 How do you want your sessions described?**
- By numbers (watts, pace, heart rate)
- By effort (how hard it should feel)
- Both

**8.2 How much explanation do you want?**
- Just tell me what to do
- Explain the reasoning
- Teach me as we go

**8.3 Is there a coaching philosophy or author you like?**
Daniels, Friel, Koop, Coggan, someone else. No opinion is a fine answer — the
coach will choose what fits.

**8.4 Anything else?**

---

## For the coach

Once this form is complete, create `config/athletes/<athlete_id>.yaml` from
`config/athletes/_template.yaml` and transfer the answers. That file is the
athlete's permanent declared profile — everything measurable comes from
Intervals.icu and never gets copied here.

Re-run the form only when something structural changes: a new goal, a new
injury, a different weekly availability, new equipment.
