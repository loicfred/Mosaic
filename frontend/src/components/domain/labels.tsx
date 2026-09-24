import {
  AlertCircle,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  CheckCircle2,
  Circle,
  Clock,
  FlaskConical,
  Gauge,
  Info,
  OctagonAlert,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Tip } from '@/components/ui/tooltip'
import { cn } from '@/lib/cn'
import { murCompact, pct } from '@/lib/format'
import type { Opportunity, OppStatus, Outcome } from '@/lib/types'
import { IMPACT_LABEL, STATUS_META } from './meta'

/** Every number shown in the product belongs to exactly one of these kinds. */
export function DataKind({ kind, className }: { kind: 'actual' | 'projected' | 'simulated' | 'predicted'; className?: string }) {
  const map = {
    actual: { label: 'Actual', tip: 'Recorded transactions from your ledger.', icon: <span className="size-2 rounded-sm bg-actual" /> },
    projected: {
      label: 'Projected',
      tip: 'Deterministic cash projection from current run-rates. Not a recorded value.',
      icon: <span className="h-0 w-3 border-t-2 border-dashed border-projected" />,
    },
    simulated: { label: 'Simulated', tip: 'Scenario output. Never written to your records.', icon: <FlaskConical /> },
    predicted: { label: 'Predicted', tip: 'Machine-learning estimate with a probability.', icon: <Gauge /> },
  }[kind]
  return (
    <Tip content={map.tip}>
      <Badge
        tone={kind === 'simulated' ? 'simulated' : kind === 'predicted' ? 'brand' : 'neutral'}
        className={cn('cursor-help', className)}
      >
        {map.icon}
        {map.label}
      </Badge>
    </Tip>
  )
}

const SEV = {
  critical: { tone: 'bad', icon: OctagonAlert, label: 'Critical' },
  high: { tone: 'serious', icon: AlertTriangle, label: 'High' },
  medium: { tone: 'warn', icon: AlertCircle, label: 'Medium' },
  low: { tone: 'neutral', icon: Info, label: 'Low' },
} as const

export function SeverityBadge({ severity }: { severity: Opportunity['severity'] }) {
  const s = SEV[severity]
  const Icon = s.icon
  return (
    <Badge tone={s.tone}>
      <Icon aria-hidden /> {s.label}
    </Badge>
  )
}

const BAND = {
  HIGH: { tone: 'bad', icon: OctagonAlert, label: 'High' },
  MODERATE: { tone: 'warn', icon: AlertTriangle, label: 'Moderate' },
  LOW: { tone: 'good', icon: CheckCircle2, label: 'Low' },
  UNKNOWN: { tone: 'neutral', icon: Info, label: 'Not enough data' },
} as const

export function BandBadge({ band, large }: { band: keyof typeof BAND; large?: boolean }) {
  const b = BAND[band]
  const Icon = b.icon
  return (
    <Badge tone={b.tone} className={large ? 'whitespace-nowrap px-2.5 py-1 text-sm [&_svg]:size-4' : 'whitespace-nowrap'}>
      <Icon aria-hidden /> {b.label} risk
    </Badge>
  )
}

export function StatusBadge({ status }: { status: OppStatus }) {
  const m = STATUS_META[status]
  const Icon = m.icon
  return (
    <Badge tone={m.tone}>
      <Icon aria-hidden /> {m.label}
    </Badge>
  )
}

function confidenceTip(basis?: Record<string, unknown>) {
  const isModel = basis?.method === 'model_probability'
  return isModel ? (
    <span>{String(basis?.note ?? 'Calibrated model probability.')}</span>
  ) : basis ? (
    <span>
      Evidence score = 0.5 × strength ({pctOf(basis.strength)}) + 0.2 × history ({pctOf(basis.coverage)}) + 0.2 × data quality (
      {pctOf(basis.data_quality)}) + 0.1 × consistency ({pctOf(basis.consistency)}), capped at 95%.
      {basis.note ? (
        <>
          <br />
          {String(basis.note)}
        </>
      ) : null}
    </span>
  ) : (
    'Confidence'
  )
}

/** Quiet confidence: a small figure with the full breakdown on hover or focus. */
export function ConfidenceNote({ value, basis }: { value: number; basis?: Record<string, unknown> }) {
  const isModel = basis?.method === 'model_probability'
  return (
    <Tip content={confidenceTip(basis)}>
      <button type="button" className="cursor-help text-xs text-ink-3 underline decoration-dotted underline-offset-2 hover:text-ink-2">
        <span className="tnum">{Math.round(value * 100)}%</span> {isModel ? 'probability' : 'confidence'}
      </button>
    </Tip>
  )
}

export function ConfidenceMeter({ value, basis }: { value: number; basis?: Record<string, unknown> }) {
  const pctV = Math.round(value * 100)
  const tone = value >= 0.75 ? 'bg-brand-700' : value >= 0.5 ? 'bg-brand-700/70' : 'bg-brand-700/40'
  const isModel = basis?.method === 'model_probability'
  const content = confidenceTip(basis)
  return (
    <Tip content={content}>
      <div className="flex cursor-help items-center gap-2" aria-label={`${isModel ? 'Probability' : 'Confidence'} ${pctV}%`}>
        <div className="h-1.5 w-16 overflow-hidden rounded-full bg-brand-100">
          <div className={cn('h-full rounded-full', tone)} style={{ width: `${pctV}%` }} />
        </div>
        <span className="tnum text-sm font-medium text-ink">{pctV}%</span>
        <span className="text-xs text-ink-3">{isModel ? 'probability' : 'confidence'}</span>
      </div>
    </Tip>
  )
}

function pctOf(v: unknown) {
  return typeof v === 'number' ? `${Math.round(v * 100)}%` : '—'
}

export function ImpactRange({
  o,
  compact,
}: {
  o: Pick<Opportunity, 'impact_low' | 'impact_high' | 'impact_kind' | 'impact_basis'>
  compact?: boolean
}) {
  if (o.impact_high === null) return <span className="text-sm text-ink-3">Not quantified</span>
  return (
    <Tip content={o.impact_basis ?? ''}>
      <div className="cursor-help">
        {!compact && <div className="text-xs text-ink-3">{IMPACT_LABEL[o.impact_kind]}</div>}
        <div className="tnum text-sm font-semibold text-ink">
          {murCompact(o.impact_low)} – {murCompact(o.impact_high).replace('MUR ', '')}
        </div>
      </div>
    </Tip>
  )
}

export function Delta({
  value,
  goodWhen = 'up',
  suffix = '%',
  unit,
}: {
  value: number | null | undefined
  goodWhen?: 'up' | 'down'
  suffix?: string
  unit?: string
}) {
  if (value === null || value === undefined) return <span className="text-xs text-ink-3">no comparison</span>
  const up = value > 0
  const good = value === 0 ? null : goodWhen === 'up' ? up : !up
  const Icon = up ? ArrowUpRight : ArrowDownRight
  return (
    <span
      className={cn(
        'inline-flex items-center gap-0.5 text-xs font-medium',
        good === null ? 'text-ink-3' : good ? 'text-good-ink' : 'text-bad-ink',
      )}
    >
      <Icon className="size-3.5" aria-hidden />
      {suffix === '%' ? pct(value) : `${value > 0 ? '+' : value < 0 ? '−' : ''}${Math.abs(value).toFixed(1)}${suffix}`}
      {unit && <span className="font-normal text-ink-3">&nbsp;{unit}</span>}
    </span>
  )
}

const OUTCOME = {
  achieved: { tone: 'good', label: 'Outcome achieved', icon: CheckCircle2 },
  partial: { tone: 'warn', label: 'Partly achieved', icon: AlertCircle },
  no_change: { tone: 'neutral', label: 'No measurable change yet', icon: Circle },
  worsened: { tone: 'bad', label: 'Metric worsened', icon: AlertTriangle },
  too_early: { tone: 'neutral', label: 'Measuring - too early', icon: Clock },
  not_started: { tone: 'neutral', label: 'Not started', icon: Circle },
  insufficient_data: { tone: 'neutral', label: 'Not enough data', icon: Info },
  manual: { tone: 'neutral', label: 'Confirm manually', icon: Info },
} as const

export function OutcomeBadge({ outcome }: { outcome: Outcome }) {
  const m = OUTCOME[outcome.status]
  const Icon = m.icon
  return (
    <Badge tone={m.tone}>
      <Icon aria-hidden /> {m.label}
    </Badge>
  )
}
