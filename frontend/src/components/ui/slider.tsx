import * as S from '@radix-ui/react-slider'

export function Slider({
  value,
  min,
  max,
  step,
  onChange,
  label,
}: {
  value: number
  min: number
  max: number
  step: number
  onChange: (v: number) => void
  label: string
}) {
  const zeroPct = ((0 - min) / (max - min)) * 100
  const valPct = ((value - min) / (max - min)) * 100
  return (
    <S.Root
      className="relative flex h-5 w-full touch-none select-none items-center"
      value={[value]}
      min={min}
      max={max}
      step={step}
      onValueChange={(v) => onChange(v[0])}
      aria-label={label}
    >
      <S.Track className="relative h-1.5 grow rounded-full bg-brand-100">
        <span
          className="absolute h-full rounded-full bg-simulated"
          style={{ left: `${Math.min(zeroPct, valPct)}%`, width: `${Math.abs(valPct - zeroPct)}%` }}
        />
        <span className="absolute top-1/2 h-3 w-px -translate-y-1/2 bg-ink-3" style={{ left: `${zeroPct}%` }} />
      </S.Track>
      <S.Thumb className="block size-4 rounded-full border-2 border-surface bg-simulated shadow ring-1 ring-simulated/40 focus-visible:outline-2 focus-visible:outline-accent-600" />
    </S.Root>
  )
}
