"""Récupère les cours, calcule la performance et écrit docs/data.json."""
import csv, json, os, datetime as dt
from zoneinfo import ZoneInfo
import pandas as pd, yfinance as yf

USD = {"ARM"}   # tickers cotés en dollars : convertis en euros automatiquement

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

start = (pd.Timestamp(min(r["buy_date"] for r in ok)) - pd.Timedelta(days=10)).strftime("%Y-%m-%d")
end = (pd.Timestamp.today() + pd.Timedelta(days=2)).strftime("%Y-%m-%d")

def hist(ticker):
    h = yf.Ticker(ticker).history(start=start, end=end, auto_adjust=True)
    if h.empty:
        return None
    h.index = h.index.tz_localize(None).normalize()
    c = h["Close"]
    return c[~c.index.duplicated(keep="last")].dropna()

fx = hist("EURUSD=X") if any(r["ticker"] in USD for r in ok) else None

holdings, vals, invs = [], {}, {}
for r in ok:
    s = hist(r["ticker"])
    if s is None:
        print(f"PAS DE COURS : {r['name']} ({r['ticker']})")
        continue
    if r["ticker"] in USD:
        if fx is None:
            print(f"PAS DE TAUX EUR/USD : {r['name']} ignorée")
            continue
        s = (s / fx.reindex(s.index, method="ffill")).dropna()
    inv = float(r["invested_eur"])
    after = s[s.index >= pd.Timestamp(r["buy_date"])]
    if after.empty:
        after = s.iloc[[-1]]
    shares = inv / float(after.iloc[0])
    vals[r["name"]] = shares * after
    invs[r["name"]] = inv
    day = (s.iloc[-1] / s.iloc[-2] - 1) * 100 if len(s) > 1 else 0.0
    print(r["name"], "| achat:", after.index[0].date(), round(float(after.iloc[0]), 2),
          "| dernier cours:", s.index[-1].date(), round(float(s.iloc[-1]), 2))
    holdings.append({"name": r["name"], "envelope": r["envelope"], "invested": inv, "day_pct": round(float(day), 2)})

df = pd.DataFrame(vals).sort_index().ffill()          # NaN conservé avant la date d'achat
for h in holdings:
    h["value"] = round(float(df[h["name"]].iloc[-1]), 2)
    h["perf_pct"] = round((h["value"] / h["invested"] - 1) * 100, 2)

inv_series = df.notna().mul(pd.Series(invs)).sum(axis=1)   # investi cumulé : seulement les lignes déjà achetées
tot = df.sum(axis=1)

def lst(x):
    return [None if pd.isna(i) else round(float(i), 2) for i in x]

def agg(kind):
    out, tv = {}, sum(h["value"] for h in holdings)
    for h in holdings:
        for k, p in expo.get(h["name"], {}).get(kind, {}).items():
            out[k] = out.get(k, 0) + h["value"] * p / tv
    return {k: round(v, 1) for k, v in sorted(out.items(), key=lambda x: -x[1])}

data = {
    "updated": dt.datetime.now(ZoneInfo("Europe/Paris")).strftime("%d/%m/%Y %H:%M"),
    "total_value": round(float(tot.iloc[-1]), 2),
    "total_invested": round(sum(invs.values()), 2),
    "holdings": holdings,
    "history": {"dates": [d.strftime("%Y-%m-%d") for d in df.index],
                "total_perf": lst((tot / inv_series - 1) * 100),
                "per_holding": {k: lst((df[k] / invs[k] - 1) * 100) for k in df.columns}},
    "geo": agg("geo"), "sector": agg("sector"),
}
os.makedirs("docs", exist_ok=True)
json.dump(data, open("docs/data.json", "w", encoding="utf-8"), ensure_ascii=False)
print("data.json mis à jour,", len(holdings), "lignes")
