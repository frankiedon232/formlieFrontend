<!--
  What a role may do (F22 R2, owner 2026-10-10: granular, with "owned" limits, better grouping). Areas on
  the start side (a sliding row of chips on phones) with how many of their actions the role holds; the
  chosen area's actions in groups, each with its reach (None · Own · Shared · All) or a switch. Search finds
  an action in any area. "Set the area" gives every action of the area the same reach in one go. Changing
  an action keeps the role consistent (what it needs is added, what needs it follows). Read-only for Owner
  and for people who can't manage roles.
-->
<script setup lang="ts">
import type { Grants, Permission, PermissionArea, Scope } from '#shared/utils/auth/permissions'
import { PERMISSION_AREAS, SCOPES, scopesOf, setGrant } from '#shared/utils/auth/permissions'

const model = defineModel<Grants>({ required: true })
defineProps<{ readonly?: boolean }>()
const { t, te } = useI18n()

const ICONS: Record<PermissionArea, string> = {
  forms: 'i-lucide-file-text',
  folders: 'i-lucide-folder',
  responses: 'i-lucide-inbox',
  templates: 'i-lucide-layout-template',
  lists: 'i-lucide-list',
  themes: 'i-lucide-palette',
  pages: 'i-lucide-panels-top-left',
  fields: 'i-lucide-bookmark',
  analytics: 'i-lucide-chart-line',
  data: 'i-lucide-database',
  api: 'i-lucide-code',
  people: 'i-lucide-users',
  roles: 'i-lucide-shield',
  settings: 'i-lucide-settings',
  audit: 'i-lucide-scroll-text',
  ai: 'i-lucide-sparkles',
}
const permissionsIn = (area: (typeof PERMISSION_AREAS)[number]) => area.groups.flatMap(group => group.actions.map(action => `${area.key}.${action.key}` as Permission))
const held = (area: (typeof PERMISSION_AREAS)[number]) => permissionsIn(area).filter(item => model.value[item]).length

const current = ref<PermissionArea>('forms')
const query = ref('')
const labelOf = (permission: Permission) => {
  const key = permission.replace('.', '_')
  return te(`access.label.${key}`) ? t(`access.label.${key}`) : t(`access.action.${permission.split('.')[1]}`)
}
/** While searching: every matching action, grouped by area; otherwise the chosen area's groups. */
const shown = computed(() => {
  const q = query.value.trim().toLowerCase()
  const areas = q ? PERMISSION_AREAS : PERMISSION_AREAS.filter(area => area.key === current.value)
  return areas
    .map(area => ({
      area,
      groups: area.groups
        .map(group => ({ key: `${area.key}_${group.key}`, items: group.actions.map(action => `${area.key}.${action.key}` as Permission).filter(item => !q || `${labelOf(item)} ${t(`access.perm.${item.replace('.', '_')}`)} ${t(`access.area.${area.key}`)}`.toLowerCase().includes(q)) }))
        .filter(group => group.items.length),
    }))
    .filter(entry => entry.groups.length)
})

const change = (permission: Permission, scope: Scope | null) => (model.value = setGrant(model.value, permission, scope))
/** The same reach for the whole area (each action as far as it allows). */
function setArea(area: (typeof PERMISSION_AREAS)[number], scope: Scope | null) {
  let next = model.value
  for (const item of permissionsIn(area)) next = setGrant(next, item, scope && (scopesOf(item) ? scope : 'all'))
  model.value = next
}
const areaChoices = (area: (typeof PERMISSION_AREAS)[number]) => {
  const scoped = new Set(permissionsIn(area).flatMap(item => scopesOf(item) ?? []))
  return [null, ...SCOPES.filter(scope => scoped.has(scope) || (scope === 'all' && !scoped.size))]
}
</script>

<template>
  <div class="flex flex-col gap-4 lg:flex-row lg:items-start">
    <!-- Areas: a column on wide screens, a sliding row of chips on phones -->
    <nav class="-mx-1 flex shrink-0 gap-1 overflow-x-auto px-1 pb-1 lg:sticky lg:top-0 lg:mx-0 lg:w-60 lg:flex-col lg:overflow-visible lg:px-0" :aria-label="t('access.what')">
      <UButton
        v-for="area in PERMISSION_AREAS"
        :key="area.key"
        :icon="ICONS[area.key]"
        :label="t(`access.area.${area.key}`)"
        color="neutral"
        :variant="current === area.key && !query ? 'soft' : 'ghost'"
        class="shrink-0 justify-start lg:w-full"
        :aria-current="current === area.key && !query ? 'true' : undefined"
        @click="((current = area.key), (query = ''))"
      >
        <template #trailing>
          <span class="ms-auto ps-2 text-xs tabular-nums" :class="held(area) ? 'text-highlighted' : 'text-dimmed'">{{ held(area) }}/{{ permissionsIn(area).length }}</span>
        </template>
      </UButton>
    </nav>

    <div class="flex min-w-0 flex-1 flex-col gap-4">
      <UInput v-model="query" icon="i-lucide-search" :placeholder="t('access.searchActions')" class="w-full" :aria-label="t('access.searchActions')">
        <template v-if="query" #trailing><UButton icon="i-lucide-x" color="neutral" variant="link" size="xs" :aria-label="t('common.clear')" @click="query = ''" /></template>
      </UInput>
      <AppEmpty v-if="!shown.length" size="sm" icon="i-lucide-search-x" :title="t('access.noActions')" :actions="[{ label: t('common.clear'), color: 'neutral', variant: 'outline', onClick: () => (query = '') }]" />
      <section v-for="entry in shown" :key="entry.area.key" class="flex flex-col gap-3">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div class="flex min-w-0 items-center gap-2">
            <UIcon :name="ICONS[entry.area.key]" class="size-4 text-muted" />
            <div class="flex min-w-0 flex-col">
              <h3 class="text-sm font-semibold text-highlighted">{{ t(`access.area.${entry.area.key}`) }}</h3>
              <p class="text-xs text-muted">{{ t(`access.areaHint.${entry.area.key}`) }}</p>
            </div>
          </div>
          <div v-if="!readonly && !query" class="flex items-center gap-2">
            <span class="text-xs text-muted">{{ t('access.setArea') }}</span>
            <UFieldGroup size="xs">
              <UButton v-for="choice in areaChoices(entry.area)" :key="choice ?? 'none'" :label="t(`access.scope.${choice ?? 'none'}`)" color="neutral" variant="outline" @click="setArea(entry.area, choice)" />
            </UFieldGroup>
          </div>
        </div>
        <div v-for="group in entry.groups" :key="group.key" class="flex flex-col gap-1.5">
          <h4 v-if="entry.area.groups.length > 1" class="text-xs font-medium text-muted uppercase">{{ t(`access.group.${group.key}`) }}</h4>
          <ul class="flex flex-col divide-y divide-default rounded-lg border border-default">
            <PeopleRolesAction v-for="item in group.items" :key="item" :permission="item" :scope="model[item] ?? null" :readonly="readonly" @change="scope => change(item, scope)" />
          </ul>
        </div>
      </section>
    </div>
  </div>
</template>
