<!-- Create a workspace (manage.* only): Account → Verify email → Workspace → new subdomain. -->
<script setup lang="ts">
import type { OtpChannel } from '#shared/types/auth'

definePageMeta({ layout: 'auth', auth: 'guest', manage: 'only' })

const { t } = useI18n()
const auth = useAuth()
const { handle } = useErrorHandler()
useHead({ title: () => t('auth.signup.title') })

const step = ref(0)
const steps = computed(() => [
  { title: t('auth.signup.stepAccount'), icon: 'i-lucide-user' },
  { title: t('auth.signup.stepVerify'), icon: 'i-lucide-mail-check' },
  { title: t('auth.signup.stepWorkspace'), icon: 'i-lucide-building-2' },
])

const otp = useTemplateRef<{ reset: () => void }>('otp')
const verifying = ref(false)
const attemptsLeft = ref<number | null>(null)
const redirecting = ref(false)

async function verify(code: string) {
  verifying.value = true
  try {
    await auth.verify(code)
    step.value = 2
  } catch (error) {
    const normalised = handle(error)
    const left = normalised.details.find(detail => detail.field === 'attempts_left')
    attemptsLeft.value = left ? Number(left.message) : null
    otp.value?.reset()
  } finally {
    verifying.value = false
  }
}

async function resend(channel?: OtpChannel) {
  try {
    await auth.resend(channel)
  } catch (error) {
    handle(error)
  }
}

function finish(url: string) {
  redirecting.value = true
  window.location.assign(url)
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <AuthHeading :title="t('auth.signup.title')" :description="t('auth.signup.desc')" class="!mb-2" />

    <UStepper
      :model-value="step"
      :items="steps"
      size="sm"
      color="neutral"
      disabled
      :ui="{ title: 'text-xs', description: 'hidden' }"
    />

    <AuthSignupAccountStep v-if="step === 0" @done="step = 1" />

    <div v-else-if="step === 1 && auth.pending.value" class="flex flex-col gap-4">
      <p class="text-sm text-muted">
        {{ t('auth.otp.desc', { destination: auth.pending.value.challenge.masked_destination }) }}
      </p>
      <AuthOtpInput
        ref="otp"
        :challenge="auth.pending.value.challenge"
        :dev-code="auth.pending.value.devCode"
        :loading="verifying"
        :attempts-left="attemptsLeft"
        @complete="verify"
        @resend="resend"
      />
      <UButton
        :label="t('auth.signup.changeEmail')"
        color="neutral"
        variant="link"
        class="self-start px-0"
        @click="step = 0"
      />
    </div>

    <AuthSignupWorkspaceStep v-else-if="step === 2 && !redirecting" @done="finish" />

    <div v-if="redirecting" class="flex items-center gap-2 text-sm text-muted">
      <UIcon name="i-lucide-loader-circle" class="size-4 animate-spin" />
      {{ t('auth.signup.redirecting') }}
    </div>

    <p class="text-center text-sm text-muted">
      {{ t('auth.signup.haveAccount') }}
      <ULink to="/auth/login" class="font-medium text-highlighted">{{ t('auth.login.submit') }}</ULink>
    </p>
  </div>
</template>
