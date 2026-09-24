import { Area, CartesianGrid, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { axisMur, shortDate } from '@/lib/format'
import { ChartTooltipBox, LegendKey } from './ChartTooltip'
import { axisTick, C, dateTitle } from './theme'

interface Props {
  actual: { date: string; cash: number }[]
  projected?: { date: string; cash: number }[]
  buffer?: number
  height?: number
}

/** Actual cash (solid) and deterministic projection (dashed), with the 14-day buffer line. */
export function CashChart({ actual, projected = [], buffer, height = 280 }: Props) {
  const last = actual[actual.length - 1]
  const data: { date: string; actual?: number; projected?: number }[] = actual.map((d) => ({ date: d.date, actual: d.cash }))
  if (last && projected.length) {
    data[data.length - 1] = { ...data[data.length - 1], projected: last.cash }
    projected.forEach((p) => data.push({ date: p.date, projected: p.cash }))
  }
  const ticks = data.filter((_, i) => i % 30 === 0).map((d) => d.date)
  return (
    <figure>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <LegendKey
          items={[
            { label: 'Actual cash', color: C.actual },
            ...(projected.length ? [{ label: 'Projected (current run-rates)', color: C.projected, dashed: true }] : []),
            ...(buffer ? [{ label: '14-day safety buffer', color: C.bad }] : []),
          ]}
        />
      </div>
      <div style={{ height }} role="img" aria-label="Cash balance over time: actual history and projection">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
            <CartesianGrid vertical={false} stroke={C.grid} />
            <XAxis dataKey="date" ticks={ticks} tickFormatter={shortDate} tick={axisTick} axisLine={{ stroke: C.axis }} tickLine={false} />
            <YAxis tickFormatter={axisMur} tick={axisTick} axisLine={false} tickLine={false} width={48} />
            <Tooltip
              cursor={{ stroke: C.axis, strokeWidth: 1 }}
              content={({ active, payload, label }) =>
                active && payload?.length ? (
                  <ChartTooltipBox
                    title={dateTitle(label)}
                    rows={[
                      { name: 'actual', value: payload.find((p) => p.dataKey === 'actual')?.value as number, color: C.actual },
                      {
                        name: 'projected',
                        value: payload.find((p) => p.dataKey === 'projected')?.value as number,
                        color: C.projected,
                        dashed: true,
                      },
                    ]}
                  />
                ) : null
              }
            />
            {buffer ? <ReferenceLine y={buffer} stroke={C.bad} strokeWidth={1} ifOverflow="extendDomain" /> : null}
            {last && projected.length ? (
              <ReferenceLine
                x={last.date}
                stroke={C.axis}
                strokeWidth={1}
                label={{ value: 'Today', position: 'insideTopRight', fill: '#6b6b67', fontSize: 12 }}
              />
            ) : null}
            <Area type="monotone" dataKey="actual" stroke="none" fill={C.actual} fillOpacity={0.08} isAnimationActive={false} />
            <Line
              type="monotone"
              dataKey="actual"
              stroke={C.actual}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, strokeWidth: 2, stroke: '#fff' }}
              isAnimationActive={false}
            />
            <Line
              type="monotone"
              dataKey="projected"
              stroke={C.projected}
              strokeWidth={2}
              strokeDasharray="5 4"
              dot={false}
              activeDot={{ r: 4, strokeWidth: 2, stroke: '#fff' }}
              isAnimationActive={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </figure>
  )
}
