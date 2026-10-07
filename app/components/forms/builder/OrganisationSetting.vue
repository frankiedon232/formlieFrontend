<!--
  Form settings → Organisation (F14 M7): which of the workspace's organisations the form belongs to
  (its name and logo on the public pages; the rail's switcher finds it there). Shown only when the
  workspace has several. Saved straight away (not part of the draft), with a spinner and a toast.
-->
<script setup lang="ts">
import type { FormSummary } from '#shared/types/forms'

const { t } = useI18n()
const api = useApi()
const toast = useToast()
const session = injectBuilderSession()
const organisations = useOrganisations()
const { busy, run } = useBusy()
onMounted(() => void organisations.load())

const items = computed(() => organisations.active.value.map(org => ({ value: org.id, label: org.name })))
const mainId = computed(() => organisations.active.value.find(org => org.main)?.id ?? null)
const current = computed(() => session?.form.value?.organisation_id ?? mainId.value)
async function move(id: string) {
  if (!session?.form.value || id === current.value) return
  const updated = await run(async () => (await api.patch<FormSummary>(`/forms/${session.formId}/organisation`, { organisation_id: id })).data)
  if (updated && session.form.value) {
    session.form.value.organisation_id = updated.organisation_id ?? null
    toast.add({ title: t('organisations.moved', { name: items.value.find(item => item.value === id)?.label ?? '' }), color: 'success', icon: 'i-lucide-building' })
  }
}
</script>

<template>
  <section v-if="organisations.several.value && session" class="flex flex-col gap-3">
    <h3 class="text-xs font-medium text-muted uppercase">{{ t('organisations.formSetting') }}</h3>
    <UFormField :description="t('organisations.formSettingHint')">
      <USelect :model-value="current ?? undefined" :items="items" icon="i-lucide-building" :loading="busy" :disabled="busy || !session.canEdit.value" class="w-full" :aria-label="t('organisations.formSetting')" @update:model-value="value => move(String(value))" />
    </UFormField>
  </section>
</template>
