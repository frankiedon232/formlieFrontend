<!-- Second step of every login (SECURITY-PROTOCOL §7): 6-digit code → tokens → portal. -->
<script setup lang="ts">
import type { OtpChannel } from '#shared/types/auth'

definePageMeta({ layout: 'auth', auth: 'guest' })

const { t } = useI18n()
const auth = useAuth()
const { handle } = useErrorHandler()
useHead({ title: () => t('auth.otp.title') })

// The challenge lives in memory only: reloading this page starts over (by design).
if (!auth.pending.value || auth.pending.value.purpose !== 'login') await navigateTo('/auth/login')

const otp = useTemplateRef<{ reset: () => void }>('otp')
const verifying = ref(false)
const attemptsLeft = ref<number | null>(null)

async function verify(code: string) {
  if (verifying.value) return
  verifying.value = true
  try {
    const redirect = auth.pending.value?.redirect
    await auth.verify(code)
    await navigateTo(redirect || '/forms', { replace: true })
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
  <div v-if="auth.pending.value" class="flex flex-col gap-6">
    <div>
      <UButton
        icon="i-lucide-arrow-left"
        :label="t('common.back')"
        color="neutral"
        variant="link"
        class="mb-4 px-0 rtl:[&_svg]:rotate-180"
        @click="back"
      />
      <h1 class="text-2xl font-semibold tracking-tight text-highlighted">{{ t('auth.otp.title') }}</h1>
      <p class="mt-1 text-sm text-muted">
        {{ t('auth.otp.desc', { destination: auth.pending.value.challenge.masked_destination }) }}
      </p>
    </div>

    <AuthOtpInput
      ref="otp"
      :challenge="auth.pending.value.challenge"
      :dev-code="auth.pending.value.devCode"
      :loading="verifying"
      :attempts-left="attemptsLeft"
      @complete="verify"
      @resend="resend"
    />

    <UButton v-if="verifying" :label="t('auth.otp.verifying')" color="neutral" size="lg" block loading />
  </div>
</template>
