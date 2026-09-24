import { ChevronRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { Opportunity } from '@/lib/types'
import { ConfidenceMeter, ImpactRange, SeverityBadge } from './labels'

/** One finding as a scannable row: severity, title, one-line reason, value, confidence. */
export function FindingRow({ o }: { o: Opportunity }) {
  return (
    <Link
      to={`/opportunities?open=${o.id}`}
      className="group grid gap-x-6 gap-y-2 px-5 py-3.5 transition-colors hover:bg-mist focus-visible:bg-surface-2 md:grid-cols-[minmax(0,1fr)_10.5rem_9rem_1rem] md:items-center"
    >
      <div className="min-w-0">
        <div className="flex items-start gap-2">
          <SeverityBadge severity={o.severity} />
          <span className="font-medium leading-snug text-ink">{o.title}</span>
        </div>
        <p className="mt-1 truncate text-sm text-ink-3" title={o.summary}>
          {o.summary}
        </p>
      </div>
      <ImpactRange o={o} />
      <ConfidenceMeter value={o.confidence} basis={o.confidence_basis} />
      <ChevronRight className="hidden size-4 text-ink-3 transition-transform group-hover:translate-x-0.5 md:block" aria-hidden />
    </Link>
  )
}
