"""Join scan results with frame roles and ASN, print sector/provider tables."""
import json, csv, collections, re
scan = {}
for l in open('full_20260926.jsonl'):
    r = json.loads(l); scan[(r['sector'], r['host'])] = r
asn = json.load(open('asn_20260926.json'))
eps = list(csv.DictReader(open('endpoints_filtered.csv', encoding='utf-8')))

EDGE = {'13335': 'Cloudflare', '20940': 'Akamai', '16625': 'Akamai', '19551': 'Imperva', '54113': 'Fastly',
        '209242': 'Cloudflare', '32787': 'Akamai-Prolexic'}
def provider(r):
    ip = next((i for i in r.get('ips', []) if ':' not in i), None)
    a = asn.get(ip, {}) if ip else {}
    n, name = a.get('asn', '?'), a.get('as_name', '')
    h = r.get('headers') or {}
    if 'x-amz-cf-id' in h or 'cloudfront' in h.get('via', '').lower(): return 'CloudFront', n, name
    # Akamai also runs edge servers inside ISP networks (e.g. AS38040, AS45430), so ASN alone misses them
    if 'akamai-grn' in h or 'x-akamai-transformed' in h or 'akamai' in h.get('server', '').lower(): return 'Akamai', n, name
    if n in EDGE: return EDGE[n], n, name
    if n == '16509' or n == '14618': return 'AWS (non-CloudFront)', n, name
    if n in ('8075', '8068'): return 'Microsoft/Azure', n, name
    if n in ('15169', '396982', '19527'): return 'Google', n, name
    return 'other: ' + re.sub(r'\s*-.*', '', name)[:22], n, name

EDGE_NAMES = {'Cloudflare', 'Akamai', 'Imperva', 'Fastly', 'CloudFront'}
recs = []
for e in eps:
    r = scan.get((e['sector'], e['host']))
    if not r: continue
    if 'worldoftanks' in e['host'] or e['org']=='Mission Hospital Phuket': continue  # listed domain now redirects to a game ad (expired domain)
    status = 'unreachable' if (r.get('dns_err') or not r['default_ok']) else ('PQ' if r['pq_only_ok'] else 'classical')
    prov, n, name = provider(r) if status != 'unreachable' else ('-', '', '')
    recs.append(dict(e, status=status, provider=prov, asn=n, as_name=name, kx=r.get('default_curve', ''), tls=r.get('tls_version', '')))
with open('results_20260926.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=recs[0].keys()); w.writeheader(); w.writerows(recs)

def table(key, filt=lambda x: True, title=''):
    print(f'\n## {title}')
    g = collections.defaultdict(collections.Counter)
    for x in recs:
        if filt(x): g[key(x)][x['status']] += 1
    for k in sorted(g, key=lambda k: str(k)):
        c = g[k]; reach = c['PQ'] + c['classical']
        pct = f"{100*c['PQ']/reach:5.1f}%" if reach else '   - '
        print(f"{str(k):45} PQ {c['PQ']:3}/{reach:3} = {pct}   unreachable {c['unreachable']}")

homes = lambda x: x['role'] in ('homepage', 'homepage-redirect')
table(lambda x: (x['sector'], x['subsector'] if x['sector'] in ('hospital', 'bank') else ''), homes, 'Homepages by sector')
table(lambda x: x['sector'], lambda x: x['role'] == 'data-bearing', 'Data-bearing endpoints by sector')
table(lambda x: x['role'], lambda x: True, 'By role')
table(lambda x: x['provider'] in EDGE_NAMES, lambda x: x['status'] != 'unreachable', 'TLS-terminating CDN edge (True) vs not (False)')
table(lambda x: x['provider'], lambda x: x['status'] != 'unreachable', 'By provider')
print('\n## classical data-bearing endpoints')
for x in recs:
    if x['role'] == 'data-bearing' and x['status'] == 'classical':
        print(f"{x['sector']:10} {x['org'][:30]:30} {x['host']:38} {x['kx']:8} {x['tls']:8} {x['provider'][:28]:28} | {x['evidence_text'][:40]}")
print('\n## PQ endpoints NOT on a CDN edge')
for x in recs:
    if x['status'] == 'PQ' and x['provider'] not in EDGE_NAMES:
        print(f"{x['sector']:10} {x['host']:40} {x['provider']} AS{x['asn']} {x['as_name'][:40]}")
