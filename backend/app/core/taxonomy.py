"""Fixed financial category taxonomy shared by the engine, ML and importer.

Keeping the taxonomy in one place means the categoriser, the analytics engine,
the data-quality checks and the frontend never disagree on what a category means.
"""

from __future__ import annotations

from typing import Final

INFLOW: Final = "inflow"
OUTFLOW: Final = "outflow"

# category -> (direction, group)
# group drives the deterministic definitions used in docs/DATA_DICTIONARY.md:
#   revenue    -> counts toward revenue (cash basis)
#   cogs       -> cost of goods / direct supplier cost
#   operating  -> operating expense
#   financing  -> loans, owner contributions (excluded from revenue/expenses)
#   tax        -> tax payments (included in expenses, excluded from margin)
CATEGORIES: Final[dict[str, tuple[str, str]]] = {
    "Sales": (INFLOW, "revenue"),
    "Other income": (INFLOW, "other_income"),
    "Owner contribution": (INFLOW, "financing"),
    "Loan proceeds": (INFLOW, "financing"),
    "Inventory & supplies": (OUTFLOW, "cogs"),
    "Payroll": (OUTFLOW, "operating"),
    "Rent": (OUTFLOW, "operating"),
    "Utilities": (OUTFLOW, "operating"),
    "Telecom & internet": (OUTFLOW, "operating"),
    "Software & subscriptions": (OUTFLOW, "operating"),
    "Marketing": (OUTFLOW, "operating"),
    "Insurance": (OUTFLOW, "operating"),
    "Repairs & maintenance": (OUTFLOW, "operating"),
    "Professional fees": (OUTFLOW, "operating"),
    "Transport & logistics": (OUTFLOW, "operating"),
    "Bank fees": (OUTFLOW, "operating"),
    "Equipment": (OUTFLOW, "operating"),
    "Other expenses": (OUTFLOW, "operating"),
    "Taxes (VAT)": (OUTFLOW, "tax"),
    "Loan repayment": (OUTFLOW, "financing"),
    "Owner drawings": (OUTFLOW, "financing"),
}

UNCATEGORISED: Final = "Uncategorised"

# Categories whose outflows are typically recurring commitments.
RECURRING_CANDIDATES: Final = frozenset(
    {
        "Payroll",
        "Rent",
        "Utilities",
        "Telecom & internet",
        "Software & subscriptions",
        "Insurance",
        "Loan repayment",
        "Professional fees",
    }
)

# Levers used by the scenario simulator map to these category groups.
MARKETING_CATEGORIES: Final = frozenset({"Marketing"})
STAFF_CATEGORIES: Final = frozenset({"Payroll"})
SUPPLIER_CATEGORIES: Final = frozenset({"Inventory & supplies"})


def all_categories() -> list[str]:
    return [*CATEGORIES.keys(), UNCATEGORISED]


def direction_of(category: str) -> str | None:
    entry = CATEGORIES.get(category)
    return entry[0] if entry else None


def group_of(category: str) -> str:
    entry = CATEGORIES.get(category)
    return entry[1] if entry else "uncategorised"


def is_valid_category(category: str) -> bool:
    return category in CATEGORIES or category == UNCATEGORISED
