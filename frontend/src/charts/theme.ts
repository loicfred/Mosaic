import { date } from '@/lib/format'

export function dateTitle(label: unknown) {
  return typeof label === 'string' ? date(label) : String(label ?? '')
}

export const C = {
  actual: 'var(--color-actual)',
  projected: 'var(--color-projected)',
  simulated: 'var(--color-simulated)',
  series3: 'var(--color-series-3)',
  expense: 'var(--color-expense)',
  before: 'var(--color-before)',
  good: 'var(--color-good)',
  warn: 'var(--color-warn)',
  serious: 'var(--color-serious)',
  grid: 'var(--color-grid)',
  axis: 'var(--color-axis)',
  bad: 'var(--color-bad)',
  ink3: 'var(--color-ink-3)',
}
export const axisTick = { fill: '#55647e', fontSize: 12 }
