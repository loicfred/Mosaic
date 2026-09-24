import { cn } from '@/lib/cn'

/**
 * The Valora mark: a charcoal and sage "V" holding four rising bars
 * (sage, gold, periwinkle, coral) with a light orbit and two data points.
 * Drawn as SVG so it stays sharp at every size; colours are the brand palette.
 */
export function ValoraMark({ className, orbit = true, title }: { className?: string; orbit?: boolean; title?: string }) {
  return (
    <svg viewBox="0 0 48 48" className={cn('shrink-0', className)} role={title ? 'img' : undefined} aria-hidden={title ? undefined : true}>
      {title && <title>{title}</title>}
      {orbit && (
        <g fill="none" stroke="#2C2C2C" strokeOpacity="0.22" strokeWidth="1.3" strokeLinecap="round">
          <path d="M5.5 30.5 C 3 22, 16 11, 33 7.2" />
          <path d="M42.5 17.5 C 45 26, 32 37, 15 40.8" />
        </g>
      )}
      <path d="M9 9.5 L24 39" stroke="#2C2C2C" strokeWidth="5" strokeLinecap="round" fill="none" />
      <path d="M24 39 L39 9.5" stroke="#7DB356" strokeWidth="5" strokeLinecap="round" fill="none" />
      <rect x="17.4" y="20" width="2.5" height="3.2" rx="0.8" fill="#7DB356" />
      <rect x="20.9" y="17.6" width="2.5" height="5.6" rx="0.8" fill="#F5B82E" />
      <rect x="24.4" y="15.2" width="2.5" height="8" rx="0.8" fill="#6770F7" />
      <rect x="27.9" y="12.8" width="2.5" height="10.4" rx="0.8" fill="#FF6B45" />
      {orbit && (
        <>
          <circle cx="33.4" cy="7.1" r="1.7" fill="#6770F7" />
          <circle cx="14.6" cy="40.9" r="1.4" fill="#F5B82E" />
        </>
      )}
    </svg>
  )
}

export function ValoraLogo({
  className,
  size = 'md',
  tagline = false,
  onColor = false,
}: {
  className?: string
  size?: 'sm' | 'md' | 'lg'
  tagline?: boolean
  /** On a coloured background: the mark sits on a white tile and the word is white. */
  onColor?: boolean
}) {
  const mark = { sm: 'size-6', md: 'size-8', lg: 'size-10' }[size]
  const word = { sm: 'text-base', md: 'text-lg', lg: 'text-2xl' }[size]
  return (
    <div className={cn('flex items-center gap-2', className)}>
      {onColor ? (
        <span className="flex size-10 items-center justify-center rounded-md bg-white">
          <ValoraMark className="size-8" />
        </span>
      ) : (
        <ValoraMark className={mark} orbit={size !== 'sm'} />
      )}
      <div className="leading-none">
        <span className={cn('block font-semibold', onColor ? 'text-white' : 'text-ink', word)}>Valora</span>
        {tagline && <span className="mt-1 block text-xs text-ink-3">Turning financial data into opportunity</span>}
      </div>
    </div>
  )
}
