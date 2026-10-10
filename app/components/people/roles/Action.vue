<!--
  One action in the role editor (F22 R2): its name and what it covers, then how far it reaches. Actions
  with a scope offer None · Own · Shared · All (only the ones that apply) as a segmented choice; on / off
  actions a switch. Read-only for Owner and for people who can't manage roles.
-->
<script setup lang="ts">
import type { Permission, Scope } from '#shared/utils/auth/permissions'
import { scopesOf } from '#shared/utils/auth/permissions'

const props = defineProps<{ permission: Permission; scope: Scope | null; readonly?: boolean }>()
const emit = defineEmits<{ change: [scope: Scope | null] }>()
const { t, te } = useI18n()

const key = computed(() => props.permission.replace('.', '_'))
const action = computed(() => props.permission.split('.')[1]!)
const label = computed(() => (te(`access.label.${key.value}`) ? t(`access.label.${key.value}`) : t(`access.action.${action.value}`)))
const scopes = computed(() => scopesOf(props.permission))
const choices = computed(() => [null, ...(scopes.value ?? [])] as (Scope | null)[])
</script>

<template>
  <li class="flex flex-col gap-2 px-3 py-2.5 sm:flex-row sm:items-center sm:gap-4" :class="scope ? '' : 'opacity-80'">
    <div class="flex min-w-0 flex-1 flex-col">
      <span class="text-sm font-medium" :class="scope ? 'text-highlighted' : 'text-muted'">{{ label }}</span>
      <span class="text-xs text-muted">{{ t(`access.perm.${key}`) }}</span>
    </div>
    <UFieldGroup v-if="scopes" size="xs" class="shrink-0 self-start sm:self-center" role="radiogroup" :aria-label="label">
      <UTooltip v-for="choice in choices" :key="choice ?? 'none'" :text="t(`access.scopeHint.${choice ?? 'none'}`)">
        <UButton
          :label="t(`access.scope.${choice ?? 'none'}`)"
          color="neutral"
          :variant="scope === choice ? 'solid' : 'outline'"
          :disabled="readonly"
          role="radio"
          :aria-checked="scope === choice"
          class="min-w-14 justify-center"
          @click="emit('change', choice)"
        />
      </UTooltip>
    </UFieldGroup>
    <USwitch v-else :model-value="!!scope" :disabled="readonly" color="neutral" class="shrink-0 self-start sm:self-center" :aria-label="label" @update:model-value="value => emit('change', value ? 'all' : null)" />
  </li>
</template>
