import { AlertTriangle, ArrowRight, CheckCircle2, Info } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { cn } from '@/lib/cn'

type Tone = 'insight' | 'attention' | 'good'

const ICON: Record<Tone, ReactNode> = {
  insight: <Info className="size-4 text-ink-3" aria-hidden />,
  attention: <AlertTriangle className="size-4 text-warn-ink" aria-hidden />,
  good: <CheckCircle2 className="size-4 text-good-ink" aria-hidden />,
}
const LABEL: Record<Tone, string> = { insight: 'Note:', attention: 'Needs attention:', good: 'Good news:' }

/**
 * The line at the foot of a section: one sentence that says what the numbers
 * mean, and at most one next step as a text action. Always built from real figures.
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
    'inline-flex shrink-0 items-center gap-1 text-sm font-medium text-accent-600 underline-offset-4 hover:text-accent-600 hover:underline'
  return (
    <div
      className={cn('mt-5 flex flex-col gap-2 border-t border-line pt-4 sm:flex-row sm:items-start sm:justify-between sm:gap-6', className)}
    >
      <p className="flex flex-1 items-start gap-2 text-sm text-ink-2">
        <span className="mt-0.5 shrink-0">{ICON[tone]}</span>
        <span>
          <span className="sr-only">{LABEL[tone]} </span>
          {children}
        </span>
      </p>
      {action &&
        (action.to ? (
          <Link to={action.to} className={btn}>
            {action.label} <ArrowRight className="size-3.5" aria-hidden />
          </Link>
        ) : (
          <button type="button" onClick={action.onClick} className={btn}>
            {action.label} <ArrowRight className="size-3.5" aria-hidden />
          </button>
        ))}
    </div>
  )
}
