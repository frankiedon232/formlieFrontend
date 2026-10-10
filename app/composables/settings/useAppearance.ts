/**
 * The workspace's look of the portal (F14 M6): loaded once for everyone, applied as Nuxt UI colours
 * (primary, neutral) and a few CSS variables (primary shade, background, radius, font, text size).
 * The shell (rail, menu, header, footer, page) reads the rest. Settings → Appearance sets `preview`
 * while someone edits, so the whole portal is the live preview; leaving or Discard drops it.
 * Light and dark (leftovers L3): other colours in dark mode (on the dark page and on dark parts such as a dark
 * menu), and the workspace's default mode for people who haven't picked one.
 */
import { FORMALIE_APPEARANCE, type AppearanceDark, type AppearanceSettings } from '#shared/types/appearance'

const saved = ref<AppearanceSettings | null>(null)
const preview = ref<AppearanceSettings | null>(null)
let loading: Promise<void> | null = null

const RADIUS = { none: '0rem', sm: '0.25rem', md: '0.5rem', lg: '0.75rem', xl: '1rem' } as const
const FONTS = {
  manrope: "'Manrope', ui-sans-serif, system-ui, sans-serif",
  system: "system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
  serif: "ui-serif, Georgia, Cambria, 'Times New Roman', serif",
  rounded: "ui-rounded, 'SF Pro Rounded', 'Nunito', 'Varela Round', system-ui, sans-serif",
} as const
const SIZES = { sm: '15px', md: '16px', lg: '17px' } as const
/** Read by the inline script in app/spa-loading-template.html (keep the name in step). */
const LOADING_LOOK_KEY = 'formalie-loading-look'
/** The workspace default mode last applied in this browser (a display choice, nothing secret). */
const MODE_DEFAULT_KEY = 'formalie-mode-default'
/** Nuxt colour mode's own key (it writes `system` on a first visit, so it can't tell a choice by itself). */
const MODE_KEY = 'nuxt-color-mode'
/** Set once the person picks a mode themselves. */
const MODE_CHOSEN_KEY = 'formalie-mode-chosen'
const SHADES = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950]
const palette = (name: string, prefix: 'primary' | 'neutral') => SHADES.map(shade => `--ui-color-${prefix}-${shade}: var(--color-${name}-${shade})`)

/** Relative luminance contrast of white text on a colour (WCAG), to warn about unreadable brand colours. */
export function contrastWithWhite(hex: string): number {
  const channel = (value: number) => {
    const c = value / 255
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
  }
  const [r, g, b] = [1, 3, 5].map(i => channel(parseInt(hex.slice(i, i + 2), 16)))
  const luminance = 0.2126 * r! + 0.7152 * g! + 0.0722 * b!
  return 1.05 / (luminance + 0.05)
}

export function useAppearance() {
  const api = useApi()
  const tenant = useTenant()
  const current = computed<AppearanceSettings>(() => preview.value ?? saved.value ?? FORMALIE_APPEARANCE)
  const brand = computed(() => tenant.profile.value?.colors.primary ?? null)

  function load(force = false) {
    if (loading && !force) return loading
    loading = api
      .get<AppearanceSettings>('/settings/appearance', undefined, { background: true })
      .then(result => void (saved.value = result.data))
      .catch(() => {
        loading = null
      })
    return loading
  }
  const put = (value: AppearanceSettings) => (saved.value = value)

  /** The CSS for the current look (empty for Formalie's own). */
  const css = computed(() => {
    const a = current.value
    const light: string[] = []
    const dark: string[] = []
    const own: AppearanceDark | null = a.dark
    // The design draws its main buttons, chips and rings in the "inverted" colour: a primary colour takes that place
    const accent = (value: string, target: string[]) => target.push(`--ui-primary: ${value}`, `--ui-bg-inverted: ${value}`, `--ui-border-inverted: ${value}`)
    if (a.primary === 'brand' && brand.value) {
      accent(brand.value, light)
      light.push('--ui-text-inverted: #ffffff')
    } else if (a.primary !== 'mono' && a.primary !== 'brand') accent('var(--ui-color-primary-600)', light)
    if (a.background === 'tinted') light.push('--ui-bg: var(--ui-color-neutral-50)')
    // Dark mode: its own colours when set, else the light ones in their dark shades
    const d = own ?? { primary: a.primary, neutral: a.neutral, background: a.background }
    if (own) {
      if (own.neutral !== a.neutral) dark.push(...palette(own.neutral, 'neutral'))
      if (own.primary !== 'mono' && own.primary !== 'brand') dark.push(...palette(own.primary, 'primary'))
      // Back to Nuxt UI's dark defaults where light mode changed them
      if (own.primary === 'mono' || (own.primary === 'brand' && !brand.value)) dark.push('--ui-primary: var(--ui-color-primary-400)', '--ui-bg-inverted: #fff', '--ui-border-inverted: #fff', '--ui-text-inverted: var(--ui-color-neutral-900)')
      if (own.background === 'plain') dark.push('--ui-bg: var(--ui-color-neutral-900)')
    }
    if (d.primary === 'brand' && brand.value) {
      accent(brand.value, dark)
      dark.push('--ui-text-inverted: #ffffff')
    } else if (d.primary !== 'mono' && d.primary !== 'brand') {
      accent('var(--ui-color-primary-500)', dark)
      dark.push('--ui-text-inverted: #ffffff')
    }
    if (d.background === 'tinted') dark.push('--ui-bg: var(--ui-color-neutral-950)')
    if (a.radius !== 'md') light.push(`--ui-radius: ${RADIUS[a.radius]}`)
    if (a.font !== 'manrope') light.push(`--font-sans: ${FONTS[a.font]}`)
    const size = a.text_size === 'md' ? '' : `html { font-size: ${SIZES[a.text_size]}; }`
    // `html .dark` too: dark parts of a light page (a dark rail or menu) take the dark colours, `.light` parts the light ones
    return [light.length ? `html:root, html .light { ${light.join('; ')} }` : '', dark.length ? `html.dark, html .dark { ${dark.join('; ')} }` : '', size].filter(Boolean).join('\n')
  })

  /**
   * The first-load screen (`spa-loading-template.html`) starts before the app, so it can't ask the API:
   * the saved look's resolved colours and font are kept in this browser for it (display values only,
   * nothing secret; each workspace address has its own storage).
   */
  async function rememberForLoading() {
    const a = saved.value
    if (!a) return
    await nextTick()
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))
    const styles = getComputedStyle(document.documentElement)
    const token = (name: string) => styles.getPropertyValue(`--ui-color-${name}`).trim()
    // Palette colours by name (every palette is in the CSS), so dark mode may use other ones
    const color = (name: string, shade: number) => styles.getPropertyValue(`--color-${name}-${shade}`).trim() || token(`neutral-${shade}`)
    const d = a.dark ?? { primary: a.primary, neutral: a.neutral, background: a.background }
    const isMono = (primary: string) => primary === 'mono' || (primary === 'brand' && !brand.value)
    const accent = (primary: string, shade: number) => (primary === 'brand' && brand.value ? brand.value : color(primary, shade))
    const look = {
      font: FONTS[a.font],
      light: { bg: a.background === 'tinted' ? color(a.neutral, 50) : '#ffffff', text: color(a.neutral, 950), accent: isMono(a.primary) ? color(a.neutral, 900) : accent(a.primary, 600), on: '#ffffff' },
      dark: { bg: d.background === 'tinted' ? color(d.neutral, 950) : color(d.neutral, 900), text: '#ffffff', accent: isMono(d.primary) ? color(d.neutral, 100) : accent(d.primary, 500), on: isMono(d.primary) ? color(d.neutral, 900) : '#ffffff' },
    }
    try {
      localStorage.setItem(LOADING_LOOK_KEY, JSON.stringify(look))
    } catch {
      // Storage blocked: the loading screen keeps Formalie's own look
    }
  }

  /** Applies the look to the page (called once, from the portal layout). */
  function apply() {
    watchEffect(() => {
      const a = current.value
      updateAppConfig({ ui: { colors: { neutral: a.neutral, primary: a.primary === 'mono' || a.primary === 'brand' ? 'indigo' : a.primary } } })
    })
    useHead({ style: [{ key: 'formalie-appearance', textContent: css }] })
    if (import.meta.client) {
      watch([saved, brand], () => void rememberForLoading(), { immediate: true })
      // The workspace's default mode, for people who haven't picked one themselves (leftovers L3)
      const colorMode = useColorMode()
      const read = (key: string) => {
        try {
          return localStorage.getItem(key)
        } catch {
          return null
        }
      }
      const write = (key: string, value: string) => {
        try {
          localStorage.setItem(key, value)
        } catch {
          // Storage blocked: the device mode stays
        }
      }
      // A mode picked by the person (anything but the default just applied) is theirs from then on
      watch(
        () => colorMode.preference,
        value => value !== read(MODE_DEFAULT_KEY) && write(MODE_CHOSEN_KEY, '1'),
      )
      watch(
        () => saved.value?.default_mode,
        mode => {
          if (!mode) return
          const stored = read(MODE_KEY)
          // A light or dark choice from before workspace defaults existed counts as the person's own
          const chosen = read(MODE_CHOSEN_KEY) === '1' || ((stored === 'light' || stored === 'dark') && read(MODE_DEFAULT_KEY) === null)
          if (chosen) return
          write(MODE_DEFAULT_KEY, mode)
          colorMode.preference = mode
        },
        { immediate: true },
      )
    }
  }

  return { current, saved, preview, brand, load, put, apply }
}
