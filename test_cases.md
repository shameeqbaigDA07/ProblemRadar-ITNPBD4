# Test cases for Problem Radar

Run these in the app and record what happened. Each run uses about 6 of
your 1,000 free Tavily credits a month. Restart the app first
(close the black window, double-click `start_app.bat`) so the latest
version is running.

For every run, note: run time, number of sources, problems kept and
removed, the verdict, any **Unverified** quotes, and anything that looks
wrong (off-topic source, wrong country, the same quote used twice).

## Data already collected (home care, UK, Businesses)

| Run | Model that answered | Problems kept | #1 | #2 | #3 |
| --- | --- | --- | --- | --- | --- |
| 20261117-202042 | gemini-3.6-flash | 0 of 1 (quote-checker bug, fixed) | – | – | – |
| 20261117-203259 | gemini-3.1-flash-lite | 2 of 2 | CQC Inspection Readiness Gap (83) | Enquiry-to-Client Conversion (67) | – |
| 20261117-204253 | gemini-3.5-flash-lite | 3 of 3 | Local authority funding margin pressure (87) | Rigorous CQC inspection and evidence (79) | Fragmented admin systems (78) |

Runs 203259 and 204253 share one problem (CQC evidence preparation) in
their top three; the top problem changed. Different Gemini models
answered each time, because the main model was overloaded.

## A. Behaviour tests

| # | What to do | Expected result | Result (pass/fail + notes) |
| --- | --- | --- | --- |
| T1 | Type `ab` as the sector and click Run research | Red message asking for at least 3 characters; your other answers stay filled in | |
| T2 | Sector `zqxv flurble widgets`, Global, Either | Few or no sources; either "No public evidence" or "No opportunity is ready to test yet". No invented problems | |
| T3 | Turn Wi-Fi off, click **Demo mode** | Newest saved report opens with the Demo mode banner | |
| T4 | Run the home care sample again (below) | Compare its top 3 with the table above (validation sheet, check 4) | |
| T5 | On any report, click **Print or save as PDF** | All 13 sections print; the sources table fits on the page | |

## B. Sector samples (copy into the form)

### S1. A sector you know (use for validation check 2)

- **Sector:** `international students at UK universities looking for private rented accommodation`
- **Market:** UK · **Who would pay:** Consumers
- **Founder advantage:** `I am an international MSc student in the UK and recently went through the accommodation search myself. I can reach other students through university societies and I can build web tools in Python.`
- **Exclude:** `buying property, mortgages`
- **Why:** you can judge from experience whether the problems are real and whether any are missing.

### S2. Business sector where the founder has no industry experience

- **Sector:** `independent veterinary clinics`
- **Market:** UK · **Who would pay:** Businesses
- **Founder advantage:** `Python and Flask developer who can build booking, reminder and admin tools. No veterinary experience.`
- **Exclude:** `medical devices, drug development`
- **Why:** checks that founder fit is honest when experience is missing.

### S3. A tech-friendly sector (Hacker News should contribute)

- **Sector:** `small online shops selling on Shopify`
- **Market:** Global · **Who would pay:** Businesses
- **Founder advantage:** `Python developer who can build integrations, automation scripts and simple dashboards.`
- **Exclude:** `payment processing, warehouse hardware`
- **Why:** Hacker News discusses e-commerce, so forum evidence should be relevant here.

### S4. A regulation-heavy sector in the EU

- **Sector:** `small restaurants and cafes in the EU dealing with food allergen labelling`
- **Market:** EU · **Who would pay:** Businesses
- **Founder advantage:** `I can build simple compliance and checklist web tools. No food industry experience.`
- **Exclude:** `food manufacturing equipment`
- **Why:** tests the regulation search and the EU market setting.

### S5. A consumer problem

- **Sector:** `parents of young children with food allergies`
- **Market:** US · **Who would pay:** Consumers
- **Founder advantage:** `I can build mobile-friendly web apps and use AI to summarise information. I know two families managing allergies.`
- **Exclude:** `medical treatment, diagnosis, prescription medicines`
- **Why:** consumer willingness to pay is usually weaker; watch whether the scores reflect that.

### S6. A deliberately vague sector

- **Sector:** `healthcare`
- **Market:** Global · **Who would pay:** Either
- **Founder advantage:** `Software developer.`
- **Exclude:** (leave empty)
- **Why:** expect broad, generic problems. Compare with S1–S5 to show why the form asks for a specific sector.

### Repeat run for consistency (T4)

- **Sector:** `small independent home care (domiciliary care) agencies`
- **Market:** UK · **Who would pay:** Businesses
- **Founder advantage:** `MSc student in Applying Generative AI with hands-on Python and Flask development skills. I can build and test AI-assisted web tools quickly and cheaply, and I am UK-based with time to interview care agency managers.`
- **Exclude:** `medical devices, hardware, clinical diagnosis, products that need NHS procurement`

## C. Results table

| Sample | Run ID | Time | Sources | Kept / proposed | Verdict | Unverified quotes | Problems you spotted |
| --- | --- | --- | --- | --- | --- | --- | --- |
| S1 | | | | | | | |
| S2 | | | | | | | |
| S3 | | | | | | | |
| S4 | | | | | | | |
| S5 | | | | | | | |
| S6 | | | | | | | |
| Repeat | | | | | | | |
