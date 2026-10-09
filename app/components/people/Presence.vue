<!--
  Online or offline (F16, owner 2026-10-09, like Recently active): a dot and Online / Offline, then when they
  were last active and how long that visit lasted. Invitations show when they were sent; never signed in
  shows Never. `inline` = one line (card pill).
-->
<script setup lang="ts">
import type { PersonRow } from '#shared/types/people'

const props = defineProps<{ person: PersonRow; inline?: boolean }>()
const { t } = useI18n()
const { relative, dateTime, span } = useFormat()

const visit = computed(() => props.person.last_visit)
const online = computed(() => !!visit.value?.online)
const length = computed(() => {
  if (!visit.value) return ''
  const ms = Date.parse(visit.value.ended_at) - Date.parse(visit.value.started_at)
  return ms < 60_000 ? `< ${span(60_000)}` : span(ms)
})
const when = computed(() => (props.person.last_active_at ? relative(props.person.last_active_at) : ''))
const title = computed(() => (props.person.last_active_at ? `${dateTime(props.person.last_active_at)}${length.value ? ` · ${t('people.team.duration')} ${length.value}` : ''}` : ''))
</script>

<template>
  <UTooltip v-if="person.invite" :text="t('people.invite.by', { name: person.invite.invited_by })">
    <span class="whitespace-nowrap text-muted">{{ t('people.invite.sentAgo', { when: relative(person.invite.sent_at) }) }}</span>
  </UTooltip>
  <span v-else-if="!person.last_active_at" class="whitespace-nowrap text-muted">{{ t('people.never') }}</span>
  <UTooltip v-else :text="title">
    <span class="flex min-w-0 whitespace-nowrap" :class="inline ? 'items-center gap-1.5' : 'flex-col'">
      <span class="flex items-center gap-1.5" :class="online ? 'font-medium text-success' : 'text-default'">
        <span class="size-2 shrink-0 rounded-full" :class="online ? 'bg-(--ui-success)' : 'bg-(--ui-border-accented)'" aria-hidden="true" />
        {{ online ? t('people.team.online') : t('people.team.offline') }}
      </span>
      <span class="flex items-center gap-1 text-xs text-muted tabular-nums" :class="inline ? '' : 'ps-3.5'">
        <template v-if="inline">·</template>
        <template v-if="!online">{{ when }} · </template>
        <UIcon name="i-lucide-timer" class="size-3" aria-hidden="true" /><span class="sr-only">{{ t('people.team.duration') }}</span>{{ length }}
      </span>
    </span>
  </UTooltip>
</template>
