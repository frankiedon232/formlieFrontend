/**
 * The workspace's look of the portal (F14 M6): loaded once for everyone, applied as Nuxt UI colours
 * (primary, neutral) and a few CSS variables (primary shade, background, radius, font, text size).
 * The shell (rail, menu, header, footer, page) reads the rest. Settings → Appearance sets `preview`
 * while someone edits, so the whole portal is the live preview; leaving or Discard drops it.
 */
import { FORMALIE_APPEARANCE, type AppearanceSettings } from '#shared/types/appearance'

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
    // The design draws its main buttons, chips and rings in the "inverted" colour: a primary colour takes that place
    const accent = (value: string, target: string[]) => target.push(`--ui-primary: ${value}`, `--ui-bg-inverted: ${value}`, `--ui-border-inverted: ${value}`)
    if (a.primary === 'brand' && brand.value) {
      accent(brand.value, light)
      accent(brand.value, dark)
      light.push('--ui-text-inverted: #ffffff')
      dark.push('--ui-text-inverted: #ffffff')
    } else if (a.primary !== 'mono' && a.primary !== 'brand') {
      accent('var(--ui-color-primary-600)', light)
      accent('var(--ui-color-primary-500)', dark)
      dark.push('--ui-text-inverted: #ffffff')
    }
    if (a.background === 'tinted') {
      light.push('--ui-bg: var(--ui-color-neutral-50)')
      dark.push('--ui-bg: var(--ui-color-neutral-950)')
    }
    if (a.radius !== 'md') light.push(`--ui-radius: ${RADIUS[a.radius]}`)
    if (a.font !== 'manrope') light.push(`--font-sans: ${FONTS[a.font]}`)
    const size = a.text_size === 'md' ? '' : `html { font-size: ${SIZES[a.text_size]}; }`
    return [light.length ? `html:root { ${light.join('; ')} }` : '', dark.length ? `html.dark { ${dark.join('; ')} }` : '', size].filter(Boolean).join('\n')
  })

  /** Applies the look to the page (called once, from the portal layout). */
  function apply() {
    watchEffect(() => {
      const a = current.value
      updateAppConfig({ ui: { colors: { neutral: a.neutral, primary: a.primary === 'mono' || a.primary === 'brand' ? 'indigo' : a.primary } } })
    })
    useHead({ style: [{ key: 'formalie-appearance', textContent: css }] })
  }

  return { current, saved, preview, brand, load, put, apply }
}
