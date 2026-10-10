<!--
  Roles, grid card (locked card format): pill with when it changed, kind and ⋯ on top; name (crown for
  Owner) and description; people and areas it opens; how much of the platform it opens (black bar);
  who holds it at the bottom. The whole card opens the role.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { RoleRow } from '#shared/types/people'
import { ALL_GRANTS, areasOf } from '#shared/utils/auth/permissions'

const props = defineProps<{ role: RoleRow; reach: number; actions: DropdownMenuItem[][]; busy?: boolean }>()
const { t } = useI18n()
const { roleName, roleDescription } = useBuiltInNames()
const { relative, number, percent } = useFormat()
const areas = computed(() => areasOf(props.role.id === 'owner' ? ALL_GRANTS : props.role.grants))
</script>

<template>
  <div class="flex h-full flex-col gap-3 rounded-xl border border-default bg-default p-4 transition hover:border-accented hover:shadow-sm" :class="busy ? 'pointer-events-none opacity-60' : ''">
    <div class="flex items-center justify-between gap-2">
      <span class="flex min-w-0 items-center gap-1.5 rounded-full border border-default px-2 py-0.5 text-[11px] text-muted"><UIcon name="i-lucide-clock" class="size-3" />{{ relative(role.updated_at) }}</span>
      <div class="flex items-center gap-1">
        <UBadge :label="role.built_in ? t('access.builtIn') : t('access.own')" color="neutral" :variant="role.built_in ? 'soft' : 'outline'" size="sm" />
        <UDropdownMenu :items="actions" :content="{ align: 'end' }">
          <UButton icon="i-lucide-ellipsis" color="neutral" variant="outline" size="xs" :loading="busy" :aria-label="t('dataView.actions')" @click.stop />
        </UDropdownMenu>
      </div>
    </div>
    <div class="flex min-w-0 flex-col gap-0.5">
      <span class="flex items-center gap-1.5 truncate font-semibold text-highlighted"><UIcon :name="role.id === 'owner' ? 'i-lucide-crown' : 'i-lucide-shield'" class="size-3.5 shrink-0 text-muted" />{{ roleName(role.id, role.name) }}</span>
      <span class="line-clamp-1 text-xs text-muted">{{ roleDescription(role.id, role.description) || t('optionSets.noDescription') }}</span>
    </div>
    <dl class="grid grid-cols-2 gap-2 text-xs">
      <div class="flex min-w-0 flex-col"><dt class="text-muted">{{ t('access.col.people') }}</dt><dd class="font-medium text-highlighted tabular-nums">{{ t('access.peopleCount', { n: number(role.people_count) }, role.people_count) }}</dd></div>
      <div class="flex min-w-0 flex-col"><dt class="text-muted">{{ t('access.col.areas') }}</dt><dd class="font-medium text-highlighted tabular-nums">{{ t('access.areasCount', { n: areas }, areas) }}</dd></div>
    </dl>
    <div class="flex flex-col gap-1.5 border-t border-default pt-3">
      <div class="flex items-center justify-between text-xs"><span class="text-muted">{{ t('access.col.reach') }}</span><span class="font-medium text-highlighted tabular-nums">{{ percent(reach) }}</span></div>
      <UProgress :model-value="reach * 100" color="neutral" size="xs" />
    </div>
    <div class="mt-auto flex items-center gap-2 text-[11px] text-muted">
      <UAvatarGroup v-if="role.people.length" size="2xs" :max="4"><UAvatar v-for="person in role.people" :key="person.id" :src="person.photo ?? undefined" :alt="person.name" /></UAvatarGroup>
      <span v-else>{{ t('access.nobody') }}</span>
    </div>
  </div>
</template>
