<!-- Second step of every login (SECURITY-PROTOCOL §7): 6-digit code → tokens → portal. -->
<script setup lang="ts">
import type { OtpChannel } from '#shared/types/auth'

definePageMeta({ layout: 'auth', auth: 'guest' })

const { t } = useI18n()
const auth = useAuth()
const { handle } = useErrorHandler()
const fromApp = computed(() => auth.pending.value?.challenge.channel === 'totp')
useHead({ title: () => (fromApp.value ? t('profile.signin.title') : t('auth.otp.title')) })

// The challenge lives in memory only: reloading this page starts over (by design).
if (!auth.pending.value || auth.pending.value.purpose !== 'login') await navigateTo('/auth/login')

const otp = useTemplateRef<{ reset: () => void }>('otp')
const verifying = ref(false)
const attemptsLeft = ref<number | null>(null)
const useRecovery = ref(false)
const recoveryCode = ref('')

async function verify(code: string) {
  if (verifying.value) return
  verifying.value = true
  try {
    const redirect = auth.pending.value?.redirect
    await auth.verify(code)
    await navigateTo(redirect || '/dashboard', { replace: true })
  } catch (error) {
    const normalised = handle(error)
    const left = normalised.details.find(detail => detail.field === 'attempts_left')
    attemptsLeft.value = left ? Number(left.message) : null
    otp.value?.reset()
    if (normalised.code === 'FRM-AUTH-1004') await navigateTo('/auth/login')
  } finally {
    verifying.value = false
  }
}

async function resend(channel?: OtpChannel) {
  try {
    await auth.resend(channel)
    attemptsLeft.value = null
  } catch (error) {
    handle(error)
  }
}

function back() {
  auth.clearPending()
  navigateTo('/auth/login')
}
</script>

<template>
  <div v-if="auth.pending.value">
    <AuthHeading :title="fromApp ? t('profile.signin.title') : t('auth.otp.title')" :back="t('common.back')" workspace @back="back">
      <template #description>
        <span v-if="auth.pending.value.challenge.channel === 'totp'">{{ t('profile.signin.appDesc') }}</span>
        <i18n-t v-else keypath="auth.otp.desc" scope="global">
          <template #destination>
            <span class="font-medium text-highlighted">{{
              auth.pending.value.challenge.masked_destination
            }}</span>
          </template>
        </i18n-t>
      </template>
    </AuthHeading>

    <AuthOtpInput
      ref="otp"
      :challenge="auth.pending.value.challenge"
      :dev-code="auth.pending.value.devCode"
      :loading="verifying"
      :attempts-left="attemptsLeft"
      @complete="verify"
      @resend="resend"
    />

    <!-- Authenticator app not at hand: a recovery code (F16 M5) -->
    <div v-if="auth.pending.value.challenge.channel === 'totp' && !verifying" class="mt-5">
      <UButton v-if="!useRecovery" :label="t('profile.signin.useRecovery')" icon="i-lucide-life-buoy" color="neutral" variant="link" size="sm" class="px-0" @click="useRecovery = true" />
      <form v-else class="flex items-end gap-2" @submit.prevent="recoveryCode.trim() && verify(recoveryCode.trim())">
        <UFormField :label="t('profile.signin.recovery')" class="flex-1">
          <UInput v-model="recoveryCode" placeholder="xxxx-xxxx" autocomplete="off" class="w-full font-mono" dir="ltr" autofocus />
        </UFormField>
        <UButton type="submit" :label="t('profile.signin.recoveryUse')" color="neutral" :disabled="!/^[a-z0-9]{4}-?[a-z0-9]{4}$/i.test(recoveryCode.trim())" />
      </form>
    </div>

    <UButton
      v-if="verifying"
      :label="t('auth.otp.verifying')"
      color="neutral"
      size="xl"
      block
      loading
      class="mt-6"
    />
  </div>
</template>
