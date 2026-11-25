# Build brief (prompt sent on 16 Nov 2026, verbatim)

This was sent as an attached text file. It replaced an earlier prompt about
extending a previous project (VentureLens AI), which was interrupted.

```text

PROJECT: PROBLEM RADAR – COMPLETE MVP DEVELOPMENT

I am starting this project completely from scratch for my MSc Applying Generative AI assignment.

I have attached a document called "MVP plan.pdf". Read and follow this document carefully. It is the main project specification.

IMPORTANT:
Do not use or refer to my previous VentureLens AI project.
This is a completely new project.
The application name is Problem Radar.

MY COMPUTER:
- Windows
- VS Code
- Python 3
- Chrome browser
- Beginner-level programming experience

PROJECT OBJECTIVE

Build a local web application called Problem Radar.

The application should help startup founders discover real business problems and potential startup opportunities across different industries and geographical markets.

A founder enters information about an industry and target market. The application researches public evidence and returns 3–7 ranked business problems worth investigating.

TECHNOLOGY

Follow the MVP plan:

- Python 3
- Flask
- HTML templates
- CSS
- Google Gemini API using a suitable available Flash model
- Tavily Search API
- Hacker News Search API (Algolia)
- Requests
- Python-dotenv
- Pytest

Do not introduce unnecessary frameworks or paid services.

Keep API keys in a .env file. Never expose API keys in the application, screenshots or reports.

APPLICATION INPUT FORM

Create a simple, professional form with these five questions:

1. Which industry or sector do you want to investigate?
2. Which geographical market? UK, EU, US or Global.
3. Who would pay? Businesses, consumers or either.
4. What is your founder advantage? Skills, experience, knowledge or network.
5. What should the research exclude? This question is optional.

The form should be beginner-friendly and easy to use.

RESEARCH ENGINE

Use Tavily to conduct six research searches:

1. Industry problems and challenges.
2. Market size and market information.
3. Customer complaints and reviews.
4. Relevant regulatory changes.
5. Startup funding and industry developments.
6. Forum discussions and practitioner experiences.

Use the Hacker News search API to find relevant discussions.

Collect source titles, URLs, snippets and available page text.

Give every retrieved source a unique ID such as S1, S2, S3.

Do not invent sources, customer opinions, quotations or statistics.

AI ANALYSIS

Send the collected evidence and founder answers to Gemini.

Ask Gemini to identify up to seven genuine business problems.

Each problem should explain:

- Who experiences the problem.
- The situation in which it occurs.
- The consequence of the problem.
- Supporting evidence.
- Customer touchpoints.
- Emerging micro-trends.
- Market-size estimate where supported.
- Founder fit.
- Riskiest assumption.
- Suggested two-week experiment.

Return structured JSON using a fixed schema.

EVIDENCE VALIDATION

Implement the following checks using Python:

1. Verify that quotations appear in the retrieved source text.
2. Mark quotations that cannot be verified as unverified.
3. Normally require at least two independent sources for a problem.
4. Remove problems that do not meet the minimum evidence requirement.
5. Label information generated from the AI's general knowledge as unverified.
6. Do not treat duplicate articles as independent sources.

OPPORTUNITY SCORING

Implement the scoring formula from the MVP plan:

- Problem severity: 30%
- Frequency: 20%
- Market potential: 20%
- Willingness to pay: 15%
- Competition gap: 15%

Each factor should have a score between 1 and 5.

Calculate the final score in Python, on a scale of 20–100.

Show the five individual scores and explain the reasons.

The weights are initial assumptions and should be documented as such.

MARKET SIZE

Show a low-to-high range rather than one unsupported number.

Display the formula, assumptions and confidence level.

If reliable inputs are unavailable, say that the market size cannot yet be estimated.

Do not invent market figures.

RESULTS PAGE

Create a professional results page containing:

1. Top three opportunities.
2. Ranked table of up to seven problems.
3. Individual problem cards.
4. Verified evidence and original source links.
5. Customer touchpoints.
6. Micro-trends.
7. Market-size range and confidence.
8. Opportunity score breakdown.
9. Founder fit.
10. Riskiest assumption.
11. Two-week validation experiment.
12. Evidence gaps.

TWO-WEEK EXPERIMENTS

For each shortlisted problem, recommend a practical experiment.

Include:

- Objective.
- Target participants.
- Steps to perform.
- Success criteria.
- Failure criteria.

For example, a customer interview or landing-page experiment.

Do not claim that an experiment has been completed when it has only been recommended.

USER INTERFACE

Build a clean, modern and responsive interface.

Use a simple design that works well in Chrome.

Include:

- Homepage.
- Founder input form.
- Loading message while research is running.
- Results page.
- Friendly error messages.
- Saved research runs.
- Demo mode.

SAVED RUNS AND DEMO MODE

Save each completed analysis as a JSON file inside a runs folder.

Allow the user to open an earlier saved result without internet access.

This is important for demonstrating the application reliably.

PROJECT STRUCTURE

Use a clear structure similar to the MVP plan:

ProblemRadar/
    app.py
    research.py
    analyse.py
    scoring.py
    templates/
        index.html
        results.html
    static/
        style.css
    runs/
    tests/
        test_scoring.py
    docs/
        development_log.md
    .env
    .gitignore
    requirements.txt
    README.md

DEVELOPMENT FRAMEWORKS FOR MY UNIVERSITY ASSIGNMENT

Organise the development around:

1. Software Development Life Cycle (SDLC):
   Requirements, design, implementation, testing, deployment and evaluation.

2. Computational Thinking:
   Decomposition, pattern recognition, abstraction and algorithm design.

3. Feynman's Method:
   Help me understand technical concepts by explaining them simply and asking me to explain them back.

Clearly separate learning activities from creating activities.

DEVELOPMENT LOG

Create docs/development_log.md.

Record actual development sessions, including:

- Date.
- Objective.
- Framework used.
- AI prompt.
- What AI generated.
- What I changed.
- Problems encountered.
- How I tested the result.
- What I learned.

Do not fabricate previous work or claim that unperformed tests passed.

TESTING AND VALIDATION

Create automated tests for:

- Scoring formula.
- Quote verification.
- Two-independent-source rule.
- Missing or invalid AI responses.
- API errors.
- Saved research runs.

Also prepare a manual validation sheet for:

- Checking ten quotations against original sources.
- Testing a sector I understand.
- Checking three market-size estimates against published reports.
- Running the same sector twice and comparing results.

Show actual pass and fail results.

BUILDING INSTRUCTIONS

I am a beginner, so:

1. Inspect the empty project folder.
2. Explain the setup in simple English.
3. Create the project files in the correct folder.
4. Give me the exact Windows terminal commands.
5. Help me install dependencies.
6. Explain where API keys must be entered without asking me to share them.
7. Start the Flask application.
8. Tell me how to open it in Chrome.
9. Test each feature before moving forward.

Do not overwhelm me with unrelated explanations.

If you cannot complete everything in one development session, divide the work into clear stages and tell me what is completed and what remains.

FINAL REQUIREMENT

The final application must be a functioning local MVP, not just a visual mock-up.

It must collect actual public evidence, analyse it, validate quotations, calculate scores in Python, rank opportunities and produce useful research results.

Start by reading the MVP plan and inspecting the project folder. Then give me the implementation plan before creating the files.

```
