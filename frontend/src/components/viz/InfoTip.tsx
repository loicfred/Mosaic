import { Info } from 'lucide-react'
import type { ReactNode } from 'react'
import { Tip } from '@/components/ui/tooltip'

/** Method notes live behind a focusable (i), not in the card body. */
export function InfoTip({ content, label = 'How this is calculated' }: { content: ReactNode; label?: string }) {
  return (
    <Tip content={content}>
      <button
        type="button"
        className="inline-flex size-5 shrink-0 items-center justify-center rounded-full text-ink-3 hover:bg-mist hover:text-ink"
        aria-label={label}
      >
        <Info className="size-3.5" aria-hidden />
      </button>
    </Tip>
  )
}
