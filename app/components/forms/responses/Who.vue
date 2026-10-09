<!--
  Respondent cell (F11): initials avatar, name and email, or the response's first answers when the
  form asks for neither (only what the form collected, owner 2026-10-09), a flag for a possible duplicate. The name is a button, so the row opens by keyboard too.
-->
<script setup lang="ts">
import type { ResponseRow } from '#shared/types/responses'

const props = defineProps<{ row: ResponseRow }>()
const emit = defineEmits<{ open: [] }>()
const { t } = useI18n()
const who = computed(() => props.row.respondent.title || `#${props.row.number}`)
const sub = computed(() => (props.row.respondent.name ? props.row.respondent.email : null))
</script>

<template>
  <div class="flex min-w-0 items-center gap-2.5">
    <UAvatar :alt="who" size="sm" :icon="row.respondent.kind === 'anonymous' ? 'i-lucide-user-round' : undefined" />
    <div class="flex min-w-0 flex-col">
      <button type="button" class="flex min-w-0 items-center gap-1.5 text-start font-medium text-highlighted hover:underline focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)" @click="emit('open')">
        <span class="truncate">{{ who }}</span>
        <UTooltip v-if="row.possible_duplicate" :text="t('responses.list.possibleDuplicate')">
          <UIcon name="i-lucide-copy" class="size-3.5 shrink-0 text-warning" :aria-label="t('responses.list.possibleDuplicate')" />
        </UTooltip>
        <UIcon v-if="row.respondent.kind === 'invite' || row.respondent.kind === 'member'" name="i-lucide-badge-check" class="size-3.5 shrink-0 text-muted" :aria-label="t(`responses.known.${row.respondent.kind}`)" />
      </button>
      <span v-if="sub" class="truncate text-xs text-muted" dir="ltr">{{ sub }}</span>
    </div>
  </div>
</template>
