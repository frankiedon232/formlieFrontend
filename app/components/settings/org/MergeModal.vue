<!--
  Merge entries (F14 M2): the chosen ones go into one that stays. Their people join it and every
  field restricted to them is restricted to it instead, so no form loses its access rules; then they
  are gone. Says exactly what will move before doing it.
-->
<script setup lang="ts">
import type { OrgItem, OrgKind } from '#shared/types/org'

const props = defineProps<{ kind: OrgKind; from: OrgItem[] }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ merged: [item: OrgItem] }>()
const { t } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()
const { number } = useFormat()

const choices = ref<OrgItem[]>([])
const into = ref<string | undefined>()
watch(open, async value => {
  if (!value) return
  into.value = undefined
  try {
    const exclude = new Set(props.from.map(item => item.id))
    choices.value = (await api.list<OrgItem>(`/org/${props.kind}`, { 'filter[status]': 'in_use,empty', page_size: 100, sort: 'name' }, { background: true })).data.filter(item => !exclude.has(item.id))
  } catch {
    choices.value = []
  }
})
const items = computed(() => choices.value.map(item => ({ value: item.id, label: item.name, description: t('settings.org.peopleCount', { n: number(item.members.length) }, item.members.length) })))
const people = computed(() => new Set(props.from.flatMap(item => item.members.map(person => person.id))).size)
const forms = computed(() => props.from.reduce((sum, item) => sum + item.forms_count, 0))
const target = computed(() => choices.value.find(item => item.id === into.value))

const saving = ref(false)
async function merge() {
  if (!into.value || saving.value) return
  saving.value = true
  try {
    const { data } = await api.post<OrgItem>(`/org/${props.kind}/merge`, { from: props.from.map(item => item.id), into: into.value })
    emit('merged', data)
    open.value = false
  } catch (error) {
    handle(error)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <AppModal v-model:open="open" :title="t('settings.org.merge.title', { n: from.length }, from.length)" :description="t('settings.org.merge.desc')" :ui="{ content: 'sm:max-w-lg' }">
    <template #body>
      <div class="flex flex-col gap-4">
        <div class="flex flex-wrap gap-1.5">
          <UBadge v-for="item in from" :key="item.id" :label="item.name" icon="i-lucide-arrow-right-from-line" color="neutral" variant="outline" class="rounded-md" />
        </div>
        <UFormField :label="t('settings.org.merge.into')" required>
          <USelectMenu v-model="into" :items="items" value-key="value" :placeholder="t('onboarding.choose')" :search-input="{ placeholder: t('common.search') }" class="w-full" />
        </UFormField>
        <ul class="flex flex-col gap-2 rounded-lg bg-elevated/40 p-3 text-sm">
          <li class="flex items-start gap-2"><UIcon name="i-lucide-users-round" class="mt-0.5 size-4 shrink-0 text-muted" />{{ t('settings.org.merge.people', { n: number(people), into: target?.name ?? '…' }, people) }}</li>
          <li class="flex items-start gap-2"><UIcon name="i-lucide-lock" class="mt-0.5 size-4 shrink-0 text-muted" />{{ t('settings.org.merge.forms', { n: number(forms) }, forms) }}</li>
          <li class="flex items-start gap-2"><UIcon name="i-lucide-trash-2" class="mt-0.5 size-4 shrink-0 text-muted" />{{ t('settings.org.merge.gone', { n: from.length }, from.length) }}</li>
        </ul>
      </div>
    </template>
    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton :label="t('common.cancel')" color="neutral" variant="outline" @click="open = false" />
        <UButton :label="t('settings.org.merge.action')" icon="i-lucide-merge" color="neutral" :disabled="!into" :loading="saving" @click="merge" />
      </div>
    </template>
  </AppModal>
</template>
