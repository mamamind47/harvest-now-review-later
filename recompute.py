"""Recompute the paper's headline figures from the released data (data/web_hosts.csv, data/app_aggregates.csv).

Web figures use the NT vantage point (columns *_nt), as in the paper; the AIS columns give the second vantage point.
Run: python3 recompute.py
"""
import csv

R = [r for r in csv.DictReader(open("data/web_hosts.csv", encoding="utf-8")) if r["reachable_nt"] == "True"]


def pct(s, col="pq_nt"):
    a = sum(r[col] == "True" for r in s)
    return f"{a}/{len(s)} ({100 * a / max(1, len(s)):.1f}%)"


def dd(s):
    d = {}
    for r in s:
        d.setdefault(r["host"], r)
    return list(d.values())


web = dd(R)
cdn = lambda s: [r for r in s if r["cdn_nt"] == "True"]
non = lambda s: [r for r in s if r["cdn_nt"] != "True"]
print("WEB unique hosts", len(web))
print("WEB CDN edge", pct(cdn(web)), "| non-edge", pct(non(web)))
home = [r for r in web if r["role"] in ("homepage", "homepage-redirect")]
print("WEB homepages", pct(home))
db = [r for r in web if r["role"] in ("public-data", "institutional-data")]
print("WEB data-bearing (P+I)", pct(db))
for s in ["bank", "insurance", "hospital", "government"]:
    print("   db", s, pct([r for r in db if r["sector"] == s]))
print("   db CDN edge", pct(cdn(db)), "| non-edge", pct(non(db)))
print("WEB PQ by sector x CDN (stratified):")
key = lambda r: r["sector"] + ("/" + r["subsector"] if r["sector"] == "hospital" else "")
for k in sorted({key(r) for r in web}):
    s = [r for r in web if key(r) == k]
    print(f"   {k:18} CDN {pct(cdn(s))} | non-CDN {pct(non(s))}")
print(f"WEB homepage/redirect hostnames {len(home)} representing {len({r['org'] for r in home})} organisations")

both = [r for r in web if r["reachable_ais"] == "True"]
same = sum(r["pq_nt"] == r["pq_ais"] for r in both)
print(f"VANTAGE: reachable from both NT and AIS {len(both)}; same PQ status {same}")

U = list(csv.DictReader(open("data/app_unique_host_totals.csv", encoding="utf-8")))
n = lambda k, c, s=None: sum(int(r[c]) for r in U if r["host_class"] == k and (s is None or r["sector"] == s))
f = lambda a, b: f"{a}/{b} ({100 * a / max(1, b):.1f}%)"
print("APP content hosts", f(n("content", "pq"), n("content", "unique_hosts")))
print("APP service hosts", f(n("service", "pq"), n("service", "unique_hosts")))
for s in ["bank", "government"]:
    print("   service", s, f(n("service", "pq", s), n("service", "unique_hosts", s)))
A = list(csv.DictReader(open("data/app_aggregates.csv", encoding="utf-8")))  # per app; shared hosts count in each app
withs = [r for r in A if int(r["service_hosts"])]
allpq = [r["app"] for r in withs if r["service_pq"] == r["service_hosts"]]
nopq = [r["app"] for r in withs if r["service_pq"] == "0"]
print(f"APPS with service hosts: {len(withs)} | all-PQ {len(allpq)} {allpq} | none-PQ {len(nopq)} {nopq} | mixed {len(withs) - len(allpq) - len(nopq)}")
