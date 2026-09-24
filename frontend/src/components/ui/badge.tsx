import { cva, type VariantProps } from 'class-variance-authority'
import type { HTMLAttributes } from 'react'
import { cn } from '@/lib/cn'

/** A small 4px tag. Semantic tones always sit next to a word or icon, never colour alone. */
const badge = cva('inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs font-medium leading-4 [&_svg]:size-3.5', {
  variants: {
    tone: {
      neutral: 'bg-mist text-ink-2',
      brand: 'bg-mist text-ink',
      accent: 'bg-accent-100 text-accent-600',
      good: 'bg-good-bg text-good-ink',
      warn: 'bg-warn-bg text-warn-ink',
      serious: 'bg-serious-bg text-serious-ink',
      bad: 'bg-bad-bg text-bad-ink',
      simulated: 'bg-gold-50 text-gold-700',
    },
  },
  defaultVariants: { tone: 'neutral' },
})

export function Badge({ className, tone, ...p }: HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badge>) {
  return <span className={cn(badge({ tone }), className)} {...p} />
}
