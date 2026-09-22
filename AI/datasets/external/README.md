# External datasets (downloaded 2026-09-22, not used by the code yet)

These files are **gitignored** (see `AI/.gitignore`). They were downloaded to evaluate
predictions that Olist cannot support (churn, customer value, returns, cross-selling, profit,
discount effects). If they are adopted, each must be treated as a **separate business
profile** in the app, never merged with Olist as if it were one company.

| File | Source | Version | SHA-256 | Licence |
| --- | --- | --- | --- | --- |
| `online_retail_ii.zip` (contains `online_retail_II.xlsx`, 45.6 MB) | UCI Machine Learning Repository, dataset 502 "Online Retail II": https://archive.ics.uci.edu/dataset/502/online+retail+ii — direct link https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip | UCI file dated 2023-05-22 | `572e36277c2390fbfde10664750731e0a86f55e33470d91919085f0408e67bfb` | CC BY 4.0 (as stated on the UCI page; verify before redistribution) |
| `DataCoSupplyChainDataset.csv` (95.9 MB) | Mendeley Data, "DataCo SMART SUPPLY CHAIN FOR BIG DATA ANALYSIS", DOI 10.17632/8gx2fvg2k6.5 | v5, published 2019-03-12 | `fa6d022ed437155e1a2f0378710602848703c8a7f203f7ff5d77805bf8480aa6` (matches the hash Mendeley publishes) | CC BY 4.0 |
| `DescriptionDataCoSupplyChain.csv` (3.4 KB, variable dictionary) | same as above | v5 | `9828e34669bd6d77e3b4463364cc44a5d52446b5e246fc258758cfe592566c4b` | CC BY 4.0 |

Not downloaded:

- DataCo `tokenized_access_logs.csv` (95 MB clickstream) — not useful for the planned analyses.
- Kaggle datasets (M5, Favorita Store Sales) — require a Kaggle account and competition-rule
  acceptance; not fetched automatically. Download manually into this folder if wanted.
- AdventureWorks — distributed as a SQL Server `.bak`; needs SQL Server to export, so it was
  not fetched.

Re-download check:

```powershell
Get-FileHash .\DataCoSupplyChainDataset.csv -Algorithm SHA256
```

What each one would unlock (see `docs/superpowers/specs/` for the current Olist scope):

- **Online Retail II**: repeat customers → churn and customer future value; cancelled
  invoices (negative quantities, invoice numbers starting with `C`) → return risk; multi-line
  invoices → cross-selling. Two years (Dec 2009 – Dec 2011), UK gift wholesaler, GBP.
- **DataCo**: per-order profit and discount rate → profit and discount/promotion analyses;
  includes a `Late_delivery_risk` label and shipping mode. Check the dictionary before use:
  some columns are only known after the outcome.
