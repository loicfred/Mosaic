import { Gauge } from 'lucide-react'
import { Link } from 'react-router-dom'
import { BandScale } from '@/components/viz/BandScale'
import { InfoTip } from '@/components/viz/InfoTip'
import type { Prediction } from '@/lib/types'
import { BandBadge, DataKind } from './labels'

/**
 * The model's view of the next 30 days, as a quiet column that sits beside the
 * cash chart: one probability, where it falls on the model's own bands, and the
 * three strongest reasons. No card of its own.
 */
export function PredictionCard({ p }: { p: Prediction }) {
  const drivers = (p.top_drivers ?? p.contributions?.filter((c) => c.contribution >= 0.25) ?? []).slice(0, 3)
  const maxC = Math.max(...drivers.map((d) => d.contribution), 0.01)
  return (
    <div className="flex h-full flex-col gap-5">
      <div className="flex items-center justify-between gap-2">
        <h3 className="flex items-center gap-1.5 text-sm font-semibold text-ink">
          <Gauge className="size-4 text-ink-3" aria-hidden /> 30-day cash pressure
          <InfoTip
            content={
              <>
                Probability that cash falls below 14 days of committed outflows within 30 days, from a locally trained model. {p.reason}{' '}
                Model {p.model_version ?? 'n/a'}.
              </>
            }
          />
        </h3>
        <DataKind kind="predicted" />
      </div>
      {p.probability !== null ? (
        <div className="flex items-end justify-between gap-3">
          <div>
            <div className="text-[40px] font-semibold leading-none tracking-tight text-ink">{Math.round(p.probability * 100)}%</div>
            <div className="mt-1 text-xs text-ink-3">chance of dropping below the buffer</div>
          </div>
          <BandBadge band={p.band} large />
        </div>
      ) : (
        <div className="space-y-2">
          <BandBadge band={p.band} large />
          <p className="text-sm text-ink-2">{p.reason}</p>
        </div>
      )}
      {p.probability !== null && p.thresholds && (
        <BandScale probability={p.probability} moderate={p.thresholds.moderate_threshold} high={p.thresholds.high_threshold} />
      )}
      {drivers.length > 0 && (
        <div>
          <div className="mb-2 text-xs font-medium text-ink-3">What pushes it up</div>
          <ul className="space-y-2.5">
            {drivers.map((d) => (
              <li key={d.feature} className="text-sm">
                <div className="flex justify-between gap-2">
                  <span className="truncate text-ink-2" title={d.label}>
                    {d.label}
                  </span>
                  <span className="tnum shrink-0 font-medium text-ink">{d.display}</span>
                </div>
                <div className="mt-1 h-1 rounded-full bg-track">
                  <div className="grow-x h-full rounded-full bg-ink/60" style={{ width: `${(d.contribution / maxC) * 100}%` }} />
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
      <Link to="/settings?tab=models" className="mt-auto text-xs font-medium text-accent-700 hover:underline">
        How the model was evaluated
      </Link>
    </div>
  )
}
