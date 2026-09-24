"""Hand-designed SYNTHETIC demo tenants.

Coastal Home & Kitchen Ltd is a fictional homeware retailer. Its ledger is built
by the same generator used for the ML panel, with deliberately scripted events
so the live demo tells one coherent story:

* revenue is still growing, but slowly;
* the main supplier raised prices sharply in mid-June 2026;
* rent went up and new subscriptions were added (recurring cost creep);
* the largest hotel customer started paying much later from May 2026;
* one refrigeration repair was far above normal, and one supplier payment was
  made twice;
* the Small Appliances line is growing fast;
* earlier in 2026 two overlapping accounting subscriptions were spotted and one
  was cancelled. That opportunity is already completed, so outcome tracking can
  be shown with real before/after data.

A second tenant, Tamarind Cafe, exists only to demonstrate tenant isolation.
"""

from __future__ import annotations

from datetime import date

from app.synthetic.generator import (
    BusinessSpec,
    CustomerSpec,
    ScheduledAnomaly,
    Shock,
    Subscription,
    SupplierSpec,
    random_spec,
)
from app.synthetic.profiles import ARCHETYPES

DEMO_START = date(2024, 10, 1)
DEMO_END = date(2026, 9, 22)  # "today" in the demo is 23 Sep 2026; data runs to the 22nd

MAIN_SUPPLIER = "Oceanic Wholesale Supplies"
KEY_CUSTOMER = "Coral Crest Hotels Ltd"


def coastal_spec() -> BusinessSpec:
    return BusinessSpec(
        key="COASTAL",
        name="Coastal Home & Kitchen Ltd",
        archetype=ARCHETYPES["retail_shop"],
        seed=20260923,
        start=DEMO_START,
        end=DEMO_END,
        base_monthly_revenue=880_000,
        growth_annual=0.045,
        product_weights={"Cookware": 0.33, "Small Appliances": 0.21, "Tableware": 0.27, "Home Decor": 0.19},
        product_growth={"Cookware": 0.02, "Small Appliances": 0.34, "Tableware": 0.01, "Home Decor": -0.14},
        b2b_share=0.33,
        customers=[
            CustomerSpec(KEY_CUSTOMER, 0.56, 3.0, 14),
            CustomerSpec("Filao Bay Guesthouses", 0.14, 6.0, 30),
            CustomerSpec("Pailles Catering Co", 0.13, 2.0, 14),
            CustomerSpec("Moka Office Hub", 0.10, 9.0, 30),
            CustomerSpec("Riverside Events Ltd", 0.07, 4.0, 30),
        ],
        cogs_ratio=0.52,
        suppliers=[
            SupplierSpec(MAIN_SUPPLIER, 0.53, 7, 1),
            SupplierSpec("Island Kitchenware Imports", 0.25, 14, 3),
            SupplierSpec("Mascarene Home Traders", 0.12, 7, 4),
            SupplierSpec("Sunrise Packaging Ltd", 0.10, 14, 0),
        ],
        staff=7,
        salary=21_500,
        rent=65_000,
        subscriptions=[
            Subscription("POS system licence", 2_600, 3, DEMO_START),
            Subscription("CloudBooks Accounting", 1_650, 7, DEMO_START),
            Subscription("LedgerPro Accounting", 2_450, 9, date(2025, 6, 1), date(2026, 5, 31)),
            Subscription("StockTrack Inventory app", 2_400, 10, date(2026, 6, 1)),
            Subscription("SafeWatch CCTV monitoring", 3_200, 16, date(2026, 7, 1), None,
                         "Software & subscriptions"),
        ],
        opening_cash=640_000,
        shocks=[
            Shock("supplier_price", date(2026, 6, 15), 0.22, target=MAIN_SUPPLIER),
            Shock("supplier_price", date(2026, 7, 1), 0.05, target="Island Kitchenware Imports"),
            Shock("customer_delay", date(2026, 5, 1), 28.0, target=KEY_CUSTOMER),
            Shock("customer_delay", date(2026, 6, 1), 10.0, target="Moka Office Hub"),
            Shock("rent_increase", date(2026, 7, 1), 0.11),
            Shock("equipment", date(2025, 11, 20), 145_000),
        ],
        loan_payment=38_000,
        vat_registered=True,
        owner_injects=False,
        anomaly_rate=0.0,
        drawings_target_months=0.6,
        scheduled_anomalies=[
            ScheduledAnomaly("unusual_amount", date(2026, 9, 9), "Repairs & maintenance",
                             "Tech Fix Services", 48_500.0, "Refrigeration unit emergency repair"),
            ScheduledAnomaly("duplicate_payment", date(2026, 9, 7), counterparty="Sunrise Packaging Ltd"),
        ],
        marketing_share=0.018,
        utilities_base=14_500,
        telecom=3_450,
    )


def tamarind_spec() -> BusinessSpec:
    spec = random_spec("TAMARIND", "restaurant", 777, date(2025, 3, 1), DEMO_END)
    spec.name = "Tamarind Cafe"
    spec.anomaly_rate = 0.1
    return spec
