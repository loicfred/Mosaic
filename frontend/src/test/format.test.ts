import { axisMur, date, monthSpan, mur, murCompact, pct } from '@/lib/format'

describe('formatting', () => {
  it('formats MUR consistently', () => {
    expect(mur(1234567.4)).toBe('MUR 1,234,567')
    expect(mur(-500)).toBe('−MUR 500')
    expect(mur(250, { signed: true })).toBe('+MUR 250')
    expect(mur(null)).toBe('—')
    expect(murCompact(2_850_000)).toBe('MUR 2.85M')
    expect(murCompact(72_344)).toBe('MUR 72K')
    expect(axisMur(450_000)).toBe('450K')
  })
  it('formats dates and percentages', () => {
    expect(date('2026-09-22')).toBe('22 Sep 2026')
    expect(monthSpan(['2026-06-01', '2026-08-31'])).toBe('Jun – Aug 2026')
    expect(pct(7.81)).toBe('+7.8%')
    expect(pct(-3)).toBe('−3.0%')
  })
})
