"""Row-level security (tenant isolation) and append-only audit log.

Revision ID: 0002
Revises: 0001
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

# Kept literal (not imported from app code) so this migration stays reproducible.
TENANT_TABLES = (
    "transactions", "invoices", "import_batches", "import_rows", "proposed_changes",
    "opportunities", "opportunity_events", "scenarios", "predictions",
)


def upgrade() -> None:
    # Every tenant table only exposes rows whose business_id matches the per-
    # transaction setting app.business_id. FORCE makes the policy apply to the
    # table owner too. If the setting is absent, no rows are visible (fail closed).
    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} "
            "USING (business_id = NULLIF(current_setting('app.business_id', true), '')::uuid) "
            "WITH CHECK (business_id = NULLIF(current_setting('app.business_id', true), '')::uuid)"
        )
    # The audit log is append-only: UPDATE and DELETE are rejected by a trigger.
    op.execute("""
        CREATE OR REPLACE FUNCTION audit_events_append_only() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'audit_events is append-only';
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("CREATE TRIGGER audit_events_no_update BEFORE UPDATE OR DELETE ON audit_events "
               "FOR EACH ROW EXECUTE FUNCTION audit_events_append_only()")


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_events_no_update ON audit_events")
    op.execute("DROP FUNCTION IF EXISTS audit_events_append_only()")
    for table in TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
