"""Build a one-page HTML accuracy report from one or more eval runs (before/after)."""
import argparse, html, json

LABELS = ["qualified", "nurture", "unqualified", "spam"]


def metrics(rows):
    n = len(rows)
    acc = sum(r["expected"] == r["got"] for r in rows) / n
    tp = sum(r["expected"] == "qualified" and r["got"] == "qualified" for r in rows)
    pred = sum(r["got"] == "qualified" for r in rows)
    actual = sum(r["expected"] == "qualified" for r in rows)
    prec = tp / pred if pred else 0.0
    rec = tp / actual if actual else 0.0
    cols = LABELS + ["invalid", "error"]
    cm = {e: {g: 0 for g in cols} for e in LABELS}
    for r in rows:
        cm[r["expected"]][r["got"] if r["got"] in cols else "invalid"] += 1
    fails = [r for r in rows if r["expected"] != r["got"]]
    return {"n": n, "acc": acc, "prec": prec, "rec": rec, "cm": cm, "cols": cols, "fails": fails}


def pct(x):
    return f"{x * 100:.0f}%"


def run_block(name, run, m):
    used = [c for c in m["cols"] if any(m["cm"][e][c] for e in LABELS)]
    head = "".join(f"<th>{c}</th>" for c in used)
    body = ""
    for e in LABELS:
        cells = "".join(
            f'<td class="{"hit" if c == e else ("miss" if m["cm"][e][c] else "")}">{m["cm"][e][c]}</td>' for c in used)
        body += f"<tr><th>{e}</th>{cells}</tr>"
    fails = "".join(
        f"<tr><td>#{r['id']}</td><td>{r['expected']}</td><td>{r['got']}</td>"
        f"<td>{html.escape(r['message'][:140])}</td><td>{html.escape(str(r['reason'])[:160])}</td></tr>"
        for r in m["fails"]) or '<tr><td colspan="5">No failures.</td></tr>'
    return f"""
<section>
  <h2>{html.escape(name)}</h2>
  <p class="meta">{html.escape(run['prompt'])} · {html.escape(run['provider'])} / {html.escape(run['model'])} · {m['n']} leads</p>
  <div class="kpis">
    <div><span>{pct(m['acc'])}</span>Overall accuracy</div>
    <div><span>{pct(m['prec'])}</span>Qualified precision<small>leads marked hot that really are</small></div>
    <div><span>{pct(m['rec'])}</span>Qualified recall<small>hot leads we caught</small></div>
    <div><span>{len(m['fails'])}</span>Mistakes</div>
  </div>
  <h3>Confusion matrix (rows = correct label, columns = AI label)</h3>
  <table class="cm"><tr><th></th>{head}</tr>{body}</table>
  <h3>Every mistake</h3>
  <table class="fails"><tr><th>Lead</th><th>Correct</th><th>AI said</th><th>Message</th><th>AI reason</th></tr>{fails}</table>
</section>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--out", default="report.html")
    ap.add_argument("--title", default="Lead classifier accuracy report")
    a = ap.parse_args()
    runs = [json.load(open(p)) for p in a.runs]
    ms = [metrics(r["rows"]) for r in runs]
    names = ["Before" if i == 0 and len(runs) > 1 else ("After" if i == len(runs) - 1 and len(runs) > 1 else f"Run {i + 1}")
             for i in range(len(runs))]
    summary = ""
    if len(runs) > 1:
        b, f = ms[0], ms[-1]
        summary = (f'<p class="summary">Accuracy went from <b>{pct(b["acc"])}</b> to <b>{pct(f["acc"])}</b>; '
                   f'qualified-lead recall from <b>{pct(b["rec"])}</b> to <b>{pct(f["rec"])}</b>; '
                   f'mistakes from <b>{len(b["fails"])}</b> to <b>{len(f["fails"])}</b>.</p>')
    blocks = "".join(run_block(n, r, m) for n, r, m in zip(names, runs, ms))
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(a.title)}</title>
<style>
:root{{--bg:#f7f6f2;--ink:#1b1f27;--muted:#5a6270;--line:#e2ded4;--good:#0e6b63;--bad:#a2510a;--card:#fff}}
body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,sans-serif}}
main{{max-width:1040px;margin:0 auto;padding:32px 16px}}
h1{{margin:0 0 6px;font-size:28px}} h2{{margin:32px 0 4px}} h3{{margin:20px 0 8px;font-size:15px;color:var(--muted)}}
.meta{{color:var(--muted);margin:0}} .summary{{font-size:18px;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}}
.kpis{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-top:12px}}
.kpis div{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px;color:var(--muted);font-size:13px}}
.kpis span{{display:block;font-size:28px;font-weight:700;color:var(--ink)}} .kpis small{{display:block}}
table{{border-collapse:collapse;background:var(--card);width:100%;font-size:13px}}
th,td{{border:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}}
.cm td{{text-align:center;width:70px}} .hit{{background:#e3f1ef;color:var(--good);font-weight:700}} .miss{{background:#f8ebdd;color:var(--bad);font-weight:700}}
.wrap{{overflow-x:auto}} @media(max-width:640px){{.kpis{{grid-template-columns:repeat(2,minmax(0,1fr))}}}}
</style></head><body><main>
<h1>{html.escape(a.title)}</h1>
<p class="meta">Every lead in the test set was labeled by hand, then classified by the AI. Mistakes are listed in full.</p>
{summary}
<div class="wrap">{blocks}</div>
</main></body></html>"""
    open(a.out, "w").write(page)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
