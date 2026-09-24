import * as M from '@radix-ui/react-dropdown-menu'
import { Accessibility, Check } from 'lucide-react'
import { useState } from 'react'
import { DEFAULT_PREFS, loadPrefs, savePrefs, type A11yPrefs } from '@/lib/a11y'
import { cn } from '@/lib/cn'

const GROUPS: { key: keyof A11yPrefs; label: string; options: { value: string; label: string }[] }[] = [
  {
    key: 'text',
    label: 'Text size',
    options: [
      { value: 'standard', label: 'Standard' },
      { value: 'large', label: 'Large' },
      { value: 'larger', label: 'Larger' },
    ],
  },
  {
    key: 'contrast',
    label: 'Contrast',
    options: [
      { value: 'standard', label: 'Standard' },
      { value: 'high', label: 'High contrast' },
    ],
  },
  {
    key: 'motion',
    label: 'Motion',
    options: [
      { value: 'standard', label: 'Standard' },
      { value: 'reduce', label: 'Reduce motion' },
    ],
  },
]

/** Header menu for text size, contrast and motion. Works fully from the keyboard. */
export function AccessibilityMenu() {
  const [prefs, setPrefs] = useState<A11yPrefs>(loadPrefs)
  const set = (k: keyof A11yPrefs, v: string) => {
    const next = { ...prefs, [k]: v } as A11yPrefs
    setPrefs(next)
    savePrefs(next)
  }
  const changed = JSON.stringify(prefs) !== JSON.stringify(DEFAULT_PREFS)
  return (
    <M.Root>
      <M.Trigger
        className="relative flex size-10 items-center justify-center rounded-full border border-line bg-surface text-ink-2 transition-colors hover:border-accent-500 hover:text-ink data-[state=open]:border-accent-500"
        aria-label="Accessibility settings: text size, contrast and motion"
      >
        <Accessibility className="size-5" aria-hidden />
        {changed && <span className="absolute right-1.5 top-1.5 size-2 rounded-full bg-accent-600" aria-hidden />}
      </M.Trigger>
      <M.Portal>
        <M.Content
          align="end"
          sideOffset={8}
          className="z-50 w-64 rounded-2xl border border-line bg-surface p-2 text-sm text-ink shadow-[0_18px_48px_-18px_rgba(20,22,48,0.35)]"
        >
          <M.Label className="px-2 pb-1 pt-1.5 text-sm font-semibold">Display settings</M.Label>
          <p className="px-2 pb-2 text-xs text-ink-3">Saved in this browser only.</p>
          {GROUPS.map((g, i) => (
            <div key={g.key}>
              {i > 0 && <M.Separator className="my-1.5 h-px bg-line" />}
              <M.Label className="px-2 pb-1 pt-1 text-xs font-semibold uppercase tracking-wider text-ink-3">{g.label}</M.Label>
              <M.RadioGroup value={prefs[g.key]} onValueChange={(v) => set(g.key, v)}>
                {g.options.map((o) => (
                  <M.RadioItem
                    key={o.value}
                    value={o.value}
                    className={cn(
                      'flex min-h-10 cursor-pointer items-center justify-between rounded-lg px-2 outline-none',
                      'data-[highlighted]:bg-accent-50 data-[state=checked]:font-semibold',
                    )}
                  >
                    {o.label}
                    <M.ItemIndicator>
                      <Check className="size-4 text-accent-700" aria-hidden />
                    </M.ItemIndicator>
                  </M.RadioItem>
                ))}
              </M.RadioGroup>
            </div>
          ))}
        </M.Content>
      </M.Portal>
    </M.Root>
  )
}
