<!--
  Settings → Security (F14 M3): the workspace's password rules: minimum length, which kinds of
  characters are required, no reuse of recent ones and an expiry. A "try a password" field checks
  against the rules being edited, with the same meter people see when they set a new password.
-->
<script setup lang="ts">
import type { SecuritySettings } from '#shared/types/settings'

const model = defineModel<SecuritySettings['password']>({ required: true })
const { t } = useI18n()

const KINDS = ['lower', 'upper', 'number', 'symbol'] as const
const reuses = computed(() => ([0, 3, 5, 10] as const).map(value => ({ value, label: value ? t('settings.security.reuseLast', { n: value }) : t('settings.security.reuseOff') })))
const expiries = computed(() => ([0, 90, 180, 365] as const).map(value => ({ value, label: value ? t('settings.security.days', { n: value }, value) : t('settings.security.never') })))
const trial = ref('')
const policy = computed(() => ({ min_length: model.value.min_length, lower: model.value.lower, upper: model.value.upper, number: model.value.number, symbol: model.value.symbol }))
const weak = computed(() => model.value.min_length < 10 && [model.value.lower, model.value.upper, model.value.number, model.value.symbol].filter(Boolean).length < 2)
</script>

<template>
  <div class="grid gap-4 sm:grid-cols-[10rem_minmax(0,1fr)]">
    <UFormField :label="t('settings.security.minLength')">
      <UInputNumber v-model="model.min_length" :min="PASSWORD_LENGTH_RANGE.min" :max="PASSWORD_LENGTH_RANGE.max" color="neutral" class="w-full" />
    </UFormField>
    <UFormField :label="t('settings.security.mustHave')">
      <div class="flex flex-wrap gap-2">
        <UCheckbox v-for="kind in KINDS" :key="kind" v-model="model[kind]" :label="t(`settings.security.kind.${kind}`)" color="neutral" variant="card" size="sm" :ui="{ root: 'py-2' }" />
      </div>
    </UFormField>
  </div>
  <UAlert v-if="weak" color="warning" variant="subtle" icon="i-lucide-triangle-alert" :title="t('settings.security.weakRules')" />
  <div class="grid gap-4 sm:grid-cols-2">
    <UFormField :label="t('settings.security.reuse')" :description="t('settings.security.reuseHint')">
      <USelect v-model="model.reuse_last" :items="reuses" class="w-full" />
    </UFormField>
    <UFormField :label="t('settings.security.expiry')" :description="t('settings.security.expiryHint')">
      <USelect v-model="model.expiry_days" :items="expiries" class="w-full" />
    </UFormField>
  </div>
  <div class="rounded-lg border border-dashed border-default p-3">
    <UFormField :label="t('settings.security.try')" :help="trial ? undefined : t('settings.security.tryHint')">
      <AuthPasswordInput v-model="trial" autocomplete="off" icon="i-lucide-flask-conical" class="w-full sm:max-w-sm" />
      <AuthPasswordStrength :value="trial" :policy="policy" />
    </UFormField>
  </div>
</template>
