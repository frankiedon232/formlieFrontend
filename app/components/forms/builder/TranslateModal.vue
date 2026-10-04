<!--
  The translation screen (F10 M4, decision 99): every text of the form in its main language with
  the translation under it, grouped like the form (form · each page). Filter to what's still to
  do, search, and see the progress. Empty = respondents see the main language text there.
  Typing goes straight into the draft (one undo step per text). A translation whose original was
  changed afterwards says so ("Changed since translated"), with "Still right" to confirm it.
-->
<script setup lang="ts">
import type { FormField } from '#shared/utils/forms/build'
import { formTexts, staleKeys, type FormText } from '#shared/utils/forms/translations'
import { APP_LOCALES } from '#shared/utils/i18n/locales'

const props = defineProps<{ language: string }>()
const open = defineModel<boolean>('open', { default: false })
const { t } = useI18n()
const builder = useBuilder()
const schema = builder.schema
const translations = useFormTranslations()

const localeOf = (code: string) => APP_LOCALES.find(item => item.code === code)
const target = computed(() => localeOf(props.language))
const source = computed(() => localeOf(translations.main.value))
const saved = computed(() => schema.value?.translations?.[props.language] ?? {})
/** With the title respondents see (the form name when there is no title of its own). */
const texts = computed<FormText[]>(() =>
  schema.value ? formTexts({ ...schema.value, settings: { ...schema.value.settings, title: translations.formTitle.value } }) : [],
)
const done = computed(() => texts.value.filter(item => saved.value[item.key]?.trim()).length)
const stale = computed(() => (schema.value ? staleKeys(schema.value, props.language, texts.value) : new Set<string>()))

// "To do" keeps the list it started with, so a text doesn't vanish while you type it.
const filter = ref<'all' | 'todo'>('all')
const todo = ref<Set<string>>(new Set())
watch(
  [filter, open],
  () => (todo.value = new Set(texts.value.filter(item => !saved.value[item.key]?.trim() || stale.value.has(item.key)).map(item => item.key))),
  { immediate: true },
)
const search = ref('')
const shown = computed(() => {
  const words = search.value.trim().toLocaleLowerCase()
  return texts.value.filter(
    item =>
      (filter.value === 'all' || todo.value.has(item.key)) &&
      (!words || `${item.text} ${saved.value[item.key] ?? ''}`.toLocaleLowerCase().includes(words)),
  )
})
const groups = computed(() => {
  const pages = schema.value?.pages ?? []
  const order = [null, ...pages.map(page => page.id)]
  return order
    .map(page => ({
      page,
      title: page === null ? t('builder.translate.wholeForm') : pages.find(item => item.id === page)?.title || t('preview.page', { n: pages.findIndex(item => item.id === page) + 1 }),
      items: shown.value.filter(item => item.page === page),
    }))
    .filter(group => group.items.length)
})

/** What a text is, in words ("Choice · Pick one"). */
const labels = computed(() => new Map(texts.value.filter(item => item.key.endsWith('.label')).map(item => [item.key.slice(0, -'.label'.length), item.text])))
function describe(key: string) {
  const parts = key.split('.')
  if (parts[0] !== 'field') return t(`builder.translate.kind.${key.replace('.', '_')}`)
  if (parts[0] === 'field' && parts[2] === 'label') return t('builder.translate.kind.question')
  const kind = ['option', 'row', 'formula', 'help', 'placeholder', 'pattern_message', 'min_label', 'max_label'].includes(parts[2]!) ? parts[2]! : 'text'
  return `${t(`builder.translate.kind.${kind}`)} · ${labels.value.get(`field.${parts[1]}`) ?? ''}`
}
const kindOf = (key: string) => (key.startsWith('page.') ? t('builder.translate.kind.page_title') : describe(key))

const editorField = { id: 'translate', key: 'translate', type: 'rich_text', label: '', width: 12, required: false, props: { toolbar: 'full' } } as FormField
const plain = (html: string) => html.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim()
const set = (item: FormText, value: unknown) => translations.set(props.language, item.key, String(value ?? ''), item.text)
</script>

<template>
  <AppModal
    v-model:open="open"
    :title="t('builder.translate.title', { language: target?.name ?? language })"
    :description="t('builder.translate.desc', { language: source?.name ?? '' })"
    :ui="{ content: 'sm:max-w-3xl' }"
  >
    <template #body>
      <div class="flex flex-col gap-4">
        <div class="flex flex-col gap-2 sm:flex-row sm:items-center">
          <UTabs
            v-model="filter"
            :items="[
              { value: 'all', label: t('builder.translate.all') },
              { value: 'todo', label: t('builder.translate.todo', { n: texts.length - done + stale.size }) },
            ]"
            :content="false"
            color="neutral"
            size="xs"
            :ui="SEGMENTED_UI"
            :aria-label="t('builder.translate.filter')"
          />
          <UInput v-model="search" icon="i-lucide-search" size="sm" :placeholder="t('common.search')" class="sm:ms-auto sm:w-56" :aria-label="t('common.search')" />
        </div>

        <UEmpty
          v-if="!groups.length"
          icon="i-lucide-check-check"
          :title="search ? t('builder.translate.noMatch') : t('builder.translate.allDone')"
          :actions="search ? [{ label: t('dataView.clearFilters'), color: 'neutral', variant: 'outline', onClick: () => (search = '') }] : []"
          variant="naked"
        />

        <section v-for="group in groups" :key="group.page ?? 'form'" class="flex flex-col gap-3">
          <h3 class="text-xs font-medium text-muted uppercase">{{ group.title }}</h3>
          <div v-for="item in group.items" :key="item.key" class="flex flex-col gap-1.5 rounded-md border border-default p-3">
            <div class="flex items-start justify-between gap-2">
              <p class="min-w-0 text-sm text-highlighted" :dir="source?.dir">{{ item.kind === 'html' ? plain(item.text) : item.text }}</p>
              <UIcon v-if="saved[item.key]?.trim() && !stale.has(item.key)" name="i-lucide-check" class="mt-0.5 size-4 shrink-0 text-muted" :aria-label="t('builder.translate.translated')" />
            </div>
            <!-- The original changed after it was translated: check it, or confirm it still fits. -->
            <div v-if="stale.has(item.key)" class="flex flex-wrap items-center gap-2">
              <UBadge :label="t('builder.translate.changed')" icon="i-lucide-triangle-alert" color="warning" variant="subtle" size="sm" />
              <UButton :label="t('builder.translate.stillRight')" icon="i-lucide-check" color="neutral" variant="link" size="xs" @click="translations.confirm(language, item.key, item.text)" />
            </div>
            <p class="truncate text-[11px] text-dimmed">{{ kindOf(item.key) }}</p>
            <FormsRendererRichText
              v-if="item.kind === 'html'"
              :id="`translate-${item.key}`"
              :model-value="saved[item.key] ?? ''"
              :field="editorField"
              mode="live"
              :dir="target?.dir"
              @update:model-value="v => set(item, v)"
            />
            <UTextarea
              v-else-if="item.kind === 'long'"
              :model-value="saved[item.key] ?? ''"
              :rows="2"
              autoresize
              :placeholder="item.text"
              :dir="target?.dir"
              class="w-full"
              :aria-label="t('builder.translate.into', { text: item.text, language: target?.name ?? language })"
              @update:model-value="v => set(item, v)"
            />
            <UInput
              v-else
              :model-value="saved[item.key] ?? ''"
              :placeholder="item.text"
              :dir="target?.dir"
              class="w-full"
              :aria-label="t('builder.translate.into', { text: item.text, language: target?.name ?? language })"
              @update:model-value="v => set(item, v)"
            />
          </div>
        </section>
      </div>
    </template>
    <template #footer>
      <div class="flex w-full flex-col gap-3 sm:flex-row sm:items-center">
        <div class="flex flex-1 items-center gap-2">
          <UProgress :model-value="texts.length ? (done / texts.length) * 100 : 100" size="xs" color="neutral" class="flex-1" />
          <span class="shrink-0 text-xs text-muted tabular-nums">{{ t('builder.languages.progress', { done, total: texts.length }) }}</span>
        </div>
        <UButton :label="t('builder.translate.done')" color="neutral" class="justify-center" @click="open = false" />
      </div>
    </template>
  </AppModal>
</template>
