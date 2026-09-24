-- Run once as the PostgreSQL superuser (e.g. in psql or pgAdmin):
--   psql -U postgres -f scripts/create_database.sql
-- The application role is deliberately NOT a superuser and does NOT have
-- BYPASSRLS, so PostgreSQL row-level security applies to it.
CREATE ROLE opportunityos LOGIN PASSWORD 'change-me-locally' NOSUPERUSER NOBYPASSRLS NOCREATEROLE;
CREATE DATABASE opportunityos OWNER opportunityos;
CREATE DATABASE opportunityos_test OWNER opportunityos;
