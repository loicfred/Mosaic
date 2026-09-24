/**
 * Display preferences for readers who need them: larger text, higher contrast,
 * less motion. They only change presentation and are kept in this browser
 * (localStorage), never sent to the server.
 */
export interface A11yPrefs {
  text: 'standard' | 'large' | 'larger'
  contrast: 'standard' | 'high'
  motion: 'standard' | 'reduce'
}

const KEY = 'valora.a11y'
export const DEFAULT_PREFS: A11yPrefs = { text: 'standard', contrast: 'standard', motion: 'standard' }

export function loadPrefs(): A11yPrefs {
  try {
    const raw = localStorage.getItem(KEY)
    return raw ? { ...DEFAULT_PREFS, ...(JSON.parse(raw) as Partial<A11yPrefs>) } : DEFAULT_PREFS
  } catch {
    return DEFAULT_PREFS
  }
}

export function applyPrefs(p: A11yPrefs) {
  const el = document.documentElement
  el.dataset.text = p.text
  el.dataset.contrast = p.contrast
  el.dataset.motion = p.motion
}

export function savePrefs(p: A11yPrefs) {
  applyPrefs(p)
  try {
    localStorage.setItem(KEY, JSON.stringify(p))
  } catch {
    /* storage unavailable (private mode): the choice still applies for this visit */
  }
}
