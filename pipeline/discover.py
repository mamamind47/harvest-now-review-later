"""Find data-bearing endpoints linked from each organisation's homepage.

For every row of frame CSV (sector,subsector,org,host,source) fetch https://host/,
follow redirects, and collect links whose URL or anchor text looks like a place where
personal data is entered or shown (login, e-service, internet banking, claims, appointments).
TLS is terminated per hostname, so only distinct hostnames matter for the scan; the matched
URL and anchor text are kept as evidence.

Output: endpoints.csv  (sector,subsector,org,role,host,evidence_url,evidence_text)
        discover_log.jsonl (per-org fetch status, final URL, blocked flag)
"""
import csv, json, re, ssl, sys, html
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlparse

FRAME = sys.argv[1] if len(sys.argv) > 1 else "frame_v1.csv"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"

KEYWORDS = re.compile(
    r"log-?in|sign-?in|signon|เข้าสู่ระบบ|ลงชื่อเข้าใช้|ลงทะเบียน|สมัครสมาชิก|register|member|"
    r"internet ?banking|i-?banking|online ?banking|e-?banking|e-?service|บริการออนไลน์|บริการอิเล็กทรอนิกส์|"
    r"e-?filing|ยื่นแบบ|ยื่นภาษี|ตรวจสอบสิทธิ|นัดหมาย|appointment|booking|จองคิว|"
    r"เคลม|claim|กรมธรรม์ของฉัน|my ?policy|my ?account|บัญชีของฉัน|portal|ผู้ป่วย|patient|"
    r"เช็คเบี้ย|ซื้อประกันออนไลน์|buy online|apply online|สมัครออนไลน์|e-?kyc",
    re.I,
)
CHALLENGE = re.compile(r"Just a moment|Attention Required|cf-browser-verification|รอสักครู่|Access Denied|Incapsula incident|Request unsuccessful", re.I)
SKIP_HOSTS = re.compile(r"facebook|line\.me|lin\.ee|twitter|x\.com|youtube|instagram|google|apple\.com|linkedin|tiktok|microsoft|office\.com|forms\.gle|bit\.ly")

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "th,en;q=0.8"})
    with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
        body = r.read(3_000_000).decode("utf-8", "ignore")
        return r.geturl(), r.status, body


def discover(row):
    host = row["host"]
    log = {"org": row["org"], "sector": row["sector"], "host": host}
    endpoints = [(row, "homepage", host, f"https://{host}/", "")]
    try:
        final, status, body = fetch(f"https://{host}/")
    except Exception as e:
        log["error"] = str(e)[:200]
        return log, endpoints
    fh = urlparse(final).hostname
    log.update(final_url=final, status=status, bytes=len(body), blocked=bool(CHALLENGE.search(body[:20000])))
    if fh and fh != host:
        endpoints.append((row, "homepage-redirect", fh, final, ""))
    seen = set()
    for m in re.finditer(r'<a\b[^>]*href=["\']([^"\'#]+)["\'][^>]*>(.*?)</a>', body, re.S | re.I):
        href, inner = m.group(1).strip(), m.group(2)
        text = html.unescape(re.sub(r"<[^>]+>", " ", inner))
        text = " ".join(text.split())[:80]
        # also consider title / aria-label / alt inside the anchor
        extra = " ".join(re.findall(r'(?:title|aria-label|alt)=["\']([^"\']+)["\']', m.group(0)))
        if not (KEYWORDS.search(href) or KEYWORDS.search(text) or KEYWORDS.search(extra)):
            continue
        url = urljoin(final, href)
        u = urlparse(url)
        if u.scheme not in ("http", "https") or not u.hostname or SKIP_HOSTS.search(u.hostname):
            continue
        if u.hostname in seen:
            continue
        seen.add(u.hostname)
        endpoints.append((row, "data-bearing-candidate", u.hostname, url, (text or extra)[:80]))
    log["n_candidates"] = len(seen)
    return log, endpoints


def main():
    rows = list(csv.DictReader(open(FRAME, encoding="utf-8")))
    with ThreadPoolExecutor(12) as ex:
        results = list(ex.map(discover, rows))
    with open("discover_log.jsonl", "w") as lf, open("endpoints.csv", "w", newline="", encoding="utf-8") as ef:
        w = csv.writer(ef)
        w.writerow(["sector", "subsector", "org", "role", "host", "evidence_url", "evidence_text"])
        seen = set()
        for log, eps in results:
            lf.write(json.dumps(log, ensure_ascii=False) + "\n")
            for row, role, h, url, text in eps:
                key = (row["org"], h)
                if key in seen:
                    continue
                seen.add(key)
                w.writerow([row["sector"], row["subsector"], row["org"], role, h, url, text])


if __name__ == "__main__":
    main()
