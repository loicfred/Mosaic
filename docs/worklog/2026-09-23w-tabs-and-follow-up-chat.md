# 2026-09-23 — Tabs and follow-up questions on the overview and trend pages

Author: Claude

- The three buttons on the overview and the three trend pages are now tabs: Evidence (open on load), Suggested investment or opportunity, and Possible caveats. A shared script, `Java/OpportunityApp/src/main/resources/static/js/panels.js` (`MosaicPanels.bind`), replaces the per-page click handlers in `fragments/index/sales.html` and `static/js/trend.js`. Each AI tab still asks the site once per page load.
- Each AI tab has a follow-up box under its answer. `PanelChatController` answers `POST /api/overview/{advice|caveats}/ask` and `/api/trend/{measure}/{advice|caveats}/ask`, with a body of `{question, history}`.
  - The panel's figures are fetched again on the server; `InvestmentAdvisor`, `CaveatWriter`, `TrendAdvisor` and `TrendCaveatWriter` gained a public `evidence(...)` method for this.
  - The browser can never supply figures of its own.
  - Questions are limited to 500 characters and the history to 8 turns (roles `user` and `assistant` only); anything else gets a 400.
- `service/ai/PanelChat` uses the new `PanelChat` chatbot in `config/ai/agents.json`, whose rules are: only the given numbers, no profit or margin talk, and "could", not "will".
  - A reply is checked against the numbers in the evidence and the system prompt only, never against the history.
  - A reply with other numbers is withheld and the user sees a message saying why.
  - A failed call shows "try again"; no configured model shows that the AI is off.
- Tests: `PanelChatTest` covers a supported answer, a number from the history being withheld, no model or an unreachable one, and the prompt order. `PanelChatControllerTest` covers the unavailable model, the trend measure routing, rejected questions never reaching the API, an unknown panel (404) and the API being down (502). `PagesRenderTest` now checks the new labels. Both Java modules' test suites pass.
- Checked live in Chrome on the running site:
  - The tabs switch.
  - The overview's suggestion shows 5 charts and its caveats 6; `/delivery` works too.
  - Seven follow-up questions were answered in about 2.5 s each, from the panel's figures.
  - One question first failed after a burst of questions, probably Groq's rate limit, and succeeded when asked again.
- Known gaps:
  - The number check allows numbers up to 12 anywhere, so a self-computed "a drop of about BRL 4" passed.
  - One answer called the returning-customer rate a share "of its sales" when it is a share of orders.
  - Phone width could not be checked, because the Chrome window would not resize.
