<!--
  Form settings → More languages (F10 M4, decision 99): the languages a form offers besides its main
  one, each with how much is translated, Translate (opens the translation screen) and Remove.
  Adding one fills in everything the built-in dictionaries know; respondents get a switcher.
-->
<script setup lang="ts">
import { translationProgress } from '#shared/utils/forms/translations'
import { APP_LOCALES } from '#shared/utils/i18n/locales'

const { t } = useI18n()
const toast = useToast()
const confirm = useConfirm()
const builder = useBuilder()
const schema = builder.schema
const translations = useFormTranslations()
const { main, extras } = translations

const localeOf = (code: string) => APP_LOCALES.find(item => item.code === code)
// Only the languages the workspace offers for forms (Settings → Language and region, F14)
const { locale: workspace } = useWorkspaceLocale()
const offered = (code: string) => !workspace.value || workspace.value.form_languages.includes(code)
const addable = computed(() =>
  APP_LOCALES.filter(item => item.code !== main.value && !extras.value.includes(item.code) && offered(item.code)).map(item => ({
    value: item.code,
    label: item.name,
    description: item.englishName,
    icon: item.flag,
  })),
)
const rows = computed(() =>
  extras.value.map(code => {
    const progress = schema.value ? translationProgress(withTitle.value!, code) : { done: 0, total: 0, stale: 0 }
    return { code, locale: localeOf(code), ...progress, percent: progress.total ? Math.round((progress.done / progress.total) * 100) : 100 }
  }),
)
/** Counted with the title respondents see (the form name when it has no title of its own). */
const withTitle = computed(() =>
  schema.value ? { ...schema.value, settings: { ...schema.value.settings, title: translations.formTitle.value } } : null,
)

const translating = ref<string | null>(null)
const modalUsed = ref(false)
watch(translating, code => code && (modalUsed.value = true))

/** The picker always shows "Add a language…" again after a pick (a fresh one each time). */
const pickerKey = ref(0)
const adding = ref<string | null>(null)
const { run } = useBusy()
async function add(code: string | undefined) {
  pickerKey.value++
  if (!code) return
  adding.value = code
  await run(async () => {
    try {
      const { filled, total } = await translations.add(code)
      toast.add({
        title: t('builder.languages.added', { language: localeOf(code)?.name ?? code }),
        description: t('builder.languages.filled', { done: filled, total }),
        icon: 'i-lucide-languages',
        color: 'success',
        actions: [{ label: t('builder.languages.translate'), color: 'neutral', variant: 'outline', size: 'xs', onClick: () => void (translating.value = code) }],
      })
    } finally {
      adding.value = null
    }
  })
}
async function remove(code: string) {
  const name = localeOf(code)?.name ?? code
  if (!(await confirm({ title: t('builder.languages.removeTitle', { language: name }), description: t('builder.languages.removeDesc'), danger: true }))) return
  translations.remove(code)
}
</script>

<template>
  <section v-if="schema" class="flex flex-col gap-3">
    <h3 class="text-xs font-medium text-muted uppercase">{{ t('builder.languages.title') }}</h3>
    <p class="text-xs text-muted">{{ t('builder.languages.hint') }}</p>

    <ul v-if="rows.length" class="flex flex-col divide-y divide-default rounded-md border border-default">
      <li v-for="row in rows" :key="row.code" class="flex flex-col gap-2 p-2.5">
        <div class="flex items-center gap-2">
          <UIcon v-if="row.locale?.flag" :name="row.locale.flag" class="size-4 shrink-0" />
          <span class="min-w-0 flex-1 truncate text-sm text-highlighted">{{ row.locale?.name ?? row.code }}</span>
          <UButton :label="t('builder.languages.translate')" color="neutral" variant="outline" size="xs" @click="translating = row.code" />
          <UButton
            icon="i-lucide-x"
            color="neutral"
            variant="ghost"
            size="xs"
            square
            :aria-label="t('builder.languages.remove', { language: row.locale?.name ?? row.code })"
            @click="remove(row.code)"
          />
        </div>
        <div class="flex items-center gap-2">
          <UProgress :model-value="row.percent" size="xs" color="neutral" class="flex-1" />
          <span class="shrink-0 text-[11px] text-muted tabular-nums">{{ t('builder.languages.progress', { done: row.done, total: row.total }) }}</span>
          <UBadge v-if="row.stale" :label="t('builder.languages.toCheck', { n: row.stale })" color="warning" variant="subtle" size="sm" />
        </div>
      </li>
    </ul>

    <USelectMenu
      :key="pickerKey"
      :items="addable"
      value-key="value"
      :search-input="{ placeholder: t('common.search') }"
      :placeholder="t('builder.languages.add')"
      icon="i-lucide-plus"
      :loading="!!adding"
      :disabled="!!adding"
      class="w-full"
      :aria-label="t('builder.languages.add')"
      @update:model-value="v => add(v as string | undefined)"
    />

    <LazyFormsBuilderTranslateModal
      v-if="modalUsed"
      :open="!!translating"
      :language="translating ?? extras[0] ?? ''"
      @update:open="v => !v && (translating = null)"
    />
  </section>
</template>
