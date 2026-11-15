# Reflection

## 1. What I Built and Why

I built a small command-line tool for Tapon Sahu, who coordinates the kitchen at the BH-7 Mess, NIT Silchar. It reads the mess's own logs from `data.csv` and suggests how much of an item to prepare for the next shift, based on what students actually ate per head in past meals. I went with an offline tool because BH-7 runs on an open coupon and register model, where students decide at the last minute whether to eat in the mess or go out. A pre-booking app would not capture who really turns up, and it would need 230+ senior students to adopt it. Paper registers already hold the right numbers, but they stay on separate daily pages. The tool pulls them together on the kitchen computer.

## 2. What I Learned From the Fieldwork

I visited on 15 November 2026 from 17:29 to 17:51, covering the end of evening snacks and the start of dinner prep. What surprised me was what Tapon Sahu said about waste. I had assumed mess staff overcook and dump pots of food every night. He told me kitchen pot waste is under 2%, and he estimated that student plate waste in the buffet setup is about ten times higher, with students taking four or five scoops and leaving half in the disposal drum. Those are his estimates, not figures I measured. It still changed how I see the tool: it can help with how much gets cooked, but it cannot do anything about what ends up in the drum.

I have not yet shown the finished tool to Tapon Sahu, so I do not know whether it fits how he works in practice. I only discussed the problem and the data with him on 15 November

## 3. What Went Wrong or Changed Along the Way

- Inconsistent register entries: Some entries in the paper register were [missing a leftover value / had no headcount / were hard to read], so I [asked Tapon Sahu what they meant / left them out / entered my best reading]

- Two sources I planned to cite, an NDRI Karnal paper and a 2026 JCMM paper, could not be found under the titles I had. I replaced them with two real papers whose abstracts I could read and verify, and my summaries only cover what those abstracts say. I have not read the full papers.
- I first planned to cover [all items on the menu], but narrowed it to [rice, boiled eggs, Aloo Chop, chicken] because those were the ones I had enough entries for

## 4. How I Used AI Tools

AI tools helped me draft the written documents and write and test the C++ code, including the checks that skip bad CSV rows. I did the fieldwork myself, talked to Tapon Sahu, collected the entries from the kitchen register and serving desk logs, and checked the results. [MY INPUT: adjust this to what is actually true.]

## 5. What I Would Do Next

- Collect several more weeks of data. 38 entries over three days (13 to 15 November 2026) cannot show weekly patterns, and rare menu items have only one data point.
- Split the history into weekdays and weekends, since Tapon Sahu says turnout is higher on Sundays.
- Log estimated plate waste at the serving desk, so the tool can start to cover the larger source of waste he described.

## 6. Time Spent

About [30min] on fieldwork and the conversation, [30min] on entering data from the register into data.csv, [4hrs] on writing and testing the code, and [2hrs] on documentation.
