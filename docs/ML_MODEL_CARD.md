# Model card - Valora

Valora ships three small, local scikit-learn models. None of them decides
anything on its own: each produces a labelled suggestion that sits next to
deterministic evidence. All numbers below are copied from the evaluation
reports written by the training scripts (`models/*/metadata.json`,
`models/benchmark_provided_csv.json`) and are reproduced by
`python scripts/train_all.py`. The walkthrough is in `notebooks/model_evaluation.ipynb`.

---

## 1. 30-day cash-pressure model (primary)

### Purpose
Early warning: estimate the probability that a business that currently has at
least 14 days of cash will fall below 14 days of committed outflows at any point
in the next 30 days. Shown as LOW / MODERATE / HIGH with the probability and
per-feature drivers.

Out of scope: businesses already below the buffer. There, arithmetic answers the
question, so the deterministic engine reports "Cash buffer is already below 14
days" instead of a prediction.

### Training data
* **Synthetic panel** (`scripts/generate_synthetic.py`, seed 2026): 210 fictional SMEs, 30 per archetype
  (retail shop, restaurant, salon, clothing boutique, electronics store, wholesaler, service company),
  daily bank-feed-style transactions and invoices from Jan 2023 to Dec 2025, in MUR.
* The generator includes seasonality (Mauritian retail and tourism patterns), growth, weekly supplier
  purchases, payroll with a 13th-month bonus, rent, utilities, subscriptions, quarterly VAT, loans,
  owner drawings and injections, late-paying customers, and random shocks (supplier price rises,
  customer payment delays, revenue drops, equipment purchases, rent increases).
* One row per business every 14 days (after 120 days of history), 14,280 rows; 12,579 eligible
  (buffer >= 14 days). Positive rate: 11.1% (train), 12.4% (test).

### Why not the provided dataset?
`data/public/small_business_cashflow.csv` (1,600 rows, 17.1% positive) has one
monthly snapshot per row, no business identifier and no history. With 5-fold
stratified cross-validation every model is near chance:

| Model | ROC-AUC |
|---|---|
| Logistic regression | 0.574 |
| Random forest | 0.524 |
| Histogram gradient boosting | 0.536 |

It is kept as an external benchmark and reported in the app.

### Features (all scale-free)
buffer days, 90-day net margin, 30-day revenue / expense / supplier-cost growth,
recurring share of outflows, collection days and their trend, overdue receivables
ratio, top customer share, top supplier share, weekly cash-flow volatility,
30-day cash trend, known obligations due in the next 30 days (recurring run-rate,
VAT on the 20th of Jan/Apr/Jul/Oct, 13th-month bonus), seasonal index, change in
transaction frequency. Definitions: `docs/DATA_DICTIONARY.md`. The same code
(`backend/app/analytics/features.py`) computes them for training and for the live app.

### Model and selection
Standardised features + logistic regression. Candidates were compared with
5-fold GroupKFold (grouped by business) on the training businesses:

| Candidate | CV ROC-AUC | Out-of-fold PR-AUC |
|---|---|---|
| Logistic regression, C=0.1 | 0.925 ± 0.011 | 0.630 |
| **Logistic regression, C=1 (chosen)** | **0.928 ± 0.009** | **0.647** |
| Histogram gradient boosting | 0.919 ± 0.009 | 0.638 |
| Rule of thumb (buffer days only) | 0.911 | 0.600 |

Rule: prefer logistic regression unless boosting is better by more than 0.01 AUC,
because every prediction must be explainable feature by feature.

### Evaluation on held-out businesses (42 businesses never seen in training)

| Metric | Model | Buffer-only rule |
|---|---|---|
| ROC-AUC | **0.943** | 0.911 |
| PR-AUC | **0.702** | 0.603 |
| Brier score | 0.057 | - |

At the HIGH threshold (0.32, chosen to maximise F1 on out-of-fold predictions):

| | Precision | Recall | F1 |
|---|---|---|---|
| Model, HIGH (p >= 0.32) | 0.619 | 0.769 | 0.686 |
| Model, MODERATE or higher (p >= 0.16) | 0.472 | 0.907 | 0.621 |
| Rule: buffer < 21 days | 0.520 | 0.714 | 0.602 |

Confusion matrix at HIGH: TN 2,055 · FP 147 · FN 72 · TP 239.

Temporal check (train on as-of dates before 1 Apr 2025, test on later dates of
unseen businesses): ROC-AUC 0.925 vs 0.889 for the rule.

Calibration: 8 quantile bins on the test set track the diagonal closely (see the
Models & data page or the notebook).

**Honest reading:** most of the signal is the current cash buffer. The model adds
a real but moderate improvement (+0.03 ROC-AUC, +0.10 PR-AUC, +0.08 F1 over the
rule), mainly by weighing known upcoming obligations, recurring cost load,
collections and concentration.

### Explanations
For logistic regression, each feature's contribution to the log-odds is
`weight x (value - training mean) / training std`. The app shows the largest
positive contributions (>= 0.25) as "why", plus the deterministic projection
(first date below the buffer, lowest balance). Each prediction is stored in
`predictions` with the model version, the features and the contributions.

### Limitations and risks
* Trained on synthetic data. Performance on real SMEs is unknown until validated on real ledgers.
* The label and the shocks come from the generator's assumptions; businesses that behave very
  differently (e.g. heavy credit-card financing) may be mis-scored.
* Cash-basis ledgers only: unrecorded payables, cheques in transit and credit lines are invisible.
* Probabilities are calibrated on the synthetic population, not on any real bank's customers.

### Responsible use
* A decision aid for the owner and accountant, not a credit decision. Do not use for lending,
  employment or any decision about individuals.
* Always read together with the projection and the evidence. Owners can dismiss findings.
* Re-train and re-evaluate on real (consented) ledgers before any production claim.

---

## 2. Unusual-payment detector

* **Purpose:** flag outflows that look unusual for this business so a person can review them.
* **Method:** Isolation Forest (300 trees) on history-relative features (amount vs the payee's
  previous median, vs the category median, vs the business median; first payment to a payee;
  weekend). A payment is flagged when (the model flags it AND it is larger than usual) **OR** an
  explainable rule fires (amount >= 4x the payee's median with at least 3 earlier payments; tax and
  payroll excluded), **and** it is material (>= 1% of average monthly outflows) - small petty-cash
  oddities are not worth an owner's time. Duplicates use a separate exact-match rule
  (same date, direction, amount and payee).
* **Evaluation:** anomalies injected into the synthetic panel (unusual amounts, large payments to
  new payees), tested on 42 held-out businesses:

| Method | Precision | Recall | F1 |
|---|---|---|---|
| Isolation Forest alone (ROC-AUC 0.986, PR-AUC 0.321) | 0.429 | 0.537 | 0.477 |
| Rule alone | 1.000 | 0.423 | 0.594 |
| Model OR rule | 0.536 | 0.824 | 0.649 |
| **Used in the app: (model AND larger than usual) OR rule, material only** | **0.694** | **0.783** | **0.736** |
| Duplicate rule, injected duplicates found | - | 1.000 | - |

* **Limitations:** real anomalies are more varied than injected ones; about three in ten flags are
  legitimate unusual payments (e.g. a first annual insurance premium). Flags never change data.

---

## 3. Category suggester

* **Purpose:** propose a category for uncategorised imported or recorded transactions.
* **Method:** TF-IDF (character 2-5 grams + word 1-2 grams) + logistic regression, trained on
  synthetic transaction descriptions plus a small hand-written keyword lexicon
  (`data/reference/category_lexicon.csv`).
* **Evaluation:**
  * held-out synthetic businesses: accuracy 1.000 (templated text, optimistic);
  * **hand-written set never used in training** (`data/eval/categoriser_handwritten.csv`, 61 rows):
    accuracy **0.869**, macro-F1 0.856.
* **Use:** suggestions below 45% confidence are marked "Low confidence - check before approving".
  Nothing is applied without approval, and the user can pick a different category before approving.

---

## 4. Deterministic cash projection (not ML, evaluated anyway)

The 90-day projection behind the Scenario Lab is a transparent driver model. A
back-test on the demo business (projecting 30 days from 8 past dates, with owner
drawings removed from the actuals) gives a median absolute error of 13.3% of
monthly outflows. The error widens the impact range shown on the cash-pressure card.
