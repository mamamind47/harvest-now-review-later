"""Static hostname extraction from a downloaded APK/XAPK (no execution, no traffic interception).

For each package:
  1. unpack the .xapk/.apk (XAPK = zip of base.apk + split APKs)
  2. record the signing certificate of base.apk (apksigner --print-certs), so the file can be
     matched to the publisher's key and a tampered mirror copy would be detectable
  3. scan every file inside every APK (dex, resources, assets, native libs) for
     https?://host and bare hostnames under the org's own domains
  4. delete the unpacked files and the download; keep only apk_hosts.jsonl

Usage: python3 extract_hosts.py <package> <org-domain-regex> [--keep]
"""
import json, os, re, shutil, subprocess, sys, tempfile, zipfile, glob, hashlib

APKSIGNER = sorted(glob.glob(os.path.expanduser("~/Library/Android/sdk/build-tools/*/apksigner")))[-1]
URL_RE = re.compile(rb"https?://([A-Za-z0-9](?:[A-Za-z0-9-]{0,62}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,62}[A-Za-z0-9])?)+)")


def all_strings_files(root):
    for dp, _, fns in os.walk(root):
        for fn in fns:
            yield os.path.join(dp, fn)


def main():
    pkg, domre = sys.argv[1], sys.argv[2]
    keep = "--keep" in sys.argv
    dom = re.compile(rb"\b([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.(?:" + domre.encode() + rb"))\b", re.I)
    dl = next((p for p in glob.glob(f"dl/{pkg}.*")), None)
    rec = {"package": pkg, "file": dl}
    if not dl:
        rec["error"] = "not downloaded"
        print(json.dumps(rec)); return
    rec["sha256"] = hashlib.sha256(open(dl, "rb").read()).hexdigest()
    work = tempfile.mkdtemp(prefix="apk_")
    try:
        apks = []
        with zipfile.ZipFile(dl) as z:
            names = z.namelist()
            inner = [n for n in names if n.endswith(".apk")]
            if inner:  # XAPK
                for n in inner:
                    z.extract(n, work); apks.append(os.path.join(work, n))
            else:
                shutil.copy(dl, os.path.join(work, "base.apk")); apks.append(os.path.join(work, "base.apk"))
        base = next((a for a in apks if os.path.basename(a) in ("base.apk", f"{pkg}.apk")), apks[0])
        cert = subprocess.run([APKSIGNER, "verify", "--print-certs", base], capture_output=True, text=True)
        rec["signer"] = [l.split(": ", 1)[1] for l in cert.stdout.splitlines() if "certificate DN" in l or "SHA-256 digest" in l]
        rec["verify_ok"] = cert.returncode == 0
        urls, doms = set(), set()
        for a in apks:
            d = os.path.join(work, "x_" + os.path.basename(a))
            try:
                with zipfile.ZipFile(a) as z: z.extractall(d)
            except Exception as e:
                rec.setdefault("unzip_errors", []).append(str(e)[:80]); continue
            for f in all_strings_files(d):
                try: data = open(f, "rb").read()
                except Exception: continue
                # dex/arsc keep strings as MUTF-8/UTF-16; also scan a UTF-16LE-decoded view
                views = [data]
                if f.endswith(".arsc"):
                    views.append(data.decode("utf-16-le", "ignore").encode("utf-8", "ignore"))
                for v in views:
                    urls.update(m.decode().lower() for m in URL_RE.findall(v))
                    doms.update(m.decode().lower() for m in dom.findall(v))
        rec["url_hosts"] = sorted(urls)
        rec["org_domain_hosts"] = sorted(doms)
    finally:
        shutil.rmtree(work, ignore_errors=True)
        if not keep:
            os.remove(dl)
    with open("apk_hosts.jsonl", "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(pkg, "verify_ok=", rec.get("verify_ok"), "url_hosts=", len(rec["url_hosts"]), "org_hosts=", len(rec["org_domain_hosts"]))


if __name__ == "__main__":
    main()
