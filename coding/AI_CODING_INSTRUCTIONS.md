# Coding task: Thai popular hosts (CrUX TH, Aug 2026)

Input: scan/popular/crux_to_code.csv (1,059 rows). For EVERY row, assign `code` and `sector`.
Use only: host name, page_title, final_url, password_field (y = homepage has a password input). Do not fetch or browse any URL. Do not look at any other files in scan/popular (especially crux_scan_*.jsonl or ai_coding/* outputs of other coders).

Question for `code`: does a user enter or see their OWN personal data through this host?
- P: used by the general public / retail customers and involves personal data (customer login, tax filing, rights checking, student registration, e-commerce account/checkout, member accounts)
- I: an organisation is the user, but the data flowing through belong to many members of the public (hospital e-claims, registries where officials enter citizens' data)
- B: business customers (business banking, seller centre)
- S: staff, agents, or internal students/personnel (e-saraban document systems, intranet, HR, agent portals, internal university systems)
- N: no personal data (news, public information, organisation homepage without login on this host)
- X: cannot tell
Edge rules: an organisation homepage whose login button points to ANOTHER host -> N. University student registration (reg.*) -> P; university internal systems (saraban, HR) -> S.

`sector`: gov, bank, insurance, hospital, finance-other, telco, ecommerce, education, transport-logistics, media, other

Output: a CSV with header `no,host,code,sector,confidence` (confidence = high/low), one row per input row, same `no`. Write it to the path given in your prompt. No other edits.
