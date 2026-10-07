<!--
  An organisation entry in a panel from the side (F14 M2, detail panel model): its name, state and ⋯
  (merge, archive / restore, delete), a one-click bar (Edit, Add people); fact tiles; the people in it
  as two-column tiles; the forms with fields restricted to it (each opens its builder). Previous (K) ·
  Next (J).
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { OrgItem, OrgKind, OrgUsage } from '#shared/types/org'

const props = defineProps<{ kind: OrgKind; id: string | null; ids: string[]; busy: boolean; actions: (item: OrgItem) => DropdownMenuItem[][] }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ go: [id: string]; edit: [item: OrgItem] }>()
const { t } = useI18n()
const api = useApi()
const { number, relative, date } = useFormat()

const item = ref<OrgItem | null>(null)
const usage = ref<OrgUsage[] | null>(null)
const failed = ref(false)
async function load(id: string) {
  failed.value = false
  try {
    const [one, used] = await Promise.all([api.get<OrgItem>(`/org/${props.kind}/${id}`), api.get<OrgUsage[]>(`/org/${props.kind}/${id}/usage`)])
    if (props.id !== id) return
    item.value = one.data
    usage.value = used.data
  } catch {
    failed.value = true
  }
}
watch(() => [props.id, open.value] as const, ([id, isOpen]) => id && isOpen && void load(id), { immediate: true })
defineExpose({ reload: () => props.id && load(props.id) })

const index = computed(() => (props.id ? props.ids.indexOf(props.id) : -1))
const prev = computed(() => (index.value > 0 ? props.ids[index.value - 1] : null))
const next = computed(() => (index.value >= 0 && index.value < props.ids.length - 1 ? props.ids[index.value + 1] : null))
defineShortcuts({
  j: { usingInput: false, handler: () => open.value && next.value && emit('go', next.value) },
  k: { usingInput: false, handler: () => open.value && prev.value && emit('go', prev.value) },
})

const tiles = computed(() => {
  const i = item.value
  if (!i) return []
  return [
    { key: 'people', icon: 'i-lucide-users-round', label: t('settings.org.col.people'), value: number(i.members.length) },
    { key: 'forms', icon: 'i-lucide-file-text', label: t('settings.org.col.forms'), value: number(i.forms_count) },
    { key: 'code', icon: 'i-lucide-hash', label: t('settings.org.col.code'), value: i.code ?? '–' },
    { key: 'created', icon: 'i-lucide-calendar-plus', label: t('settings.org.col.created'), value: date(i.created_at) },
    { key: 'updated', icon: 'i-lucide-clock', label: t('settings.org.col.updated'), value: relative(i.updated_at) },
    { key: 'archived', icon: 'i-lucide-archive', label: t('settings.org.archived'), value: i.archived_at ? date(i.archived_at) : '–' },
  ]
})
const initials = (name: string) => name.split(/\s+/).map(part => part[0]).join('').slice(0, 2).toUpperCase()
</script>

<template>
  <USlideover
    v-model:open="open"
    :content="{ onOpenAutoFocus: (event: Event) => event.preventDefault() }"
    :title="item?.name || t(`settings.org.kind.${kind}.many`)"
    :ui="{ content: 'w-full sm:max-w-2xl', header: 'border-b-0 pb-2', body: 'flex flex-col gap-6 pb-40', footer: 'pointer-events-none absolute inset-x-0 bottom-0 justify-center border-t-0 bg-gradient-to-t from-(--ui-bg) via-(--ui-bg)/85 to-transparent pt-10 pb-4' }"
  >
    <template #header>
      <div v-if="!item" class="flex w-full items-center gap-3.5">
        <USkeleton class="size-14 rounded-2xl" />
        <div class="flex flex-1 flex-col gap-2"><USkeleton class="h-5 w-48" /><USkeleton class="h-4 w-32" /></div>
      </div>
      <div v-else class="flex w-full flex-col gap-4">
        <div class="flex items-start gap-3.5">
          <span class="flex size-14 shrink-0 items-center justify-center rounded-2xl bg-inverted text-inverted"><UIcon :name="SETTINGS_ORG_ICONS[kind]" class="size-6" /></span>
          <div class="flex min-w-0 flex-1 flex-col gap-1">
            <h2 class="truncate text-lg leading-tight font-semibold text-highlighted">{{ item.name }}</h2>
            <p class="line-clamp-2 text-sm text-muted">{{ item.description || t('settings.org.noDescription') }}</p>
            <div class="mt-1 flex flex-wrap items-center gap-1.5"><SettingsOrgState :item="item" /><UBadge v-if="item.code" :label="item.code" color="neutral" variant="soft" size="sm" class="rounded-md font-mono" /></div>
          </div>
          <div class="flex shrink-0 items-center gap-1">
            <UDropdownMenu :items="actions(item)" :content="{ align: 'end' }">
              <UButton icon="i-lucide-ellipsis" color="neutral" variant="ghost" size="sm" square :aria-label="t('dataView.actions')" />
            </UDropdownMenu>
            <UButton icon="i-lucide-x" color="neutral" variant="soft" size="sm" square class="rounded-full" :aria-label="t('common.close')" @click="open = false" />
          </div>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <UButton :label="t('settings.org.addPeople')" icon="i-lucide-user-plus" color="neutral" size="sm" :disabled="busy" @click="emit('edit', item)" />
          <UButton :label="t('apiService.actions.edit')" icon="i-lucide-pencil" color="neutral" variant="outline" size="sm" :disabled="busy" @click="emit('edit', item)" />
        </div>
      </div>
    </template>

    <template #body>
      <AppEmpty v-if="failed && !item" icon="i-lucide-cloud-alert" :title="t('dataView.errorTitle')" :actions="[{ label: t('common.retry'), color: 'neutral', variant: 'outline', onClick: () => id && load(id) }]" />
      <div v-else-if="!item" class="flex flex-col gap-4"><div class="grid grid-cols-2 gap-2 sm:grid-cols-3"><USkeleton v-for="n in 6" :key="n" class="h-14 rounded-lg" /></div><USkeleton class="h-40 w-full" /></div>
      <template v-else>
        <UAlert v-if="item.status === 'archived'" icon="i-lucide-archive" color="neutral" variant="subtle" :title="t('settings.org.archivedTitle')" :description="t('settings.org.archivedDesc')" />
        <div class="grid grid-cols-2 gap-2 transition-opacity sm:grid-cols-3" :class="busy ? 'opacity-60' : ''">
          <div v-for="tile in tiles" :key="tile.key" class="flex min-w-0 items-center gap-2.5 rounded-lg border border-default p-2.5">
            <span class="flex size-8 shrink-0 items-center justify-center rounded-md bg-elevated"><UIcon :name="tile.icon" class="size-4 text-muted" /></span>
            <div class="flex min-w-0 flex-col">
              <span class="truncate text-[11px] text-muted">{{ tile.label }}</span>
              <span class="truncate text-sm font-semibold text-highlighted tabular-nums">{{ tile.value }}</span>
            </div>
          </div>
        </div>

        <section class="flex flex-col gap-3">
          <h3 class="text-sm font-semibold text-highlighted">{{ t('settings.org.col.people') }} · {{ number(item.members.length) }}</h3>
          <AppEmpty v-if="!item.members.length" size="xs" icon="i-lucide-users-round" :title="t('settings.org.nobody')" :actions="[{ label: t('settings.org.addPeople'), icon: 'i-lucide-user-plus', color: 'neutral', onClick: () => emit('edit', item!) }]" />
          <div v-else class="grid gap-2 sm:grid-cols-2">
            <div v-for="person in item.members" :key="person.id" class="flex h-full min-w-0 items-center gap-3 rounded-lg border border-default p-2.5">
              <span class="flex size-8 shrink-0 items-center justify-center rounded-full bg-elevated text-xs font-semibold text-highlighted">{{ initials(person.name) }}</span>
              <div class="flex min-w-0 flex-col">
                <span class="truncate text-sm font-medium text-highlighted">{{ person.name }}</span>
                <span class="truncate text-xs text-muted" dir="ltr">{{ person.email }}</span>
              </div>
            </div>
          </div>
        </section>

        <section v-if="kind === 'departments' || kind === 'job_titles'" class="flex flex-col gap-3">
          <h3 class="text-sm font-semibold text-highlighted">{{ t('settings.org.usedBy') }}</h3>
          <div v-if="!usage" class="grid gap-2 sm:grid-cols-2"><USkeleton v-for="n in 2" :key="n" class="h-16 rounded-lg" /></div>
          <p v-else-if="!usage.length" class="text-sm text-muted">{{ t('settings.org.notUsed') }}</p>
          <div v-else class="grid gap-2 sm:grid-cols-2">
            <NuxtLink v-for="entry in usage" :key="entry.form.id" :to="`/forms/${entry.form.id}`" class="flex h-full flex-col gap-1.5 rounded-lg border border-default p-3 transition-colors hover:border-accented hover:bg-elevated/40 focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)">
              <div class="flex items-center justify-between gap-2">
                <span class="truncate text-sm font-semibold text-highlighted">{{ entry.form.name }}</span>
                <DataStatusBadge :status="entry.form.status" />
              </div>
              <span class="flex min-w-0 items-center gap-1.5 text-xs text-muted"><UIcon name="i-lucide-lock" class="size-3.5 shrink-0" /><span class="truncate">{{ entry.fields.join(', ') }}</span></span>
            </NuxtLink>
          </div>
        </section>
      </template>
    </template>

    <template #footer>
      <nav class="pointer-events-auto flex items-center gap-1 rounded-full border border-default bg-default/95 p-1 shadow-lg backdrop-blur" :aria-label="t('apiService.navigate')">
        <UButton :label="t('responses.detail.prevShort')" icon="i-lucide-arrow-up" color="neutral" variant="ghost" size="sm" class="rounded-full" :disabled="!prev" @click="prev && emit('go', prev)">
          <template #trailing><UKbd value="K" size="sm" class="hidden sm:inline-flex" /></template>
        </UButton>
        <span v-if="index >= 0" class="px-2 text-xs text-muted tabular-nums">{{ t('responses.detail.position', { n: index + 1, total: ids.length }) }}</span>
        <UButton :label="t('responses.detail.nextShort')" icon="i-lucide-arrow-down" color="neutral" variant="solid" size="sm" class="rounded-full" :disabled="!next" @click="next && emit('go', next)">
          <template #trailing><UKbd value="J" size="sm" class="hidden sm:inline-flex" /></template>
        </UButton>
      </nav>
    </template>
  </USlideover>
</template>
