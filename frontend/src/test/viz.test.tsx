import { render, screen } from '@testing-library/react'
import { TooltipProvider } from '@/components/ui/tooltip'
import { BandScale } from '@/components/viz/BandScale'
import { CompositionBar } from '@/components/viz/CompositionBar'
import { DivergingBars } from '@/components/viz/DivergingBars'
import { Meter } from '@/components/viz/Meter'

describe('visual components carry their meaning in text, not only colour', () => {
  it('meter exposes value and max to assistive technology', () => {
    render(<Meter value={18} max={30} marker={{ value: 14, label: '14-day buffer' }} label="Cash covers 18 days" />)
    const m = screen.getByRole('meter', { name: 'Cash covers 18 days' })
    expect(m).toHaveAttribute('aria-valuenow', '18')
    expect(m).toHaveAttribute('aria-valuemax', '30')
    expect(screen.getByText('14-day buffer')).toBeInTheDocument()
  })

  it('band scale names the band the probability falls in', () => {
    render(<BandScale probability={0.64} moderate={0.16} high={0.32} />)
    expect(screen.getByRole('meter', { name: 'Probability 64%, in the high band' })).toBeInTheDocument()
    expect(screen.getByText('High')).toHaveClass('font-semibold')
  })

  it('composition bar lists every segment with value and share', () => {
    render(
      <TooltipProvider>
        <CompositionBar
          label="Receivables by age"
          format={(v) => `MUR ${v}`}
          segments={[
            { key: 'a', label: 'Not due yet', value: 300, color: 'blue' },
            { key: 'b', label: '1–30 days late', value: 100, color: 'orange' },
          ]}
        />
      </TooltipProvider>,
    )
    expect(screen.getByRole('img', { name: 'Receivables by age' })).toBeInTheDocument()
    expect(screen.getByText('75%')).toBeInTheDocument()
    expect(screen.getByText('25%')).toBeInTheDocument()
  })

  it('diverging bars print the signed value and mark zero as no change', () => {
    render(
      <DivergingBars
        rows={[
          { label: 'Supplier purchases', value: 151000 },
          { label: 'VAT payments', value: -20000 },
          { label: 'Payroll', value: 0 },
        ]}
        format={(v) => (v > 0 ? `+${v}` : `${v}`)}
      />,
    )
    expect(screen.getByText('+151000')).toBeInTheDocument()
    expect(screen.getByText('-20000')).toBeInTheDocument()
    expect(screen.getByText('No change')).toBeInTheDocument()
  })
})
