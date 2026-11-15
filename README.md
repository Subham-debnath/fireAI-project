# BH-7 Mess Waste-Adjusted Prep Quantity Advisor

| | |
|---|---|
| **Project** | BH-7 Mess Waste-Adjusted Prep Quantity Advisor |
| **Place** | Boys' Hostel 7 (BH-7) Mess, NIT Silchar, Assam |
| **Target user** | Tapon Sahu (Mess Staff) |
| **Fieldwork date** | 15 November 2026 |
| **Demo video** | https://drive.google.com/file/d/1cvKtNOfZyKuzahGIVa-_4i9BAlbGZdrW/view?usp=sharing |
| **Repository** | https://github.com/Subham-debnath/fireAI-project.git |

## What it does

Tapon Sahu currently decides daily quantities of rice, dal, boiled eggs and evening snacks (e.g., Aloo Chop) from rough mental estimates. When student turnout changes, this leads to mid-shift shortages or soggy and excess leftovers.

This is a small offline command-line tool for the kitchen computer. It reads the mess's own logs from `data.csv`, works out how much of an item students actually consumed per head in past meals, and recommends a prep quantity for the coming shift.

For each past meal of the chosen item:

```
net_consumed    = prepared_qty - leftover_qty + shortage_refill_qty
per_student_rate = net_consumed / students_served
```

The recommendation is:

```
average per_student_rate × expected headcount × (1 + SAFETY_BUFFER_PERCENT / 100)
```

The output also shows how many past meals matched, the average historical batch size, how much to add or save against that batch, and a waste or shortage risk alert when leftovers or refills were heavy.

## Files

| File | Purpose |
|------|---------|
| `advisor.py` | The advisor program (Python 3, standard library only) |
| `data.csv` | Meal-by-meal kitchen register and serving desk entries |
| `research.md` | Problem statement, existing solutions and sources |
| `fieldwork.md` | On-site observation, conversation with Tapon Sahu, data collection method |
| `photos/` | Timestamped fieldwork photos |

## How to run

The program is a single Python 3 script (Python 3.7 or newer) that uses only the standard library, so there is nothing to install or compile.

```bash
py advisor.py
```

Run it from the folder that contains `data.csv`.

### The two inputs

1. **Item keyword**: a case-insensitive part of the item name, for example `rice`, `Boiled eggs`, `Aloo Chop` or `Chicken`. Every row whose `item_name` contains the keyword is used.
2. **Expected student count**: how many students you expect for the upcoming shift, for example `215`.

You can also pass both on the command line and skip the prompts:

```bash
py advisor.py "rice" 215
py advisor.py "Boiled eggs" 145
py advisor.py "rice" 215 other_file.csv   # optional third argument: CSV path
```

### Settings in `advisor.py`

Both thresholds are constants near the top of `advisor.py`, under the `CONFIGURABLE THRESHOLDS` heading. Edit them and run the script again.

```python
SAFETY_BUFFER_PERCENT = 5.0              # line 31
HIGH_VARIANCE_ALERT_PERCENT = 8.0        # line 35
```

- `SAFETY_BUFFER_PERCENT`: extra buffer added above the average net consumed per student.
- `HIGH_VARIANCE_ALERT_PERCENT`: if average leftover or average shortage refill, as a percentage of the prepared quantity, is above this value, the item is flagged.


### Bad rows

Malformed rows (missing columns, non-numeric quantities, `students_served <= 0` and similar) are skipped without crashing, and each one prints a line like:

```
[WARN] Skipping malformed row 14: students_served must be > 0 (got 0)
```

## Data format

`data.csv` has these columns:

```
date,meal_type,item_name,prepared_qty,unit,students_served,leftover_qty,shortage_refill_qty,recorded_by_place
```

It holds 38 meal-by-meal entries from 3 days (`2026-11-13` to `2026-11-15`), taken from the BH-7 daily kitchen register and serving desk logs. Each entry records where it was noted (`BH-7 Mess kitchen counter` or `BH-7 Mess serving desk`). See `fieldwork.md` for details.

### Actual Output on BH-7 Data

Paste the exact terminal output below after running these commands on your own `data.csv`.

**`py advisor.py "rice" 215`**

```text
=========== WASTE-ADJUSTED PREP ADVISOR (BH-7 Mess) ===========
  Item keyword                    : rice
  Matched items                   : Raw rice (soaked), Raw rice (washed), Jeera rice (washed), Jeera/Pulao rice (washed)
  Historical meals matched        : 6
  Avg net consumption / student   : 0.120 kg
  Expected headcount              : 215
  Safety buffer                   : 5.0%
  ----------------------------------------------------------
  RECOMMENDED PREP QUANTITY       : 27.0 kg
  Historical avg batch size       : 27.9 kg  (served ~218 students)
  Versus average batch            : SAVE 0.9 kg vs average batch
  ----------------------------------------------------------
  Avg leftover (% of prepared)    : 6.6%  (0 of 6 meals above 8.0%)
  Avg shortage refill (% prepared): 0.0%  (0 of 6 meals above 8.0%)
  No high-variance alert: past prep matched demand within 8.0%.
================================================================
```

**`py advisor.py "Boiled eggs" 145`**

```text
=========== WASTE-ADJUSTED PREP ADVISOR (BH-7 Mess) ===========
  Item keyword                    : Boiled eggs
  Matched items                   : Boiled eggs
  Historical meals matched        : 3
  Avg net consumption / student   : 1.17 eggs
  Expected headcount              : 145
  Safety buffer                   : 5.0%
  ----------------------------------------------------------
  RECOMMENDED PREP QUANTITY       : 179 eggs
  Historical avg batch size       : 157 eggs  (served ~139 students)
  Versus average batch            : ADD 22 eggs vs average batch
  ----------------------------------------------------------
  Avg leftover (% of prepared)    : 1.2%  (0 of 3 meals above 8.0%)
  Avg shortage refill (% prepared): 5.2%  (1 of 3 meals above 8.0%)
  No high-variance alert: past prep matched demand within 8.0%.
================================================================
```

## What this tool gets wrong and should not be trusted for

- **Plate waste vs. kitchen waste.** Tapon Sahu told me that kitchen pot waste is under 2%, while student plate waste in the buffet setup (taking 4 to 5 scoops and dumping half into the disposal drum) is roughly 10 times higher. These are his estimates, not figures I measured. This tool only sees pot-level preparation, leftovers and refills. It does not track how much food students throw into the disposal drum, so it cannot reduce that waste.
- **Sudden external shocks.** It cannot predict exam schedules, heavy rain, or students going out for evening snacks on a given day. Tapon Sahu still has to adjust the expected student count by hand, since the recommendation is only as good as the headcount he enters.
- **Small 3-day sample.** The recommendation rests on 38 entries from `2026-11-13` to `2026-11-15`. Rare weekly menu items (for example Sattu Paratha or Methi Puri) have only one data point so far, so their recommendations are close to a single past meal. Three days also cannot show weekday and weekend patterns reliably.

Treat the output as a data-backed starting point for Tapon Sahu's own judgement, not a replacement for it.