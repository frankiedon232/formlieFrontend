<!-- An organisation entry's state as a small badge: in use (people in it), empty, or archived. -->
<script setup lang="ts">
import type { OrgItem } from '#shared/types/org'

const props = defineProps<{ item: Pick<OrgItem, 'status' | 'members'> }>()
const { t } = useI18n()
const state = computed(() => (props.item.status === 'archived' ? 'archived' : props.item.members.length ? 'in_use' : 'empty'))
const DOT = { in_use: 'bg-green-500', empty: 'bg-amber-500', archived: 'bg-(--ui-border-accented)' } as const
const LABEL = { in_use: 'settings.org.inUse', empty: 'settings.org.empty', archived: 'settings.org.archived' } as const
</script>

<template>
  <UBadge color="neutral" variant="outline" size="sm" class="gap-1.5 rounded-md">
    <span class="size-1.5 rounded-full" :class="DOT[state]" />{{ t(LABEL[state]) }}
  </UBadge>
</template>
