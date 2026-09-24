import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { axisMur, shortDate } from '@/lib/format'
import { ChartTooltipBox, LegendKey } from './ChartTooltip'
import { axisTick, C, dateTitle } from './theme'

export function ScenarioChart({
  series,
  buffer,
  height = 300,
}: {
  series: { date: string; baseline: number; scenario: number }[]
  buffer?: number
  height?: number
}) {
  const ticks = series.filter((_, i) => i % 15 === 0).map((d) => d.date)
  return (
    <figure>
      <LegendKey
        items={[
          { label: 'Projected - no change', color: C.projected, dashed: true },
          { label: 'Simulated - with your assumptions', color: C.simulated },
          ...(buffer ? [{ label: '14-day safety buffer', color: C.bad }] : []),
        ]}
      />
      <div style={{ height }} className="mt-3" role="img" aria-label="Projected cash without changes versus the simulated scenario">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={series} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
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
                      { name: 'simulated', value: payload.find((p) => p.dataKey === 'scenario')?.value as number, color: C.simulated },
                      {
                        name: 'no change',
                        value: payload.find((p) => p.dataKey === 'baseline')?.value as number,
                        color: C.projected,
                        dashed: true,
                      },
                    ]}
                  />
                ) : null
              }
            />
            {buffer ? <ReferenceLine y={buffer} stroke={C.bad} strokeWidth={1} ifOverflow="extendDomain" /> : null}
            <Line
              type="monotone"
              dataKey="baseline"
              stroke={C.projected}
              strokeWidth={2}
              strokeDasharray="5 4"
              dot={false}
              isAnimationActive={false}
            />
            <Line
              type="monotone"
              dataKey="scenario"
              stroke={C.simulated}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, strokeWidth: 2, stroke: '#fff' }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </figure>
  )
}
