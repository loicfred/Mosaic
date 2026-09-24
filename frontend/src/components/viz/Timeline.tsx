import type { ReactNode } from 'react'
import { cn } from '@/lib/cn'

export interface TimelineItem {
  id: string | number
  title: ReactNode
  meta?: ReactNode
  note?: ReactNode
  tone?: 'neutral' | 'accent' | 'good' | 'warn' | 'bad'
}

const DOT = {
  neutral: 'bg-line-strong',
  accent: 'bg-accent-600',
  good: 'bg-good',
  warn: 'bg-warn',
  bad: 'bg-bad',
}

/** Events in order, newest last: "what happened, who did it, when". */
export function Timeline({ items, className }: { items: TimelineItem[]; className?: string }) {
  return (
    <ol className={cn('relative space-y-4 border-l border-line pl-5', className)}>
      {items.map((e) => (
        <li key={e.id} className="relative text-sm">
          <span
            className={cn('absolute -left-[25px] top-1 size-2.5 rounded-full ring-4 ring-surface', DOT[e.tone ?? 'neutral'])}
            aria-hidden
          />
          <div className="font-medium text-ink">{e.title}</div>
          {e.meta && <div className="text-xs text-ink-3">{e.meta}</div>}
          {e.note && <div className="mt-1 rounded-md bg-surface-2 px-2.5 py-1.5 text-ink-2">{e.note}</div>}
        </li>
      ))}
    </ol>
  )
}
