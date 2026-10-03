# Harvest Now, Review Later — replication package

Code and data for *Harvest Now, Review Later: Measuring Post-Quantum Protection of Thai Personal Data and What the PDPA Requires* (manuscript, 2026).

The study measures whether the web endpoints of 288 Thai banks, insurers, hospitals, government agencies and regulators, and service hosts referenced by 20 banking and government Android apps, negotiate hybrid post-quantum key exchange (X25519MLKEM768) with a browser-like TLS client. Scans were run from two Thai networks: NT fixed broadband on 26 September 2026 and AIS mobile on 27 September 2026.

## Reproduce the paper's figures

```
python3 recompute.py
```

This prints the headline figures of Sections 4.1–4.5 from the released data, including the server-software breakdown, Wilson intervals and the matched within-organisation comparison. It needs Python 3 and no extra packages.

## Contents

| Path | What it is |
|---|---|
| `scanner/pqscan.go` | Go 1.25 `crypto/tls` scanner. It runs a PQ-only probe, a browser-like probe (X25519MLKEM768, X25519, P-256, P-384) and one `HEAD` request per host. Build with `go build`. `controls.csv` lists the six control hosts. |
| `pipeline/discover.py` | Finds candidate personal-data endpoints by keyword-matching links on each organisation's homepage. |
| `pipeline/analyze.py` | Attributes each host to a TLS-terminating CDN by origin ASN and response headers. It documents the method but cannot be run here, because its raw scan inputs contain withheld hostnames. |
| `pipeline/extract_hosts.py` | Static hostname extraction from Android packages, with signer verification via `apksigner`. |
| `frame/frame.csv` | The sampling frame: 288 organisations with their homepage hosts and the list each came from. |
| `coding/CODEBOOK.md`, `CODEBOOK_TH.md` | Codebook for classifying candidate endpoints (English and Thai). |
| `coding/endpoint_codes.csv` | Codes for the 93 candidate endpoints, assigned by an AI model applying the codebook and spot-checked informally by the first author (see the paper, Section 3.2). |
| `data/web_hosts.csv` | Per-host results for all web hosts at both vantage points. |
| `data/app_aggregates.csv` | Per-app counts of service and content hosts and how many negotiated PQ. |
| `data/app_unique_host_totals.csv` | App-host totals counting each host once, even if several apps reference it. The paper's app figures use this file. |
| `data/popular_hosts.csv` | CrUX-derived popular-host sample: Thailand list, August 2026, top 10,000, `.th` or frame-organisation domains (1,103 unique hosts selected). The file has one row per host reachable on 3 October 2026 (1,040), with CDN attribution and the role and sector codes of two independent AI coders (`coding/AI_CODING_INSTRUCTIONS.md`). Hosts are unweighted. Bank hosts appear as `bank-crux-NN`. |

### Columns of `data/web_hosts.csv`

- `role`: `homepage`, `homepage-redirect`, `public-data` (P), `institutional-data` (I), `b2b`, `staff`, `no-personal-data` or `unclear`. The paper's "personal-data endpoints" are P and I.
- `pq_*`: whether X25519MLKEM768 was negotiated under the browser-like offer.
- `kx_nt`: the group that was negotiated.
- `cdn_nt`: whether the host sits behind a TLS-terminating CDN (Cloudflare, Akamai, Imperva, Fastly or CloudFront).
- `server_family_nt`: server software named in the HTTP `Server` header (nginx, Apache, IIS, other, or not disclosed). Self-reported and unverified.

## What is not released, and why

- **Banks are pseudonymised.** Bank hosts and organisations in `data/` and `coding/` appear as `bank-host-NN` and `bank-NN`, and bank subsectors are blank. Bank apps appear as `banking app A`–`N`.
  - Apps A–G correspond to Banks A–G in the paper. H–N have no counterpart in the paper. One bank has two apps in the sample.
  - The frame lists the banks sampled, because it is needed for replication; it does not link them to results.
  - The key is available to the journal editor on request.
- **Hostnames extracted from apps are not released**, not even for government apps. This avoids publishing internal and test-environment hosts. Only aggregates are given.
- **Application packages (APKs) are not redistributed.**
- **Raw scan logs and the script that merges web and app results are withheld**, because they contain the hostnames above.
- **No personal data was collected.**

## Measurement scope

The metric describes only the connection between a browser-like client and the first TLS endpoint. For hosts behind a CDN, that is the CDN edge; the onward connection from the CDN to the organisation's origin server was not observable. Older clients, and apps built on older TLS libraries, may negotiate classical key exchange even where the server supports the hybrid group.

## Licence

Code is released under the MIT licence (`LICENSE`); data under CC BY 4.0 (`LICENSE-DATA`).
