"""Seed the SYNTHETIC demo tenants (idempotent: wipes and recreates demo data).

    python scripts/seed_demo.py

Creates:
  * Coastal Home & Kitchen Ltd (fictional retailer, main demo story)
  * Tamarind Cafe (fictional restaurant, used to demonstrate tenant isolation)
  * demo users for each role (see README "Demo accounts")
"""

from __future__ import annotations

import sys
from datetime import date, datetime, timezone
from decimal import Decimal

import _paths  # noqa: F401
import pandas as pd
from sqlalchemy import select, text

from app.db.session import SessionLocal, engine, set_tenant
from app.models import (
    Business,
    Invoice,
    Membership,
    Opportunity,
    OpportunityEvent,
    Role,
    Transaction,
    User,
)
from app.opportunities.engine import EngineContext, detect_overlapping_tools
from app.security.passwords import hash_password
from app.services import audit_service, import_service, opportunity_service
from app.services.analysis_service import get_analysis, invalidate
from app.synthetic.demo import coastal_spec, tamarind_spec
from app.synthetic.generator import generate

UTC = timezone.utc  # datetime.UTC needs Python 3.11+

DEMO_PASSWORD = "Coastal-Demo-2026!"  # noqa: S105 - documented demo account, synthetic data only
USERS = [
    ("owner@coastal.demo", "Nadia Ramsamy", "COASTAL", Role.owner),
    ("accountant@coastal.demo", "Kevin Li Kwong", "COASTAL", Role.accountant),
    ("viewer@coastal.demo", "Sara Appadoo", "COASTAL", Role.viewer),
    ("owner@tamarind.demo", "Yusuf Joomun", "TAMARIND", Role.owner),
]
TENANT_TABLES = ["scenarios", "opportunity_events", "opportunities", "proposed_changes", "import_rows",
                 "transactions", "import_batches", "invoices", "predictions"]

# Deliberate imperfections so the Data Health workflow has real work to do.
UNCATEGORISE = {("Transport & logistics", "2026-08"), ("Transport & logistics", "2026-09"),
                ("Repairs & maintenance", "2026-07")}


def wipe() -> None:
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE " + ", ".join(TENANT_TABLES) + ", refresh_tokens, memberships, users, "
                          "businesses CASCADE"))


def insert_business(key: str, spec, label: str = "synthetic_demo") -> Business:  # type: ignore[no-untyped-def]
    gen = generate(spec)
    db = SessionLocal()
    b = Business(name=spec.name, sector=spec.archetype.sector, currency="MUR",
                 opening_cash=Decimal(str(round(spec.opening_cash, 2))), opening_date=spec.start, data_label=label)
    db.add(b)
    db.commit()
    set_tenant(db, b.id)
    tx = gen.transactions
    rows = []
    uncategorised_done: set[tuple[str, str]] = set()
    for r in tx.itertuples(index=False):
        cat = r.category
        month = pd.Timestamp(r.date).strftime("%Y-%m")
        if key == "COASTAL" and (cat, month) in UNCATEGORISE and (cat, month) not in uncategorised_done:
            uncategorised_done.add((cat, month))
            cat = "Uncategorised"
        cp = r.counterparty if isinstance(r.counterparty, str) else None
        rows.append(Transaction(
            business_id=b.id, txn_date=pd.Timestamp(r.date).date(), direction=r.direction,
            amount=Decimal(f"{r.amount:.2f}"), category=cat,
            subcategory=r.subcategory if isinstance(r.subcategory, str) else None,
            description=str(r.description)[:300], counterparty=cp,
            counterparty_type=r.counterparty_type if isinstance(r.counterparty_type, str) else None,
            reference=r.reference if isinstance(r.reference, str) else None,
            payment_method=r.payment_method, source="seed", external_ref=r.txn_ref))
    db.add_all(rows)
    for inv in gen.invoices.itertuples(index=False):
        db.add(Invoice(business_id=b.id, invoice_no=inv.invoice_no, customer=inv.customer,
                       issue_date=inv.issue_date.date(), due_date=inv.due_date.date(),
                       amount=Decimal(f"{inv.amount:.2f}"),
                       paid_date=None if pd.isna(inv.paid_date) else inv.paid_date.date()))
    db.commit()
    db.close()
    print(f"  {spec.name}: {len(rows):,} transactions, {len(gen.invoices):,} invoices")
    return b


def seed_history(business: Business, owner: User, accountant: User) -> None:
    """Replay the engine on data up to 3 March 2026 to recreate the completed
    'overlapping accounting tools' opportunity, then record the real lifecycle
    the owner followed (the subscription stops appearing in the ledger after May)."""
    db = SessionLocal()
    set_tenant(db, business.id)
    a = get_analysis(db, business)
    hist_as_of = pd.Timestamp("2026-03-03")
    f = detect_overlapping_tools(EngineContext(ledger=a.ledger, as_of=hist_as_of, data_health=95))
    if f is None:
        print("  ! historical opportunity not detected - check the demo spec")
        db.close()
        return
    f.priority_score = 1.0
    [o] = opportunity_service.upsert_findings(db, business.id, a, [f], hist_as_of.date(), None, mark_inactive=False)
    o.detected_at = datetime(2026, 3, 4, 7, 30, tzinfo=UTC)
    o.provenance = {**o.provenance, "data_window": [str(a.ledger.start.date()), "2026-03-03"],
                    "note": "Detected on the data available on 3 Mar 2026 (replayed by the seed script)."}
    o.status = "completed"
    o.action_started_at = date(2026, 5, 12)
    o.completed_at = date(2026, 6, 5)
    db.flush()
    db.execute(text("UPDATE opportunity_events SET created_at = :t WHERE opportunity_id = :o"),
               {"t": datetime(2026, 3, 4, 7, 30, tzinfo=UTC), "o": o.id})
    steps = [
        ("new", "reviewed", owner, datetime(2026, 3, 6, 9, 12, tzinfo=UTC), None),
        ("reviewed", "planned", accountant, datetime(2026, 3, 10, 14, 5, tzinfo=UTC),
         "Keep CloudBooks (cheaper, already has our history). Cancel LedgerPro at the end of May."),
        ("planned", "in_progress", accountant, datetime(2026, 5, 12, 10, 40, tzinfo=UTC),
         "Cancellation notice sent to LedgerPro; data exported."),
        ("in_progress", "completed", owner, datetime(2026, 6, 5, 16, 20, tzinfo=UTC),
         "Last LedgerPro charge was in May. Nothing billed in June."),
    ]
    for frm, to, who, at, note in steps:
        db.add(OpportunityEvent(business_id=business.id, opportunity_id=o.id, user_id=who.id,
                                event_type="status_change", from_status=frm, to_status=to, note=note, created_at=at))
    o.outcome = opportunity_service.outcome_for(a, o)
    db.commit()
    print(f"  history: '{o.title}' -> outcome {o.outcome.get('status')}")
    db.close()


def main() -> None:
    print("Seeding synthetic demo data (fictional businesses)...")
    wipe()
    coastal = insert_business("COASTAL", coastal_spec())
    tamarind = insert_business("TAMARIND", tamarind_spec())
    db = SessionLocal()
    pw = hash_password(DEMO_PASSWORD)
    users = {}
    for email, name, key, role in USERS:
        u = User(email=email, full_name=name, password_hash=pw, password_changed_at=datetime.now(UTC))
        db.add(u)
        db.flush()
        users[email] = u
        db.add(Membership(user_id=u.id, business_id=(coastal if key == "COASTAL" else tamarind).id, role=role))
    db.commit()

    seed_history(coastal, users["owner@coastal.demo"], users["accountant@coastal.demo"])
    for b in (coastal, tamarind):
        db = SessionLocal()
        set_tenant(db, b.id)
        biz = db.get(Business, b.id)
        invalidate(b.id)
        r = opportunity_service.refresh(db, biz, None)
        n = import_service.sync_ledger_proposals(db, biz, get_analysis(db, biz))
        db.commit()
        opps = db.scalars(select(Opportunity).where(Opportunity.business_id == b.id)).all()
        print(f"  {biz.name}: {len(opps)} opportunities, cash-pressure {r['prediction_band']}, "
              f"{n} data proposals")
        db.close()
    audit_service.record("system.demo_seeded", "security", details={"tenants": 2, "note": "synthetic demo data"})
    print("Done. Sign in with owner@coastal.demo /", DEMO_PASSWORD)


if __name__ == "__main__":
    sys.exit(main())
