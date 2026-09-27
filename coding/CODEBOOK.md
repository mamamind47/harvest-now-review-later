# Codebook: is this host a place where the public's personal data flows?

**File to fill in:** `data_bearing_coding_han.csv` (93 rows). Fill in only the `code` column, and `note` when unsure.
**Method:** open `evidence_url` in your normal browser and look at the page.
**Do not** log in, submit a form, or enter any data.

## The question for each row
> "Would an ordinary member of the public enter their own personal data here, or see it here, over this connection?"

## Codes (use exactly one)

| code | use it when | example |
|---|---|---|
| `P` | **Public-facing personal data**: a login for customers/patients/citizens, or a form asking for name, ID card number, phone, address, health, income or policy number | efiling (tax filing), patient registration, checking health-insurance rights with an ID number, buying insurance online, member login |
| `S` | **Staff/agents/vendors**: the users are employees, insurance agents or vendors, not the public | agent.aia.co.th, intranet, HR, vendor registration |
| `I` | **Institutions sending the public's personal data**: the users are organisations (hospitals, clinics), but what flows through is the personal data of large numbers of people | NHSO e-Claim (hospitals claiming for patient care), disease registries clinicians enter patient data into, an insurer's portal for partner hospitals |
| `B` | **Business customers**: corporate banking, B2B portals, where the users are companies and the data is mainly the business's own | Business Banking, BizChannel, vendor registration |
| `N` | **No personal data**: public information only, statistics, lookups where nothing personal is entered, news | tariff lookup, statistics page, public announcements |
| `X` | **Cannot tell**: the page won't load, redirects somewhere unrelated, or it is a login page with no clue who it is for | |

## Tie-breakers
- A login page for the public, even with no form visible yet → `P`
- A system serving both the public and agents (e.g. online insurance sales) → `P` if the public can use it directly
- "Checking rights" / "checking status" that asks for an ID card number or policy number → `P` (the ID card number is personal data)
- The page is dead or errors out → `X`, and write the error in `note`
- **A foreign-branch system that serves customers abroad** (e.g. Bank of America US, Taiwanese, Japanese or Indian portals) → code it as usual, but write `foreign` in `note`. These will be excluded from the Thai figures.
- The same host appears twice (e.g. generali.co.th and www.generali.co.th) → code both rows the same. This is a duplicate in the frame and will be deduplicated later.

## How the codes were produced
The script tags hosts from keywords, which is noisy (vehicle booking and statistics pages got counted), so every candidate was classified against this codebook. The operative codes were assigned by an AI model (Claude, Anthropic) from each candidate's URL, anchor text, and the title and form fields of the fetched page. The first author independently coded a stratified random sample of 30 Thai-facing candidates without seeing the model's codes; agreement (Cohen's κ) and the adjudication of disagreements are reported in the paper.
