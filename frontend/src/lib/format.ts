/** Formatting helpers. One currency (MUR) and one date style (22 Sep 2026) everywhere. */

const nf0 = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 0 })
const nf1 = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 1, minimumFractionDigits: 1 })
const nf2 = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 2, minimumFractionDigits: 2 })

export const CURRENCY = 'MUR'

export function mur(v: number | null | undefined, opts: { signed?: boolean; cents?: boolean } = {}) {
  if (v === null || v === undefined || Number.isNaN(v)) return '—'
  const sign = v < 0 ? '−' : opts.signed && v > 0 ? '+' : ''
  const body = (opts.cents ? nf2 : nf0).format(Math.abs(v))
  return `${sign}${CURRENCY} ${body}`
}

/** Compact MUR for tiles and axes: MUR 1.2M, MUR 845K */
export function murCompact(v: number | null | undefined, signed = false) {
  if (v === null || v === undefined || Number.isNaN(v)) return '—'
  const a = Math.abs(v)
  const sign = v < 0 ? '−' : signed && v > 0 ? '+' : ''
  let body: string
  if (a >= 1_000_000) body = `${(a / 1_000_000).toFixed(a >= 10_000_000 ? 0 : 2)}M`
  else if (a >= 10_000) body = `${Math.round(a / 1_000)}K`
  else body = nf0.format(a)
  return `${sign}${CURRENCY} ${body}`
}

export function axisMur(v: number) {
  const a = Math.abs(v)
  const s = v < 0 ? '−' : ''
  if (a >= 1_000_000) return `${s}${(a / 1_000_000).toFixed(1)}M`
  if (a >= 1_000) return `${s}${Math.round(a / 1_000)}K`
  return `${s}${a}`
}

export function pct(v: number | null | undefined, signed = true, digits = 1) {
  if (v === null || v === undefined || Number.isNaN(v)) return '—'
  const s = v < 0 ? '−' : signed && v > 0 ? '+' : ''
  return `${s}${Math.abs(v).toFixed(digits)}%`
}

export function pp(v: number | null | undefined) {
  if (v === null || v === undefined) return '—'
  return `${v < 0 ? '−' : v > 0 ? '+' : ''}${nf1.format(Math.abs(v))} pp`
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

export function date(iso: string | null | undefined) {
  if (!iso) return '—'
  const [y, m, d] = iso.slice(0, 10).split('-').map(Number)
  return `${String(d).padStart(2, '0')} ${MONTHS[m - 1]} ${y}`
}

/** "Jun – Aug 2026" from an ISO [start, end] pair */
export function monthSpan(p: [string, string]) {
  const [y0, m0] = p[0].split('-').map(Number)
  const [y1, m1] = p[1].split('-').map(Number)
  return y0 === y1 ? `${MONTHS[m0 - 1]} – ${MONTHS[m1 - 1]} ${y1}` : `${MONTHS[m0 - 1]} ${y0} – ${MONTHS[m1 - 1]} ${y1}`
}

export function shortDate(iso: string) {
  const [, m, d] = iso.slice(0, 10).split('-').map(Number)
  return `${d} ${MONTHS[m - 1]}`
}

export function monthLabel(ym: string) {
  const [y, m] = ym.split('-').map(Number)
  return `${MONTHS[m - 1]} ${String(y).slice(2)}`
}

export function dateTime(iso: string) {
  const d = new Date(iso)
  return `${date(d.toISOString())} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

export function num(v: number | null | undefined) {
  if (v === null || v === undefined) return '—'
  return nf0.format(v)
}

/** A count in full under 1,000, then in thousands with one decimal: 842, 1k, 1.1k, 2.6k. */
export function countCompact(v: number) {
  return v < 1000 ? nf0.format(v) : `${Number((v / 1000).toFixed(1))}k`
}

export function percent01(v: number | null | undefined) {
  if (v === null || v === undefined) return '—'
  return `${Math.round(v * 100)}%`
}

export function titleCase(s: string) {
  return s.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase())
}

/** Whole days from ISO date a to ISO date b (b - a). */
export function daysBetween(a: string, b: string) {
  const d = (s: string) => Date.UTC(+s.slice(0, 4), +s.slice(5, 7) - 1, +s.slice(8, 10))
  return Math.round((d(b) - d(a)) / 86_400_000)
}

/** A tracked metric in its own unit (MUR, %, days). */
export function metric(v: number | undefined | null, unit?: string) {
  if (v === undefined || v === null) return '—'
  if (unit === 'MUR') return mur(v)
  if (unit === '%') return `${v.toFixed(1)}%`
  if (unit === 'days') return `${v.toFixed(1)} days`
  return v.toFixed(2)
}

/** Greeting from the viewer's own clock (not data). */
export function greeting(hour = new Date().getHours()) {
  return hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening'
}
