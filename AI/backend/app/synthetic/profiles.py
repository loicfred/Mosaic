"""SME archetype profiles for the SYNTHETIC data generator.

Everything in this package produces synthetic data. Nothing here is real-world
business data, and every output is labelled as such (see data/README.md).
Amounts are in Mauritian rupees (MUR).
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Month-of-year revenue multipliers (index 1..12). Mauritius-flavoured:
# retail peaks in Nov/Dec (end-of-year bonus spending), tourism peaks Dec-Jan
# and Jul-Aug, and a post-holiday dip in Jan/Feb.
SEASON_RETAIL = {1: 0.84, 2: 0.88, 3: 0.95, 4: 0.97, 5: 0.98, 6: 0.96,
                 7: 0.99, 8: 1.00, 9: 0.98, 10: 1.03, 11: 1.12, 12: 1.36}
SEASON_TOURISM = {1: 1.18, 2: 1.02, 3: 0.98, 4: 0.96, 5: 0.84, 6: 0.82,
                  7: 1.05, 8: 1.08, 9: 0.93, 10: 0.97, 11: 1.03, 12: 1.22}
SEASON_FLAT = {m: 1.0 for m in range(1, 13)} | {12: 1.12, 1: 0.92}


@dataclass(frozen=True)
class ArchetypeProfile:
    key: str
    label: str
    sector: str
    monthly_revenue: tuple[float, float]  # MUR range for base monthly revenue
    product_lines: tuple[str, ...]
    b2b_share: tuple[float, float]  # share of revenue invoiced to business customers
    n_b2b_customers: tuple[int, int]
    cogs_ratio: tuple[float, float]
    n_suppliers: tuple[int, int]
    staff: tuple[int, int]
    salary: tuple[float, float]  # average monthly salary per staff member
    rent_share: tuple[float, float]  # rent as share of monthly revenue
    season: dict[int, float] = field(default_factory=lambda: SEASON_FLAT)
    open_sunday: bool = True


ARCHETYPES: dict[str, ArchetypeProfile] = {
    "retail_shop": ArchetypeProfile(
        "retail_shop", "Retail shop", "Retail", (450_000, 1_300_000),
        ("Household goods", "Groceries", "Personal care"),
        (0.05, 0.35), (3, 8), (0.48, 0.58), (3, 6), (3, 8), (17_000, 24_000),
        (0.05, 0.09), SEASON_RETAIL, True,
    ),
    "restaurant": ArchetypeProfile(
        "restaurant", "Restaurant", "Hospitality", (350_000, 1_100_000),
        ("Dine-in", "Takeaway", "Events & catering"),
        (0.0, 0.2), (1, 4), (0.30, 0.40), (3, 7), (5, 12), (16_000, 22_000),
        (0.07, 0.12), SEASON_TOURISM, True,
    ),
    "salon": ArchetypeProfile(
        "salon", "Salon & beauty services", "Personal services", (180_000, 520_000),
        ("Hair services", "Beauty treatments", "Retail products"),
        (0.0, 0.08), (1, 3), (0.08, 0.16), (2, 4), (3, 7), (15_000, 21_000),
        (0.08, 0.13), SEASON_FLAT, False,
    ),
    "clothing": ArchetypeProfile(
        "clothing", "Clothing boutique", "Retail", (300_000, 900_000),
        ("Womenswear", "Menswear", "Accessories"),
        (0.0, 0.12), (1, 4), (0.45, 0.58), (2, 5), (2, 6), (16_000, 22_000),
        (0.07, 0.12), SEASON_RETAIL, True,
    ),
    "electronics": ArchetypeProfile(
        "electronics", "Electronics store", "Retail", (600_000, 1_800_000),
        ("Phones & accessories", "Computing", "Repairs"),
        (0.10, 0.40), (3, 10), (0.58, 0.68), (2, 5), (3, 8), (18_000, 27_000),
        (0.04, 0.07), SEASON_RETAIL, True,
    ),
    "wholesaler": ArchetypeProfile(
        "wholesaler", "Wholesaler / distributor", "Wholesale", (1_500_000, 4_000_000),
        ("Food & beverage", "Cleaning products", "Packaging"),
        (0.70, 0.95), (8, 25), (0.66, 0.76), (3, 8), (6, 15), (18_000, 26_000),
        (0.02, 0.04), SEASON_FLAT, False,
    ),
    "service_company": ArchetypeProfile(
        "service_company", "Small service company", "Professional services",
        (400_000, 1_400_000),
        ("Retainers", "Projects", "Support contracts"),
        (0.75, 1.0), (4, 14), (0.05, 0.14), (1, 3), (4, 12), (24_000, 40_000),
        (0.04, 0.08), SEASON_FLAT, False,
    ),
}

# Fictional counterparty name parts. None of these are intended to refer to
# real organisations.
SUPPLIER_STEMS = [
    "Oceanic", "Island", "Sunrise", "Mascarene", "Lagoon", "Tropic", "Bluewave",
    "Northpoint", "Cane Field", "Harbourline", "Coral", "Summit", "Evergreen",
    "Palmside", "Southwind", "Anchor", "Keystone", "Meridian",
]
SUPPLIER_SUFFIX = [
    "Wholesale Supplies", "Imports Ltd", "Trading Co", "Distributors",
    "Packaging Ltd", "Foods Ltd", "Merchants", "Supply Chain Ltd",
]
CUSTOMER_STEMS = [
    "Coral Crest", "Filao Bay", "Pailles", "Moka", "Riverside", "Belle Vue",
    "Grand Sable", "Tamarin", "Chamarel", "Beau Bassin", "Trou d'Eau", "Pereybere",
    "Flacq", "Souillac", "Midlands", "Vacoas", "Curepipe Hill", "Rose Belle",
    "Albion", "Poste Lafayette",
]
CUSTOMER_SUFFIX = [
    "Hotels Ltd", "Catering Co", "Office Hub", "Guesthouses", "Clinic",
    "Property Services", "School Trust", "Events Ltd", "Traders", "Holdings",
]


# Payroll as a share of revenue per archetype (drives staff count in random specs).
PAYROLL_SHARE: dict[str, tuple[float, float]] = {
    "retail_shop": (0.10, 0.15), "restaurant": (0.20, 0.28), "salon": (0.28, 0.38), "clothing": (0.10, 0.16),
    "electronics": (0.06, 0.09), "wholesaler": (0.04, 0.07), "service_company": (0.32, 0.45),
}
