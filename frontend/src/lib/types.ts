export type Role = 'owner' | 'accountant' | 'viewer'

export interface Me {
  id: string
  email: string
  full_name: string
  role: Role
  business: { id: string; name: string; sector: string; currency: string; data_label: string }
  memberships: { business_id: string; business_name: string; role: Role }[]
  permissions: string[]
}

export interface Contribution {
  feature: string
  label: string
  value: number
  display: string
  contribution: number
  direction: string
}

export interface Prediction {
  mode: 'model' | 'deterministic' | 'insufficient_data'
  band: 'LOW' | 'MODERATE' | 'HIGH' | 'UNKNOWN'
  probability: number | null
  model_version: string | null
  reason: string
  contributions?: Contribution[]
  top_drivers?: Contribution[]
  features?: Record<string, number>
  thresholds?: { moderate_threshold: number; high_threshold: number }
  test_roc_auc?: number
  as_of?: string
}

export interface ProjectionSummary {
  starting_cash: number
  cash_day_30: number
  cash_day_60: number
  cash_day_90: number
  lowest_cash: number
  lowest_cash_date: string
  buffer_threshold: number
  days_below_buffer: number
  first_date_below_buffer: string | null
  total_inflow: number
  total_outflow: number
}

export interface MonthRow {
  month: string
  partial: boolean
  days_covered: number
  revenue: number
  cost_of_goods: number
  operating_expenses: number
  tax: number
  expenses: number
  gross_margin_pct: number
  net_cash_flow: number
  closing_cash: number
}

export interface Overview {
  as_of: string
  data_window: [string, string]
  cash: { balance: number; balance_30d_ago: number; buffer_days: number; buffer_threshold: number }
  kpis_90d: {
    period: [string, string]
    previous_period: [string, string]
    revenue: number
    revenue_change_pct: number | null
    expenses: number
    expenses_change_pct: number | null
    gross_margin_pct: number
    gross_margin_change_pp: number
    operating_cash_flow: number
    operating_cash_flow_prev: number
  }
  cash_series: { date: string; cash: number; ma7: number; ma30: number }[]
  projection_series: { date: string; cash: number }[]
  projection: ProjectionSummary
  monthly: MonthRow[]
  prediction: Prediction
  data_health: { score: number; issues: number }
}

export interface Evidence {
  label: string
  value: unknown
  display: string
  detail?: string
  period?: string
  compared_to?: string
  source?: string
  contribution?: number
  transaction_ids?: string[]
}

export interface Outcome {
  status: 'achieved' | 'partial' | 'no_change' | 'worsened' | 'too_early' | 'not_started' | 'insufficient_data' | 'manual'
  message: string
  metric?: string
  metric_label?: string
  unit?: string
  baseline?: number
  current?: number
  change?: number
  expected_change?: number | null
  progress_pct?: number
  window?: [string, string]
  days_observed?: number
  caveat?: string
}

export type OppStatus = 'new' | 'reviewed' | 'planned' | 'in_progress' | 'completed' | 'dismissed'

export interface Opportunity {
  id: string
  detector: string
  kind: 'risk' | 'opportunity'
  category: string
  title: string
  summary: string
  why_it_matters: string
  explanation: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  priority_score: number
  confidence: number
  confidence_basis: Record<string, unknown>
  impact_low: number | null
  impact_high: number | null
  impact_kind: 'saving' | 'cash_release' | 'exposure' | 'shortfall' | 'revenue_upside' | 'none'
  impact_basis: string | null
  evidence: Evidence[]
  supporting_records: Record<string, unknown>
  actions: { title: string; detail: string; effort: string }[]
  scenario_preset: { name: string; assumptions: Partial<Assumptions> } | null
  provenance: Record<string, unknown>
  target: { key: string; label: string; unit: string; better: string; params: Record<string, string> } | null
  baseline_value: number | null
  expected_change: number | null
  status: OppStatus
  is_active: boolean
  action_started_at: string | null
  completed_at: string | null
  outcome: Outcome | null
  data_as_of: string
  detected_at: string
  updated_at: string
  events?: { id: string; type: string; from: string | null; to: string | null; note: string | null; by: string | null; at: string }[]
}

export interface Assumptions {
  supplier_cost_pct: number
  price_pct: number
  sales_volume_pct: number
  recurring_expense_pct: number
  collection_days_change: number
  marketing_spend_pct: number
  staffing_cost_pct: number
  inventory_spend_pct: number
}

export interface Lever {
  key: keyof Assumptions
  label: string
  min: number
  max: number
  step: number
  unit: string
}

export interface SimulationResult {
  as_of: string
  horizon_days: number
  assumptions: Assumptions
  baseline: ProjectionSummary
  scenario: ProjectionSummary
  difference: Record<string, number>
  series: { date: string; baseline: number; scenario: number }[]
  breakdown: { driver: string; baseline: number; scenario: number; difference: number }[]
  method_notes: string[]
  label: string
  drivers: Record<string, number>
  backtest_median_error_pct: number | null
}

export interface Transaction {
  id: string
  date: string
  direction: 'inflow' | 'outflow'
  amount: number
  category: string
  subcategory: string | null
  description: string
  counterparty: string | null
  reference: string | null
  source: string
  is_anomaly: boolean
  anomaly_reason: string | null
  duplicate_group: string | null
  excluded: boolean
}

export interface TransactionDetail extends Transaction {
  counterparty_type: string | null
  payment_method: string | null
  anomaly_score: number | null
  import_batch_id: string | null
  created_at: string
  related_opportunities: { id: string; title: string; status: string }[]
  counterparty_history: {
    count: number
    median: number | null
    total: number
    recent: { id: string; date: string; amount: number }[]
  } | null
  duplicates: { id: string; date: string; amount: number; excluded: boolean }[]
  pending_changes: { id: string; change_type: string; new_value: string; reason: string; status: string }[]
}

export interface Facets {
  categories: { name: string; count: number }[]
  counterparties: { name: string; count: number }[]
  date_min: string | null
  date_max: string | null
}

export interface HealthCheck {
  key: string
  status: 'ok' | 'warning' | 'info'
  label: string
  detail: string
  count?: number
}

export interface LedgerHealth {
  /** null, with no components or weights, while the business has no transactions. */
  score: number | null
  components?: Record<string, number>
  weights?: Record<string, number>
  checks: HealthCheck[]
  totals: Record<string, number | string>
  pending_changes: number
  as_of: string
}

export interface Proposal {
  id: string
  target_type: 'transaction' | 'import_row'
  target_id: string
  change_type: 'set_category' | 'exclude_duplicate' | 'set_counterparty'
  field: string
  old_value: string | null
  new_value: string | null
  reason: string
  confidence: number | null
  source: string
  status: 'pending' | 'approved' | 'rejected' | 'expired'
  decided_by: string | null
  decided_at: string | null
  target: Record<string, string | number | null>
  batch_id: string | null
}

export interface ImportRowOut {
  id: string
  row_number: number
  raw: Record<string, string>
  parsed: Record<string, string | null>
  status: 'valid' | 'warning' | 'error' | 'duplicate'
  issues: { code: string; field: string; message: string; level: string }[]
  include: boolean
}

export interface ImportBatch {
  id: string
  filename: string
  status: 'validated' | 'committed' | 'discarded'
  row_count: number
  valid_count: number
  warning_count: number
  error_count: number
  duplicate_count: number
  committed_rows: number
  health: {
    score: number
    components: Record<string, number>
    errors: number
    duplicates: number
    uncategorised: number
    missing_payee: number
    issue_counts: Record<string, number>
    valid_dates_pct: number
    column_mapping?: Record<string, string>
  }
  created_at: string
  uploaded_by: string | null
  committed_at: string | null
  file_sha256: string
  rows?: ImportRowOut[]
  proposals?: Proposal[]
  pending_duplicates?: number
  pending_changes?: number
}

export interface AuditEvent {
  id: number
  at: string
  event: string
  category: string
  outcome: 'success' | 'failure' | 'denied'
  actor: string | null
  resource_type: string | null
  resource_id: string | null
  details: Record<string, unknown>
  ip_hash: string | null
}
