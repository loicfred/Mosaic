# Demo script (7 minutes)

All data in the demo is synthetic and fictional. Say so once, at the start.

## Before you present (10 minutes earlier)

1. `python scripts/seed_demo.py` - resets the demo to a known state (about 10 seconds).
2. Start the API (`cd backend && python -m uvicorn app.main:app --port 8000`) and the web app (`cd frontend && npm run dev`).
3. Open http://localhost:5173, sign in as `owner@coastal.demo` / `Coastal-Demo-2026!`. Keep `data/demo/coastal_petty_cash_sep2026.csv` ready (it can also be downloaded from the Import tab).
4. Optional safety net: `python tests/e2e/demo_flow.py` runs the whole flow in a headless browser in about a minute. Re-seed afterwards.

Nothing in the demo needs the internet.

## 30-second pitch

> "Accounting software tells a small business what happened. Valora
> connects what happened to what should be investigated, what could be done,
> what it is worth, and whether it actually worked. Every finding is backed by
> evidence from the ledger, every number is computed by a deterministic engine,
> machine learning adds a calibrated early warning, and the owner can simulate a
> decision, act on it, and measure the outcome - on their own data, without
> sending it to an external AI."

## The story

Coastal Home & Kitchen Ltd is a fictional homeware shop in Mauritius with hotel
and catering customers. Sales are flat, but since June its main supplier raised
prices, its biggest hotel customer pays four weeks later, rent went up and two
new subscriptions appeared. The owner has not noticed yet.

## Walkthrough

**1. Overview (60 s) - "Where is the business now?"**
* Read the banner first: *Cash is projected to fall below your safety buffer on 28 Sep - in 6 days*, with 8 findings to decide and 3 data items to review. That is the 5-second answer.
* Cash MUR 575K, covering about 18 days of outflows (the meter shows it just above the 14-day buffer mark). Revenue −2.6% for Jun–Aug vs Mar–May, expenses +5.7%, gross margin down 8.4 points.
* Point at the labels: *Actual* (solid), *Projected* (dashed) and *Predicted*. They never mix.
* Cash-pressure card: **High risk, 64%** on the Low / Moderate / High band scale, probability of dropping below a 14-day buffer within 30 days. The "why" lists the drivers; the projection says the buffer is breached on 28 Sep and cash bottoms at MUR 330K on 26 Oct.

**2. Data Health and import (90 s) - "Clean"**
* Data Health: score 99, three proposals on the existing ledger (two category suggestions, one duplicate supplier payment of MUR 21,687).
* Import tab -> upload `coastal_petty_cash_sep2026.csv`. The file health score is **74/100**: 4 rows rejected (impossible dates 31/09 and 2026-13-02, an amount typed with the letter O, a future date), 2 duplicates (one in the file, one already in the ledger), a formula-injection description neutralised, and payees matched from descriptions.
* Show a low-confidence category suggestion (the CEB bill at 37%) - correct it before approving. Commit is blocked until each duplicate has a decision. Approve the duplicates and commit 16 rows.
* "Nothing was changed silently. Every decision is in the audit trail with before and after values."

**3. Opportunities (2 min) - "Detect, explain, quantify"**
* The top of the page answers "which is worth the most?": the action pipeline (8 new, 1 completed) and each finding's estimated range on one scale, gains and risks kept apart.
* Open *Supplier costs up 13% while revenue fell 3%* -> **Show evidence & track**.
* Walk the eight numbered sections: what was found, the evidence (periods, supporting transactions you can click), confidence and how it is computed, impact **MUR 183K–366K a year** with its stated basis, recommended actions.
* Open *Customers paying 15 days slower*: Coral Crest Hotels moved from 32 to 58 days; about MUR 145K is sitting with customers.

**4. Scenario Lab (60 s) - "Simulate"**
* From the supplier card click **Simulate** (supplier prices −10%): +MUR 187K cash after 90 days, lowest balance +MUR 69K.
* Add *Collect 10 days faster*: days below the buffer drop from 21 to 0.
* "Simulated values are orange, the baseline is dashed, and historical records are never touched."

**5. Act and measure (60 s)**
* Back on the collections card: add a note ("Call Coral Crest finance on Monday") and click **Start action**. The outcome panel says *Measuring - too early* and names the metric it will re-measure.
* Open **Acting on** -> *Paying for 2 accounting tools* (detected in March, LedgerPro cancelled in May): **Outcome achieved** - fixed tool cost went from MUR 4,100 to MUR 1,650 a month, measured on data after the action started.

**6. Security and model evaluation (60 s)**
* Security & Audit: *Tenant isolation enforced in the database* (PostgreSQL row-level security), Argon2id, rotating refresh tokens, RBAC, and the audit trail with the import and status change you just made.
* Optional: sign in as `viewer@coastal.demo` (read-only), or as `owner@tamarind.demo` (a different business that sees none of Coastal's data).
* Settings -> Models & data: test ROC-AUC 0.943 vs 0.911 for the buffer-only rule, calibration, confusion matrix, and the provided dataset benchmark (~0.57).

**Close (15 s):** "Data, clean, understand, detect, explain, quantify, simulate, act, measure - in one product, with evidence at every step."

## Likely jury questions

| Question | Answer |
|---|---|
| Is the ML meaningful? | It predicts the *onset* of cash pressure for businesses that are not yet in trouble. It beats a buffer-only rule on unseen businesses (ROC-AUC 0.943 vs 0.911, F1 0.686 vs 0.602) and in a later time period. We show the baseline next to the model on purpose. |
| Why synthetic data? | The provided file has no business ids or history; all models score about 0.52–0.57 ROC-AUC on it, which we report. Real SME ledgers are private. The generator is reproducible and documented, and every screen is labelled synthetic. |
| Could the model just be learning your generator? | That is the main limitation, stated in the model card. Mitigations: labels come from the simulated future cash path, not from a feature formula; random shocks are unseen at prediction time; evaluation is grouped by business and checked over time. Validation on real ledgers is the next step. |
| Can the AI invent numbers? | No. Narratives are generated from values the engine computed; there is no LLM in the loop. |
| Can business A see business B? | No: every query is filtered by the business in the verified token, and PostgreSQL row-level security blocks it even if a developer forgets a filter. Tests cover both. |
| How is confidence computed? | Rule-based findings: 0.5 × effect strength + 0.2 × history + 0.2 × data quality + 0.1 × consistency, capped at 95%. The cash-pressure card shows the calibrated model probability instead. |
| How do you know an action worked? | Each finding names a target metric. When the action starts, the baseline is frozen; the same metric is recomputed on later data and compared with the expected change. We say it is evidence, not proof of cause. |
| Does it scale? | Stateless API, per-tenant cached analysis, O(n) analytics. For many instances move rate limiting and cache to Redis. |
