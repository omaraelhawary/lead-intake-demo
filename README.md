# AI Lead Intake + Accuracy Report

A lead classifier for a fictional home renovation company (BrightBuild Renovations, Austin TX), plus the part most AI automations skip: a hand-labeled test set and a report that shows exactly how often the AI is right, before and after the prompt is fixed.

## What's here
- `data/leads.jsonl`: 60 hand-labeled leads (19 qualified, 16 nurture, 15 unqualified, 10 spam), including hard cases: Spanish, budget written in words, sarcasm, two decision makers who disagree, a landlord, someone acting for their parents.
- `prompts/v1.txt`: a naive prompt (what most builds ship with).
- `prompts/v2.txt`: the same task with the business rules written out.
- `eval.py`: runs a prompt over the dataset and saves every prediction.
- `report.py`: turns one or more runs into a one-page HTML report (accuracy, precision and recall on qualified leads, confusion matrix, every mistake).

No dependencies beyond Python 3.10+.

## Run it
```bash
cp .env.example .env            # add your Gemini key (free tier) or use Ollama
export $(grep -v '^#' .env | xargs)

python eval.py --prompt prompts/v1.txt --provider gemini --out runs/v1.json --sleep 4
python eval.py --prompt prompts/v2.txt --provider gemini --out runs/v2.json --sleep 4
python report.py runs/v1.json runs/v2.json --out report.html
open report.html
```
`--sleep 4` keeps you under free-tier rate limits. `--provider mock` runs offline with a keyword heuristic, only to check the pipeline works; its numbers mean nothing.

## The live flow (n8n + HubSpot)
1. `npx n8n` and open http://localhost:5678
2. Webhook node (POST) receiving: name, email, phone, zip, budget, timeline, message
3. HTTP Request node to Gemini with the text of `prompts/v2.txt` (same prompt as the eval, so the report describes what runs in production)
4. Code node: parse the JSON, map label to HubSpot lifecycle stage (qualified = salesqualifiedlead, nurture = lead, unqualified = other, spam = stop)
5. HubSpot node (private-app token): create or update the contact, add a note with the AI's reason
6. IF qualified: send an email or Slack alert to the owner

## Results (qwen3:8b running locally via Ollama, temperature 0)

| | Accuracy | Qualified precision | Qualified recall | Mistakes |
|---|---|---|---|---|
| v1, naive prompt | 63% | 54% | 100% | 22 / 60 |
| v2, business rules written out | 95% | 95% | 95% | 3 / 60 |

v1 sent almost every lead to sales as "qualified": 10 unqualified and 6 nurture leads were marked hot, so roughly half of the leads a salesperson would call were a waste of time. Writing the business rules into the prompt (service area, ownership, $10k floor, 6-month window, what counts as spam) fixed most of it.

The 3 mistakes left in v2:
- #8, an $18k deck and patio job, called a small handyman job (wrong).
- #27, a buyer under contract who doesn't own the house yet, called qualified (a judgement call the rules don't settle).
- #48, gibberish, called unqualified instead of spam (harmless).

The dataset is synthetic and labeled by hand; the numbers show the method, not a production benchmark.
