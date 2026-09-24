import { cva, type VariantProps } from 'class-variance-authority'
import type { HTMLAttributes } from 'react'
import { cn } from '@/lib/cn'

const badge = cva('inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium [&_svg]:size-3.5', {
  variants: {
    tone: {
      neutral: 'bg-brand-50 text-ink-2 ring-1 ring-inset ring-line',
      brand: 'bg-brand-100 text-brand-800',
      accent: 'bg-accent-50 text-accent-700 ring-1 ring-inset ring-accent-100',
      good: 'bg-good-bg text-good-ink',
      warn: 'bg-warn-bg text-warn-ink',
      serious: 'bg-serious-bg text-serious-ink',
      bad: 'bg-bad-bg text-bad-ink',
      simulated: 'bg-gold-50 text-gold-700 ring-1 ring-inset ring-gold-500/50',
    },
  },
  defaultVariants: { tone: 'neutral' },
})

export function Badge({ className, tone, ...p }: HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badge>) {
  return <span className={cn(badge({ tone }), className)} {...p} />
}
