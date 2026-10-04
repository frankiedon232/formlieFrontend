import { readableOn, type FormTheme } from '#shared/utils/forms/theme'

export interface FrameProps {
  theme: FormTheme
  title: string
  intro?: string
  questions: number
  minutes: number
  org: { name: string; logo: string | null; website: string | null }
}

/**
 * What every page style around a public form shares (F10; page designs, owner 2026-10-04): the
 * brand colour and the text on it, the bar / panel surface for the chosen tone, the organisation's
 * website (https only, never the portal), its initials, the quick facts and the year.
 */
export function useFrameParts(props: FrameProps) {
  const { t } = useI18n()
  const frame = computed(() => props.theme.frame)
  const primary = computed(() => props.theme.colors.primary)
  const onPrimary = computed(() => readableOn(primary.value))
  const brandGradient = computed(() => `linear-gradient(135deg, ${primary.value}, color-mix(in oklab, ${primary.value} 62%, #000))`)

  /** Bar / band surface for the chosen tone. */
  const tone = computed(() => {
    switch (frame.value.tone) {
      case 'dark':
        return { background: '#0a0a0a', color: '#fafafa', borderColor: 'rgb(255 255 255 / 0.08)' }
      case 'brand':
        return { background: primary.value, color: onPrimary.value, borderColor: 'transparent' }
      default:
        return { background: props.theme.container.bg, color: props.theme.colors.text, borderColor: 'var(--ui-border)' }
    }
  })
  /** Large surfaces (side panel, banner): the brand tone as a gradient. */
  const surface = computed(() =>
    frame.value.tone === 'light'
      ? { background: props.theme.container.bg, color: props.theme.colors.text }
      : frame.value.tone === 'dark'
        ? { background: '#0a0a0a', color: '#fafafa' }
        : { background: brandGradient.value, color: onPrimary.value },
  )

  const website = computed(() => (frame.value.show_website && props.org.website && /^https:\/\//i.test(props.org.website) ? props.org.website : null))
  const websiteHost = computed(() => {
    try {
      return website.value ? new URL(website.value).hostname.replace(/^www\./, '') : ''
    } catch {
      return ''
    }
  })
  const initials = computed(() =>
    props.org.name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map(word => word[0]!.toUpperCase())
      .join(''),
  )
  const facts = computed(() =>
    frame.value.show_facts
      ? [
          { icon: 'i-lucide-timer', label: t('public.frame.minutes', { n: props.minutes }, props.minutes) },
          { icon: 'i-lucide-list-checks', label: t('public.frame.questions', { n: props.questions }, props.questions) },
          { icon: 'i-lucide-lock-keyhole', label: t('public.frame.encrypted') },
        ]
      : [],
  )
  const year = new Date().getFullYear()
  return { frame, primary, onPrimary, brandGradient, tone, surface, website, websiteHost, initials, facts, year }
}
