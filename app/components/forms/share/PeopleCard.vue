<!--
  Share → People with access (F10 M3, decision 97): who in the workspace may work on this form.
  Always full access: workspace owner / admins and the form's owner. Everyone else: the workspace
  default (can edit, as before · can view · no access), unless given their own level (can edit ·
  can view · responses only), more or less than the default. Saved with the page.
-->
<script setup lang="ts">
import type { Directory } from '#shared/types/directory'
import type { FormAccessLevel, FormShareSettings, ShareDraft } from '#shared/types/forms'

const props = defineProps<{ settings: FormShareSettings }>()
const draft = defineModel<ShareDraft>('draft', { required: true })
const { t } = useI18n()
const api = useApi()

type Level = Exclude<FormAccessLevel, 'none'>
const teamItems = computed(() => [
  { value: 'edit', label: t('share.people.level.edit'), description: t('share.people.levelDesc.edit') },
  { value: 'view', label: t('share.people.level.view'), description: t('share.people.levelDesc.view') },
  { value: 'none', label: t('share.people.level.none'), description: t('share.people.levelDesc.none') },
])
const levelItems = computed(() =>
  (['edit', 'view', 'responses'] as Level[]).map(value => ({ value, label: t(`share.people.level.${value}`), description: t(`share.people.levelDesc.${value}`) })),
)

// Everyone in the workspace who could be added (not already listed).
const directory = ref<Directory['users']>([])
onMounted(async () => {
  try {
    directory.value = (await api.get<Directory>('/directory', undefined, { background: true })).data.users
  } catch {
    directory.value = []
  }
})
const listed = computed(() => new Set([...props.settings.people.always.map(item => item.user.id), ...draft.value.grants.map(grant => grant.user.id)]))
const candidates = computed(() =>
  directory.value.filter(person => !listed.value.has(person.id)).map(person => ({ value: person.id, label: person.name, description: person.detail ?? '' })),
)
function add(id: string) {
  const person = directory.value.find(item => item.id === id)
  if (!person) return
  draft.value.grants = [...draft.value.grants, { user: { id: person.id, name: person.name, email: person.detail ?? '' }, level: 'view' }]
}
/** The picker empties itself after each choice (it never keeps or re-sends an old one). */
const picked = ref<string | undefined>()
watch(picked, id => {
  if (!id) return
  add(id)
  nextTick(() => (picked.value = undefined))
})
const remove = (id: string) => (draft.value.grants = draft.value.grants.filter(grant => grant.user.id !== id))
const initials = (name: string) =>
  name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map(word => word[0]!.toUpperCase())
    .join('')
</script>

<template>
  <UCard variant="outline" :ui="{ body: 'p-4 sm:p-5' }">
    <div class="mb-4 flex items-start gap-3">
      <UIcon name="i-lucide-users" class="mt-0.5 size-5 shrink-0 text-muted" />
      <div>
        <h2 class="text-sm font-semibold text-highlighted">{{ t('share.people.title') }}</h2>
        <p class="text-xs text-muted">{{ t('share.people.desc') }}</p>
      </div>
    </div>

    <UFormField :label="t('share.people.team')" :description="t('share.people.teamDesc')">
      <USelect v-model="draft.teamAccess" :items="teamItems" value-key="value" class="w-full sm:w-72" :ui="{ itemDescription: 'text-xs' }" />
    </UFormField>

    <ul class="mt-4 flex flex-col divide-y divide-default rounded-md border border-default">
      <!-- Always full access. -->
      <li v-for="item in settings.people.always" :key="`always-${item.user.id}`" class="flex items-center gap-3 px-3 py-2">
        <UAvatar :text="initials(item.user.name)" size="sm" />
        <div class="min-w-0 flex-1">
          <p class="truncate text-sm text-highlighted">{{ item.user.name }}</p>
          <p class="truncate text-xs text-muted">{{ item.user.email }}</p>
        </div>
        <UBadge :label="t(`share.people.always.${item.reason}`)" color="neutral" variant="subtle" size="sm" icon="i-lucide-shield-check" />
      </li>
      <!-- People given their own level. -->
      <li v-for="grant in draft.grants" :key="grant.user.id" class="flex flex-wrap items-center gap-3 px-3 py-2">
        <UAvatar :text="initials(grant.user.name)" size="sm" />
        <div class="min-w-0 flex-1">
          <p class="truncate text-sm text-highlighted">{{ grant.user.name }}</p>
          <p class="truncate text-xs text-muted">{{ grant.user.email }}</p>
        </div>
        <USelect v-model="grant.level" :items="levelItems" value-key="value" size="sm" class="w-40" :aria-label="t('share.people.levelFor', { name: grant.user.name })" />
        <UButton icon="i-lucide-x" color="neutral" variant="ghost" size="xs" :aria-label="t('share.people.remove', { name: grant.user.name })" @click="remove(grant.user.id)" />
      </li>
    </ul>

    <USelectMenu
      v-model="picked"
      :items="candidates"
      value-key="value"
      :placeholder="t('share.people.add')"
      icon="i-lucide-user-plus"
      :search-input="{ placeholder: t('common.search') }"
      class="mt-3 w-full sm:w-72"
    />
    <p class="mt-2 text-xs text-muted">{{ t('share.people.note') }}</p>
  </UCard>
</template>
