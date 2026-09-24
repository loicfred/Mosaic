import type { AskContext } from '@/lib/insight/engine'
import { cn } from '@/lib/cn'
import { InsightOrb } from './InsightOrb'
import { useInsight } from './context'

/**
 * "Ask Valora about this": a quiet text button placed on a chart or a finding.
 * It opens Valora Insight with the thing the user was looking at as context.
 * Renders nothing outside the signed-in shell.
 */
export function AskValora({
  question,
  context,
  label = 'Ask Valora about this',
  className,
}: {
  question: string
  context?: AskContext
  label?: string
  className?: string
}) {
  const ins = useInsight()
  if (!ins) return null
  return (
    <button
      type="button"
      onClick={() => ins.ask(question, context)}
      className={cn(
        'no-print group inline-flex items-center gap-1.5 rounded-md py-1 pl-1.5 pr-2 text-xs font-medium text-ink-2 transition-colors hover:bg-mist hover:text-accent-600',
        className,
      )}
      title={question}
    >
      <InsightOrb className="size-4 text-accent-600" />
      {label}
    </button>
  )
}
