import type { PublicForm } from '#shared/types/public'
import { acceptedLanguages, pickLanguage } from '#shared/utils/forms/translations'
import { APP_LOCALES } from '#shared/utils/i18n/locales'

/**
 * The respondent's language on a public form (decisions 73 and 99): the link's `?lang=`, else the
 * browser's languages the form offers, else its main language. Chosen once on the server (so the
 * first paint is already right) and kept in state; the switcher changes it and puts `?lang=` in
 * the address so the link can be shared. Buttons, messages, dates and right-to-left follow it, for
 * this page only (a signed-in person's portal language stays as it is).
 */
export async function usePublicLanguage(formKey: string, form: Ref<PublicForm | null>) {
  const route = useRoute()
  const router = useRouter()
  const nuxtApp = useNuxtApp()
  const offered = computed(() => form.value?.languages ?? [])
  const wanted = () => (typeof route.query.lang === 'string' ? route.query.lang : null)
  const accepted = import.meta.server
    ? acceptedLanguages(useRequestHeaders(['accept-language'])['accept-language'])
    : [...(navigator.languages ?? [])]

  const language = useState(`form-language:${formKey}`, () => pickLanguage(offered.value, wanted(), accepted))
  // A language the form no longer offers (or one asked for in the link) is checked again.
  watch([offered, () => route.query.lang], () => (language.value = pickLanguage(offered.value, wanted() ?? language.value, accepted)))

  async function apply(code: string) {
    const i18n = nuxtApp.$i18n
    if (i18n.locale.value === code) return
    await i18n.loadLocaleMessages(code as Parameters<typeof i18n.loadLocaleMessages>[0])
    ;(i18n.locale as unknown as { value: string }).value = code
  }
  /** The switcher: answers stay, the address gets `?lang=` (shareable). */
  function choose(code: string) {
    if (!offered.value.includes(code)) return
    language.value = code
    void router.replace({ query: { ...route.query, lang: code } })
  }
  const dir = computed(() => APP_LOCALES.find(locale => locale.code === language.value)?.dir ?? 'ltr')
  // Watchers before the first await, so they belong to the page (and stop with it).
  watch(language, code => void apply(code))
  await apply(language.value)
  return { language, offered, choose, dir }
}
