import { arrowPair, compactDisplay, supportStats } from '@/lib/findings'

describe('finding presentation helpers only reshape engine values', () => {
  it('reads before → after pairs the engine wrote', () => {
    expect(arrowPair('MUR 79,490 → MUR 89,790')).toEqual([79490, 89790])
    expect(arrowPair('34 days → 48 days')).toEqual([34, 48])
    expect(arrowPair('+13.1%')).toBeNull()
    expect(arrowPair(undefined)).toBeNull()
  })

  it('shortens money for supporting facts', () => {
    expect(compactDisplay('MUR 121,633')).toBe('MUR 122K')
    expect(compactDisplay('32.4%')).toBe('32.4%')
  })

  it('picks at most two short facts, skipping what the visual already shows', () => {
    const stats = supportStats({
      detector: 'supplier_cost_inflation',
      evidence: [
        { label: 'Supplier costs', value: 13.1, display: '+13.1%' },
        { label: 'Revenue', value: -2.6, display: '-2.6%' },
        { label: 'Supplier cost per MUR 100 of sales', value: 60.3, display: 'MUR 60.3 (was 51.9)' },
      ],
    })
    expect(stats).toEqual([
      { value: '+13.1%', label: 'Supplier costs', trend: 'up' },
      { value: '-2.6%', label: 'Revenue', trend: 'down' },
    ])
  })
})
