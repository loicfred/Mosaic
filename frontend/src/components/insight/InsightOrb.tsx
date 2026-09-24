import { MessageSquareText } from 'lucide-react'
import { cn } from '@/lib/cn'

export type OrbState = 'idle' | 'hover' | 'open' | 'thinking' | 'answer' | 'static'

/** The Valora Insight mark: one outline icon in the current text colour. No motion. */
export function InsightOrb({ state = 'idle', className }: { state?: OrbState; className?: string }) {
  return <MessageSquareText className={cn('shrink-0', className)} data-state={state} aria-hidden />
}
