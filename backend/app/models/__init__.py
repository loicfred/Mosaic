"""SQLAlchemy models. Importing this package registers every table on Base.metadata."""

from app.models.audit import AuditEvent
from app.models.base import TENANT_TABLES, Base
from app.models.finance import Invoice, Transaction
from app.models.identity import Business, Membership, RefreshToken, Role, User
from app.models.opportunity import OPPORTUNITY_STATUSES, Opportunity, OpportunityEvent
from app.models.quality import ImportBatch, ImportRow, ProposedChange
from app.models.scenario import Prediction, Scenario

__all__ = [
    "AuditEvent", "Base", "TENANT_TABLES", "Invoice", "Transaction", "Business", "Membership",
    "RefreshToken", "Role", "User", "OPPORTUNITY_STATUSES", "Opportunity", "OpportunityEvent",
    "ImportBatch", "ImportRow", "ProposedChange", "Prediction", "Scenario",
]
