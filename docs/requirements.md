# Mosaic — Requirements & Plan

Hackathon project for Challenge 3, *Turning Financial Data into Opportunity*: help a small-business owner spot
when an apparently positive result hides deterioration elsewhere, inspect the evidence, and explore the next
step. Guidelines for working on the code are in `.claude/CLAUDE.md` (shared with Codex as `AGENTS.md`); the
session history is in `docs/worklog/`.

## Actors

| Actor | Role |
| --- | --- |
| Business owner | Reads the findings, opens the evidence, tries a scenario, reads the suggestion and caveats with their charts. The only user of the site. |
| Analytics API (`Java/OpportunityApp/config/py/mosaic/`, Python FastAPI) | Loads the Olist dataset, computes every figure, trains and serves the forecast and risk models. |
| Website (`Java/OpportunityApp`, Spring Boot) | Shows the figures, writes the scenario summary, the investment suggestion and the caveats through the local model. |
| Local language model (LM Studio) | Writes prose from figures it is given. Never a source of numbers. |

## Scope

- One dataset: Olist Brazilian e-commerce, January 2017 to August 2018, amounts in BRL (gross item sales).
- One local, single-user demo. No accounts, no payments, no bank or ERP integration, no autonomous actions.
- Out of scope: other datasets merged with Olist, personal finance, chat-to-SQL, training a language model.
- One backend-only exception, kept as a separate profile and never joined with Olist: a synthetic small-business
  cash-flow snapshot dataset (`Java/OpportunityApp/config/py/mosaic/datasets/small_business_cashflow.csv`, gitignored, supplied for this
  hackathon, no real-world provenance) trains one extra classifier, `cashflow_stress` — see FR-12. Its
  ROC-AUC (0.53) is barely above chance; it is documented and shipped as an honest demonstration of the
  method, not as a usable risk score.

## Functional Requirements

| Code | Requirement | Where |
| --- | --- | --- |
| FR-1 | Show monthly sales and orders for the analysed range, with the records left out and why. | `Java/OpportunityApp/config/py/mosaic/app/api/get_sales_history.py`; `Java/OpportunityApp/.../templates/fragments/sales/page.html` |
| FR-2 | Forecast the next months of sales with a range, and compare the model honestly against simple rules. | `Java/OpportunityApp/config/py/mosaic/app/forecast/`; `fragments/sales/page.html` |
| FR-3 | Flag categories falling well behind the whole business, and categories whose latest month is unusual. | `Java/OpportunityApp/config/py/mosaic/app/analysis/categories.py`; `categories.html` |
| FR-4 | For a category or seller, show its sales, late-delivery and low-review rates by month against the whole business, with a small-sample warning. The category page with its flag rule was removed with the trend pages. | `Java/OpportunityApp/config/py/mosaic/app/analysis/financial_views.py` (`entity_detail`), `app/api/get_financial_views.py`; `controller/ExploreController.java`, `templates/explore.html`, `static/js/explore.js` |
| FR-5 | Show late-delivery and low-review rates, how they go together, the riskiest open orders and the least reliable sellers. | `Java/OpportunityApp/config/py/mosaic/app/api/get_delivery_summary.py` and the other `get_delivery_*`/`get_review*`/`get_unreviewed_orders.py` routes; `trend.html`, `fragments/trend/page.html` (the risk page was removed; open orders and sellers are API routes only) |
| FR-6 | Run a hypothetical sales change and show its effect on orders, late deliveries, low reviews and seller capacity, with its assumptions and limitations. | `Java/OpportunityApp/config/py/mosaic/app/analysis/impact.py`; `controller/ScenarioPageController.java`, `templates/what-if.html`, `static/js/what-if.js` (whole business or one category) |
| FR-7 | Summarise a scenario in plain language; fall back to a fixed template when the model is off, fails, or uses a figure not in the evidence. | `service/ai/ScenarioNarrator.java` |
| FR-8 | Base the overview's investment suggestion and caveats on nearly all of the Olist data, and show charts of the observed figures behind each. Suggestion: category growth from items; late-delivery, low-review and cancellation rates against the business; a profile from orders, payments, customers, reviews and sellers (average order value, freight share, instalments, card payments, returning customers, seller count and top seller share, customer states, review score, delivery days); risks (one seller, heavy freight, shrinking basket) that mark a category "watch". Caveats: falling categories, late and low-review rates, low reviews on late orders, cancellations, basket size, freight share, instalments, returning customers, seller and state concentration. Each button asks the site once per page load. The chat assistant was removed. | `Java/OpportunityApp/config/py/mosaic/app/data/orders.py`, `Java/OpportunityApp/config/py/mosaic/app/analysis/business_profile.py`, `opportunities.py`, `caveats.py`; `controller/api/AiButtonsController.java`, `service/ai/InvestmentAdvisor.java`, `CaveatWriter.java`, `templates/fragments/sales/page.html`, `static/js/charts.js` |
| FR-9 | Start the analytics API with the website and stop it with it. | `service/PythonApiLauncher.java` |
| FR-10 | Keep the Olist records in the website's own database and compute every API figure from that database's CSV export. | `Java/OpportunityApp/.../data/BusinessDatabase.java`, `entity/` |
| FR-11 | Under the sales forecast, three buttons: show the forecast's evidence; suggest where to invest when the forecast rises (growing categories labelled by growth, size, late-delivery and low-review levels against explicit thresholds); and list the hidden problems behind the result from deterministic checks. Both written answers fall back to fixed text when the model is off, slow, or uses a figure not in the evidence. | `Java/OpportunityApp/config/py/mosaic/app/analysis/opportunities.py`, `Java/OpportunityApp/config/py/mosaic/app/analysis/caveats.py`; `service/ai/InvestmentAdvisor.java`, `CaveatWriter.java`, `CheckedWriter.java`; `controller/api/AiButtonsController.java`; `fragments/sales/page.html` |
| FR-12 | Show observed cash-flow-stress rate by sector and month from the separate small-business practice dataset, and rank its held-out snapshots by a trained classifier's risk score only while that model's held-out ROC-AUC is at least 0.6 (currently 0.53, so ranking returns 503); degrade to `available: false` / HTTP 503 (never 500) when that dataset or model is absent. Not yet wired into the website (Python API only). | `Java/OpportunityApp/config/py/mosaic/app/api/get_cashflow_summary.py`, `get_cashflow_risk.py`; `Java/OpportunityApp/config/py/mosaic/app/analysis/cashflow.py`; `Java/OpportunityApp/config/py/mosaic/app/models/cashflow.py`, `train_cashflow.py` |
| FR-13 | Show an About page naming the five application authors, linked from the site navigation. | `Java/OpportunityApp/src/main/java/mu/mosaic/opportunity/controller/AboutController.java`; `Java/OpportunityApp/src/main/resources/templates/about.html` |
| FR-14 | One ranked list of every check from the Sales, Delivery, Reviews and Sellers pages (triggered first, then by sales exposed), each with its size of change, its threshold and the gross item value of the orders it touches ("sales exposed", never "lost"). The owner can choose recent and comparison months, a category or a customer state, and change any threshold for that page only; the default list is on the overview. Record-backed findings open the exact orders behind the rate (all counted or only flagged, paginated), download as CSV with the rule and dataset version on every row, and print as a one-page summary. | `Java/OpportunityApp/config/py/mosaic/app/analysis/findings.py`, `selection.py`, `app/api/get_findings.py`; `controller/FindingsController.java`, `templates/findings.html`, `finding.html`, `fragments/items/selection.html`, `sales.html` |
| FR-15 | Let the owner test a trend page with other months, a category or a customer state; the chart and comparison follow the selection. | `app/api/get_findings.py` (`/api/findings/trend/{measure}`); `controller/TrendController.java`, `templates/trend.html` |
| FR-16 | Explore views: data coverage and quality with checksums, customer payments by month and type, freight share by month, category and state, returning-customer cohorts with incomplete cohorts marked, model cards read from the saved `.json` files, and a list of categories and sellers. | `app/analysis/financial_views.py`, `app/api/get_financial_views.py`; `controller/ExploreController.java`, `templates/explore.html`, `static/js/explore.js` |
| FR-17 | Optional external context markers (Brazilian events and economy) on the sales chart, labelled as coinciding, hidden when the downloads are absent. | `controller/api/ContextController.java`, `static/js/chart-context.js`, `fragments/sales/page.html` |

## Non-Functional Requirements

| Code | Requirement |
| --- | --- |
| NFR-1 | The Python API is the only source of figures; the website formats them and never recomputes them. |
| NFR-2 | Every page renders when the API, a model or the language model is unavailable, saying what is missing and how to fix it. |
| NFR-3 | Observed data, model predictions and hypothetical scenarios are visually distinct on every page. |
| NFR-4 | No claim of causation, profit, cash or guaranteed outcome anywhere in the product. |
| NFR-5 | Only aggregated figures reach the language model for the summaries. |
| NFR-6 | One LLM client: every model call uses the Java AI manager configured in `Java/OpportunityApp/config/ai/agents.json`. |
| NFR-7 | The demo needs no internet: Bootstrap and Chart.js are served from WebJars, the model is local. |

## Not recommended


- Chat-to-SQL, bank or payment integration, profit or cash-balance figures: out of scope and unsupported by Olist.
- Joining the cash-flow practice dataset (FR-12) or any new dataset to Olist as if it were the same business.
- Putting the `cashflow_stress` ranking on the site while it does not beat its baseline.
- Any feature whose only purpose is to show "AI" without supporting a decision.

## Outstanding work

The running list of what is left. **Update it in the same pass as the job it covers** — add an item the
moment it appears, strike it the moment it is done. Finished items move to `docs/worklog` and are removed
from here, never left standing as done.

### Website

- Click the Sales and trend pages' suggestion and caveats buttons and ask one follow-up on the running site, with the model on and off, after the typed-reply refactor (`Panels`, `CheckedWriter<T>`, `obj/api`). The writers were checked offline against saved real replies only.
- Finish the packaged JAR check with Python autostart from `mosaic-python.zip` and a configured interpreter. The JAR now starts outside the repository on port 18080 after adding `slf4j-api`, and first-start import completed, but the smoke run disabled Python autostart because a user-run API already occupied port 8000.
- Sign-in: finish a real Google sign-in in a browser on port 8080 (only the redirect to Google was checked), and send one real password-reset email; the link and new-password form were checked without the email.
- Repeat the Chrome page pass after the latest fixes at desktop and phone width, with the site restarted on the database export. The 23 Sep desktop pass covered the overview, delivery, reviews, sellers, Help and an unknown route; phone width and fixes made after that pass still need checking.
- AI provider for the demo: Groq (`GROQ_API_KEY`) answers in seconds, but its free tier allows 8,000 tokens a minute on `openai/gpt-oss-120b`, about four summaries. Decide whether to try a model with a larger allowance, and rehearse at a pace that stays under the limit. LM Studio remains the fallback without the variable. Still unchecked live: the provider stopped mid-answer.
- Recheck the overview suggestion and caveat charts in Chrome at phone width after the latest fixes.
- Check the shared page layout (page switcher, question, tab strip; `fragments/items/pages.html`, `fragments/items/panels.html`) at phone width in Chrome; the 24 Sep desktop check of Sales and Delivery could not resize the window.
- Open the simplified overview in Chrome after restarting the site: the three buttons, their loading state, a Groq-written advice and caveat text, and phone width.
- Check the follow-up chat and tabs at phone width.
- Fixed 24 Sep: `.chat-log` lacked `overscroll-behavior: contain` (unlike `#sidebar`, which already had it), so scrolling past the top or bottom of a long conversation could chain into scrolling the whole page instead of staying inside the chat box. Verified the box does scroll internally and the page does not move while scrolling it (discrete wheel ticks, desktop); could not reproduce or verify the leak itself, or check it on a narrow/touch viewport, because the browser window would not resize in this environment.
- Follow-up chat tools (`PanelTools`, 14 read-only tools incl. Brazilian events and Central Bank economy context): check tool calling live on Groq and LM Studio, and whether several tool calls per question hit Groq's per-minute limit. On a fresh machine run `python -m app.data.events` and `python -m app.data.economy` once (the downloads are gitignored).
- Rotate the Groq key after the hackathon; it was pasted into a chat session.
- Check the sidebar opening on a real phone-width browser; the headless screenshots could not click.
- Chrome pass of the new pages at desktop and phone width with the real API: Findings (thresholds, periods, filters), a finding's records, CSV download and print, the overview's findings card, the trend pages' period form, What if, and the explore views. Only MockMvc renders and API calls on the real data were checked.
- Trend pages with a selection: the chart and comparison follow it, but the Evidence, Suggested opportunity and Possible caveats tabs still use the default windows (the page says so and links to Findings). Pass the selection through `/api/trend/...` if the tabs should follow it.
- Order records exist for five rate findings (`RECORD_RULES` in `app/analysis/findings.py`); the other checks link to their page. Sales exposed is shown in the findings list, not yet next to each "watch" category in the investment suggestion.
- Thresholds and periods live in the page address: "Reset to defaults" restores them, but reloading a changed address keeps the change.


### AI backend
- Fixed 24 Sep: active-sellers rule text now names the priciest-item limitation; the late-orders/low-reviews sentence on both Sales and Reviews now names its period; the What-if fitted late-rate variant is dropped unless it reproduces the recent rate (`FIT_TOLERANCE`), its low-review estimate now scales from the baseline instead of mixing whole-period rates, an unknown What-if category returns 400 (was 502) with no duplicated full stop, and the fixed-text scenario summary says "rise"/"fall" instead of "change". `agents.json` prompts gained rules against calling `in_line` "better", flagging an untriggered risk, saying a group "drove" a business figure, undercounting named groups, and the follow-up chat now must call a tool for a month/event/cause question rather than say it lacks the figures. **Not yet re-verified live** (Groq is rate-limited to one call per 30s–1min in this environment): confirm the model actually follows the new prompt rules on a real run.
- Confirm every teammate uses the canonical Olist CSV copies documented with SHA-256 hashes in `Java/OpportunityApp/config/py/mosaic/README.md`; a different copy makes the committed models answer 409.

### Team setup
- Commit the artifactId rename in this repository's Java modules.
- Republish SolarFramework to GitHub Packages before pushing the `LocalAi` change: it now needs `EnvValue` (core) and the AI module's `${NAME}` key resolution, installed only in this machine's `~/.m2`. Version `1.0` cannot be overwritten, so delete it on GitHub first or bump the version. Until then a teammate's build fails to compile `LocalAi`.
