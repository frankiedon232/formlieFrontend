<!--
  New / edit organisation entry (F14 M2): a name (unique within its kind), an optional short code and
  description, and the people in it (a person may be in several). Saving keeps the dialog's place in
  the list; a name already used says so on the field.
-->
<script setup lang="ts">
import type { Directory } from '#shared/types/directory'
import type { OrgItem, OrgItemSaveRequest, OrgKind } from '#shared/types/org'

const props = defineProps<{ kind: OrgKind; item?: OrgItem | null }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ saved: [item: OrgItem] }>()
const { t } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()

const state = reactive({ name: '', code: '', description: '', member_ids: [] as string[] })
const nameError = ref<string>()
const people = ref<{ value: string; label: string; description: string }[]>([])
watch(open, async value => {
  if (!value) return
  nameError.value = undefined
  Object.assign(state, { name: props.item?.name ?? '', code: props.item?.code ?? '', description: props.item?.description ?? '', member_ids: props.item?.members.map(person => person.id) ?? [] })
  try {
    people.value = (await api.get<Directory>('/directory', undefined, { background: true })).data.users.map(user => ({ value: user.id, label: user.name, description: user.detail ?? '' }))
  } catch {
    people.value = []
  }
}, { immediate: true })

const saving = ref(false)
async function save() {
  nameError.value = state.name.trim() ? undefined : t('settings.invalid.too_small')
  if (nameError.value || saving.value) return
  saving.value = true
  try {
    const body: OrgItemSaveRequest = { name: state.name.trim(), code: state.code.trim() || null, description: state.description.trim() || null, member_ids: state.member_ids }
    const { data } = props.item ? await api.patch<OrgItem>(`/org/${props.kind}/${props.item.id}`, body) : await api.post<OrgItem>(`/org/${props.kind}`, body)
    emit('saved', data)
    open.value = false
  } catch (error) {
    const normalised = handle(error, { silent: true })
    if (normalised.code === 'FRM-ORG-1001') nameError.value = t('settings.org.nameTaken')
    else handle(error)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <AppModal v-model:open="open" keep-open :title="item ? t('settings.org.editTitle', { name: item.name }) : t(`settings.org.kind.${kind}.new`)" :description="t(`settings.org.kind.${kind}.hint`)" :ui="{ content: 'sm:max-w-lg' }">
    <template #body>
      <form :id="`org-form-${kind}`" class="flex flex-col gap-4" @submit.prevent="save">
        <div class="grid gap-4 sm:grid-cols-[minmax(0,1fr)_8rem]">
          <UFormField :label="t('settings.org.col.name')" :error="nameError" required>
            <UInput v-model="state.name" maxlength="80" class="w-full" :placeholder="t(`settings.org.kind.${kind}.placeholder`)" autofocus />
          </UFormField>
          <UFormField :label="t('settings.org.col.code')" :hint="t('apiService.optional')">
            <UInput v-model="state.code" maxlength="20" class="w-full" :ui="{ base: 'font-mono uppercase' }" dir="ltr" />
          </UFormField>
        </div>
        <UFormField :label="t('settings.org.description')" :hint="t('apiService.optional')">
          <UTextarea v-model="state.description" :rows="2" autoresize maxlength="200" class="w-full" />
        </UFormField>
        <UFormField :label="t('settings.org.col.people')" :description="t('settings.org.peopleHelp')">
          <USelectMenu v-model="state.member_ids" :items="people" value-key="value" multiple :placeholder="t('settings.org.pickPeople')" :search-input="{ placeholder: t('common.search') }" class="w-full" />
        </UFormField>
      </form>
    </template>
    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton :label="t('common.cancel')" color="neutral" variant="outline" @click="open = false" />
        <UButton type="submit" :form="`org-form-${kind}`" :label="item ? t('common.save') : t(`settings.org.kind.${kind}.create`)" color="neutral" :loading="saving" />
      </div>
    </template>
  </AppModal>
</template>
