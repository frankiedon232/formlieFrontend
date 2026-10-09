<!--
  Team in the page header (design: overlapping avatars "+10 ⌄" then "+ Add Member", F16 M4), for owners
  and admins: the most recently active people; the menu lists them (each opens their panel on People)
  and All people. Invite user opens the invite dialog. Only in the People area (owner, 2026-10-09), so
  other pages keep the header space. Avatars from lg, the button from sm (icon only below md).
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'

const { t } = useI18n()
const { number } = useFormat()
const { team, canSee, refresh } = useTeam()
const route = useRoute()
// Only in the People area (People, Departments, Job titles, Roles & access)
const inPeople = computed(() => route.path === '/people' || route.path.startsWith('/people/'))
watch(inPeople, value => value && !team.value && void refresh(), { immediate: true })

const shown = computed(() => team.value?.people.slice(0, 3) ?? [])
const more = computed(() => Math.max(0, (team.value?.total ?? 0) - shown.value.length))
const items = computed<DropdownMenuItem[][]>(() => [
  [{ type: 'label', label: t('people.team.recent') }, ...(team.value?.people ?? []).map(person => ({ label: person.name, description: person.email, avatar: { src: person.photo ?? undefined, alt: person.name }, to: { path: '/people', query: { person: person.id } } }))],
  [{ label: t('people.team.all', { n: number(team.value?.total ?? 0) }), icon: 'i-lucide-users', to: '/people' }],
])
</script>

<template>
  <template v-if="canSee && inPeople">
    <UDropdownMenu v-if="team?.people.length" :items="items" :content="{ align: 'end' }" :ui="{ content: 'w-64' }">
      <UButton color="neutral" variant="ghost" class="hidden gap-1.5 px-1.5 lg:inline-flex" :aria-label="t('people.team.label', { n: team.total }, team.total)">
        <UAvatarGroup size="xs" :max="3">
          <UAvatar v-for="person in shown" :key="person.id" :src="person.photo ?? undefined" :alt="person.name" />
        </UAvatarGroup>
        <span v-if="more" class="text-xs font-medium text-default tabular-nums">+{{ number(more) }}</span>
        <UIcon name="i-lucide-chevron-down" class="size-3.5 text-muted" />
      </UButton>
    </UDropdownMenu>
    <UButton :label="t('people.team.invite')" icon="i-lucide-plus" color="neutral" variant="outline" class="hidden sm:inline-flex max-md:[&_[data-slot=label]]:hidden" :to="{ path: '/people', query: { invite: '1' } }" :aria-label="t('people.team.invite')" />
  </template>
</template>
