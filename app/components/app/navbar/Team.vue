<!--
  Team in the page header (design: overlapping avatars "+10 ⌄" then "+ Add Member", F16 M4), for owners
  and admins: the most recently active people; the menu lists them (each opens their panel on People)
  and All people, each with when they were last active and for how long (green dot = online now). Invite user opens the invite dialog. Only in the People area (owner, 2026-10-09), so
  other pages keep the header space. Avatars from xl, the button from sm (icon only below xl, so the header never overflows).
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { PersonRow } from '#shared/types/people'

const { t } = useI18n()
const { number, moment, span, dateTime } = useFormat()
const { team, canSee, refresh } = useTeam()
const route = useRoute()
// Only in the People area (People, Departments, Job titles, Roles & access)
const inPeople = computed(() => route.path === '/people' || route.path.startsWith('/people/'))
watch(inPeople, value => value && !team.value && void refresh(), { immediate: true })

// Last visit for a menu row: when (or Online), how long, the full date and time on hover (as a list so the template can bind it)
// A visit of a single action has no real length: "< 1m"
const lengthOf = (ms: number) => (ms < 60_000 ? `< ${span(60_000)}` : span(ms))
const personOf = (item: { person: PersonRow }) => item.person
function visitOf({ person }: { person: PersonRow }) {
  const visit = person.last_visit
  if (!visit) return []
  return [{ online: visit.online, when: visit.online ? t('people.team.online') : moment(visit.ended_at), length: lengthOf(Date.parse(visit.ended_at) - Date.parse(visit.started_at)), title: dateTime(visit.ended_at) }]
}
const shown = computed(() => team.value?.people.slice(0, 3) ?? [])
const more = computed(() => Math.max(0, (team.value?.total ?? 0) - shown.value.length))
const items = computed<DropdownMenuItem[][]>(() => [
  [{ type: 'label', label: t('people.team.recent') }, ...(team.value?.people ?? []).map(person => ({ slot: 'person' as const, label: person.name, description: person.email, person, to: { path: '/people', query: { person: person.id } } }))],
  [{ label: t('people.team.all', { n: number(team.value?.total ?? 0) }), icon: 'i-lucide-users', to: '/people' }],
])
</script>

<template>
  <template v-if="canSee && inPeople">
    <UDropdownMenu v-if="team?.people.length" :items="items" :content="{ align: 'end' }" :ui="{ content: 'w-80' }">
      <UButton color="neutral" variant="ghost" class="hidden gap-1.5 px-1.5 xl:inline-flex" :aria-label="t('people.team.label', { n: team.total }, team.total)">
        <UAvatarGroup size="xs" :max="3">
          <UAvatar v-for="person in shown" :key="person.id" :src="person.photo ?? undefined" :alt="person.name" />
        </UAvatarGroup>
        <span v-if="more" class="text-xs font-medium text-default tabular-nums">+{{ number(more) }}</span>
        <UIcon name="i-lucide-chevron-down" class="size-3.5 text-muted" />
      </UButton>
      <template #person-leading="{ item }">
        <UChip v-for="person in [personOf(item)]" :key="person.id" :show="!!person.last_visit?.online" color="success" position="bottom-right" inset>
          <UAvatar :src="person.photo ?? undefined" :alt="person.name" size="sm" />
        </UChip>
      </template>
      <template #person-trailing="{ item }">
        <template v-for="visit in visitOf(item)" :key="visit.title">
          <span class="ms-2 flex shrink-0 flex-col items-end text-xs leading-4 tabular-nums" :title="visit.title">
            <span :class="visit.online ? 'font-medium text-success' : 'text-default'">{{ visit.when }}</span>
            <span class="inline-flex items-center gap-1 text-muted">
              <UIcon name="i-lucide-timer" class="size-3" aria-hidden="true" />
              <span class="sr-only">{{ t('people.team.duration') }}</span>{{ visit.length }}
            </span>
          </span>
        </template>
      </template>
    </UDropdownMenu>
    <UButton :label="t('people.team.invite')" icon="i-lucide-plus" color="neutral" variant="outline" class="hidden sm:inline-flex max-xl:[&_[data-slot=label]]:hidden" :to="{ path: '/people', query: { invite: '1' } }" :aria-label="t('people.team.invite')" />
  </template>
</template>
