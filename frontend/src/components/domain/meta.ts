import { CheckCircle2, Circle, CircleDot, Clock, PlayCircle, XCircle } from 'lucide-react'
import type { Opportunity, OppStatus } from '@/lib/types'

export const STATUS_META: Record<
  OppStatus,
  { label: string; icon: typeof Circle; tone: 'neutral' | 'brand' | 'accent' | 'good' | 'warn' }
> = {
  new: { label: 'New', icon: CircleDot, tone: 'brand' },
  reviewed: { label: 'Reviewed', icon: Circle, tone: 'neutral' },
  planned: { label: 'Planned', icon: Clock, tone: 'neutral' },
  in_progress: { label: 'In progress', icon: PlayCircle, tone: 'accent' },
  completed: { label: 'Completed', icon: CheckCircle2, tone: 'good' },
  dismissed: { label: 'Dismissed', icon: XCircle, tone: 'neutral' },
}

export const IMPACT_LABEL: Record<Opportunity['impact_kind'], string> = {
  saving: 'Potential saving / year',
  cash_release: 'Cash that could be released',
  exposure: 'Revenue exposure / year',
  shortfall: 'Cash gap to a 14-day buffer',
  revenue_upside: 'Gross-profit upside / year',
  none: 'Impact',
}
