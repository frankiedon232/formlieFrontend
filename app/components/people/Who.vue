<!-- People table, name cell (F16): avatar (green dot = online now), name and email; the name is a button so the row opens by keyboard too. -->
<script setup lang="ts">
import type { PersonRow } from '#shared/types/people'

defineProps<{ person: PersonRow }>()
const emit = defineEmits<{ open: [] }>()
const { t } = useI18n()
</script>

<template>
  <div class="flex min-w-0 items-center gap-2.5">
    <UChip :show="!!person.last_visit?.online" color="success" position="bottom-right" inset><UAvatar :src="person.photo ?? undefined" :alt="person.name" size="sm" /></UChip>
    <div class="flex min-w-0 flex-col">
      <button type="button" class="flex min-w-0 items-center gap-1.5 text-start font-medium text-highlighted hover:underline focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)" @click="emit('open')">
        <span class="truncate">{{ person.name }}</span>
        <UTooltip v-if="person.privileged && !person.two_step && person.status === 'active'" :text="t('people.flagTwoStep')"><UIcon name="i-lucide-flag" class="size-3.5 shrink-0 text-error" :aria-label="t('people.flagTwoStep')" /></UTooltip>
      </button>
      <span v-if="person.name !== person.email" class="truncate text-xs text-muted" dir="ltr">{{ person.email }}</span>
    </div>
  </div>
</template>
