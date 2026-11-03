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
Watch it run (62 seconds): [media/lead-intake-demo.mp4](media/lead-intake-demo.mp4)

`n8n/lead-intake.workflow.json` is the workflow from the video. Import it into n8n (Workflows, Import from file).

1. Webhook (POST `/webhook/lead-intake`) receives name, email, phone, zip, budget, timeline, message.
2. A Code node fills in `prompts/v2.txt`, the same prompt the eval scores, so the report describes what runs in production.
3. The model (qwen3:8b through Ollama in the video) returns the label, the missing info and a one-sentence reason as JSON.
4. Spam stops here: nothing is written to the CRM.
5. HubSpot: create or update the contact by email (qualified becomes a sales qualified lead), then attach a note with the label and the reason.
6. A follow-up email is drafted, not sent: a site-visit request for qualified leads, a question about the missing details for nurture leads.

The HubSpot service key is read from the `HUBSPOT_TOKEN` environment variable, so it never sits inside the workflow. `demo/form.html` is the contact form used in the video; serve it locally and it posts to the webhook.

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
