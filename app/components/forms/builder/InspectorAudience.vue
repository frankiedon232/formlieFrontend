<!--
  Field access (owner, 2026-10-03): who the field is for. Everyone (default) overrides everything;
  otherwise pick departments, job titles, roles or people, all of them, or some from the list. The
  departments and job titles are the workspace's own (Settings → Organisation, F14 M2): with none yet,
  a link to set them up; archived or removed ones a form still uses are marked. A restricted
  field is never required (people it isn't meant for must still be able to submit), and its
  answers are later shown only to the same audience (F11).
-->
<script setup lang="ts">
import type { Directory, DirectoryItem } from '#shared/types/directory'
import type { FormField } from '#shared/utils/forms/build'

type Mode = NonNullable<FormField['audience']>['mode']

const props = defineProps<{ field: FormField }>()
const { t } = useI18n()
const builder = useBuilder()
const api = useApi()

// The workspace directory, loaded once and shared (the inspector is rebuilt when the field
// changes, so the result and the request in flight live outside it). In the background, no page bar.
const directory = useState<Directory | null>('field-access-directory', () => null)
const loading = useState('field-access-directory-loading', () => false)
async function load() {
  if (directory.value || loading.value) return
  loading.value = true
  try {
    directory.value = (await api.get<Directory>('/directory', undefined, { background: true })).data
  } catch {
    // The list stays empty ("No data"); choosing the mode again retries.
  } finally {
    loading.value = false
  }
}

const audience = computed(() => props.field.audience ?? { mode: 'everyone' as Mode })
const mode = computed(() => audience.value.mode)
watch(mode, value => value !== 'everyone' && load(), { immediate: true })

const ICONS: Record<Mode, string> = { everyone: 'i-lucide-users-round', department: 'i-lucide-network', job_title: 'i-lucide-id-card', role: 'i-lucide-shield', user: 'i-lucide-user-round' }
const modes = computed(() =>
  (['everyone', 'department', 'job_title', 'role', 'user'] as const).map(value => ({ value, label: t(`builder.audience.mode.${value}`), icon: ICONS[value] })),
)
const LIST: Record<Exclude<Mode, 'everyone'>, Exclude<keyof Directory, never>> = { department: 'departments', job_title: 'job_titles', role: 'roles', user: 'users' }
const SETTINGS: Partial<Record<Mode, string>> = { department: '/people/departments', job_title: '/people/job-titles' }
const listed = computed<DirectoryItem[]>(() => (mode.value === 'everyone' ? [] : (directory.value?.[LIST[mode.value]] ?? [])))
// Active entries to choose from; archived ones only while chosen (marked)
const items = computed(() =>
  listed.value
    .filter(item => !item.archived || audience.value.ids?.includes(item.id))
    .map(item => ({ value: item.id, label: item.archived ? `${item.name} (${t('builder.audience.archived')})` : item.name, description: item.detail })),
)
/** The workspace has none of this kind yet (departments, job titles). */
const noneYet = computed(() => !!directory.value && !!SETTINGS[mode.value] && !listed.value.some(item => !item.archived))
/** Chosen entries that are archived or no longer exist. */
const stale = computed(() => (audience.value.ids ?? []).filter(id => { const item = listed.value.find(entry => entry.id === id); return !item || item.archived }).length)

/** One undo step per change; switching away from "everyone" also switches "required" off. */
function write(next: FormField['audience']) {
  builder.updateField(props.field.id, {
    audience: next?.mode === 'everyone' ? undefined : next,
    ...(next && next.mode !== 'everyone' ? { required: false } : {}),
  })
}
const setMode = (value: string | number) => write({ mode: value as Mode, all: false, ids: [] })
const setAll = (all: boolean) => write({ ...audience.value, all, ids: all ? [] : audience.value.ids ?? [] })
const setIds = (ids: string[]) => write({ ...audience.value, all: false, ids })

const summary = computed(() => {
  if (mode.value === 'everyone') return t('builder.audience.everyoneHint')
  if (audience.value.all) return t(`builder.audience.all.${mode.value}`)
  const n = audience.value.ids?.length ?? 0
  return n ? t('builder.audience.selected', { n }) : t('builder.audience.placeholder')
})
</script>

<template>
  <section class="flex flex-col gap-3">
    <h3 class="text-xs font-medium text-muted uppercase">{{ t('builder.audience.title') }}</h3>
    <UFormField :label="t('builder.audience.label')" :description="summary">
      <USelect :model-value="mode" :items="modes" :icon="ICONS[mode]" class="w-full" @update:model-value="setMode" />
    </UFormField>

    <AppEmpty v-if="noneYet" size="xs" icon="i-lucide-network" :title="t(`builder.audience.none.${mode}`)" :description="t('builder.audience.noneDesc')" :actions="[{ label: t('builder.audience.setUp'), icon: 'i-lucide-settings', color: 'neutral', variant: 'outline', to: SETTINGS[mode], target: '_blank' }]" />
    <template v-else-if="mode !== 'everyone'">
      <USwitch
        :model-value="!!audience.all"
        :label="t(`builder.audience.all.${mode}`)"
        color="neutral"
        @update:model-value="setAll"
      />
      <UFormField v-if="!audience.all" :label="t(`builder.audience.pick.${mode}`)">
        <USelectMenu
          :model-value="audience.ids ?? []"
          :items="items"
          value-key="value"
          multiple
          :loading="loading"
          :placeholder="t('builder.audience.placeholder')"
          :search-input="{ placeholder: t('common.search') }"
          class="w-full"
          @update:model-value="v => setIds(v as string[])"
        />
      </UFormField>
      <UAlert v-if="stale" icon="i-lucide-archive" color="warning" variant="subtle" :description="t('builder.audience.stale', { n: stale }, stale)" :ui="{ description: 'text-xs' }" />
      <UAlert
        icon="i-lucide-lock"
        color="neutral"
        variant="soft"
        :description="t('builder.audience.noRequired')"
        :ui="{ description: 'text-xs' }"
      />
    </template>
  </section>
</template>
