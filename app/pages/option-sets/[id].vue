<!--
  One option list (F15 M1): name and description, then Options (edit, reorder, retire, paste, import),
  Translations (labels per language) and Used in (forms using it, "Update forms"). Changes are a draft
  until Save (Ctrl / ⌘ + S); Discard puts them back; leaving with unsaved changes asks first. Levels
  (F15 M2) sit above the tabs: a plain list or Country → Region → City. Size (F15 M5): standard, or
  large (up to 200,000 options kept on the server).
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { LocalisationSettings } from '#shared/types/settings'
import type { OptionColumn, OptionItem, OptionLevel, OptionListRow } from '#shared/types/forms'
import { keptOnServer } from '#shared/utils/forms/options'

definePageMeta({ breadcrumb: 'nav.optionSets' })
const { t } = useI18n()
const route = useRoute()
const api = useApi()
const toast = useToast()
const confirm = useConfirm()
const { handle } = useErrorHandler()
const { relative } = useFormat()
const id = String(route.params.id)
const breadcrumbs = useBreadcrumbs()

const list = ref<OptionListRow | null>(null)
const failed = ref(false)
type Draft = { name: string; description: string | null; levels: OptionLevel[] | null; columns: OptionColumn[] | null; large: boolean; options: OptionItem[] }
const draft = ref<Draft | null>(null)
const draftOf = (row: OptionListRow): Draft => clone({ name: row.name, description: row.description ?? null, levels: row.levels ?? null, columns: row.columns ?? null, large: !!row.large, options: row.options })
function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T
}
async function load() {
  failed.value = false
  try {
    list.value = (await api.get<OptionListRow>(`/option-lists/${id}`)).data
    draft.value = draftOf(list.value)
    breadcrumbs.setLabel(route.path, list.value.name)
  } catch (error) {
    failed.value = true
    handle(error, { silent: true })
  }
}
// Languages of the workspace's forms other than its own (translations)
const languages = ref<string[]>([])
onMounted(async () => {
  await load()
  try {
    const { data } = await api.get<LocalisationSettings>('/settings/localisation', undefined, { background: true })
    languages.value = data.form_languages.filter(code => code !== data.language)
  } catch {
    languages.value = []
  }
})
useHead({ title: () => list.value?.name ?? t('nav.optionSets') })

const saved = computed(() => (list.value ? draftOf(list.value) : null))
const dirty = computed(() => !!draft.value && JSON.stringify(draft.value) !== JSON.stringify(saved.value))
const savedValues = computed(() => new Set((list.value?.options ?? []).map(option => option.value)))
const tab = ref<'items' | 'translations' | 'usage'>('items')
const tabs = computed(() => [
  { value: 'items', label: t('optionSets.tab.items'), icon: 'i-lucide-list', badge: draft.value?.options.length },
  { value: 'translations', label: t('optionSets.tab.translations'), icon: 'i-lucide-languages' },
  { value: 'usage', label: t('optionSets.tab.usage'), icon: 'i-lucide-file-search', badge: list.value?.forms_count },
])

const saving = ref(false)
const usageRef = useTemplateRef<{ load: () => Promise<void> }>('usage')
async function save() {
  if (!draft.value || !dirty.value || saving.value) return
  const empty = draft.value.options.filter(option => !option.label.trim())
  if (empty.length) {
    toast.add({ title: t('optionSets.emptyLabels', { n: empty.length }, empty.length), color: 'warning', icon: 'i-lucide-triangle-alert' })
    return
  }
  const levels = draft.value.levels
  // Values per level, built once (a large list has up to 200,000 options)
  const byLevel = new Map<number, Set<string>>()
  for (const option of draft.value.options) {
    const at = option.level ?? 0
    if (!byLevel.has(at)) byLevel.set(at, new Set())
    byLevel.get(at)!.add(option.value)
  }
  const orphans = levels ? draft.value.options.filter(option => (option.level ?? 0) > 0 && !byLevel.get((option.level ?? 0) - 1)?.has(option.parent ?? '')) : []
  if (levels?.some(level => !level.label.trim()) || orphans.length) {
    toast.add({ title: orphans.length ? t('optionSets.levels.orphans', { n: orphans.length }, orphans.length) : t('optionSets.levels.unnamed'), color: 'warning', icon: 'i-lucide-triangle-alert' })
    return
  }
  if (draft.value.columns?.some(column => !column.label.trim())) {
    toast.add({ title: t('optionSets.columns.unnamed'), color: 'warning', icon: 'i-lucide-triangle-alert' })
    return
  }
  saving.value = true
  try {
    list.value = (await api.patch<OptionListRow>(`/option-lists/${id}`, { name: draft.value.name, description: draft.value.description, levels: draft.value.levels ?? [], columns: draft.value.columns ?? [], large: draft.value.large, options: draft.value.options })).data
    draft.value = draftOf(list.value)
    toast.add({ title: t('optionSets.saved'), description: list.value.forms_count ? (keptOnServer(list.value) ? t('optionSets.savedLive') : t('optionSets.savedUsed', { n: list.value.forms_count }, list.value.forms_count)) : undefined, color: 'success', icon: 'i-lucide-circle-check' })
    void usageRef.value?.load()
  } catch (error) {
    handle(error)
  } finally {
    saving.value = false
  }
}
const discard = () => saved.value && (draft.value = clone(saved.value))
defineShortcuts({ meta_s: { usingInput: true, handler: () => canEdit.value && void save() } })
onBeforeRouteLeave(async () => (!dirty.value ? true : await confirm({ title: t('settings.leave.title'), description: t('settings.leave.desc'), confirmLabel: t('settings.leave.confirm'), danger: true })))
useEventListener(window, 'beforeunload', event => dirty.value && event.preventDefault())

// Paste / import
const importOpen = ref(false)
const importSource = ref<'paste' | 'file'>('paste')
const openImport = (source: 'paste' | 'file') => ((importSource.value = source), (importOpen.value = true))
// An import can also set up levels (a file with one column per level, owner 2026-10-08)
const applyImport = (options: OptionItem[], levels: OptionLevel[] | null) => draft.value && ((draft.value.options = options), (draft.value.levels = levels))
// A file over 20,000 options can make the list large (F15 M5), after the import explains what that means
const makeLarge = () => draft.value && (draft.value.large = true)

// What this person may do with this list (F22 R2 M3: own · all; Formalie's lists are use-only)
const { can } = useCan()
const canEdit = computed(() => !!list.value?.can?.edit)
const moreItems = computed<DropdownMenuItem[][]>(() =>
  [
    can('lists.duplicate') ? [{ label: t('optionSets.duplicate'), icon: 'i-lucide-copy', onSelect: duplicate }] : [],
    list.value?.can?.delete ? [{ label: t('apiService.actions.delete'), icon: 'i-lucide-trash-2', color: 'error' as const, onSelect: remove }] : [],
  ].filter(group => group.length),
)
async function duplicate() {
  try {
    const { data } = await api.post<{ id: string; name: string }>(`/option-lists/${id}/duplicate`)
    toast.add({ title: t('optionSets.duplicated', { name: list.value?.name ?? '' }), color: 'success', icon: 'i-lucide-copy' })
    await navigateTo(`/option-sets/${data.id}`)
  } catch (error) {
    handle(error)
  }
}
async function remove() {
  if (!list.value) return
  const ok = await confirm({ title: t('optionSets.deleteTitle', { name: list.value.name }), description: list.value.forms_count ? t('optionSets.deleteUsed', { n: list.value.forms_count }, list.value.forms_count) : t('optionSets.deleteDesc'), confirmLabel: t('apiService.delete.confirm'), danger: true })
  if (!ok) return
  try {
    await api.del(`/option-lists/${id}`)
    draft.value = saved.value ? clone(saved.value) : null
    toast.add({ title: t('optionSets.deleted', { name: list.value.name }), color: 'success', icon: 'i-lucide-trash-2' })
    await navigateTo('/option-sets')
  } catch (error) {
    handle(error)
  }
}
</script>

<template>
  <AppPanel id="option-set" :title="list?.name ?? t('nav.optionSets')" :subtitle="list ? t('optionSets.updatedBy', { when: relative(list.updated_at), name: list.created_by.name }) : undefined">
    <template #actions>
      <UButton v-if="canEdit" :label="t('settings.discard')" color="neutral" variant="outline" :disabled="!dirty || saving" class="hidden sm:inline-flex" @click="discard" />
      <UButton v-if="canEdit" :label="t('common.save')" icon="i-lucide-check" color="neutral" :loading="saving" :disabled="!dirty" @click="save">
        <template #trailing><UKbd value="meta" size="sm" class="hidden sm:inline-flex" /><UKbd value="S" size="sm" class="hidden sm:inline-flex" /></template>
      </UButton>
      <UDropdownMenu v-if="moreItems.length" :items="moreItems" :content="{ align: 'end' }">
        <UButton icon="i-lucide-ellipsis" color="neutral" variant="outline" square :aria-label="t('dataView.actions')" />
      </UDropdownMenu>
    </template>

    <AppEmpty v-if="failed" icon="i-lucide-list-x" :title="t('optionSets.notFound')" :actions="[{ label: t('nav.optionSets'), icon: 'i-lucide-arrow-left', color: 'neutral', variant: 'outline', to: '/option-sets' }]" />
    <div v-else-if="!draft" class="flex flex-col gap-4"><USkeleton class="h-24 rounded-lg" /><USkeleton v-for="n in 5" :key="n" class="h-10" /></div>
    <template v-else>
      <UAlert v-if="!canEdit" icon="i-lucide-lock" color="neutral" variant="subtle" :title="t('library.readOnly')" :description="list?.created_by.id === 'system' ? t('library.readOnlySystem') : t('library.readOnlyRole')" />
      <!-- Without "change lists" (or a Formalie list) everything is shown but locked -->
      <fieldset :disabled="!canEdit" class="contents">
      <div class="grid gap-4 sm:grid-cols-[minmax(0,20rem)_minmax(0,1fr)]">
        <UFormField :label="t('optionSets.name')" required :error="!draft.name.trim() ? t('library.nameRequired') : undefined">
          <UInput v-model="draft.name" maxlength="80" class="w-full" />
        </UFormField>
        <UFormField :label="t('optionSets.description')">
          <UInput :model-value="draft.description ?? ''" maxlength="300" :placeholder="t('optionSets.descriptionPlaceholder')" class="w-full" @update:model-value="value => draft && (draft.description = String(value) || null)" />
        </UFormField>
      </div>
      <OptionSetsGuide />
      <OptionSetsSize v-model:large="draft.large" :count="draft.options.length" />
      <OptionSetsLevels v-model:levels="draft.levels" v-model:options="draft.options" :saved-values="savedValues" />
      <OptionSetsColumns v-model:columns="draft.columns" v-model:options="draft.options" />
      </fieldset>
      <UTabs v-model="tab" :items="tabs" :content="false" color="neutral" variant="link" class="w-full" />
      <fieldset :disabled="!canEdit" class="contents">
      <OptionSetsItems v-if="tab === 'items'" v-model="draft.options" :saved-values="savedValues" :levels="draft.levels" :columns="draft.columns" @paste="openImport('paste')" @import="openImport('file')" />
      <OptionSetsTranslations v-else-if="tab === 'translations'" v-model="draft.options" :languages="languages" />
      <OptionSetsUsage v-show="tab === 'usage'" ref="usage" :list-id="id" :dirty="dirty" @synced="load" />
      </fieldset>
    </template>

    <OptionSetsImportModal v-if="draft" v-model:open="importOpen" :source="importSource" :options="draft.options" :languages="languages" :levels="draft.levels" :columns="draft.columns" :large="draft.large" @apply="applyImport" @large="makeLarge" />
  </AppPanel>
</template>
