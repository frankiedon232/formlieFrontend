<!--
  What a role may do (F22): one row per area of the platform with its actions as switches. Ticking an
  action also ticks what it needs (editing needs viewing); unticking one also unticks what relies on it.
  Read-only for Owner (everything) and for people who can't manage roles.
-->
<script setup lang="ts">
import type { Permission } from '#shared/utils/auth/permissions'
import { PERMISSION_AREAS, PERMISSION_NEEDS, withNeeds } from '#shared/utils/auth/permissions'

const model = defineModel<string[]>({ required: true })
defineProps<{ readonly?: boolean }>()
const { t } = useI18n()

const has = (permission: string) => model.value.includes(permission)
/** Everything that (directly or not) relies on this permission. */
function dependents(permission: Permission): Permission[] {
  const out = new Set<Permission>()
  for (let changed = true; changed; ) {
    changed = false
    for (const [item, needs] of Object.entries(PERMISSION_NEEDS) as [Permission, Permission[]][])
      if (!out.has(item) && needs.some(need => need === permission || out.has(need))) {
        out.add(item)
        changed = true
      }
  }
  return [...out]
}
function toggle(permission: Permission, on: boolean) {
  if (on) model.value = withNeeds([...model.value, permission])
  else {
    const gone = new Set([permission, ...dependents(permission)])
    model.value = model.value.filter(item => !gone.has(item as Permission))
  }
}
const areaOn = (key: string) => PERMISSION_AREAS.find(area => area.key === key)!.actions.filter(action => has(`${key}.${action}`)).length
function setArea(key: string, on: boolean) {
  const area = PERMISSION_AREAS.find(item => item.key === key)!
  if (on) model.value = withNeeds([...model.value, ...area.actions.map(action => `${key}.${action}`)])
  else for (const action of area.actions) toggle(`${key}.${action}` as Permission, false)
}
</script>

<template>
  <ul class="flex flex-col divide-y divide-default rounded-lg border border-default">
    <li v-for="area in PERMISSION_AREAS" :key="area.key" class="flex flex-col gap-3 p-3 sm:flex-row sm:items-start sm:gap-6">
      <div class="flex min-w-0 items-start gap-3 sm:w-64 sm:shrink-0">
        <UCheckbox :model-value="areaOn(area.key) === area.actions.length ? true : areaOn(area.key) ? 'indeterminate' : false" :disabled="readonly" color="neutral" :aria-label="t(`access.area.${area.key}`)" @update:model-value="value => setArea(area.key, value === true)" />
        <div class="flex min-w-0 flex-col">
          <span class="text-sm font-medium text-highlighted">{{ t(`access.area.${area.key}`) }}</span>
          <span class="text-xs text-muted">{{ t(`access.areaHint.${area.key}`) }}</span>
        </div>
      </div>
      <div class="flex min-w-0 flex-1 flex-wrap gap-2">
        <UTooltip v-for="action in area.actions" :key="action" :text="t(`access.perm.${area.key}_${action}`)">
          <label class="flex cursor-pointer items-center gap-2 rounded-md border px-2.5 py-1.5 text-xs transition" :class="[has(`${area.key}.${action}`) ? 'border-inverted bg-elevated text-highlighted' : 'border-default text-muted', readonly ? 'cursor-default opacity-80' : 'hover:border-accented']">
            <USwitch :model-value="has(`${area.key}.${action}`)" :disabled="readonly" size="xs" color="neutral" @update:model-value="value => toggle(`${area.key}.${action}` as Permission, !!value)" />
            {{ t(`access.action.${action}`) }}
          </label>
        </UTooltip>
      </div>
    </li>
  </ul>
</template>
