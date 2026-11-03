"""Run a lead classifier prompt against a labeled dataset and write an accuracy report.

Usage:
  python eval.py --prompt prompts/v1.txt --provider gemini --out runs/v1.json
  python eval.py --prompt prompts/v2.txt --provider gemini --out runs/v2.json
  python report.py runs/v1.json runs/v2.json --out report.html

Providers: gemini (env GEMINI_API_KEY), ollama (local, env OLLAMA_MODEL), mock (offline smoke test).
"""
import argparse, json, os, re, time, urllib.request

LABELS = ["qualified", "nurture", "unqualified", "spam"]


def format_lead(lead):
    keys = ["name", "zip", "budget", "timeline", "message"]
    return "\n".join(f"{k}: {lead.get(k, '')}" for k in keys)


def call_gemini(prompt, model):
    key = os.environ["GEMINI_API_KEY"]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}}
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.load(r)
    return data["candidates"][0]["content"]["parts"][0]["text"]


def call_ollama(prompt, model):
    url = os.environ.get("OLLAMA_URL", "http://localhost:11434") + "/api/generate"
    body = {"model": model, "prompt": prompt, "stream": False, "format": "json", "think": False,
            "options": {"temperature": 0}}
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)["response"]


def call_mock(prompt, model):
    """Keyword heuristic, only to test the pipeline without any API."""
    text = prompt.rsplit("Lead:", 1)[-1].lower()
    if re.search(r"seo|bitcoin|loan|bit\.ly|test|asdf|leads per month|va from|suspended|websites for", text):
        label = "spam"
    elif re.search(r"rent|landlord won|hiring|student|fort worth|houston|manhattan|gutter|fence|water heater", text):
        label = "unqualified"
    elif re.search(r"\$\d|\d+k|grand|thousand", text) and re.search(r"month|asap|january|february|spring|week", text):
        label = "qualified"
    else:
        label = "nurture"
    return json.dumps({"label": label, "reason": "mock heuristic"})


PROVIDERS = {"gemini": call_gemini, "ollama": call_ollama, "mock": call_mock}


def parse(raw):
    m = re.search(r"\{.*\}", raw, re.S)
    try:
        out = json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        out = {}
    label = str(out.get("label", "")).strip().lower()
    return (label if label in LABELS else "invalid"), out.get("reason", "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--data", default="data/leads.jsonl")
    ap.add_argument("--provider", default="gemini", choices=PROVIDERS)
    ap.add_argument("--model", default=os.environ.get("MODEL", "gemini-2.5-flash"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--sleep", type=float, default=0.0, help="seconds between calls (free-tier rate limits)")
    a = ap.parse_args()

    if a.provider == "mock":
        a.model = "keyword-heuristic"
    template = open(a.prompt).read()
    leads = [json.loads(l) for l in open(a.data) if l.strip()]
    call = PROVIDERS[a.provider]
    rows = []
    for lead in leads:
        prompt = template.replace("{lead}", format_lead(lead))
        try:
            got, reason = parse(call(prompt, a.model))
        except Exception as e:  # keep the run going, record the failure
            got, reason = "error", str(e)[:200]
        rows.append({"id": lead["id"], "expected": lead["label"], "got": got, "reason": reason,
                     "message": lead["message"]})
        print(f"{lead['id']:>3} expected={lead['label']:<11} got={got:<11}")
        time.sleep(a.sleep)

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    json.dump({"prompt": a.prompt, "provider": a.provider, "model": a.model, "rows": rows},
              open(a.out, "w"), indent=1, ensure_ascii=False)
    acc = sum(r["expected"] == r["got"] for r in rows) / len(rows)
    print(f"\naccuracy: {acc:.1%}  ->  {a.out}")


if __name__ == "__main__":
    main()
