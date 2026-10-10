<!--
  Share → Who can see this form (leftovers L4, owner 2026-10-10): everyone in the workspace and what they may
  do with the form (can edit · can view · responses only · no access), whether they see its responses, and
  the rule that decides it (workspace owner, a role that sees every form, the form's maker, their own level,
  the default for everyone, their role, the folder). Read only, worked out by the server with the same rules
  as everything else; it reloads after the page saves. Filter by level, search by name.
-->
<script setup lang="ts">
import type { AccessReason, FormAccessLevel, FormAccessOverview, FormShareSettings } from '#shared/types/forms'

const props = defineProps<{ formId: string; settings: FormShareSettings }>()
const { t } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()
const { roleName } = useBuiltInNames()

const data = ref<FormAccessOverview | null>(null)
const failed = ref(false)
async function load() {
  failed.value = false
  try {
    data.value = (await api.get<FormAccessOverview>(`/forms/${props.formId}/access`, undefined, { background: !!data.value })).data
  } catch (error) {
    failed.value = true
    handle(error, { silent: !!data.value })
  }
}
// Saving the page replaces its settings: the overview follows
watch(() => props.settings, load, { immediate: true })

type Filter = 'all' | FormAccessLevel
const filter = ref<Filter>('all')
const query = ref('')
const LEVELS: FormAccessLevel[] = ['edit', 'view', 'responses', 'none']
const count = (level: FormAccessLevel) => data.value?.people.filter(person => person.level === level).length ?? 0
const filters = computed(() => [
  { value: 'all' as const, label: t('share.who.all', { n: data.value?.people.length ?? 0 }) },
  ...LEVELS.map(level => ({ value: level, label: `${t(`share.who.level.${level}`)} · ${count(level)}` })),
])
const shown = computed(() => {
  const q = query.value.trim().toLowerCase()
  return (data.value?.people ?? []).filter(person => (filter.value === 'all' || person.level === filter.value) && (!q || person.user.name.toLowerCase().includes(q) || person.user.email.toLowerCase().includes(q)))
})
const LEVEL_COLOR: Record<FormAccessLevel, 'neutral' | 'warning' | 'error'> = { edit: 'neutral', view: 'neutral', responses: 'warning', none: 'error' }
const reasonText = (reason: AccessReason) => t(`share.who.reason.${reason}`, { folder: data.value?.folder?.name ?? '' })
const initials = (name: string) =>
  name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map(word => word[0]!.toUpperCase())
    .join('')
</script>

<template>
  <UCard variant="outline" :ui="{ body: 'p-4 sm:p-5' }">
    <div class="mb-4 flex items-start gap-3">
      <UIcon name="i-lucide-scan-eye" class="mt-0.5 size-5 shrink-0 text-muted" />
      <div class="min-w-0 flex-1">
        <h2 class="text-sm font-semibold text-highlighted">{{ t('share.who.title') }}</h2>
        <p class="text-xs text-muted">{{ t('share.who.desc') }}</p>
      </div>
      <UButton icon="i-lucide-refresh-cw" color="neutral" variant="ghost" size="xs" square :aria-label="t('share.who.refresh')" @click="load" />
    </div>

    <AppEmpty v-if="failed && !data" size="sm" icon="i-lucide-cloud-off" :title="t('share.who.failed')" :actions="[{ label: t('common.retry'), icon: 'i-lucide-refresh-cw', color: 'neutral', variant: 'outline', onClick: load }]" />
    <div v-else-if="!data" class="flex flex-col gap-2"><USkeleton class="h-8 w-full" /><USkeleton v-for="n in 4" :key="n" class="h-12 w-full" /></div>
    <template v-else>
      <p v-if="data.folder?.restricted" class="mb-3 flex items-start gap-1.5 rounded-md bg-elevated/60 px-3 py-2 text-xs text-muted">
        <UIcon name="i-lucide-folder-lock" class="mt-0.5 size-3.5 shrink-0" />{{ t('share.who.folderNote', { folder: data.folder.name }) }}
      </p>
      <div class="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center">
        <div class="-mx-1 flex min-w-0 flex-1 gap-1.5 overflow-x-auto px-1 pb-1 [scrollbar-width:none]">
          <UButton v-for="item in filters" :key="item.value" :label="item.label" size="xs" color="neutral" :variant="filter === item.value ? 'solid' : 'outline'" class="shrink-0" @click="filter = item.value" />
        </div>
        <UInput v-model="query" icon="i-lucide-search" size="sm" :placeholder="t('share.who.search')" class="w-full sm:w-52" />
      </div>
      <ul v-if="shown.length" class="flex max-h-[28rem] flex-col divide-y divide-default overflow-y-auto rounded-md border border-default" :class="failed ? 'opacity-60' : ''">
        <li v-for="person in shown" :key="person.user.id" class="flex flex-wrap items-center gap-x-3 gap-y-1 px-3 py-2">
          <UAvatar :src="person.user.photo ?? undefined" :text="initials(person.user.name)" size="sm" />
          <div class="min-w-0 flex-1">
            <p class="truncate text-sm text-highlighted">{{ person.user.name }} <span class="text-xs text-muted">· {{ roleName(person.role.id, person.role.name) }}</span></p>
            <p class="truncate text-xs text-muted">{{ reasonText(person.reason) }}</p>
          </div>
          <UTooltip v-if="person.responses" :text="t('share.who.seesResponses')">
            <span class="flex shrink-0 text-muted"><UIcon name="i-lucide-inbox" class="size-4" /><span class="sr-only">{{ t('share.who.seesResponses') }}</span></span>
          </UTooltip>
          <UBadge :label="t(`share.who.level.${person.level}`)" :color="LEVEL_COLOR[person.level]" variant="subtle" size="sm" />
        </li>
      </ul>
      <AppEmpty v-else size="xs" icon="i-lucide-search-x" :title="t('share.who.none')" :actions="[{ label: t('share.who.clear'), icon: 'i-lucide-x', color: 'neutral', variant: 'outline', onClick: () => ((filter = 'all'), (query = '')) }]" />
      <p class="mt-2 text-xs text-muted">{{ t('share.who.note') }}</p>
    </template>
  </UCard>
</template>
