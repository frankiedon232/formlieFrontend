<!--
  People, grid card (locked card format, rule 21): pill with when they were last active, status and ⋯
  on top; name (red flag = an owner or admin without two-step sign-in) and email; department, job title,
  role and manager; a profile line (how complete the profile is, black bar); avatar, joined date and
  counts at the bottom. The whole card opens the person.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { PersonRow } from '#shared/types/people'

const props = defineProps<{ person: PersonRow; actions: DropdownMenuItem[][]; busy?: boolean }>()
const { t } = useI18n()
const { relative, date, number, percent } = useFormat()
const flagged = computed(() => props.person.role !== 'member' && !props.person.two_step && props.person.status === 'active')
const profile = computed(() => profileShare(props.person))
const names = (items: { name: string }[]) => items.map(item => item.name).join(', ') || '–'
</script>

<template>
  <div class="flex h-full flex-col gap-3 rounded-xl border border-default bg-default p-4 transition hover:border-accented hover:shadow-sm" :class="busy ? 'pointer-events-none opacity-60' : ''">
    <div class="flex items-center justify-between gap-2">
      <span class="flex min-w-0 items-center gap-1.5 rounded-full border border-default px-2 py-0.5 text-[11px] text-muted"><UIcon name="i-lucide-clock" class="size-3" />{{ person.invite ? t('people.invite.sentAgo', { when: relative(person.invite.sent_at) }) : person.last_active_at ? relative(person.last_active_at) : t('people.never') }}</span>
      <div class="flex items-center gap-1">
        <PeopleStatus :person="person" />
        <UDropdownMenu :items="actions" :content="{ align: 'end' }">
          <UButton icon="i-lucide-ellipsis" color="neutral" variant="outline" size="xs" :loading="busy" :aria-label="t('dataView.actions')" @click.stop />
        </UDropdownMenu>
      </div>
    </div>
    <div class="flex min-w-0 flex-col gap-0.5">
      <span class="flex min-w-0 items-center gap-1.5">
        <UTooltip v-if="flagged" :text="t('people.flagTwoStep')"><UIcon name="i-lucide-flag" class="size-3.5 shrink-0 text-error" :aria-label="t('people.flagTwoStep')" /></UTooltip>
        <span class="truncate font-semibold text-highlighted">{{ person.name }}</span>
      </span>
      <span class="truncate text-xs text-muted" dir="ltr">{{ person.name !== person.email ? person.email : t('people.invite.notJoined') }}</span>
    </div>
    <dl class="grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
      <div class="flex min-w-0 flex-col"><dt class="text-muted">{{ t('people.col.department') }}</dt><dd class="truncate font-medium text-highlighted">{{ names(person.departments) }}</dd></div>
      <div class="flex min-w-0 flex-col"><dt class="text-muted">{{ t('people.col.jobTitle') }}</dt><dd class="truncate font-medium text-highlighted">{{ names(person.job_titles) }}</dd></div>
      <div class="flex min-w-0 flex-col"><dt class="text-muted">{{ t('people.col.role') }}</dt><dd class="truncate font-medium text-highlighted">{{ t(`people.role.${person.role}`) }}</dd></div>
      <div class="flex min-w-0 flex-col"><dt class="text-muted">{{ t('people.col.manager') }}</dt><dd class="truncate font-medium text-highlighted">{{ person.manager?.name ?? '–' }}</dd></div>
    </dl>
    <div class="flex flex-col gap-1.5 border-t border-default pt-3">
      <div class="flex items-center justify-between text-xs"><span class="text-muted">{{ t('people.profile') }}</span><span class="font-medium text-highlighted tabular-nums">{{ percent(profile) }}</span></div>
      <UProgress :model-value="profile * 100" color="neutral" size="xs" />
    </div>
    <div class="mt-auto flex items-center justify-between gap-2 text-[11px] text-muted">
      <div class="flex min-w-0 items-center gap-2">
        <UAvatar :alt="person.name" size="xs" />
        <span class="truncate">{{ person.invite ? t('people.invite.by', { name: person.invite.invited_by }) : t('people.joinedOn', { date: date(person.joined_at) }) }}</span>
      </div>
      <div class="flex shrink-0 items-center gap-2.5">
        <UTooltip :text="t('people.formsOwned', { n: person.forms_count }, person.forms_count)"><span class="flex items-center gap-1"><UIcon name="i-lucide-file-text" class="size-3.5" />{{ number(person.forms_count) }}</span></UTooltip>
        <UTooltip :text="person.two_step ? t('people.twoStepOn') : t('people.twoStepOff')"><UIcon :name="person.two_step ? 'i-lucide-shield-check' : 'i-lucide-shield-off'" class="size-3.5" :class="person.two_step ? 'text-highlighted' : ''" /></UTooltip>
      </div>
    </div>
  </div>
</template>
