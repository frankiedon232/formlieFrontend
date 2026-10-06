<!--
  Form settings → Form language (decision 73). The language sets everything Formalie shows
  (buttons, messages, dates) and, in the same step (owner, 2026-10-04: "why a second button?"),
  moves the form's own text into it: every text that came from a template is translated
  (POST /templates/translate-content); text people wrote stays as it is (translated per language
  per language in More languages, decision 99). One undo brings back both the language and the text.
  A language the form already offers becomes the main one with its translations; the old main text
  is kept as a translation (nothing is lost).
-->
<script setup lang="ts">
import type { FormSchemaV1 } from '#shared/utils/forms/schema'
import { formTexts } from '#shared/utils/forms/translations'
import { APP_LOCALES } from '#shared/utils/i18n/locales'

const { t } = useI18n()
const api = useApi()
const toast = useToast()
const { handle } = useErrorHandler()
const builder = useBuilder()
const schema = builder.schema
const session = injectBuilderSession()
const translations = useFormTranslations()

const current = computed(() => schema.value?.settings?.language ?? 'en')
// Only the languages the workspace offers for forms (Settings → Language and region, F14); the form's own stays
const { locale: workspace } = useWorkspaceLocale()
const items = computed(() => APP_LOCALES.filter(item => !workspace.value || workspace.value.form_languages.includes(item.code) || item.code === current.value).map(item => ({ value: item.code, label: item.name, description: item.englishName, icon: item.flag })))
const flag = computed(() => APP_LOCALES.find(item => item.code === current.value)?.flag)
const nameOf = (code: string) => APP_LOCALES.find(item => item.code === code)?.name ?? code

const { busy, run } = useBusy()
async function setLanguage(value: string) {
  if (!schema.value || value === current.value) return
  const from = current.value
  const before = new Map(formTexts(schema.value).map(item => [item.key, item.text]))
  if (translations.extras.value.includes(value)) {
    translations.promote(value)
    toast.add({
      title: t('builder.language.changed', { language: nameOf(value) }),
      description: t('builder.languages.promoted', { language: nameOf(from) }),
      icon: 'i-lucide-languages',
      color: 'success',
      actions: [{ label: t('builder.undo'), color: 'neutral', variant: 'outline', size: 'xs', onClick: () => void builder.history.undo() }],
    })
    return
  }
  // One undo step for the language and the translated text.
  builder.history.record()
  schema.value.settings = { ...schema.value.settings, language: value }
  await run(async () => {
    try {
      // The title respondents see follows too (the form name in the list stays as it is).
      const current = schema.value
      if (!current) return
      const formName = session?.form.value?.name ?? ''
      const title = current.settings?.title || formName
      const { data } = await api.post<{ schema: FormSchemaV1; translated: number; kept: number }>('/templates/translate-content', {
        schema: { ...current, settings: { ...current.settings, title } },
        from,
        to: value,
      })
      if (!schema.value || schema.value.settings?.language !== value) return
      const shown = data.schema.settings?.title
      schema.value.settings = { ...schema.value.settings, title: shown && shown !== formName ? shown : undefined }
      schema.value.pages = data.schema.pages
      schema.value.thank_you = data.schema.thank_you
      if (data.schema.settings?.guide) schema.value.settings = { ...schema.value.settings, guide: data.schema.settings.guide }
      if (data.schema.theme) schema.value.theme = data.schema.theme
      translations.rebase(before)
      toast.add({
        title: t('builder.language.changed', { language: nameOf(value) }),
        description: [
          data.translated ? t('builder.language.translated', { n: data.translated }, data.translated) : '',
          data.kept ? t('builder.language.kept', { n: data.kept }, data.kept) : '',
        ]
          .filter(Boolean)
          .join(' '),
        icon: 'i-lucide-languages',
        color: 'success',
        actions: [{ label: t('builder.undo'), color: 'neutral', variant: 'outline', size: 'xs', onClick: () => void builder.history.undo() }],
      })
    } catch (error) {
      // The language is changed; only the text stays as it was.
      handle(error)
    }
  })
}
</script>

<template>
  <section v-if="schema" class="flex flex-col gap-3">
    <h3 class="text-xs font-medium text-muted uppercase">{{ t('builder.language.title') }}</h3>
    <UFormField :description="t('builder.language.hint')">
      <USelectMenu
        :model-value="current"
        :items="items"
        value-key="value"
        :search-input="{ placeholder: t('common.search') }"
        :icon="busy ? 'i-lucide-loader-circle' : flag"
        :loading="busy"
        :disabled="busy"
        class="w-full"
        :aria-label="t('builder.language.title')"
        @update:model-value="v => setLanguage(String(v))"
      />
    </UFormField>
  </section>
</template>
