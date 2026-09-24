import { AlertTriangle, CheckCircle2, ChevronRight } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { InsightOrb } from '@/components/insight/InsightOrb'
import { cn } from '@/lib/cn'

type Tone = 'insight' | 'attention' | 'good'

const ICON: Record<Tone, ReactNode> = {
  insight: <InsightOrb state="static" className="size-5 text-ink" />,
  attention: <AlertTriangle className="size-5 text-serious-ink" aria-hidden />,
  good: <CheckCircle2 className="size-5 text-good-ink" aria-hidden />,
}
const LABEL: Record<Tone, string> = { insight: 'Valora noticed:', attention: 'Needs attention:', good: 'Good news:' }

/**
 * The strip at the foot of a card: one sentence that says what the card's numbers
 * mean, and at most one next step. The sentence is always built from real figures.
 */
export function InsightStrip({
  tone = 'insight',
  children,
  action,
  className,
}: {
  tone?: Tone
  children: ReactNode
  /** One next step: a link inside the app, or a button action. */
  action?: { label: string; to?: string; onClick?: () => void }
  className?: string
}) {
  const btn =
    'inline-flex shrink-0 items-center gap-1 self-start rounded-xl border border-line bg-surface px-3 py-2 text-sm font-medium text-accent-700 transition-colors hover:border-accent-500 hover:bg-accent-50 @lg:self-auto'
  return (
    <div className={cn('@container mt-5', className)}>
      <div
        className={cn(
          'flex flex-col gap-3 rounded-2xl border px-4 py-3 @lg:flex-row @lg:items-center',
          tone === 'attention'
            ? 'border-coral-100 bg-coral-50'
            : tone === 'good'
              ? 'border-sage-100 bg-sage-50'
              : 'border-line bg-white/80',
        )}
      >
        <p className="flex flex-1 items-start gap-2.5 text-sm leading-relaxed text-ink">
          <span className="mt-px shrink-0">{ICON[tone]}</span>
          <span>
            <span className="sr-only">{LABEL[tone]} </span>
            {children}
          </span>
        </p>
        {action &&
          (action.to ? (
            <Link to={action.to} className={btn}>
              {action.label} <ChevronRight className="size-4" aria-hidden />
            </Link>
          ) : (
            <button type="button" onClick={action.onClick} className={btn}>
              {action.label} <ChevronRight className="size-4" aria-hidden />
            </button>
          ))}
      </div>
    </div>
  )
}
