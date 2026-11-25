# Problem Radar (ITNPBD4 Applying Generative AI, University of Stirling)

**Proof of process for Shameeq Baig (3608527).**

This repository holds the artifact for my ITNPBD4 assignment. It was built
with AI at **AIAS level 4**: Claude wrote the code, tests and supporting files
from my requirements; Gemini and Groq are the AI models the app calls; Codex
reviewed one app output. I set the requirements, ran and tested the app on my
PC, reported problems and checked the results. The report itself is submitted
separately on Canvas and is not stored here.

Where to look:

| What | File |
|---|---|
| Day-by-day development log (16-23 Nov 2026): prompts, problems, fixes | `development_log.md` |
| Planning and build prompts | `01_planning_prompts.md`, `02_build_brief.md` |
| Test cases and validation sheet | `test_cases.md`, `validation_sheet.md` |
| Screenshot of 188 automated tests passing (23 Nov) | `test_results_2026-11-23_188_passed.jpg` |
| External review of one output (Codex) | `Problem_Radar_review.xlsx` |
| Evidence appendix (prompts and responses) | `Problem Radar evidence appendix.docx` |
| Sample app output, home care run (17 Nov) | `Problem Radar sample output - home care run 17 Nov.pdf` |

Note: the files were uploaded through the GitHub web page, which placed them
all at the top level instead of in their folders (`docs/`, `tests/`,
`templates/`, `static/`). To run the app, use the project zip submitted on
Canvas, which keeps the original folder layout.

This repository was uploaded on 25 Nov 2026, so GitHub shows only that
upload date. The development log is the record of the process over
time. The saved run files (`runs/*.json`) contain text copied from
third-party web pages, so they are kept out of this public repository; they are
in the project zip submitted on Canvas. API keys are never stored here (`.env`
is excluded).

---

## About the app

A local web app that helps startup founders find real business problems in a
sector. It collects public evidence, asks an AI model (Google Gemini, with Groq as backup) to interpret it, checks
every quote against its source in Python, and ranks the problems that survive.

To run it, unzip the project zip from Canvas, double-click `setup.bat` (one time; paste your own free API keys into `.env`),
then `run_tests.bat` and `start_app.bat`. The tests use fake API replies, so they need no internet and no keys.

## How it works

| File | Job |
| --- | --- |
| `app.py` | Web pages and the order of the steps |
| `research.py` | 6 Tavily searches + Hacker News search, numbered S1, S2... |
| `analyse.py` | Prompt to the AI (Gemini, with Groq and Mistral as optional backups), JSON reply, format checks |
| `scoring.py` | Quote verification, two-independent-source rule, market-size checks, score |
| `summary.py` | Final conclusion |
| `brief.py` | Picks the key insights and builds the 5-page brief (`brief.html`, `brief.css`) |
| `storage.py` | Saving and reopening runs |
| `base.html`, `index.html`, `progress.html`, `results.html`, `style.css` | Page layouts and styling |
| `test_*.py`, `conftest.py` | 188 automated tests (pytest) |

Score = 20 x (0.30 severity + 0.20 frequency + 0.20 market + 0.15 willingness
to pay + 0.15 competition gap), each factor 1-5, so totals run 20-100. The
weights are initial assumptions from the MVP plan.
