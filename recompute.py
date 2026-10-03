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

# ---- Section 4.2: classical hosts outside a CDN by TLS version and server family ----
nc = [r for r in web if r["cdn_nt"] != "True" and r["pq_nt"] != "True"]
print(f"\nNON-CDN classical {len(nc)} | TLS 1.3 {sum(r['tls_nt'] == 'TLS 1.3' for r in nc)} | TLS 1.2 {sum(r['tls_nt'] == 'TLS 1.2' for r in nc)}")
for fam in ["nginx", "Apache", "IIS", "other", "not disclosed"]:
    s = [r for r in nc if r["server_family_nt"] == fam]
    print(f"   {fam:14} TLS 1.3 {sum(r['tls_nt'] == 'TLS 1.3' for r in s):3} | TLS 1.2 {sum(r['tls_nt'] == 'TLS 1.2' for r in s):3}")

# ---- Section 4.3: Wilson intervals and the matched within-organisation comparison ----
import math, collections


def wilson(k, n, z=1.959964):
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return f"{k}/{n} ({100 * k / n:.1f}%, 95% CI {100 * (c - h):.1f}-{100 * (c + h):.1f})"


print("\nWilson: homepages", wilson(sum(r["pq_nt"] == "True" for r in home), len(home)),
      "| personal-data", wilson(sum(r["pq_nt"] == "True" for r in db), len(db)))
for lab, f in [("CDN-fronted", lambda r: r["cdn_nt"] == "True"), ("other", lambda r: r["cdn_nt"] != "True")]:
    h = [r for r in home if f(r)]; d = [r for r in db if f(r)]
    print(f"   {lab:12} homepages {wilson(sum(r['pq_nt'] == 'True' for r in h), len(h))} | personal-data {wilson(sum(r['pq_nt'] == 'True' for r in d), len(d))}")
H = collections.defaultdict(list); D = collections.defaultdict(list)
for r in home:
    H[r["org"]].append(r["pq_nt"] == "True")
for r in db:
    D[r["org"]].append(r["pq_nt"] == "True")
cell = collections.Counter((any(H[o]), any(D[o])) for o in D if o in H)
print(f"MATCHED organisations {sum(cell.values())}: both PQ {cell[(True, True)]} | both classical {cell[(False, False)]} | "
      f"homepage only {cell[(True, False)]} | data endpoint only {cell[(False, True)]}")

# ---- Section 4.5: popular-host (CrUX) sample ----
C = [r for r in csv.DictReader(open("data/popular_hosts.csv", encoding="utf-8")) if r["reachable"] == "True"]
EDGE5 = {"Cloudflare", "Akamai", "Imperva", "Fastly", "CloudFront"}
pk = lambda s: sum(r["pq"] == "True" for r in s)
cc = [r for r in C if r["provider"] in EDGE5]; oo = [r for r in C if r["provider"] not in EDGE5]
print(f"\nPOPULAR reachable {len(C)} | CDN {pk(cc)}/{len(cc)} | other {pk(oo)}/{len(oo)}")
for name, f in [("consensus", lambda r: r["code_claude"] if r["code_claude"] == r["code_codex"] else None),
                ("claude", lambda r: r["code_claude"]), ("codex", lambda r: r["code_codex"])]:
    pd = [r for r in C if f(r) in ("P", "I")]; ii = [r for r in C if f(r) == "I"]
    print(f"   {name:9} personal-data (P+I) {pk(pd)}/{len(pd)} | institutional (I) {pk(ii)}/{len(ii)}")
