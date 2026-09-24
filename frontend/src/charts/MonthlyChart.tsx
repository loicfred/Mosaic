import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { axisMur, monthLabel } from '@/lib/format'
import type { MonthRow } from '@/lib/types'
import { ChartTooltipBox, LegendKey } from './ChartTooltip'
import { axisTick, C } from './theme'

/** Revenue vs expenses per month (actual). Partial months are flagged in the axis label. */
export function MonthlyChart({ months, height = 260 }: { months: MonthRow[]; height?: number }) {
  const data = months.map((m) => ({ ...m, label: `${monthLabel(m.month)}${m.partial ? '*' : ''}` }))
  const partial = months.find((m) => m.partial)
  return (
    <figure>
      <LegendKey
        items={[
          { label: 'Revenue', color: C.actual, kind: 'rect' },
          { label: 'Expenses (stock, operating, VAT)', color: C.expense, kind: 'rect' },
        ]}
      />
      <div style={{ height }} className="mt-3" role="img" aria-label="Monthly revenue and expenses">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }} barGap={2} barCategoryGap="28%">
            <CartesianGrid vertical={false} stroke={C.grid} />
            <XAxis
              dataKey="label"
              tick={axisTick}
              axisLine={{ stroke: C.axis }}
              tickLine={false}
              interval="preserveStartEnd"
              minTickGap={8}
            />
            <YAxis tickFormatter={axisMur} tick={axisTick} axisLine={false} tickLine={false} width={48} />
            <Tooltip
              cursor={{ fill: 'rgba(44,44,44,0.04)' }}
              content={({ active, payload, label }) =>
                active && payload?.length ? (
                  <ChartTooltipBox
                    title={String(label)}
                    rows={[
                      { name: 'revenue', value: payload[0]?.payload.revenue, color: C.actual },
                      { name: 'expenses', value: payload[0]?.payload.expenses, color: C.expense },
                      { name: 'net cash flow', value: payload[0]?.payload.net_cash_flow, color: C.ink3 },
                    ]}
                  />
                ) : null
              }
            />
            <Bar dataKey="revenue" fill={C.actual} radius={[4, 4, 0, 0]} maxBarSize={20} isAnimationActive={false} />
            <Bar dataKey="expenses" fill={C.expense} radius={[4, 4, 0, 0]} maxBarSize={20} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      {partial && (
        <figcaption className="mt-2 text-xs text-ink-3">
          * {monthLabel(partial.month)} is partial ({partial.days_covered} days of data).
        </figcaption>
      )}
    </figure>
  )
}
