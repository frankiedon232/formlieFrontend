<!--
  Form settings → Form language (decision 73). The language sets everything Formalie shows
  (buttons, messages, dates); the form's own text is what the creator wrote. Changing the language
  offers to translate that text too (owner, 2026-10-04): every text that came from a template is
  translated (POST /templates/translate-content); text people wrote stays as it is — translated per
  language later (form translations, M4). Undo brings the previous text back.
-->
<script setup lang="ts">
import type { FormSchemaV1 } from '#shared/utils/forms/schema'
import { APP_LOCALES } from '#shared/utils/i18n/locales'

const { t } = useI18n()
const api = useApi()
const toast = useToast()
const { handle } = useErrorHandler()
const builder = useBuilder()
const schema = builder.schema

const items = computed(() => APP_LOCALES.map(item => ({ value: item.code, label: item.name, description: item.englishName, icon: item.flag })))
const current = computed(() => schema.value?.settings?.language ?? 'en')
const flag = computed(() => APP_LOCALES.find(item => item.code === current.value)?.flag)
const languageName = computed(() => APP_LOCALES.find(item => item.code === current.value)?.name ?? current.value)

/** The language the text was in before the last change (offered as "translate from"). */
const previous = ref<string | null>(null)
function setLanguage(value: string) {
  if (!schema.value || value === current.value) return
  builder.history.record()
  previous.value = current.value
  schema.value.settings = { ...schema.value.settings, language: value }
}

const { busy, run } = useBusy()
async function translate() {
  if (!schema.value) return
  await run(async () => {
    try {
      const { data } = await api.post<{ schema: FormSchemaV1; translated: number; kept: number }>('/templates/translate-content', {
        schema: schema.value,
        from: previous.value ?? 'en',
        to: current.value,
      })
      if (!schema.value) return
      builder.history.record()
      schema.value.pages = data.schema.pages
      schema.value.thank_you = data.schema.thank_you
      previous.value = null
      toast.add({
        title: t('builder.language.translated', { n: data.translated }, data.translated),
        description: data.kept ? t('builder.language.kept', { n: data.kept }, data.kept) : undefined,
        icon: 'i-lucide-languages',
        color: data.translated ? 'success' : 'neutral',
      })
    } catch (error) {
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
        :icon="flag"
        class="w-full"
        :aria-label="t('builder.language.title')"
        @update:model-value="v => setLanguage(String(v))"
      />
    </UFormField>
    <UAlert
      v-if="previous"
      icon="i-lucide-languages"
      color="neutral"
      variant="subtle"
      :title="t('builder.language.offer', { language: languageName })"
      :description="t('builder.language.offerDesc')"
      :actions="[
        { label: t('builder.language.translate'), color: 'neutral', size: 'xs', loading: busy, onClick: translate },
        { label: t('builder.language.notNow'), color: 'neutral', variant: 'ghost', size: 'xs', disabled: busy, onClick: () => (previous = null) },
      ]"
      orientation="vertical"
    />
    <UButton
      v-else
      :label="t('builder.language.translateTo', { language: languageName })"
      icon="i-lucide-languages"
      color="neutral"
      variant="outline"
      size="xs"
      class="self-start"
      :loading="busy"
      @click="translate"
    />
  </section>
</template>
