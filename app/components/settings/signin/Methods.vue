<!--
  Settings → Sign-in (F14 M3): one card per way to sign in, each with a switch. At least one stays
  on (the last one can't be switched off); turning off email and password asks first, since people
  then sign in only with the providers that are left.
-->
<script setup lang="ts">
import type { AuthProvider } from '#shared/types/auth'
import { SIGNIN_METHODS } from '#shared/utils/settings/schemas'

const model = defineModel<AuthProvider[]>({ required: true })
const { t } = useI18n()
const confirm = useConfirm()
const access = usePlanAccess()

const isOn = (method: AuthProvider) => model.value.includes(method)
const isLast = (method: AuthProvider) => isOn(method) && model.value.length === 1
/** Google, Apple, Microsoft and Facebook come with a higher plan (F24); one that is on can still be switched off. */
const locked = (method: AuthProvider) => method !== 'password' && !isOn(method) && !access.allows('social_signin')
const nameOf = (method: AuthProvider) => (method === 'password' ? t('settings.signin.password') : PROVIDER_NAMES[method])

async function toggle(method: AuthProvider, on: boolean) {
  if (!on && isLast(method)) return
  if (!on && method === 'password' && !(await confirm({ title: t('settings.signin.passwordOffTitle'), description: t('settings.signin.passwordOffDesc'), confirmLabel: t('settings.signin.passwordOff'), danger: true }))) return
  model.value = on ? SIGNIN_METHODS.filter(item => item === method || model.value.includes(item)) : model.value.filter(item => item !== method)
}
</script>

<template>
  <div class="grid gap-3 sm:grid-cols-2">
    <label
      v-for="method in SIGNIN_METHODS"
      :key="method"
      class="flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition-colors"
      :class="[isOn(method) ? 'border-accented bg-elevated/40' : 'border-default hover:border-accented', method === 'password' ? 'sm:col-span-2' : '', isLast(method) || locked(method) ? 'cursor-not-allowed' : '']"
    >
      <span class="flex size-9 shrink-0 items-center justify-center rounded-lg border border-default bg-default">
        <UIcon :name="PROVIDER_ICONS[method]" class="size-4.5" :class="isOn(method) ? 'text-highlighted' : 'text-muted'" />
      </span>
      <span class="flex min-w-0 flex-1 flex-col gap-0.5">
        <span class="flex items-center gap-2 text-sm font-medium text-highlighted">
          {{ nameOf(method) }}
          <UBadge v-if="isLast(method)" :label="t('settings.signin.onlyOne')" color="neutral" variant="soft" size="xs" />
          <BillingLocked v-if="locked(method)" feature="social_signin" inline />
        </span>
        <span class="text-xs text-muted">{{ method === 'password' ? t('settings.signin.passwordHint') : t('settings.signin.providerHint', { name: nameOf(method) }) }}</span>
      </span>
      <USwitch :model-value="isOn(method)" color="neutral" :disabled="isLast(method) || locked(method)" :aria-label="nameOf(method)" @update:model-value="value => toggle(method, !!value)" />
    </label>
  </div>
</template>
