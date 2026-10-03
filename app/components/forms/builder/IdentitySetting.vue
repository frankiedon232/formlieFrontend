<!--
  Form settings → Recognise respondents (F10, owner 2026-10-03): which answers tell people apart —
  the respondent's OWN email (suggested: the first email that isn't a reference's, manager's…),
  an ID / account number — and whether to verify the email with a one-time code. Without either,
  only the same browser is recognised. Rules: shared/utils/forms/identity.ts.
-->
<script setup lang="ts">
import { allFields } from '#shared/utils/forms/build'
import { identityOf, suggestEmailField, suggestIdField, type IdentitySettings } from '#shared/utils/forms/identity'

const { t } = useI18n()
const builder = useBuilder()
const schema = builder.schema

const fields = computed(() => (schema.value ? allFields(schema.value) : []))
const current = computed<IdentitySettings>(() => (schema.value ? identityOf(schema.value) : { email: null, id: null, verify: false }))
const suggestedEmail = computed(() => suggestEmailField(fields.value))
const suggestedId = computed(() => suggestIdField(fields.value))

/** "Off" needs a real value: the select menu doesn't accept an empty one (the menu wouldn't open). */
const OFF = '__off'
const label = (key: string, suggested: string | null) => {
  const field = fields.value.find(f => f.key === key)
  const name = field?.label?.trim() || t('builder.untitled')
  return key === suggested ? `${name} · ${t('builder.identity.suggested')}` : name
}
const emailItems = computed(() => [
  { value: OFF, label: t('builder.identity.off') },
  ...fields.value.filter(f => f.type === 'email').map(f => ({ value: f.key, label: label(f.key, suggestedEmail.value) })),
])
const idItems = computed(() => [
  { value: OFF, label: t('builder.identity.off') },
  ...fields.value.filter(f => f.type === 'short_text' || f.type === 'number').map(f => ({ value: f.key, label: label(f.key, suggestedId.value) })),
])

function update(patch: Partial<IdentitySettings>) {
  if (!schema.value) return
  builder.history.record()
  const next = { ...current.value, ...patch }
  if (!next.email) next.verify = false
  schema.value.settings = { ...schema.value.settings, identity: next }
  // Verification needs an email to send the code to: that question becomes required.
  if (next.verify && next.email) {
    const field = fields.value.find(f => f.key === next.email)
    if (field && !field.required) field.required = true
  }
}
/** Verification was turned on, but its email question was removed (or turned off). */
const verifyLost = computed(() => !!schema.value?.settings?.identity?.verify && !current.value.email)
</script>

<template>
  <section class="flex flex-col gap-3">
    <h3 class="text-xs font-medium text-muted uppercase">{{ t('builder.identity.title') }}</h3>
    <p class="text-xs text-muted">{{ t('builder.identity.hint') }}</p>
    <UFormField :label="t('builder.identity.email')" :description="t('builder.identity.emailHint')">
      <USelectMenu
        :model-value="current.email ?? OFF"
        :items="emailItems"
        value-key="value"
        :search-input="false"
        icon="i-lucide-at-sign"
        class="w-full"
        @update:model-value="v => update({ email: v && v !== OFF ? String(v) : null })"
      />
    </UFormField>
    <UFormField :label="t('builder.identity.id')" :description="t('builder.identity.idHint')">
      <USelectMenu
        :model-value="current.id ?? OFF"
        :items="idItems"
        value-key="value"
        :search-input="false"
        icon="i-lucide-id-card"
        class="w-full"
        @update:model-value="v => update({ id: v && v !== OFF ? String(v) : null })"
      />
    </UFormField>
    <USwitch
      :model-value="current.verify"
      :disabled="!current.email"
      :label="t('builder.identity.verify')"
      :description="t('builder.identity.verifyHint')"
      color="neutral"
      @update:model-value="v => update({ verify: v })"
    />
    <UAlert
      v-if="verifyLost"
      icon="i-lucide-triangle-alert"
      color="warning"
      variant="subtle"
      :description="t('builder.identity.verifyLost')"
      :ui="{ description: 'text-xs' }"
    />
    <p v-else-if="current.verify" class="flex items-center gap-1.5 text-xs text-muted">
      <UIcon name="i-lucide-asterisk" class="size-3 shrink-0" />{{ t('builder.identity.verifyRequired') }}
    </p>
    <UAlert v-if="!current.email && !current.id" icon="i-lucide-info" color="neutral" variant="subtle" :description="t('builder.identity.none')" :ui="{ description: 'text-xs' }" />
  </section>
</template>
