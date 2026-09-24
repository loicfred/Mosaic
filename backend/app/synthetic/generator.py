"""Reproducible SYNTHETIC SME transaction generator.

Produces bank-feed style transactions and receivable invoices for a fictional
small business. The same generator drives:

* the ML training panel (many random businesses, see scripts/generate_synthetic.py)
* the hand-designed demo SME (see app/synthetic/demo.py)

All output is synthetic and must be labelled as such wherever it is shown.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date, timedelta

import numpy as np
import pandas as pd

from app.synthetic.profiles import (
    ARCHETYPES,
    CUSTOMER_STEMS,
    CUSTOMER_SUFFIX,
    PAYROLL_SHARE,
    SUPPLIER_STEMS,
    SUPPLIER_SUFFIX,
    ArchetypeProfile,
)

VAT_RATE = 0.15  # Mauritius standard VAT rate
DOW_FACTOR = [0.92, 0.95, 0.98, 1.02, 1.18, 1.32, 0.63]  # Mon..Sun


@dataclass
class CustomerSpec:
    name: str
    weight: float  # share of B2B revenue
    lateness_days: float  # average days paid after due date
    invoice_every_days: int
    terms_days: int = 30


@dataclass
class SupplierSpec:
    name: str
    share: float  # share of COGS purchases
    every_days: int
    weekday: int


@dataclass
class Subscription:
    name: str
    amount: float
    day: int
    start: date
    end: date | None = None
    category: str = "Software & subscriptions"


@dataclass
class Shock:
    """A latent event. Shocks are what make future cash pressure hard to predict."""

    kind: str  # supplier_price | customer_delay | revenue_drop | equipment | rent_increase
    start: date
    magnitude: float
    target: str | None = None
    end: date | None = None


@dataclass
class ScheduledAnomaly:
    kind: str  # duplicate_payment | unusual_amount | new_payee
    on: date
    category: str = "Repairs & maintenance"
    counterparty: str | None = None
    amount: float | None = None
    description: str | None = None


@dataclass
class BusinessSpec:
    key: str
    name: str
    archetype: ArchetypeProfile
    seed: int
    start: date
    end: date
    base_monthly_revenue: float
    growth_annual: float
    product_weights: dict[str, float]
    product_growth: dict[str, float]
    b2b_share: float
    customers: list[CustomerSpec]
    cogs_ratio: float
    suppliers: list[SupplierSpec]
    staff: int
    salary: float
    rent: float
    subscriptions: list[Subscription]
    opening_cash: float
    shocks: list[Shock] = field(default_factory=list)
    loan_payment: float = 0.0
    vat_registered: bool = True
    owner_injects: bool = True
    anomaly_rate: float = 0.2  # expected injected anomalies per month (random businesses)
    # Owners of profitable SMEs withdraw surplus cash; this keeps the cash buffer
    # near a target instead of growing forever. 0 disables drawings.
    drawings_target_months: float = 0.0
    scheduled_anomalies: list[ScheduledAnomaly] = field(default_factory=list)
    marketing_share: float = 0.02
    utilities_base: float = 0.0
    telecom: float = 2_900.0


@dataclass
class GeneratedBusiness:
    spec: BusinessSpec
    transactions: pd.DataFrame
    invoices: pd.DataFrame


# --------------------------------------------------------------------------- helpers


def _daterange(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def _business_day_on_or_before(d: date) -> date:
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def _business_day_on_or_after(d: date) -> date:
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def _month_day(year: int, month: int, day: int) -> date:
    last = calendar.monthrange(year, month)[1]
    return date(year, month, min(day, last))


def _months(start: date, end: date):
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        yield y, m
        m += 1
        if m == 13:
            y, m = y + 1, 1


def _shock_active(shock: Shock, d: date) -> bool:
    return d >= shock.start and (shock.end is None or d <= shock.end)


# --------------------------------------------------------------------------- random spec


def random_spec(key: str, archetype_key: str, seed: int, start: date, end: date) -> BusinessSpec:
    """Draw a random but plausible business for the ML training panel."""
    rng = np.random.default_rng(seed)
    a = ARCHETYPES[archetype_key]
    base = float(rng.uniform(*a.monthly_revenue))
    lines = list(a.product_lines)
    weights = rng.dirichlet(np.ones(len(lines)) * 3)
    product_weights = {ln: float(w) for ln, w in zip(lines, weights, strict=True)}
    product_growth = {ln: float(rng.normal(0.04, 0.12)) for ln in lines}
    b2b_share = float(rng.uniform(*a.b2b_share))

    n_cust = int(rng.integers(a.n_b2b_customers[0], a.n_b2b_customers[1] + 1))
    zipf_a = float(rng.uniform(0.6, 2.0))  # higher -> more concentrated
    raw = 1.0 / np.arange(1, n_cust + 1) ** zipf_a
    cw = raw / raw.sum()
    stems = rng.permutation(CUSTOMER_STEMS)
    customers = [
        CustomerSpec(
            name=f"{stems[i % len(stems)]} {CUSTOMER_SUFFIX[int(rng.integers(len(CUSTOMER_SUFFIX)))]}",
            weight=float(cw[i]),
            lateness_days=float(rng.gamma(2.0, 4.0)),
            invoice_every_days=int(rng.choice([7, 14, 14, 30, 30])),
        )
        for i in range(n_cust)
    ]

    n_sup = int(rng.integers(a.n_suppliers[0], a.n_suppliers[1] + 1))
    sw = rng.dirichlet(np.ones(n_sup) * float(rng.uniform(0.6, 3.0)))
    sstems = rng.permutation(SUPPLIER_STEMS)
    suppliers = [
        SupplierSpec(
            name=f"{sstems[i % len(sstems)]} {SUPPLIER_SUFFIX[int(rng.integers(len(SUPPLIER_SUFFIX)))]}",
            share=float(sw[i]),
            every_days=int(rng.choice([7, 7, 14])),
            weekday=int(rng.integers(0, 5)),
        )
        for i in range(n_sup)
    ]

    salary = float(rng.uniform(*a.salary))
    staff = max(1, round(base * float(rng.uniform(*PAYROLL_SHARE[archetype_key])) / salary))
    rent = round(base * float(rng.uniform(*a.rent_share)), -2)
    subs = [
        Subscription("POS system licence", float(rng.choice([1_450, 1_900, 2_600])), 3, start),
        Subscription("Cloud accounting", float(rng.choice([1_200, 1_650, 2_100])), 7, start),
    ]
    if rng.random() < 0.4:
        s = start + timedelta(days=int(rng.integers(60, 500)))
        subs.append(Subscription("Inventory app", float(rng.choice([1_800, 2_400])), 10, s))

    shocks: list[Shock] = []
    span = (end - start).days

    def rand_day(lo: int = 90) -> date:
        return start + timedelta(days=int(rng.integers(lo, max(lo + 1, span - 10))))

    if rng.random() < 0.55 and suppliers:
        shocks.append(Shock("supplier_price", rand_day(), float(rng.uniform(0.06, 0.28)),
                            target=suppliers[0].name))
    if rng.random() < 0.45 and customers:
        shocks.append(Shock("customer_delay", rand_day(), float(rng.uniform(10, 40)),
                            target=customers[0].name))
    for _ in range(int(rng.poisson(0.8))):
        s = rand_day(60)
        shocks.append(Shock("revenue_drop", s, float(rng.uniform(0.10, 0.35)),
                            end=s + timedelta(days=int(rng.integers(20, 75)))))
    for _ in range(int(rng.poisson(0.6))):
        shocks.append(Shock("equipment", rand_day(30), float(base * rng.uniform(0.2, 0.9))))
    if rng.random() < 0.35:
        shocks.append(Shock("rent_increase", rand_day(), float(rng.uniform(0.05, 0.15))))

    monthly_out_est = base * (1 - 0.05)
    opening_cash = float(monthly_out_est * rng.uniform(0.3, 1.6))

    return BusinessSpec(
        key=key,
        name=f"Synthetic {a.label} #{key}",
        archetype=a,
        seed=seed,
        start=start,
        end=end,
        base_monthly_revenue=base,
        growth_annual=float(rng.normal(0.05, 0.10)),
        product_weights=product_weights,
        product_growth=product_growth,
        b2b_share=b2b_share,
        customers=customers,
        cogs_ratio=float(rng.uniform(*a.cogs_ratio)),
        suppliers=suppliers,
        staff=staff,
        salary=salary,
        rent=rent,
        subscriptions=subs,
        opening_cash=opening_cash,
        shocks=shocks,
        loan_payment=float(round(base * rng.uniform(0.02, 0.06), -2)) if rng.random() < 0.5 else 0.0,
        vat_registered=bool(base > 250_000),
        owner_injects=bool(rng.random() < 0.7),
        drawings_target_months=float(rng.uniform(0.35, 1.4)) if rng.random() < 0.85 else 0.0,
        anomaly_rate=0.25,
        marketing_share=float(rng.uniform(0.005, 0.035)),
        utilities_base=float(base * rng.uniform(0.008, 0.03)),
        telecom=float(rng.choice([1_900, 2_900, 3_900])),
    )


# --------------------------------------------------------------------------- generator


class _Ledger:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def add(self, d: date, direction: str, amount: float, category: str, description: str,
            counterparty: str | None = None, cp_type: str | None = None,
            subcategory: str | None = None, reference: str | None = None,
            method: str = "bank_transfer", anomaly: str | None = None) -> None:
        amount = round(float(amount), 2)
        if amount <= 0:
            return
        self.rows.append({
            "date": d, "direction": direction, "amount": amount, "category": category,
            "subcategory": subcategory, "description": description,
            "counterparty": counterparty, "counterparty_type": cp_type,
            "reference": reference, "payment_method": method, "injected_anomaly": anomaly,
        })


def _desc(rng: np.random.Generator, options: list[str]) -> str:
    text = options[int(rng.integers(len(options)))]
    r = rng.random()
    if r < 0.25:
        return text.upper()
    if r < 0.35:
        return text.lower()
    return text


def _owner_row(d: date, direction: str, amount: float, category: str, description: str) -> dict:
    return {
        "date": pd.Timestamp(d), "direction": direction, "amount": float(amount), "category": category,
        "subcategory": None, "description": description, "counterparty": "Owner",
        "counterparty_type": None, "reference": None, "payment_method": "bank_transfer",
        "injected_anomaly": None,
    }


def generate(spec: BusinessSpec) -> GeneratedBusiness:
    rng = np.random.default_rng(spec.seed)
    led = _Ledger()
    a = spec.archetype
    days = list(_daterange(spec.start, spec.end))
    t0 = spec.start

    # ---- expected daily revenue (used for sales and to size supplier purchases)
    def revenue_multiplier(d: date) -> float:
        m = (1 + spec.growth_annual) ** ((d - t0).days / 365.0)
        m *= a.season[d.month]
        for s in spec.shocks:
            if s.kind == "revenue_drop" and _shock_active(s, d):
                m *= 1 - s.magnitude
        return m

    daily_base = spec.base_monthly_revenue / 30.4
    expected_rev = {d: daily_base * revenue_multiplier(d) for d in days}

    # ---- B2C sales by product line
    b2c = 1.0 - spec.b2b_share
    for d in days if b2c >= 0.05 else []:
        dow = DOW_FACTOR[d.weekday()]
        if d.weekday() == 6 and not a.open_sunday:
            continue
        total = expected_rev[d] * b2c * dow * float(rng.lognormal(0, 0.16))
        yrs = (d - t0).days / 365.0
        w = {ln: spec.product_weights[ln] * (1 + spec.product_growth[ln]) ** yrs for ln in spec.product_weights}
        wsum = sum(w.values())
        for ln, wl in w.items():
            amt = total * wl / wsum * float(rng.lognormal(0, 0.10))
            if amt < 50:
                continue
            method = "card" if rng.random() < 0.6 else "cash"
            label = "Card settlement" if method == "card" else "Cash deposit"
            led.add(d, "inflow", amt, "Sales", _desc(rng, [f"{label} - {ln}", f"POS sales {ln}", f"{ln} sales {d:%d/%m}"]),
                    subcategory=ln, method=method)

    # ---- B2B invoices and their payments
    invoices: list[dict] = []
    inv_no = 1000
    b2b_monthly = spec.base_monthly_revenue * spec.b2b_share
    for c in spec.customers:
        nxt = spec.start + timedelta(days=int(rng.integers(0, c.invoice_every_days)))
        while nxt <= spec.end:
            mult = revenue_multiplier(nxt)
            amount = b2b_monthly * c.weight * c.invoice_every_days / 30.4 * mult * float(rng.lognormal(0, 0.12))
            delay_extra = 0.0
            for s in spec.shocks:
                if s.kind == "customer_delay" and s.target == c.name and nxt >= s.start:
                    delay_extra += s.magnitude
            pay_after = max(0.0, c.terms_days + c.lateness_days + delay_extra + float(rng.normal(0, 4)))
            inv_no += 1
            paid = nxt + timedelta(days=int(round(pay_after)))
            invoices.append({
                "invoice_no": f"INV-{inv_no}", "customer": c.name, "issue_date": nxt,
                "due_date": nxt + timedelta(days=c.terms_days), "amount": round(amount, 2),
                "paid_date": paid if paid <= spec.end else None,
            })
            if paid <= spec.end:
                led.add(paid, "inflow", amount, "Sales",
                        _desc(rng, [f"Payment INV-{inv_no} {c.name}", f"{c.name} - settlement INV-{inv_no}",
                                    f"Transfer from {c.name} ref INV-{inv_no}"]),
                        counterparty=c.name, cp_type="customer", subcategory="Trade accounts",
                        reference=f"INV-{inv_no}")
            nxt += timedelta(days=c.invoice_every_days + int(rng.integers(-2, 3)))

    # ---- supplier purchases (COGS)
    total_rev_expected = {d: expected_rev[d] for d in days}
    for sup in spec.suppliers:
        d = spec.start + timedelta(days=(sup.weekday - spec.start.weekday()) % 7)
        n = 0
        while d <= spec.end:
            window = [total_rev_expected.get(d - timedelta(days=k), daily_base) for k in range(sup.every_days)]
            price = 1.0
            for s in spec.shocks:
                if s.kind == "supplier_price" and s.target == sup.name and d >= s.start:
                    price *= 1 + s.magnitude
            amt = sum(window) * spec.cogs_ratio * sup.share * price * float(rng.lognormal(0, 0.09))
            n += 1
            led.add(d, "outflow", amt, "Inventory & supplies",
                    _desc(rng, [f"Payment {sup.name} inv {n:04d}", f"{sup.name} stock purchase",
                                f"Supplier payment - {sup.name}"]),
                    counterparty=sup.name, cp_type="supplier", reference=f"PO-{n:04d}")
            d += timedelta(days=sup.every_days)

    # ---- monthly fixed and semi-fixed costs
    rent = spec.rent
    for y, m in _months(spec.start, spec.end):
        mon = date(y, m, 1)
        label = mon.strftime("%b %Y")
        raise_factor = 1.03 ** (y - spec.start.year)
        cur_rent = rent
        for s in spec.shocks:
            if s.kind == "rent_increase" and mon >= s.start:
                cur_rent = rent * (1 + s.magnitude)
        rd = _business_day_on_or_after(_month_day(y, m, 1 if m != 1 else 2))
        if spec.start <= rd <= spec.end:
            led.add(rd, "outflow", cur_rent, "Rent",
                    _desc(rng, [f"Shop rent {label}", f"Lease payment {label}", f"Rent {label} - landlord"]),
                    counterparty="Landlord - Commercial lease", cp_type="supplier")
        pay_day = _business_day_on_or_before(_month_day(y, m, 26))
        payroll = spec.staff * spec.salary * raise_factor * float(rng.normal(1, 0.015))
        if spec.start <= pay_day <= spec.end:
            led.add(pay_day, "outflow", payroll, "Payroll",
                    _desc(rng, [f"Salaries {label}", f"Staff wages {label}", f"Payroll {label}"]))
            led.add(pay_day + timedelta(days=3) if pay_day + timedelta(days=3) <= spec.end else pay_day,
                    "outflow", payroll * 0.085, "Payroll",
                    _desc(rng, [f"PAYE/CSG contributions {label}", f"MRA payroll contributions {label}"]),
                    counterparty="MRA", cp_type="supplier")
        if m == 12:
            bonus_day = _business_day_on_or_before(_month_day(y, m, 20))
            if spec.start <= bonus_day <= spec.end:
                led.add(bonus_day, "outflow", spec.staff * spec.salary * raise_factor, "Payroll",
                        _desc(rng, ["End of year bonus (13th month)", "13th month bonus payment"]))
        ed = _month_day(y, m, 12)
        if spec.start <= ed <= spec.end and spec.utilities_base > 0:
            summer = 1.25 if m in (12, 1, 2, 3) else 1.0
            led.add(ed, "outflow", spec.utilities_base * summer * float(rng.lognormal(0, 0.07)), "Utilities",
                    _desc(rng, ["CEB electricity bill", f"Electricity {label} CEB", "CEB ELEC PAYMENT"]),
                    counterparty="CEB Electricity", cp_type="supplier")
        if m % 2 == 0:
            wd = _month_day(y, m, 18)
            if spec.start <= wd <= spec.end:
                led.add(wd, "outflow", spec.utilities_base * 0.12 * float(rng.lognormal(0, 0.1)), "Utilities",
                        _desc(rng, ["CWA water bill", f"Water {label}"]), counterparty="CWA Water", cp_type="supplier")
        td = _month_day(y, m, 5)
        if spec.start <= td <= spec.end:
            led.add(td, "outflow", spec.telecom, "Telecom & internet",
                    _desc(rng, ["FibreNet business broadband", f"Internet & phone {label}", "FIBRENET TELECOM"]),
                    counterparty="FibreNet Telecom", cp_type="supplier")
        for sub in spec.subscriptions:
            sd = _month_day(y, m, sub.day)
            if sd >= sub.start and (sub.end is None or sd <= sub.end) and spec.start <= sd <= spec.end:
                led.add(sd, "outflow", sub.amount, sub.category,
                        _desc(rng, [f"{sub.name} subscription", f"{sub.name} monthly plan", f"{sub.name} {label}"]),
                        counterparty=sub.name, cp_type="supplier", method="card")
        md = _month_day(y, m, 8)
        if spec.start <= md <= spec.end and spec.marketing_share > 0:
            boost = 1.6 if m in (11, 12) else 1.0
            led.add(md, "outflow",
                    spec.base_monthly_revenue * spec.marketing_share * boost * float(rng.lognormal(0, 0.25)),
                    "Marketing", _desc(rng, ["Social media ads", "Facebook ads campaign", "Radio advert slot",
                                             "Flyers printing & distribution"]),
                    counterparty="Adverta Media", cp_type="supplier", method="card")
        bd = _month_day(y, m, 28)
        if spec.start <= bd <= spec.end:
            led.add(bd, "outflow", 350 + spec.base_monthly_revenue * 0.0012 * float(rng.lognormal(0, 0.1)),
                    "Bank fees", _desc(rng, ["Bank charges", "Monthly account & card fees", "MERCHANT FEES"]),
                    counterparty="Bank", cp_type="supplier")
        if spec.loan_payment > 0:
            ld = _month_day(y, m, 15)
            if spec.start <= ld <= spec.end:
                led.add(ld, "outflow", spec.loan_payment, "Loan repayment",
                        _desc(rng, ["Loan instalment", "Business loan repayment", "LOAN REPAYMENT"]),
                        counterparty="Bank", cp_type="supplier")
        if m in (3, 6, 9, 12):
            pd_ = _month_day(y, m, 22)
            if spec.start <= pd_ <= spec.end:
                led.add(pd_, "outflow", 9_500 + spec.base_monthly_revenue * 0.004, "Professional fees",
                        _desc(rng, ["Accountant quarterly fee", "Accounting & payroll services"]),
                        counterparty="Ledger & Co Accountants", cp_type="supplier")
        if m == 1:
            idt = _month_day(y, m, 14)
            if spec.start <= idt <= spec.end:
                led.add(idt, "outflow", spec.base_monthly_revenue * 0.035, "Insurance",
                        _desc(rng, ["Annual business insurance premium", "Insurance renewal"]),
                        counterparty="Harbour Mutual Insurance", cp_type="supplier")
        # occasional repairs and transport
        for _ in range(int(rng.poisson(0.5))):
            rd2 = _month_day(y, m, int(rng.integers(1, 28)))
            if spec.start <= rd2 <= spec.end:
                led.add(rd2, "outflow", spec.base_monthly_revenue * 0.006 * float(rng.lognormal(0, 0.35)),
                        "Repairs & maintenance",
                        _desc(rng, ["Maintenance call-out", "Repair works", "Aircon servicing", "Plumbing repair"]),
                        counterparty="Tech Fix Services", cp_type="supplier")
        for _ in range(int(rng.poisson(2))):
            xd = _month_day(y, m, int(rng.integers(1, 28)))
            if spec.start <= xd <= spec.end:
                led.add(xd, "outflow", spec.base_monthly_revenue * 0.003 * float(rng.lognormal(0, 0.3)),
                        "Transport & logistics", _desc(rng, ["Delivery charges", "Courier services", "Fuel"]),
                        counterparty="QuickMove Logistics", cp_type="supplier", method="card")

    for s in spec.shocks:
        if s.kind == "equipment" and spec.start <= s.start <= spec.end:
            led.add(s.start, "outflow", s.magnitude, "Equipment",
                    _desc(rng, ["Equipment purchase", "New shop fittings", "Display units & shelving"]),
                    counterparty="ProFit Equipment Ltd", cp_type="supplier")

    df = pd.DataFrame(led.rows)

    # ---- VAT: quarterly return paid on the 20th of the following month
    if spec.vat_registered:
        dts = pd.to_datetime(df["date"])
        for y, m in _months(spec.start, spec.end):
            if m not in (1, 4, 7, 10):
                continue
            q_end = date(y, m, 1) - timedelta(days=1)
            q_start = date(q_end.year, q_end.month, 1) - pd.DateOffset(months=2)
            q_start = q_start.date()
            if q_start < spec.start:
                continue
            mask = (dts.dt.date >= q_start) & (dts.dt.date <= q_end)
            sales = df.loc[mask & (df.category == "Sales"), "amount"].sum()
            purchases = df.loc[mask & (df.category == "Inventory & supplies"), "amount"].sum()
            vat = max(0.0, VAT_RATE / (1 + VAT_RATE) * (sales - purchases))
            vd = _month_day(y, m, 20)
            if vd <= spec.end:
                led.add(vd, "outflow", vat, "Taxes (VAT)",
                        _desc(rng, [f"VAT return Q{(q_end.month - 1) // 3 + 1} {q_end.year}", "MRA VAT payment"]),
                        counterparty="MRA", cp_type="supplier")

    # ---- injected anomalies (ground truth kept for evaluation only)
    months = list(_months(spec.start, spec.end))
    base_rows = list(led.rows)
    out_rows = [r for r in base_rows if r["direction"] == "outflow" and r["category"] == "Inventory & supplies"]
    for y, m in months:
        if rng.random() >= spec.anomaly_rate:
            continue
        kind = rng.choice(["duplicate_payment", "unusual_amount", "new_payee"])
        d = _month_day(y, m, int(rng.integers(1, 28)))
        if not (spec.start <= d <= spec.end):
            continue
        if kind == "duplicate_payment" and out_rows:
            src = out_rows[int(rng.integers(len(out_rows)))]
            dup = dict(src)
            dup["injected_anomaly"] = "duplicate_payment"
            led.rows.append(dup)
        elif kind == "unusual_amount":
            led.add(d, "outflow", spec.base_monthly_revenue * 0.006 * float(rng.uniform(5, 10)),
                    "Repairs & maintenance", "Emergency repair works", counterparty="Tech Fix Services",
                    cp_type="supplier", anomaly="unusual_amount")
        else:
            led.add(d, "outflow", spec.base_monthly_revenue * float(rng.uniform(0.04, 0.12)), "Other expenses",
                    _desc(rng, ["Transfer - consultancy", "Payment misc services"]),
                    counterparty=f"Unknown Payee {int(rng.integers(100, 999))}", cp_type="supplier",
                    anomaly="new_payee")
    for sa in spec.scheduled_anomalies:
        if sa.kind == "duplicate_payment":
            match = [r for r in led.rows if r["date"] == sa.on and r["counterparty"] == sa.counterparty]
            if match:
                dup = dict(match[0])
                dup["injected_anomaly"] = "duplicate_payment"
                led.rows.append(dup)
        else:
            led.add(sa.on, "outflow", sa.amount or 0, sa.category, sa.description or "Payment",
                    counterparty=sa.counterparty, cp_type="supplier", anomaly=sa.kind)

    df = pd.DataFrame(led.rows)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["date", "direction", "amount"], ascending=[True, True, False]).reset_index(drop=True)

    # ---- owner behaviour: injections when cash runs out, drawings when surplus builds
    if spec.owner_injects or spec.drawings_target_months > 0:
        extra = []
        signed = np.where(df["direction"] == "inflow", df["amount"], -df["amount"])
        daily = pd.Series(signed, index=df["date"]).groupby(level=0).sum()
        daily = daily.reindex(pd.date_range(df["date"].min(), df["date"].max(), freq="D"), fill_value=0.0)
        cash = spec.opening_cash
        monthly_out = spec.base_monthly_revenue * 0.95
        pending = 0.0
        for d, net in daily.items():
            cash += net + pending
            pending = 0.0
            nd = (d + pd.Timedelta(days=1)).date()
            if nd > spec.end:
                continue
            if spec.owner_injects and cash < -0.05 * spec.base_monthly_revenue and rng.random() < 0.85:
                amt = round(-cash + spec.base_monthly_revenue * float(rng.uniform(0.3, 0.6)), -3)
                extra.append(_owner_row(nd, "inflow", amt, "Owner contribution", "Owner capital injection"))
                pending = amt
            elif (spec.drawings_target_months > 0 and d.day == 28
                  and cash > spec.drawings_target_months * monthly_out):
                amt = round((cash - spec.drawings_target_months * monthly_out) * float(rng.uniform(0.4, 0.9)), -3)
                if amt > 0:
                    extra.append(_owner_row(nd, "outflow", amt, "Owner drawings", "Owner drawings / dividend"))
                    pending = -amt
        if extra:
            df = pd.concat([df, pd.DataFrame(extra)], ignore_index=True)
            df = df.sort_values(["date", "direction", "amount"], ascending=[True, True, False]).reset_index(drop=True)

    df.insert(0, "txn_ref", [f"{spec.key}-{i:06d}" for i in range(len(df))])
    inv = pd.DataFrame(invoices)
    if not inv.empty:
        inv["issue_date"] = pd.to_datetime(inv["issue_date"])
        inv["due_date"] = pd.to_datetime(inv["due_date"])
        inv["paid_date"] = pd.to_datetime(inv["paid_date"])
    else:
        inv = pd.DataFrame(columns=["invoice_no", "customer", "issue_date", "due_date", "amount", "paid_date"])
    return GeneratedBusiness(spec=spec, transactions=df, invoices=inv)
