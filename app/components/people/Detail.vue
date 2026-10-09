<!--
  A person in a panel from the side (F16 M1, detail panel model): header with avatar, name, email,
  status and role, a one-click bar (email them, their activity in the audit trail); fact tiles; their
  profile (departments, job titles, manager, people who report to them); last sign-in. Editing comes
  with M3. Previous (K) · position · Next (J).
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { PersonDetail } from '#shared/types/people'

const props = defineProps<{ id: string | null; ids: string[]; busy?: boolean; menu?: (person: PersonDetail) => DropdownMenuItem[][] }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ go: [id: string]; resend: [person: PersonDetail]; copyLink: [person: PersonDetail]; revoke: [person: PersonDetail]; edit: [person: PersonDetail] }>()
const { t } = useI18n()
const api = useApi()
const { number, relative, date, dateTime, percent } = useFormat()

const person = ref<PersonDetail | null>(null)
const failed = ref(false)
async function load(id: string) {
  failed.value = false
  try {
    const { data } = await api.get<PersonDetail>(`/people/${id}`)
    if (props.id === id) person.value = data
  } catch {
    failed.value = true
  }
}
watch(() => [props.id, open.value] as const, ([id, isOpen]) => id && isOpen && void load(id), { immediate: true })
defineExpose({ reload: () => props.id && load(props.id) })
// Owners are changed only by owners
const session = useSession()
const canEdit = computed(() => !!props.menu && !(person.value?.role === 'owner' && session.user.value?.role !== 'owner'))
// After an action (resend renews the link's dates)
watch(() => props.busy, (now, before) => before && !now && props.id && open.value && void load(props.id))

const index = computed(() => (props.id ? props.ids.indexOf(props.id) : -1))
const prev = computed(() => (index.value > 0 ? props.ids[index.value - 1] : null))
const next = computed(() => (index.value >= 0 && index.value < props.ids.length - 1 ? props.ids[index.value + 1] : null))
defineShortcuts({
  j: { usingInput: false, handler: () => open.value && next.value && emit('go', next.value) },
  k: { usingInput: false, handler: () => open.value && prev.value && emit('go', prev.value) },
})

const names = (items: { name: string }[]) => items.map(item => item.name).join(', ') || t('people.none')
const tiles = computed(() => {
  const p = person.value
  if (!p) return []
  return [
    { key: 'role', icon: 'i-lucide-shield', label: t('people.col.role'), value: t(`people.role.${p.role}`) },
    { key: 'active', icon: 'i-lucide-clock', label: t('people.col.lastActive'), value: p.last_active_at ? relative(p.last_active_at) : t('people.never') },
    p.invite ? { key: 'joined', icon: 'i-lucide-mail', label: t('people.status.invited'), value: date(p.invite.sent_at) } : { key: 'joined', icon: 'i-lucide-calendar', label: t('people.col.joined'), value: date(p.joined_at) },
    { key: 'twoStep', icon: p.two_step ? 'i-lucide-shield-check' : 'i-lucide-shield-off', label: t('people.col.twoStep'), value: p.two_step ? t('people.twoStepOn') : t('people.twoStepOff') },
    { key: 'signIns', icon: 'i-lucide-log-in', label: t('people.signIns30'), value: number(p.sign_ins_30d) },
    { key: 'forms', icon: 'i-lucide-file-text', label: t('people.col.forms'), value: number(p.forms_count) },
  ]
})
const place = computed(() => {
  const s = person.value?.last_sign_in
  if (!s) return ''
  return [[s.city, s.country].filter(Boolean).join(', '), [s.browser, s.os].filter(Boolean).join(' · ')].filter(Boolean).join(' · ')
})
</script>

<template>
  <USlideover
    v-model:open="open"
    :content="{ onOpenAutoFocus: (event: Event) => event.preventDefault() }"
    :title="person?.name || t('people.title')"
    :ui="{ content: 'w-full sm:max-w-2xl', header: 'border-b-0 pb-2', body: 'flex flex-col gap-6 pb-40', footer: 'pointer-events-none absolute inset-x-0 bottom-0 justify-center border-t-0 bg-gradient-to-t from-(--ui-bg) via-(--ui-bg)/85 to-transparent pt-10 pb-4' }"
  >
    <template #header>
      <div v-if="!person" class="flex w-full items-center gap-3.5">
        <USkeleton class="size-16 rounded-full" />
        <div class="flex flex-1 flex-col gap-2"><USkeleton class="h-5 w-48" /><USkeleton class="h-4 w-32" /></div>
      </div>
      <div v-else class="flex w-full flex-col gap-4">
        <div class="flex items-start gap-3.5">
          <UAvatar :alt="person.name" size="2xl" class="ring-4 ring-(--ui-bg-elevated)" />
          <div class="flex min-w-0 flex-1 flex-col gap-1">
            <h2 class="truncate text-lg leading-tight font-semibold text-highlighted">{{ person.name }}</h2>
            <p v-if="person.name !== person.email" class="truncate text-sm text-muted" dir="ltr">{{ person.email }}</p>
            <div class="mt-1 flex flex-wrap items-center gap-1.5">
              <PeopleStatus :person="person" />
              <UBadge :label="t(`people.role.${person.role}`)" icon="i-lucide-shield" color="neutral" variant="outline" size="sm" class="rounded-md" />
            </div>
          </div>
          <div class="flex shrink-0 items-center gap-1">
            <UDropdownMenu v-if="menu" :items="menu(person)" :content="{ align: 'end' }">
              <UButton icon="i-lucide-ellipsis" color="neutral" variant="ghost" size="sm" square :loading="busy" :aria-label="t('dataView.actions')" />
            </UDropdownMenu>
            <UButton icon="i-lucide-x" color="neutral" variant="soft" size="sm" square class="rounded-full" :aria-label="t('common.close')" @click="open = false" />
          </div>
        </div>
        <div v-if="person.invite" class="flex flex-wrap items-center gap-2">
          <UButton :label="t('people.invite.resend')" icon="i-lucide-send" color="neutral" size="sm" :loading="busy" @click="emit('resend', person)" />
          <UButton :label="t('people.invite.copyLink')" icon="i-lucide-link" color="neutral" variant="outline" size="sm" :disabled="busy" @click="emit('copyLink', person)" />
          <UButton :label="t('people.invite.revoke')" icon="i-lucide-user-minus" color="error" variant="outline" size="sm" :disabled="busy" @click="emit('revoke', person)" />
        </div>
        <div v-else class="flex flex-wrap items-center gap-2">
          <UButton v-if="canEdit" :label="t('people.manage.edit')" icon="i-lucide-pencil" color="neutral" size="sm" :disabled="busy" @click="emit('edit', person)" />
          <UButton :label="t('people.email')" icon="i-lucide-mail" color="neutral" variant="outline" size="sm" :to="`mailto:${person.email}`" external />
          <UButton :label="t('people.activity')" icon="i-lucide-scroll-text" color="neutral" variant="outline" size="sm" :to="{ path: '/audit', query: { actor_id: person.id } }" />
        </div>
      </div>
    </template>

    <template #body>
      <AppEmpty v-if="failed && !person" icon="i-lucide-cloud-alert" :title="t('dataView.errorTitle')" :actions="[{ label: t('common.retry'), color: 'neutral', variant: 'outline', onClick: () => id && load(id) }]" />
      <div v-else-if="!person" class="grid grid-cols-2 gap-2 sm:grid-cols-3"><USkeleton v-for="n in 6" :key="n" class="h-14 rounded-lg" /></div>
      <template v-else>
        <UAlert v-if="person.invite" :icon="person.invite.expired ? 'i-lucide-clock-alert' : 'i-lucide-mail'" :color="person.invite.expired ? 'warning' : 'neutral'" variant="subtle" :title="person.invite.expired ? t('people.invite.expiredOn', { date: dateTime(person.invite.expires_at) }) : t('people.invite.waiting', { date: dateTime(person.invite.expires_at) })" :description="t('people.invite.sentBy', { name: person.invite.invited_by, when: relative(person.invite.sent_at) })" />
        <UAlert v-if="person.role !== 'member' && !person.two_step && person.status === 'active'" icon="i-lucide-flag" color="error" variant="subtle" :title="t('people.flagTwoStep')" :description="t('people.flagTwoStepDesc')" />
        <div class="grid grid-cols-2 gap-2 sm:grid-cols-3">
          <div v-for="tile in tiles" :key="tile.key" class="flex min-w-0 items-center gap-2.5 rounded-lg border border-default p-2.5">
            <span class="flex size-8 shrink-0 items-center justify-center rounded-md bg-elevated"><UIcon :name="tile.icon" class="size-4 text-muted" /></span>
            <div class="flex min-w-0 flex-col">
              <span class="truncate text-[11px] text-muted">{{ tile.label }}</span>
              <span class="truncate text-sm font-semibold text-highlighted tabular-nums">{{ tile.value }}</span>
            </div>
          </div>
        </div>

        <section class="flex flex-col gap-3">
          <div class="flex items-center justify-between gap-2">
            <h3 class="text-sm font-semibold text-highlighted">{{ t('people.profile') }}</h3>
            <span class="text-xs text-muted tabular-nums">{{ percent(profileShare(person)) }}</span>
          </div>
          <UProgress :model-value="profileShare(person) * 100" color="neutral" size="xs" />
          <div class="grid gap-2 sm:grid-cols-2">
            <div class="flex h-full flex-col gap-1 rounded-lg border border-default p-3"><span class="text-[11px] text-muted">{{ t('people.col.departments') }}</span><span class="text-sm text-highlighted">{{ names(person.departments) }}</span></div>
            <div class="flex h-full flex-col gap-1 rounded-lg border border-default p-3"><span class="text-[11px] text-muted">{{ t('people.col.jobTitles') }}</span><span class="text-sm text-highlighted">{{ names(person.job_titles) }}</span></div>
            <div class="flex h-full flex-col gap-1 rounded-lg border border-default p-3"><span class="text-[11px] text-muted">{{ t('people.col.manager') }}</span><span class="text-sm text-highlighted">{{ person.manager?.name ?? t('people.none') }}</span></div>
            <div class="flex h-full flex-col gap-1 rounded-lg border border-default p-3"><span class="text-[11px] text-muted">{{ t('people.reports') }}</span><span class="text-sm text-highlighted">{{ names(person.reports) }}</span></div>
            <div class="flex h-full flex-col gap-1 rounded-lg border border-default p-3"><span class="text-[11px] text-muted">{{ t('people.col.phone') }}</span><span class="text-sm text-highlighted" dir="ltr">{{ person.phone ?? t('people.none') }}</span></div>
            <div class="flex h-full flex-col gap-1 rounded-lg border border-default p-3"><span class="text-[11px] text-muted">{{ t('people.lastSignIn') }}</span><span class="text-sm text-highlighted">{{ person.last_sign_in ? `${relative(person.last_sign_in.at)}${place ? ` · ${place}` : ''}` : t('people.never') }}</span></div>
          </div>
        </section>

        <section v-if="person.forms?.length" class="flex flex-col gap-3">
          <div class="flex items-center justify-between gap-2">
            <h3 class="text-sm font-semibold text-highlighted">{{ t('people.forms.title') }}</h3>
            <UButton v-if="person.forms_count > person.forms.length" :label="t('people.forms.all', { n: number(person.forms_count) })" color="neutral" variant="link" size="xs" trailing-icon="i-lucide-arrow-right" :to="{ path: '/forms', query: { owner_id: person.id } }" class="rtl:[&_svg]:rotate-180" />
          </div>
          <ul class="flex flex-col divide-y divide-default rounded-lg border border-default">
            <li v-for="form in person.forms" :key="form.id">
              <NuxtLink :to="`/forms/${form.id}`" class="flex items-center gap-3 px-3 py-2.5 text-sm hover:bg-elevated/50 focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)">
                <UIcon name="i-lucide-file-text" class="size-4 shrink-0 text-muted" />
                <span class="min-w-0 flex-1 truncate text-highlighted">{{ form.name }}</span>
                <DataStatusBadge :status="form.status" />
              </NuxtLink>
            </li>
          </ul>
        </section>
      </template>
    </template>

    <template #footer>
      <nav class="pointer-events-auto flex items-center gap-1 rounded-full border border-default bg-default/95 p-1 shadow-lg backdrop-blur" :aria-label="t('apiService.navigate')">
        <UButton :label="t('responses.detail.prevShort')" icon="i-lucide-arrow-up" color="neutral" variant="ghost" size="sm" class="rounded-full" :disabled="!prev" @click="prev && emit('go', prev)">
          <template #trailing><UKbd value="K" size="sm" class="hidden sm:inline-flex" /></template>
        </UButton>
        <span v-if="index >= 0" class="px-2 text-xs text-muted tabular-nums">{{ t('responses.detail.position', { n: index + 1, total: ids.length }) }}</span>
        <UButton :label="t('responses.detail.nextShort')" icon="i-lucide-arrow-down" color="neutral" variant="solid" size="sm" class="rounded-full" :disabled="!next" @click="next && emit('go', next)">
          <template #trailing><UKbd value="J" size="sm" class="hidden sm:inline-flex" /></template>
        </UButton>
      </nav>
    </template>
  </USlideover>
</template>
