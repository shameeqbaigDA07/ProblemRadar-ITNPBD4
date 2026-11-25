# Problem Radar development log

A factual record of each development session: what was asked, what the AI
(Claude) produced, what was decided, what went wrong and how it was tested.
It is evidence for the assignment report, not the report itself. The report
and all reflections must be written by the student (AIAS level 4).

Fields marked **(student to complete)** are left blank on purpose. Only the
student can say what they changed and learned.

## Session summary

| # | Date | SDLC stage | Mode | Outcome |
| --- | --- | --- | --- | --- |
| 1 | 16 Nov 2026 | Requirements, design | Learning + creating | MVP plan written; free APIs researched |
| 2 | 16 Nov 2026 | Requirements (build brief), design | Creating | Build brief agreed; staged plan proposed; first files drafted |
| 3 | 17 Nov 2026 | Implementation, testing | Creating | Complete app built; automated tests written and run in Claude's workspace |
| 4 | 17 Nov 2026 | Deployment, testing on Windows, live runs | Creating + validation | Ran on the student's PC; 5 live failures fixed; first ranked results |
| 4b–4d | 17 Nov 2026 | Implementation, validation | Creating + validation | Conclusion added; printed report reviewed; quote, market-size and speed fixes |
| 4e–4f | 23 Nov 2026 | Validation, implementation | Validation + creating | Live checks; Groq backup; external Codex review and fixes |
| 4g | 23 Nov 2026 | Implementation, testing | Creating | 5-page brief; 188 tests passed on Windows |
| 5 | — | Validation, evaluation | — | **Student to complete** (validation sheet, test cases) |

---

## Session 1: 16 Nov 2026, planning

- **Objective:** choose a project and plan a minimum viable product (MVP).
- **SDLC stage:** requirements and design.
- **Frameworks:** SDLC for the overall structure; Computational Thinking for the design (decomposition into four steps).
- **Mode:** learning (understanding what was feasible on free tools) and creating (the plan).
- **AI prompts:** Prompts 1 and 2 in `docs/prompts/01_planning_prompts.md`.

**What the AI did**

1. Recommended a software project and suggested separating learning stages (AI as tutor) from creating stages (AI as pair programmer).
2. Ran 4 web searches to check which free services worked in November 2026.
3. Wrote the MVP plan (the "MVP plan" PDF / shared document): intake questions, results design, architecture, scoring formula, sprints, validation plan, risks.

**Research findings the plan relied on** (from secondary sources; to be re-checked)

- Reddit closed unauthenticated `.json` access in May 2026, so Reddit was not used as a direct source.
- A Google forum answer said Gemini's built-in Google Search grounding is not in the Gemini 3 free tier, so a separate search API (Tavily) was chosen.
- Tavily offers 1,000 free credits a month; the Hacker News Algolia API is free with no key.

**Design decisions**

| Decision | Options considered | Chosen | Reason |
| --- | --- | --- | --- |
| Web framework | Flask, Streamlit, React + Node | Flask | All Python, but still a real front end / back end split |
| AI model | Gemini, OpenAI, Claude API | Gemini free tier | Free API tier available |
| Web evidence | Gemini search grounding, Tavily, Brave | Tavily | Free, returns page text for quote checking |
| Forum evidence | Reddit API, Hacker News API | Hacker News | Reddit access closed in 2026 |
| Ranking | AI ranks, Python formula | Python formula | Repeatable and testable |
| Storage | Database, JSON files | JSON files | Enough for an MVP; allows offline demo |
| Weights | Equal, weighted | 30/20/20/15/15 | Pain and frequency signal a real problem. An assumption, not evidence |

- **Problems encountered:** two sources gave conflicting Gemini free-tier limits; resolved by not hard-coding limits and pointing to AI Studio.
- **How tested:** not applicable (planning only).
- **What I changed (student to complete):**
- **What I learned (student to complete):**

---

## Session 2: 16 Nov 2026, build brief and staged plan

- **Objective:** turn the MVP plan into a build specification and start the code.
- **SDLC stage:** requirements (detailed brief) and design.
- **Mode:** creating.
- **AI prompts:** a first prompt asked to extend an earlier project (VentureLens AI); it was interrupted and replaced by the build brief in `docs/prompts/02_build_brief.md`.

**What happened**

1. Claude could not see the student's PC at first (the chat was not linked), so it explained this and proposed a 7-stage implementation plan before writing files, as the brief asked.
2. Claude noted that its cloud workspace cannot reach Tavily, Gemini or Hacker News, so live searches can only be tested on the student's PC.
3. Claude drafted `requirements.txt`, `.env.example`, `.gitignore`, `errors.py` and `research.py`.
4. The student chose to link the PC through the Claude desktop app so files could be written directly into the project folder.

- **Problems encountered:** the attached "MVP plan.pdf" was not available to Claude in this chat; Claude worked from the version of the plan it had written in Session 1.
- **How tested:** not yet tested.
- **What I changed (student to complete):**
- **What I learned (student to complete):**

---

## Session 3: 17 Nov 2026, implementation and automated testing

- **Objective:** build the complete MVP described in the build brief.
- **SDLC stage:** implementation and testing.
- **Frameworks:** Computational Thinking (below); SDLC testing stage.
- **Mode:** creating (Claude as pair programmer).
- **AI prompt:** Prompt 3 in `docs/prompts/01_planning_prompts.md`, following the build brief.

**Computational Thinking applied**

| Technique | Where it shows in the code |
| --- | --- |
| Decomposition | Four modules, one per step: `research.py` (gather), `analyse.py` (interpret), `scoring.py` (check and rank), `app.py` + templates (display); `storage.py` for saved runs |
| Pattern recognition | Every source has the same fields (id, title, url, domain, published, text). Every problem has the same fixed JSON shape, so one card template shows them all |
| Abstraction | The pipeline steps are swappable functions (`app.config["GATHER"]` etc.), so tests can replace the internet with fakes |
| Algorithm design | Quote matching after normalising text; union-find grouping for independent sources; the weighted score formula |

**What the AI generated**

- `research.py`: six Tavily queries built from the form answers, one Hacker News search (last two years, no usernames stored), HTML cleaning, URL de-duplication, numbering S1…Sn, and error handling (a bad key or used-up quota stops the run; one failed search or a Hacker News outage only adds a warning).
- `analyse.py`: the Gemini prompt with 11 rules and a fixed JSON shape; one automatic retry if the reply is not valid JSON; checks that reject problems with missing fields or scores outside 1–5; plain-English messages for Gemini errors (quota, unknown model, bad key, server busy).
- `scoring.py`: quote verification; the two-independent-source rule (same website counts once, except separate forum threads; near-copies detected by overlapping 5-word phrases count once); market-size checks (every input must cite a real source; GDP is refused; range must be valid); the score formula; confidence levels.
- `storage.py`: saving runs as JSON, listing them, safe loading (only valid run names, so no other file can be opened).
- `app.py`, templates and CSS: home page with the five questions, loading overlay, results page with the 12 required sections plus method and source list, demo mode, friendly error messages, print / save as PDF.
- Tests: 7 test files (listed below). `README.md` with Windows commands. `docs/validation_sheet.md` for manual checks.

**Decisions made during implementation**

| Decision | Reason |
| --- | --- |
| Default model name `gemini-flash-latest` in `.env` | Google documents this alias as always pointing to the current Flash model, so the app keeps working when model versions change |
| Library versions checked before coding (tavily-python 0.8.5, google-genai 3.3.0) | Claude inspected the installed libraries' function signatures and error classes rather than relying on memory |
| Quotes must be at least 6 words to count as verified | Very short phrases appear by chance in many texts |
| Unverified quotes are shown with a warning, not hidden | Lets the founder (and the marker) see what the AI got wrong |
| Only verified quotes count towards the two-source rule | Stops invented quotes from keeping a weak problem in the ranking |
| Problems removed by the rules are listed under Evidence gaps | Transparency about what was filtered and why |
| Confidence falls one level when under half the quotes verify | The brief asked for weak evidence to reduce confidence |
| Demo mode only replays real saved runs; no invented sample is shipped | The brief forbids fabricated results |
| Commands use `.venv\Scripts\python` directly | Avoids the PowerShell script-activation error common on Windows |

**How it was tested**

- Automated tests run in Claude's Linux workspace (Python 3.13): **98 passed, 0 failed.**

| Test file | What it checks |
| --- | --- |
| `test_scoring.py` | Formula (20, 100 and a hand-calculated 67), invalid scores rejected, confidence levels, market-size acceptance and rejection (no source, GDP, reversed range) |
| `test_quotes.py` | Exact match, case/spacing/curly-quote tolerance, changed words, invented quotes, stitched fragments, short quotes, partial words |
| `test_independence.py` | Same site counts once, copied article counts once, forum threads count separately, problems dropped below 2 sources, unverified quotes not counted, ranking order |
| `test_analyse.py` | Code fences, non-JSON replies, retry once then friendly error, missing fields, bad scores, 7-problem cap, missing key, Gemini error messages |
| `test_research.py` | Six queries, numbering, HTML cleaning, duplicate URLs, missing key, quota and bad-key errors, one failed search, Hacker News outage, no evidence |
| `test_storage.py` | Save/load, newest-first list, damaged files, unsafe file names refused, Unicode |
| `test_app.py` | Form validation, full run with fake APIs, all report sections present, polite errors, no traceback shown, demo mode offline, 404s |

- Visual check: Claude rendered the home page and a results page filled with clearly labelled test data in a headless Chrome and looked at the screenshots. Three layout issues were found and fixed: a misaligned form label, extra space above the Evidence gaps heading, and stray brackets around source links in micro-trends.

**Problems encountered**

- All 98 tests passed on the first run, so no code defects were found by the tests in this session. This means the tests have not yet caught a real bug; the live run in Session 4 is the first real-world check.
- The app has **not** yet run on Windows or with real API keys. Live research, real Gemini replies and real quote-verification rates are untested.

- **What I changed (student to complete):**
- **What I learned (student to complete):**

---

## Session 3b: 17 Nov 2026, making setup possible without the terminal

- **Objective:** let the student run the app without typing terminal commands.
- **SDLC stage:** deployment.
- **Mode:** creating.
- **AI prompts (verbatim):** "i cant locate the file can u pls add the file on desktop that would be better", then "i cant not even cmd so can you plss locate it or do it on desktop".

**Problem encountered:** the student could not find the project folder and could
not use the command prompt, so the terminal-based setup in the README was not
usable. This is a real usability finding: the first design assumed a user who
can type commands.

**What the AI did**

1. Added three double-click files: `setup.bat` (finds Python, creates the
   environment, installs libraries, creates `.env` and opens it in Notepad),
   `run_tests.bat` and `start_app.bat`.
2. Changed `app.py` so `start_app.bat` opens the browser automatically
   (`--open` option).
3. Added a "double-click" section at the top of the README.
4. Used computer use to put a shortcut to the project folder on the Desktop.

- **How tested:** automated tests re-run in Claude's workspace after the
  `app.py` change. The `.bat` files have **not** yet been run on Windows.
- **What I changed (student to complete):**
- **What I learned (student to complete):**

---

## Session 4: Windows setup and first live run (in progress)

- **Date:** 17 Nov 2026
- **SDLC stage:** deployment and testing.
- **What happened so far:**
    1. The student ran `setup.bat`; the `.venv` folder was created and the
       app started in the browser with `start_app.bat`. The home page
       rendered as designed (screenshot sent in the chat).
    2. The student asked Claude to fill in the form as a founder. Claude
       suggested: sector "small independent home care (domiciliary care)
       agencies", UK, Businesses, an MSc / software-builder founder advantage,
       and exclusions (medical devices, hardware, clinical diagnosis, NHS
       procurement).
    3. Clicking Run research showed: "TAVILY_API_KEY is missing. Add it to
       your .env file (see README step 4), then restart the app."
- **Cause:** the `.env` file was still identical to the blank template (same
  size and timestamp), so the keys had not been saved. Claude checked only
  the file's size and date, not its contents.
- **What this shows:** the missing-key check worked on a real machine: the
  app stopped before using any API and gave a plain-English instruction
  instead of crashing.
- **Fix:** added `edit_keys.bat`, which opens `.env` in Notepad with
  step-by-step instructions.
    4. After the keys were saved (`.env` grew from 591 to 698 bytes), the
       second attempt at 19:39 showed "Something unexpected went wrong". The
       terminal showed: `ImportError: DLL load failed while importing
       _tiktoken: An Application Control policy has blocked this file.`

- **Second problem: Windows blocked a library file.** The `tavily-python`
  library imports `tiktoken`, which contains a compiled file (`.pyd`).
  Windows Application Control (Smart App Control) on the student's PC
  refused to load it. This could not have been caught by the automated
  tests, which ran on Linux with fake APIs: it only appeared on the real
  target machine.
- **Design change (made by Claude):** removed both vendor libraries
  (`tavily-python` and `google-genai`) and called both services' web APIs
  directly with `requests`, which already worked on the PC:
    - Tavily: `POST https://api.tavily.com/search` with an
      `Authorization: Bearer` header; 401 = bad key, 432/433 = credits used up.
    - Gemini: `POST .../v1beta/models/{model}:generateContent` with an
      `x-goog-api-key` header and `responseMimeType: application/json`.
    - `google-genai` was removed too as a precaution: it depends on
      `pydantic-core`, another compiled library that the same policy might block.
  `requirements.txt` went from 6 libraries to 4.
- **Tests added:** 13 new tests for the direct connections (correct headers
  and URLs, 401/432/433/429/404/400/500/503 responses, timeouts, offline,
  blocked replies). **111 passed** in Claude's workspace, and again in a
  fresh environment with only the 4 listed libraries installed, which
  confirms that none of the removed libraries is still needed.
- **Side finding:** Gemini keys created in AI Studio now start with `AQ.`
  (new "auth key" format), not `AIza`. Claude first told the student the
  `AQ.` key looked wrong; a web search showed this was outdated, and Claude
  corrected itself. Example of AI knowledge going out of date.
- **Security note:** the student pasted a Gemini key into the chat. Claude
  declined to write it into the file and advised deleting that key and
  creating a new one.
- **Third attempt (19:47):** the six Tavily searches and the Hacker News
  search now completed, which confirms the direct Tavily connection works
  live. Gemini then answered HTTP 404: the model name `gemini-flash-latest`
  was not recognised for this key. The app showed its prepared message
  ("Gemini could not find the model named in GEMINI_MODEL...").
- **Design change (made by Claude):** instead of asking a beginner to find
  and copy model names, the app now handles this itself. On a 404 it calls
  Google's `models.list` endpoint (`GET /v1beta/models`), keeps Flash
  models that support `generateContent`, ranks them (full Flash before
  Lite, stable before preview, newest first), tries up to three, and
  remembers the one that works. The chosen model is written to the
  terminal and saved with each run.
- **Tests added:** model ranking, a failed model list, switching to a
  working model, and the message when no alternative exists.
  **115 passed** in Claude's workspace and in a clean environment.
- **Lesson for the reflection (student to interpret):** a model name
  chosen from documentation still failed on a real account. Hard-coded AI
  model names are fragile; asking the service what is available is more robust.
- **Fourth attempt (about 19:55):** research and model selection worked,
  but the page showed "Gemini took too long to answer" (the app's 180-second
  limit was reached).
- **Cause (Claude's assessment):** Google's documentation says Gemini 3
  models think at "high" by default unless told otherwise; with about 40
  sources of up to 1,500 characters each and a long JSON answer, the reply
  took over 3 minutes.
- **Changes (made by Claude):**
    - `thinkingConfig: {"thinkingLevel": "low"}` sent with each request,
      with an automatic retry without it if a model rejects the setting;
    - the prompt now sends at most 30 sources, picked in turn from each
      search so every evidence type is kept, and 1,000 characters each
      instead of 1,500;
    - a new prompt rule asks for concise fields (under 35 words, at most 3
      quotes / touchpoints / trends / alternatives per problem);
    - time limit raised to 5 minutes; each Gemini call's duration is now
      written to the terminal; loading message changed to "2–3 minutes".
- **Trade-off to note:** less text per source means quotes can only come
  from the first 1,000 characters Gemini sees, and fewer sources are
  analysed. Speed was chosen over coverage for the MVP.
- **Tests:** 4 more (low thinking sent, fallback, timeout message, 30-source
  cap with every search represented). **119 passed.**
- **Fifth attempt (about 19:59):** no timeout this time, but Gemini
  answered with a server error (5xx). The app showed "Gemini is busy or
  unavailable right now". The terminal output was not captured, so the
  exact status code and model are not recorded.
- **Change (made by Claude):** temporary server errors (500/503/504) are now
  retried on the same model after 5 and 15 seconds. If the model still
  fails, or is not found (404) or out of free quota (429), the app tries up
  to three other Flash models from Google's model list. The busy message
  now says that retries were already made.
- **Tests:** 4 more (retry after waiting, switch when still overloaded,
  switch on quota without waiting, everything overloaded). **123 passed.**
- **Pattern for the reflection (student to interpret):** five attempts, five
  different failures, each found only on the real machine and real
  services: missing key, blocked library, unknown model name, slow reply,
  overloaded service. None was caught by the automated tests, which used
  fake services.
- **Sixth attempt (20:08):** the terminal showed "Collected 23 sources" at
  20:08:32 (searches took about 27 seconds), then nothing for over 4
  minutes. The browser just showed the loading screen. The student reported
  "it's very slow, it is not responding".
- **Root cause found (Claude's own error):** Claude had set Gemini's
  `temperature` to 0.2, a habit from older models. Google's Gemini 3 guide
  strongly recommends keeping the default of 1.0 and warns that lower values
  can cause looping. A looping reply keeps writing until its length limit,
  which fits the very long wait. This is a clear case of the AI applying
  outdated knowledge; it was found by searching the current documentation
  after the failure, not before.
- **Changes (made by Claude):**
    - removed the temperature setting; added `maxOutputTokens: 16384` so a
      runaway reply is cut off rather than running for minutes;
    - **live progress page:** research now runs in a background thread. The
      browser goes straight to a progress page that checks every 2 seconds
      and lists each step with its time (searching, sources collected,
      waiting for Gemini and which model, retries, model switches,
      checking quotes, report saved), then opens the report by itself.
      This answers the usability problem "it looks frozen".
- **Tests:** 6 more (no temperature sent, output cap, progress messages,
  progress recorded through a full run, progress page while running,
  the form returns immediately in background mode). **129 passed.**
  The progress page was also checked visually in a headless browser.
- **Seventh attempt (20:17), first full diagnosis from the terminal:**
  searches took 34 seconds (28 sources). Gemini (`gemini-flash-latest`)
  then answered **HTTP 503 after 65 seconds**, again after 1 second on the
  5-second retry, and the 15-second retry was in progress when the student
  asked for "another alternative, this is not working out". So the
  temperature fix let the request run, but Google's main free Flash model
  was overloaded.
- **Options considered (Claude researched current free tiers):**

| Option | Verdict |
| --- | --- |
| Keep retrying the same model | Rejected: each try can take 65 s before failing |
| Gemini Flash-Lite (same key) | Adopted as first fallback: lighter, usually less busy, no new key |
| Groq (fast, free) | Rejected: free plan is about 8,000 tokens a minute, smaller than one prompt (about 10,000) |
| OpenRouter free models | Not chosen: 50 requests a day, quality varies by model |
| Mistral free "Experiment" plan | Adopted as optional backup: 1 request per analysis fits its limit of about 2 a minute; large token allowance |

- **Changes (made by Claude):**
    - only one retry (after 5 s), then switch model, trying Flash-Lite
      models first when Google is overloaded; if the model list cannot be
      fetched, the `gemini-flash-lite-latest` alias is tried;
    - new `ServiceUnavailableError` separates "busy / no quota / unknown
      model" (worth switching service) from real errors such as a wrong key
      (not worth switching);
    - new Mistral connection (`POST api.mistral.ai/v1/chat/completions`,
      JSON mode) and a provider chain: Gemini first, Mistral if a key is
      present; `AI_PROVIDER=mistral` reverses the order. Each saved run
      records which service and model answered;
    - README, `.env.example` and `edit_keys.bat` explain the optional key.
- **Ethics note for the report (student to discuss):** Mistral's free
  plan may train on submitted data unless switched off; Gemini's free tier
  terms differ by region. The prompts contain only public web text and the
  founder's own answers, but this should be considered before real use.
- **Tests:** 4 retry tests rewritten for the new rules (one retry,
  Flash-Lite first); 11 new tests (alias fallback, Mistral request and
  errors, switching, no switching on a wrong key, the tip to add Mistral,
  provider order). **139 passed** in Claude's workspace and in a clean
  environment.
### First complete live run: 17 Nov 2026, 20:17–20:20

Read from the terminal window and the saved run file
`runs/20261117-202042-small-independent-home-care-domiciliary.json`:

| Measure | Result |
| --- | --- |
| Sector | small independent home care (domiciliary care) agencies, UK, Businesses |
| Searches | 6 Tavily searches, 28 sources, about 34 s; 0 Hacker News results |
| Gemini | `gemini-flash-latest` 503 (after 65 s), 503 on retry; `gemini-3.8-flash` 503; `gemini-3.7-flash` 503; `gemini-3.6-flash` answered 200 in 7 s |
| Total time | 184 s |
| Problems proposed by Gemini | 1 ("Unprofitable local authority rates threatening agency margins") |
| Problems kept after checks | **0** (the one problem was dropped: only 1 verified independent source) |

**Diagnosis (Claude, from the saved file):**

1. **Bug in Claude's code:** source excerpts sent to Gemini were cut at
   exactly 1,000 characters, mid-word. Gemini copied a real sentence up to
   the cut, ending in "tighter regul". The quote checker correctly found no
   exact match and marked it unverified, so a problem backed by 2 different
   websites (birdie.care and caresyncexperts.co.uk) was wrongly dropped.
   All 20 words were on the source page.
2. **Thin answer:** Gemini proposed only 1 problem from 28 sources. Likely
   causes: the "low" thinking setting (answered in 7 s) and a prompt rule
   that over-emphasised leaving problems out.
3. **Hacker News found nothing** for the long sector name, because Algolia
   requires every word to match.

**Fixes:**

- excerpts now end on a whole word, followed by "[...]";
- the quote checker accepts a cut-off **final** word only (at least 3
  letters, every earlier word exact); a changed or cut word anywhere else
  still fails;
- the prompt now asks for 3 to 7 distinct problems where the evidence
  allows, and still forbids inventing evidence to reach 3;
- thinking level changed from "low" to Google's balanced "medium";
- Hacker News retries with optional words when the exact search finds nothing.

**Validation of the fix on real data:** re-running Python's checks (not
Gemini) on the saved run with the fixed checker keeps the problem: 2
independent sources, 2 of 2 quotes verified, score 80, Low confidence.
The saved file itself was left unchanged as the record of what happened.

**Tests:** 8 new, including regression tests built from the live quote.
**147 passed.**

### Problem found: some updates had not reached the PC (17 Nov, 20:30)

When Claude compared file sizes on the PC with its own copies, several files
were older versions (for example `app.py` 6,516 bytes on the PC against
9,183 bytes in Claude's copy; `requirements.txt` still listed the removed
libraries). The file transfer had reported every write as successful.
This explains why the 20:17 run had no progress page and used the old
retry timings. **Fix:** the whole project was re-sent from a fresh folder
and every file size was checked against Claude's copy. All matched.
**Lesson:** "the tool says it worked" is not verification; checking the
result independently (here, file sizes) is.

### Automated tests on Windows (17 Nov, 20:31)

Run by double-clicking `run_tests.bat` on the student's PC:
**147 passed in 0.41 s** (Windows, Python 3.14.5, pytest 9.2.0).

### First successful live run with ranked results (17 Nov, 20:32)

Claude, with the student's permission, started the app and filled in the
form in the Claude desktop app's built-in browser. Facts from the progress
page and the saved file `runs/20261117-203259-small-independent-home-care-domiciliary.json`:

| Measure | Result |
| --- | --- |
| Total time | 41 s |
| Sources | 38 (28 Tavily, 10 Hacker News: the optional-words fallback worked) |
| Gemini | `gemini-flash-latest` 503, 503 on retry; `gemini-3.5-flash-lite` failed; `gemini-3.1-flash-lite` answered |
| Problems proposed | 2 (none rejected by the format check) |
| Problems kept | 2 of 2 (every quote verified: 4 of 4) |
| #1 | CQC Inspection Readiness Gap: 83.0 (severity 5, frequency 4, market 4, WTP 4, gap 3); sources caresyncexperts.co.uk, cqcask.co.uk |
| #2 | Enquiry-to-Client Conversion Bottleneck: 67.0 (4, 3, 4, 3, 2); sources caresyncexperts.co.uk, birdie.care |
| Confidence | Low for both (2 independent sources each) |
| Market size | Not estimated for either: the sources lacked the inputs. The app said so rather than inventing a figure |

**Honest limitations of this result:**

- Only 2 problems, below the 3–7 the brief asks for. The answer came from
  a Flash-Lite model, because the full Flash models were overloaded.
- Both problems share one source (caresyncexperts.co.uk), which is a care
  consultancy with a commercial interest. Independence holds between the
  pairs, but source quality has not been judged.
- No manual validation has been done yet. The scores are the AI's
  judgement combined by Python, and have not been checked against reality.

- **Still to record:** the manual validation sheet (10-quote audit,
  known-sector test, market-size check, repeat run), and a second run of the
  same sector for the consistency check. (run ID, time taken, number of sources, problems kept and
  dropped), and any further errors.
- **What I changed (student to complete):**
- **What I learned (student to complete):**

## Session 4b: 17 Nov 2026, adding a final conclusion

- **AI prompt (verbatim):** "is this website running smoothly i think want
  add i last conlusion or summary that tells final result"
- **SDLC stage / mode:** implementation (a new requirement from use), creating.
- **Design decision:** the conclusion is written by **Python from the checked
  results** (`summary.py`), not by asking Gemini for another piece of text.
  Reasons: it cannot contradict the ranking or scores, it adds no
  unverified claims, it costs no extra AI call (so is unaffected by Gemini
  being busy), and it works for runs saved before the feature existed
  because it is built when the report is shown.
- **What it says:** a verdict (strong / worth testing / promising but thin
  / weak / none ready), what was searched and how many problems survived
  the checks, the top problem with its score, confidence, strongest and
  weakest factor, the other options, whether market size could be
  estimated, the riskiest assumption (labelled as Gemini's), and a
  recommended next step taken from the two-week experiment, including when
  to stop and move to problem #2. A caveat says the conclusion was written
  by the app and not reviewed by a person.
- **Verdict rule (an assumption, like the weights):** score of 75 or more
  with Medium/High confidence = strong; 65 or more with Medium/High = worth
  testing; 65 or more with Low confidence = promising but thin; below 65 = weak.
- **Result on the real 20:32 run:** "Promising, but the evidence is thin:
  test it cheaply before committing", because the top score was 83 but
  confidence was Low (2 sources).
- **Tests:** 7 new in `tests/test_summary.py`, plus the full-page test now
  checks the section appears. **154 passed.**
- **What I changed (student to complete):**
- **What I learned (student to complete):**

## Session 4c: 17 Nov 2026, analysing the printed report

- **AI prompt (verbatim):** "analysis the output is we ready to prepare the
  report after this and give me samples that i can test" (with the PDF of
  run `20261117-204253`).
- **Mode:** validation (Claude reviewing the output against the saved data).

**Run 20261117-204253 facts:** 41 s, 38 sources (28 Tavily, 10 Hacker News),
answered by `gemini-3.5-flash-lite`, 3 problems proposed and 3 kept, 6 of 6
quotes verified, all Low confidence, no market size estimated.

**What the review found:**

1. **Unrelated Hacker News sources.** All 10 HN threads (Splunk onboarding,
   Treasury yields, green cards, Alibaba, etc.) came from the
   "optional words" fallback Claude added at 20:29. They took prompt space
   and one of them supported problem #3.
2. **Right topic, wrong country.** The HN quote used for problem #3 ("The
   admin we have to fund is absolutely ridiculous and wasteful.") was first
   assumed to be off-topic. Checking the full text showed the writer says
   they "own home health care agencies in 14 states", so it is about home
   care, but in the **US**, not the UK. Lesson: **a verified quote proves
   the words exist, not that they support the claim in this market.**
3. **One quote reused.** The same S1 sentence (caresyncexperts.co.uk) was
   used for problems #1 and #2. It is general marketing text from a
   consultancy, and many sources are vendors or consultancies with a
   commercial interest.
4. **Unsourced score reasons.** 10 of the 15 factor reasons cite no source
   ID, despite the prompt rule asking for one.
5. **Unstable ranking.** Compared with run 203259, one problem (CQC
   evidence) appears in both top threes; the #1 problem changed. Different
   Flash-Lite models answered each time.
6. **Print layout.** The sources table was cut off at the right edge of the PDF.

**Changes (made by Claude):**

- Hacker News fallback removed (exact search only).
- Prompt rules added: quote only sources about this sector; name the
  country when a source is about a different market; use each quote for one
  problem only.
- Score reasons without a source ID are now labelled **No source cited** in
  the breakdown table.
- Print stylesheet fixes the sources table width.
- `docs/test_cases.md` added: 5 behaviour tests and 7 ready-to-paste samples.
- **Tests:** 3 new or changed; **156 passed.**

**Not fixable in code, and left for the validation sheet:** whether vendor
or consultancy sources should be trusted, and whether the problems are real.
Both need human judgement.

## Session 4d: 17 Nov 2026, "the reply is still slow"

- **AI prompt (verbatim):** "the thing still the reply is slow"
- **Diagnosis from the live job (read from the app's status page):**
  32 sources collected in 21 s, then `gemini-flash-latest` gave **no answer
  for over 3 minutes**. In the two successful runs, Flash-Lite models
  answered in seconds and their answers passed the same Python checks.
  The black window was also flooded with a status-check line every
  2 seconds, which hid the real progress messages.
- **Design decision (trade-off):** speed and reliability over model depth.
  The fast `gemini-flash-lite-latest` is now tried first; the configured
  model (`gemini-flash-latest`) is the fallback. `AI_SPEED=quality` in
  `.env` reverses the order. Quality is protected by the same evidence
  rules whichever model answers.
- **Changes:**
    - per-model time limit cut from 300 s to **90 s**; a model that does not
      answer in time is **skipped** for the next one (no same-model retry);
    - a model is never tried twice in one run;
    - status-check lines are hidden from the black window;
    - expected-time messages changed to "usually under a minute".
- **Tests:** 5 new, 1 rewritten. **161 passed.**

**Live test of that change (21:07, sample S3 "small online shops selling on
Shopify", run by Claude in the built-in browser): failed.** From the black window:

| Time | Event |
| --- | --- |
| 21:07:51 → 21:08:07 | 6 searches + HN: 29 sources (16 s) |
| 21:08:09 | `gemini-flash-lite-latest` 503 (2 s); retry after 5 s: 503 |
| 21:08:18 → 21:09:48 | `gemini-flash-latest`: no answer in 90 s, skipped |
| 21:09:51 | `gemini-3.5-flash-lite` 503; app stopped ("Gemini is busy") |

`gemini-3.1-flash-lite`, which had worked at 20:32, was never tried.
**Cause:** Google's free service was heavily loaded, and Claude's ordering
put the slow full model before the remaining Lite models and allowed only 2
alternatives.

**Second change:**

- when Gemini is busy, **every Lite model is tried before any full model**
  (busy Lite models answer in about 2 s, so this is cheap); full models last;
- up to 5 alternatives instead of 2;
- a **200-second time budget**: no new model is started after that;
- if everything was busy, **one last try of the first model after 15 s**.
- **Tests:** 4 new (including one that replays the 21:08 sequence and
  checks `gemini-3.1-flash-lite` is now reached without touching the slow
  model), 2 updated. **165 passed.**
- **Honest limit:** if Google's free models are all overloaded, no code
  change can make them answer. The app now fails within about 3.5 minutes
  instead of 5+, and says why.

**Live test after the second change (21:11, same sample S3): succeeded in
27 s** (`gemini-flash-lite-latest` answered first time). 29 sources (27 Tavily,
2 Hacker News), 2 problems kept, 4 of 4 quotes verified, both Low confidence.

**New problem found in that report:** problem #2 showed a market size of
**USD 48.1bn to 100bn**. The saved file showed the "range" was the whole
Shopify market's 2025 value and its 2035 forecast from one market-research
page (S6, wiseguyreports.com), with the "formula" "Total Shopify Market
Valuation range from 2025 to 2035". Both numbers really are on that page,
so every existing check passed: sourced inputs, no GDP, low below high.
**The checks tested the form of the estimate, not its meaning.**

**Change:** a market size is now accepted only if it is **bottom-up**: the
formula must multiply at least two inputs (customers x spend), and each
input's number must be found in its cited source (scale words handled, for
example "USD 48.1 Billion" = 48,100,000,000). The prompt now asks for this
explicitly and forbids industry valuations and forecasts. Re-checking the
saved Shopify run with the new rule rejects the estimate with that reason.
**Tests:** 4 new, 2 updated. **168 passed.**

## Session 4e: 23 Nov 2026, live check by Claude acting as a founder

**Run attempted (15:07, sample S1, international students' accommodation,
UK, Consumers):** searches took 8 s (23 sources). Every Gemini model then
answered **503 overloaded** within 1–3 s each (`gemini-flash-lite-latest`
twice, `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`,
`gemini-3.1-flash-lite-preview`, `gemini-flash-latest`);
`gemini-2.5-flash-lite` answered 404 (retired by Google). After the 15 s last
try, the app stopped at 41 s with the "Gemini is busy" message. **The app
behaved as designed; the free service was unavailable.** No report was produced.

**Review of the student's own runs** (groceries in small UK towns,
17 Nov 21:33 and 18 Nov 00:40):

- Mechanics correct: 37 s and 59 s, all quotes verified, every kept problem
  has 2 independent sources, market size honestly "not estimated".
- **Verified but irrelevant evidence:** in run 213312, problem #2 ("B2B
  payment complexity") is supported by a vendor press line, "Ottimate has
  been recognized as a Leader in two IDC MarketScape reports", which says
  nothing about groceries. The checks confirm that quotes exist, not that
  they are relevant, as found on 17 Nov.
- **Generic marketing quotes** (lightspeedhq.com, a YouTube description)
  support several problems across both runs.
- **Input quality affects output:** the "exclude" field contained a request
  ("Find small towns that don't have small groceries shops") rather than
  something to exclude; the founder advantage described a goal rather than
  an advantage; and "Businesses" was chosen as the payer for a shop whose
  customers are residents. The two runs gave different top problems.
- Uncited score reasons are now visible ("No source cited" label): 2 to 3
  of the 5 factors per problem in the 18 Nov run.

**Conclusion for evaluation:** the software works; the AI interpretation
is the weakest part, and judging relevance still needs a person.

**Automated tests on Windows (23 Nov, 15:24):** `run_tests.bat` was
double-clicked in File Explorer: **168 passed in 0.58 s** (Python 3.14.5,
pytest 9.2.0). Screenshot: `docs/test_results_2026-11-23.jpg`.

## Session 4f: 23 Nov 2026, free backup AI service (Groq)

**Why:** Gemini's free service returned 503 "overloaded" for every model
(15:07 and again at about 15:38, when the student's Codex review run also
failed). The student found Mistral's plan unsuitable (paid), so the backup
needed to be free with no card.

**Change:** added `make_groq_generator` in `analyse.py`. Order is now
Gemini → Groq → Mistral (each used only if its key is in `.env`).
Groq models are tried in turn (Llama 4 Scout, Llama 3.3 70B, Llama 4
Maverick), skipping any the key cannot use. Replies are limited to 3,500
tokens because our prompt is about 8,300 tokens (33,348 characters,
measured on the 18 Nov groceries run) and Groq's free plan limits tokens
per minute. The "Gemini is busy" tip now suggests a Groq key.

**Tests:** 7 new tests with fake Groq replies (request shape, model
fallback on 503/413, all busy, bad key, model filtering, switching from
Gemini, provider order). 175 passed locally.

**First live test (16:05):** the student first added an xAI "Grok" key
by mistake (a different, paid company); a new `check_keys.bat` (shows
which keys are set without showing them) found this. With a real Groq
key, Groq accepted the key but answered **404 for all three chosen
models**: Groq had retired them.

**Fix:** the app now asks Groq which models the key can use, prefers a
short list (gpt-oss-120b, llama-3.3-70b, gpt-oss-20b, llama-4-scout) and
otherwise uses any listed chat model (skipping speech and safety models).
Because Groq's free plan allows only about 8,000 tokens a minute, Groq
gets a shorter prompt: at most 18,000 characters, keeping the rules and
taking sources in turns from each search (18 of 30 sources on the
groceries run). If Groq says "too large" (413), it retries once with an
even shorter prompt. Tests: 178 passed.

**Live results with Groq (23 Nov):**
- 16:08 — Groq (openai/gpt-oss-120b) answered in 7 s, so the backup
  worked. But it proposed only 2 problems; one failed the 2-source rule
  and one was rejected for missing scores. Report: "no opportunity is
  ready to test yet".
- To make it think less and answer more, reasoning was set to "low".
  16:10 — it answered in 1 s with **0 problems**: worse. Reverted to
  "medium", raised the reply budget to 3,500 tokens and cut the Groq
  prompt to 16,000 characters to stay under the free limit.
- If a Groq model proposes no problems, the next model (qwen3.8-27b,
  then gpt-oss-20b) is now tried. Report wording now says "the AI"
  instead of "Gemini", because Groq may have answered. Tests: 180 passed.
- **Lesson:** the backup keeps the app working, but the smaller free
  model with a shortened prompt gives thinner analysis than Gemini.

**External review (16:26):** the student had Codex test a fictional UK
vet-clinic brief. Gemini 503, Groq answered, 28 sources, no rankable
problem. Codex rated it 5/10: evidence discipline 8, source relevance 4
(US/global pages, chain reviews, duplicate Trustpilot pages),
consistency 3. Two points were real bugs, fixed:
- **Conflicting counts:** the conclusion said "proposed 1 … 2 removed"
  because problems rejected by the format check were not counted as
  proposed. Now counted (test added).
- **Gaps without evidence:** removed problems now list each quote with
  "Verified" / "Not found in source" and a link to the source (test added).
Not fixed: source relevance (search results still include non-UK pages).
Tests: 182 passed.

## Session 4g: 23 Nov 2026, 5-page brief

**Request:** a well-designed 5-page report of key line items and insights,
communicating clear value in a particular market.

**Approach: insights first, then pages.** `brief.py` first picks 3–4 key
insights from the checked results (top score, how many problems survived,
the strongest and weakest score factor, and market size or, if unknown,
the independent websites behind the top problem). The pages are then built
around them:
1. Verdict, value statement, radar of problems (closer to the centre =
   higher score), key insights.
2. Opportunity landscape: score bars, five-factor bars and a factor
   matrix, removed problems.
3. Lead opportunity: who / when / cost, verified quotes with sources,
   touchpoints.
4. Market size, trends, competition gap, alternatives, runner-up, founder fit.
5. Riskiest assumption, two-week experiment, stop/continue criteria,
   open questions, method.
When nothing survives the checks, the brief says so and gives a
problem-discovery interview plan instead.

Like the conclusion, everything is written by Python from checked data,
not by the AI. Text is trimmed to a word limit so each page stays one page.

**Checks:** rendered the brief for all 10 saved runs with headless Chrome:
every run printed to exactly 5 A4 pages with no overflow. One honesty bug
found while checking: older runs did not store quotes for removed problems,
and the brief wrongly said "no lead had verified evidence"; it now says the
quotes were not saved. Tests: 6 new, 188 passed.

**Test bug found on Windows (17:24):** `run_tests.bat` on the PC gave
1 failed, 187 passed in 9.4 s. The failing test expected "no Gemini key"
to stop the app, but the real `.env` (now with a Groq key) is loaded when
the app is imported, so the test fell through to Groq and made a real
internet call (hence 9 s). Fix: an automatic test fixture removes the
backup AI keys during tests, so no test can reach a real AI service.

## Session 4h: 23 Nov 2026, final checks before submission

- Every project file on the PC was compared with Claude's checked copy:
  all matched.
- `run_tests.bat` on the PC: **188 passed in 0.49 s** (22:34).
- All 14 saved reports and their 5-page briefs opened without errors in
  the running app; an unknown run correctly gave 404.
- **Bug found in the zip maker:** Windows PowerShell's `Compress-Archive`
  wrote paths with backslashes (`ProblemRadar\app.py`), which can unzip
  as wrongly named files on a Mac or Linux machine. The zip maker now uses
  Windows' built-in `tar`, which writes standard paths.
- The new zip was checked by unzipping it on a separate Linux machine: 62
  files, 14 saved runs, no `.env`, no key-like strings, and **188 tests
  passed** from the unzipped copy, so a marker can run it from the zip.

## Session 5: validation and evaluation (to do)

Complete `docs/validation_sheet.md`, then summarise the results here,
including failures and any changes made because of them.

## Entry template

- **Date:**
- **Objective:**
- **SDLC stage / framework / mode (learning or creating):**
- **AI prompt:** (verbatim, or file / screenshot reference)
- **What the AI generated:**
- **What I changed:**
- **Problems encountered:**
- **How I tested the result:**
- **What I learned:**
