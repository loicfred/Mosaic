# Mosaic — Requirements & Plan

Hackathon project for Challenge 3, *Turning Financial Data into Opportunity*: help a small-business owner spot
when an apparently positive result hides deterioration elsewhere, inspect the evidence, and explore the next
step. Guidelines for working on the code are in `.claude/CLAUDE.md` (shared with Codex as `AGENTS.md`); the
session history is in `docs/worklog/`.

## Actors

| Actor | Role |
| --- | --- |
| Business owner | Reads the findings, opens the evidence, tries a scenario, asks the assistant. The only user of the site. |
| Analytics API (`AI/`, Python FastAPI) | Loads the Olist dataset, computes every figure, trains and serves the forecast and risk models. |
| Website (`Java/OpportunityApp`, Spring Boot) | Shows the figures, writes the scenario summary and runs the assistant through the local model. |
| Local language model (LM Studio) | Writes prose from figures it is given. Never a source of numbers. |

## Scope

- One dataset: Olist Brazilian e-commerce, January 2017 to August 2018, amounts in BRL (gross item sales).
- One local, single-user demo. No accounts, no payments, no bank or ERP integration, no autonomous actions.
- Out of scope: other datasets merged with Olist, personal finance, chat-to-SQL, training a language model.

## Functional Requirements

| Code | Requirement | Where |
| --- | --- | --- |
| FR-1 | Show monthly sales and orders for the analysed range, with the records left out and why. | `AI/app/api/get_sales_history.py`; `Java/OpportunityApp/.../templates/fragments/index/sales.html` |
| FR-2 | Forecast the next months of sales with a range, and compare the model honestly against simple rules. | `AI/app/forecast/`; `fragments/index/sales.html` |
| FR-3 | Flag categories falling well behind the whole business, and categories whose latest month is unusual. | `AI/app/analysis/categories.py`; `categories.html` |
| FR-4 | For a flagged category, show the rule, its inputs, its threshold and the monthly series. | `category.html`, `fragments/category/evidence.html` |
| FR-5 | Show late-delivery and low-review rates, how they go together, the riskiest open orders and the least reliable sellers. | `AI/app/api/get_delivery_summary.py` and the other `get_delivery_*`/`get_review*`/`get_unreviewed_orders.py` routes; `risk.html` |
| FR-6 | Run a hypothetical sales change and show its effect on orders, late deliveries, low reviews and seller capacity, with its assumptions and limitations. | `AI/app/analysis/impact.py`; `scenario.html` |
| FR-7 | Summarise a scenario in plain language; fall back to a fixed template when the model is off, fails, or uses a figure not in the evidence. | `service/ai/ScenarioNarrator.java` |
| FR-8 | Answer questions about the data in a chat box on every page, using only read-only tools, and withhold an answer that uses a figure not in the tools' replies. | `service/ai/Assistant.java`, `service/ai/MosaicToolbox.java` |
| FR-9 | Start the analytics API with the website and stop it with it. | `service/PythonApiLauncher.java` |
| FR-10 | Keep the Olist records in the website's own database and compute every API figure from that database's CSV export. | `Java/OpportunityApp/.../data/BusinessDatabase.java`, `entity/` |
| FR-11 | Under the sales forecast, three buttons: show the forecast's evidence; suggest where to invest when the forecast rises (growing categories labelled by growth, size, late-delivery and low-review levels against explicit thresholds); and list the hidden problems behind the result from deterministic checks. Both written answers fall back to fixed text when the model is off, slow, or uses a figure not in the evidence. | `AI/app/analysis/opportunities.py`, `AI/app/analysis/caveats.py`; `service/ai/InvestmentAdvisor.java`, `CaveatWriter.java`, `CheckedWriter.java`; `controller/api/OverviewAiController.java`; `fragments/index/sales.html` |

## Non-Functional Requirements

| Code | Requirement |
| --- | --- |
| NFR-1 | The Python API is the only source of figures; the website formats them and never recomputes them. |
| NFR-2 | Every page renders when the API, a model or the language model is unavailable, saying what is missing and how to fix it. |
| NFR-3 | Observed data, model predictions and hypothetical scenarios are visually distinct on every page. |
| NFR-4 | No claim of causation, profit, cash or guaranteed outcome anywhere in the product. |
| NFR-5 | Only aggregated figures reach the language model for the summary; the assistant's tools reach only the API. |
| NFR-6 | One LLM client: every model call uses the Java AI manager configured in `Java/OpportunityApp/config/ai/agents.json`. |
| NFR-7 | The demo needs no internet: Bootstrap and Chart.js are served from WebJars, the model is local. |

## Outstanding work

The running list of what is left. **Update it in the same pass as the job it covers** — add an item the
moment it appears, strike it the moment it is done. Finished items move to `docs/worklog` and are removed
from here, never left standing as done.

### Website
- Decide whether first-start import from `mosaic.data.source-dir` remains part of `BusinessDatabase`, or the website should assume an already populated database. The import currently fills empty Olist tables from the original CSVs.
- Run a packaged JAR outside the repository with a configured Python interpreter and installed packages. `mosaic-python.zip` is now rebuilt from `AI/app` on every OpportunityImpl Maven build (antrun, `generate-resources`) as well as by the Claude `Stop` hook, but packaged startup and automatic model training on the database export remain untested. A `.py` file deleted from `AI/app` stays in the zip until another file changes.
- Sign-in: finish a real Google sign-in in a browser on port 8080 (only the redirect to Google was checked), and send one real password-reset email; the link and new-password form were checked without the email.
- One more Chrome pass over every page (desktop and phone width) after the module split and the business database, with the site restarted on the database export: the Mosaic palette and Help page were checked in Chrome on 23 Sep 2026 before the split. Both Java suites and the Help page render test pass after the split.
- AI provider for the demo: Groq (`GROQ_API_KEY`) answers in seconds, but its free tier allows 8,000 tokens a minute on `openai/gpt-oss-120b`, about four chat questions. Decide whether to try a model with a larger allowance, and rehearse at a pace that stays under the limit. LM Studio remains the fallback without the variable. Still unchecked live: the assistant's withheld answer, "New" and the provider stopped.
- The assistant sometimes ends with a page link named after a tool (`/investmentOpportunities`, `/salesOverview`); the tools' "Page: /" hint should name the real page.
- Check the 3.4 reais-per-dollar rate in `Formatter.BRL_PER_USD` against a published 2017–2018 average before the pitch, and decide whether the chart axes should also show dollars.
- Open the simplified overview in Chrome after restarting the site: the three buttons, their loading state, a Groq-written advice and caveat text, and phone width.
- Rotate the Groq key after the hackathon; it was pasted into a chat session.
- Check the sidebar opening and the chat box on a real phone-width browser; the headless screenshots could not click.

### Team setup
- Commit the artifactId rename in this repository's Java modules.
