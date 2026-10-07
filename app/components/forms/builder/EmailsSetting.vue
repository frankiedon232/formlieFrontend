<!--
  Form settings → Response emails (F14 M4, owner 2026-10-07): every new response by email to chosen
  team members (with a link to it) and / or outside addresses (no link; personal answers masked unless
  allowed, asks first), and a copy for the respondent at the email they gave, in their language.
  The texts are the workspace's templates (Settings → Email templates). Applies once published.
-->
<script setup lang="ts">
import { allFields } from '#shared/utils/forms/build'
import { formEmailsOf, suggestReceiptField, type FormEmails } from '#shared/utils/forms/emails'

const { t } = useI18n()
const api = useApi()
const confirm = useConfirm()
const builder = useBuilder()
const schema = builder.schema

const current = computed<FormEmails>(() => formEmailsOf(schema.value))
function update(patch: Partial<FormEmails>) {
  if (!schema.value) return
  builder.history.record()
  schema.value.settings = { ...schema.value.settings, emails: { ...current.value, ...patch } }
}

const people = ref<{ value: string; label: string; description: string }[]>([])
onMounted(async () => {
  try {
    const { data } = await api.get<{ users: { id: string; name: string; detail: string }[] }>('/directory', undefined, { background: true })
    people.value = data.users.map(user => ({ value: user.id, label: user.name, description: user.detail }))
  } catch {
    people.value = []
  }
})

// Outside addresses: typed as people like, kept tidy; only real addresses stay
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const others = computed({
  get: () => current.value.others,
  set: list => update({ others: [...new Set(list.map(item => item.trim().toLowerCase()))].filter(item => EMAIL.test(item)).slice(0, 20) }),
})
async function setPersonal(on: boolean) {
  if (on && !(await confirm({ title: t('builder.emails.personalTitle'), description: t('builder.emails.personalDesc'), confirmLabel: t('builder.emails.personalConfirm') }))) return
  update({ others_personal: on })
}

const emailFields = computed(() => (schema.value ? allFields(schema.value).filter(field => field.type === 'email') : []))
const receiptItems = computed(() => emailFields.value.map(field => ({ value: field.key, label: field.label?.trim() || t('builder.untitled') })))
const receiptOn = computed(() => !!current.value.receipt_field)
const receiptLost = computed(() => receiptOn.value && !emailFields.value.some(field => field.key === current.value.receipt_field))
const toggleReceipt = (on: boolean) => update({ receipt_field: on && schema.value ? suggestReceiptField(schema.value) : null })
</script>

<template>
  <section class="flex flex-col gap-3">
    <h3 class="text-xs font-medium text-muted uppercase">{{ t('builder.emails.title') }}</h3>
    <p class="text-xs text-muted">{{ t('builder.emails.hint') }}</p>

    <UFormField :label="t('builder.emails.team')" :description="t('builder.emails.teamHint')">
      <USelectMenu :model-value="current.team" :items="people" value-key="value" multiple icon="i-lucide-users-round" :placeholder="t('builder.emails.nobody')" :search-input="{ placeholder: t('common.search') }" class="w-full" @update:model-value="value => update({ team: (value as string[]).slice(0, 50) })" />
    </UFormField>

    <UFormField :label="t('builder.emails.others')" :description="t('builder.emails.othersHint')">
      <UInputTags v-model="others" :placeholder="t('builder.emails.othersPlaceholder')" icon="i-lucide-at-sign" :add-on-blur="true" :add-on-paste="true" class="w-full" />
    </UFormField>
    <USwitch v-if="current.others.length" :model-value="current.others_personal" :label="t('builder.emails.personal')" :description="current.others_personal ? t('builder.emails.personalOn') : t('builder.emails.personalOff')" color="neutral" @update:model-value="value => setPersonal(!!value)" />

    <USwitch :model-value="receiptOn" :disabled="!emailFields.length" :label="t('builder.emails.receipt')" :description="emailFields.length ? t('builder.emails.receiptHint') : t('builder.emails.receiptNoEmail')" color="neutral" @update:model-value="value => toggleReceipt(!!value)" />
    <UFormField v-if="receiptOn && receiptItems.length > 1" :label="t('builder.emails.receiptField')">
      <USelect :model-value="current.receipt_field ?? undefined" :items="receiptItems" icon="i-lucide-at-sign" class="w-full" @update:model-value="value => update({ receipt_field: String(value) })" />
    </UFormField>
    <UAlert v-if="receiptLost" icon="i-lucide-triangle-alert" color="warning" variant="subtle" :description="t('builder.emails.receiptLost')" :ui="{ description: 'text-xs' }" />

    <NuxtLink to="/settings/emails" class="flex w-fit items-center gap-1 text-xs text-muted underline-offset-2 hover:text-highlighted hover:underline">
      <UIcon name="i-lucide-mail" class="size-3.5" />{{ t('builder.emails.templates') }}
    </NuxtLink>
  </section>
</template>
