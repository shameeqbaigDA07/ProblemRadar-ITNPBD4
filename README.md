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
| Day-by-day development log (16-23 Nov 2026): prompts, problems, fixes | `docs/development_log.md` |
| Planning and build prompts | `docs/prompts/` |
| Test cases and validation sheet | `docs/test_cases.md`, `docs/validation_sheet.md` |
| Screenshot of 188 automated tests passing (23 Nov) | `docs/test_results_2026-11-23_188_passed.jpg` |
| External review of one output (Codex) | `docs/Problem_Radar_review.xlsx` |
| Evidence appendix (prompts and responses) | `docs/Problem Radar evidence appendix.docx` |
| Sample app output, home care run (17 Nov) | `docs/Problem Radar sample output - home care run 17 Nov.pdf` |

Note: this repository was uploaded in one go on 25 Nov 2026, so GitHub shows a
single upload date. The development log is the record of the process over
time. The saved run files (`runs/*.json`) contain text copied from
third-party web pages, so they are kept out of this public repository; they are
in the project zip submitted on Canvas. API keys are never stored here (`.env`
is excluded).

---

## About the app

A local web app that helps startup founders find real business problems in a
sector. It collects public evidence, asks Google Gemini to interpret it, checks
every quote against its source in Python, and ranks the problems that survive.

Built for the MSc module *Applying Generative AI*. See `docs/development_log.md`
for how it was developed.

## Easiest way: double-click (no typing)

Open the `ProblemRadar` folder in File Explorer and double-click:

1. **`setup.bat`**: one time only. Installs everything, then opens your `.env`
   file in Notepad so you can paste your two API keys and save.
2. **`run_tests.bat`**: runs the automated tests and shows the result.
3. **`start_app.bat`**: starts the app and opens it in your browser. Keep the
   black window open while you use the app; close it to stop the app.

If Windows shows "Windows protected your PC", click **More info → Run anyway**.
These files only run the commands listed below.

## Set up on Windows using the terminal (one time)

Do these steps in the VS Code terminal (**Terminal → New Terminal**), with the
`ProblemRadar` folder open (**File → Open Folder**).

**1. Check Python is installed**

```
py --version
```

You need Python 3.10 or newer. If the command is not found, install Python
from python.org and tick **"Add python.exe to PATH"** during installation.

**2. Create a private Python environment for this project**

```
py -m venv .venv
```

This makes a `.venv` folder that holds this project's libraries, separate from
anything else on your computer.

**3. Install the libraries**

```
.venv\Scripts\python -m pip install -r requirements.txt
```

**4. Add your API keys**

```
copy .env.example .env
```

Open the new `.env` file in VS Code and paste your keys after the `=` signs:

- `GEMINI_API_KEY`: free from Google AI Studio (aistudio.google.com/apikey)
- `TAVILY_API_KEY`: free from app.tavily.com

Save the file. Never share `.env`, paste it into a chat, or show it in a
screenshot. `.gitignore` keeps it out of any Git upload.

### Recommended: a free backup AI service (Groq)

Google's free Gemini service is sometimes overloaded ("Gemini is busy").
With a free Groq key the app switches to Groq automatically, so you still
get a report.

1. Go to https://console.groq.com and sign up (free, no card needed).
2. Open **API Keys** (https://console.groq.com/keys), click **Create API Key**, and copy it.
3. Double-click `edit_keys.bat` and add this line at the bottom of `.env`:
   `GROQ_API_KEY=your-groq-key`
4. Save, close Notepad, and restart `start_app.bat`.

The report shows which service answered (for example "Groq: meta-llama/llama-4-scout...").
To use Groq first instead of Gemini, also add `AI_PROVIDER=groq`.

### Optional: a third AI service (Mistral)

Google's free Gemini service is sometimes overloaded ("Gemini is busy").
The app then tries lighter Gemini models first. For extra reliability you
can add a free Mistral key; the app switches to Mistral when Gemini cannot answer.

1. Go to https://console.mistral.ai, sign up, and choose the free
   **Experiment** plan (it may ask you to verify your phone number).
2. Open **API Keys**, click **Create new key**, and copy it.
3. Double-click `edit_keys.bat` and add this line at the bottom of `.env`:
   `MISTRAL_API_KEY=your-mistral-key`
4. Save, close Notepad, and restart `start_app.bat`.

To use Mistral first instead of Gemini, also add `AI_PROVIDER=mistral`.
Note: Mistral's free plan may use your requests to train its models unless
you switch this off in its settings.

## The 5-page brief

Every saved report has an **Open 5-page brief** button. It turns the run
into a short A4 brief: the verdict and key insights with a radar of the
problems, the opportunity landscape, the lead opportunity and its verified
evidence, market and competition, and a 14-day test plan. Click **Save as
PDF** (A4, margins none, background graphics on) to share it.

The insights are chosen by Python from the checked results, not written
by the AI, so the brief always agrees with the full report.

## Run the tests

```
.venv\Scripts\python -m pytest
```

These tests use fake API replies, so they need no internet and no keys.

## Start the app

```
.venv\Scripts\python app.py
```

Then open **http://127.0.0.1:5000** in Chrome. To stop the app, click in the
terminal and press **Ctrl+C**.

## Using it

1. Answer the five questions and click **Run research** (about 1–2 minutes,
   about 6 Tavily credits).
2. Every finished analysis is saved in the `runs` folder.
3. **Demo mode** (top right) reopens the newest saved run without internet:
   use it for presentations.
4. **Print or save as PDF** on a report gives a printable copy.

## If something goes wrong

| Message or problem | What to do |
| --- | --- |
| `py` is not recognised | Install Python from python.org with "Add to PATH" ticked, then reopen VS Code |
| TAVILY_API_KEY / GEMINI_API_KEY is missing | Check the file is called exactly `.env` (not `.env.txt`) and the key is after the `=` |
| Gemini could not find the model | Open Google AI Studio, copy the name of a current Flash model, set `GEMINI_MODEL=` in `.env`, restart |
| Free quota used up | Wait (Gemini) or until next month (Tavily); use Demo mode meanwhile |
| Gemini is busy | The app already retried and tried lighter models. Add a free Groq key (above) so the app switches automatically, or try again in a few minutes |
| Port 5000 already in use | Close the other terminal running the app, or restart VS Code |

## How it works

| File | Job |
| --- | --- |
| `app.py` | Web pages and the order of the steps |
| `research.py` | 6 Tavily searches + Hacker News search, numbered S1, S2… |
| `brief.py` | Picks the key insights and builds the 5-page brief (`templates/brief.html`, `static/brief.css`) |
| `analyse.py` | Prompt to the AI (Gemini, with Groq and Mistral as optional backups), JSON reply, format checks |
| `scoring.py` | Quote verification, two-independent-source rule, market-size checks, score |
| `storage.py` | Saving and reopening runs |
| `templates/`, `static/` | Page layouts and styling |
| `tests/` | Automated tests (pytest) |
| `docs/` | Development log and manual validation sheet |

Score = 20 × (0.30 severity + 0.20 frequency + 0.20 market + 0.15 willingness
to pay + 0.15 competition gap), each factor 1–5, so totals run 20–100. The
weights are initial assumptions from the MVP plan.
