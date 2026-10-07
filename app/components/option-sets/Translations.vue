<!--
  Option list editor → Translations (F15 M1): the labels in the other languages the workspace's forms
  use, one column per language with its progress. A form gets them when it is updated from the list,
  for the languages it offers. Retired options are left out.
-->
<script setup lang="ts">
import type { OptionItem } from '#shared/types/forms'
import { APP_LOCALES } from '#shared/utils/i18n/locales'

const options = defineModel<OptionItem[]>({ required: true })
const props = defineProps<{ languages: string[] }>()
const { t } = useI18n()
const { percent } = useFormat()

const language = ref(props.languages[0] ?? '')
watch(() => props.languages, list => !list.includes(language.value) && (language.value = list[0] ?? ''))
const active = computed(() => options.value.filter(option => option.active !== false))
const progress = (code: string) => (active.value.length ? active.value.filter(option => option.translations?.[code]?.trim()).length / active.value.length : 0)
const items = computed(() => props.languages.map(code => {
  const locale = APP_LOCALES.find(item => item.code === code)
  return { value: code, label: `${locale?.name ?? code} · ${percent(progress(code))}`, icon: locale?.flag }
}))
function setText(option: OptionItem, text: string) {
  const others = Object.entries(option.translations ?? {}).filter(([code]) => code !== language.value)
  const translations = Object.fromEntries(text.trim() ? [...others, [language.value, text]] : others)
  if (Object.keys(translations).length) option.translations = translations
  else delete option.translations
}
const q = ref('')
const limit = ref(100)
const shown = computed(() => {
  const term = q.value.trim().toLowerCase()
  return (term ? active.value.filter(option => `${option.label} ${option.translations?.[language.value] ?? ''}`.toLowerCase().includes(term)) : active.value).slice(0, limit.value)
})
</script>

<template>
  <AppEmpty v-if="!languages.length" size="sm" icon="i-lucide-languages" :title="t('optionSets.translations.none')" :description="t('optionSets.translations.noneDesc')" :actions="[{ label: t('optionSets.translations.settings'), icon: 'i-lucide-settings-2', color: 'neutral', variant: 'outline', to: '/settings/language' }]" />
  <div v-else class="flex flex-col gap-3">
    <div class="flex flex-wrap items-center gap-2">
      <USelect v-model="language" :items="items" :icon="items.find(item => item.value === language)?.icon" class="w-full sm:w-64" :aria-label="t('optionSets.translations.language')" />
      <UInput v-model="q" icon="i-lucide-search" :placeholder="t('optionSets.items.search')" size="sm" class="w-full sm:w-56" />
      <UProgress :model-value="Math.round(progress(language) * 100)" color="neutral" size="xs" class="w-32" :aria-label="t('optionSets.translations.progress')" />
    </div>
    <p class="text-xs text-muted">{{ t('optionSets.translations.hint') }}</p>
    <ul class="flex flex-col divide-y divide-default rounded-lg border border-default">
      <li v-for="option in shown" :key="option.value" class="grid items-center gap-2 px-3 py-1.5 sm:grid-cols-2">
        <span class="truncate text-sm text-default">{{ option.label }}</span>
        <UInput :model-value="option.translations?.[language] ?? ''" size="sm" class="w-full" :placeholder="option.label" :aria-label="t('optionSets.translations.for', { label: option.label })" @update:model-value="value => setText(option, String(value))" />
      </li>
    </ul>
    <UButton v-if="active.length > limit" :label="t('optionSets.items.more', { n: active.length - limit })" color="neutral" variant="outline" size="sm" class="self-center" @click="limit += 200" />
  </div>
</template>
