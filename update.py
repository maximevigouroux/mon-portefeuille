"""Récupère les cours, calcule la performance et écrit docs/data.json."""
import csv, json, datetime as dt
import pandas as pd, yfinance as yf

txt = open("holdings.csv", encoding="utf-8-sig").read().splitlines()
delim = ";" if txt[0].count(";") > txt[0].count(",") else ","
rows = []
for r in csv.DictReader(txt, delimiter=delim):
    r = {k: (v or "").strip() for k, v in r.items() if k}
    if not r.get("name"):
        continue
    manquants = [k for k in ("ticker", "envelope", "invested_eur", "buy_date") if not r.get(k)]
    if manquants:
        raise SystemExit(f"holdings.csv : la ligne '{r['name']}' n'a pas de valeur pour {manquants}")
    r["invested_eur"] = r["invested_eur"].replace(",", ".")
    rows.append(r)
expo = json.load(open("exposure.json", encoding="utf-8"))
ok = []
for r in rows:
    if r["ticker"].startswith("?"):
        print(f"IGNORÉ (ticker à remplir) : {r['name']}")
    else:
        ok.append(r)

start = min(r["buy_date"] for r in ok)
raw = yf.download([r["ticker"] for r in ok], start=start, auto_adjust=True, progress=False)["Close"]
if isinstance(raw, pd.Series):
    raw = raw.to_frame(ok[0]["ticker"])
px = raw.ffill()

holdings, value_series, perf_series = [], {}, {}
for r in ok:
    t = r["ticker"]
    if t not in px or px[t].dropna().empty:
        print(f"PAS DE COURS : {r['name']} ({t})")
        continue
    s = px[t].dropna()
    bd = pd.Timestamp(r["buy_date"])
    after = s[s.index >= bd]
    if after.empty:                       # date d'achat future : on prend le dernier cours
        after = s.iloc[[-1]]
    inv = float(r["invested_eur"])
    shares = inv / float(after.iloc[0])
    v = (shares * after)
    value_series[r["name"]] = v
    perf_series[r["name"]] = (v / inv - 1) * 100
    day = (s.iloc[-1] / s.iloc[-2] - 1) * 100 if len(s) > 1 else 0.0
    holdings.append({"name": r["name"], "envelope": r["envelope"], "invested": inv,
                     "value": round(float(v.iloc[-1]), 2),
                     "perf_pct": round(float(perf_series[r["name"]].iloc[-1]), 2),
                     "day_pct": round(float(day), 2)})

df = pd.DataFrame(value_series).ffill().fillna(0)
inv_by_date = pd.DataFrame({h["name"]: [h["invested"]] for h in holdings}).sum(axis=1).iloc[0]
tot = df.sum(axis=1)

def agg(kind):
    out = {}
    tv = sum(h["value"] for h in holdings)
    for h in holdings:
        for k, p in expo.get(h["name"], {}).get(kind, {}).items():
            out[k] = out.get(k, 0) + h["value"] * p / 100 / tv * 100
    return {k: round(v, 1) for k, v in sorted(out.items(), key=lambda x: -x[1])}

data = {
    "updated": dt.datetime.now().strftime("%d/%m/%Y %H:%M"),
    "total_value": round(float(tot.iloc[-1]), 2),
    "total_invested": inv_by_date,
    "holdings": holdings,
    "history": {"dates": [d.strftime("%Y-%m-%d") for d in df.index],
                "total_perf": [round(float(x), 2) for x in ((tot / inv_by_date - 1) * 100)],
                "per_holding": {k: [round(float(x), 2) for x in v.reindex(df.index).ffill().fillna(0)]
                                for k, v in perf_series.items()}},
    "geo": agg("geo"), "sector": agg("sector"),
}
json.dump(data, open("docs/data.json", "w", encoding="utf-8"), ensure_ascii=False)
print("data.json mis à jour,", len(holdings), "lignes")
