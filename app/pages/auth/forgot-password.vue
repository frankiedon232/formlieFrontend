<!-- Workspace host: email → code + new password (same policy as signup) → back to sign in. -->
<script setup lang="ts">
import type { FormSubmitEvent } from '@nuxt/ui'
import type { OtpChannel } from '#shared/types/auth'

definePageMeta({ layout: 'auth', auth: 'guest' })

const { t } = useI18n()
const auth = useAuth()
const { handle } = useErrorHandler()
const { busy, run } = useBusy()
useHead({ title: () => t('auth.forgot.title') })

const emailSchema = computed(() => emailOnlySchema(t))
const emailState = reactive({ email: '' })
const passwordSchema = computed(() => resetSchema(t))
const passwordState = reactive({ password: '', confirm: '' })
const code = ref('')
const attemptsLeft = ref<number | null>(null)
const otp = useTemplateRef<{ reset: () => void }>('otp')
const saving = ref(false)

const inReset = computed(() => auth.pending.value?.purpose === 'reset')

async function sendCode(event: FormSubmitEvent<typeof emailState>) {
  await run(() => auth.forgotPassword(event.data.email))
}

async function save(event: FormSubmitEvent<typeof passwordState>) {
  if (!/^\d{6}$/.test(code.value)) {
    handle(new ApiError('FRM-AUTH-1003', 'Invalid or expired code.'))
    return
  }
  saving.value = true
  try {
    await auth.resetPassword(code.value, event.data.password)
    await navigateTo({ path: '/auth/login', query: { reset: '1' } })
  } catch (error) {
    const normalised = handle(error)
    const left = normalised.details.find(detail => detail.field === 'attempts_left')
    attemptsLeft.value = left ? Number(left.message) : null
    code.value = ''
    otp.value?.reset()
  } finally {
    saving.value = false
  }
}

async function resend(channel?: OtpChannel) {
  try {
    await auth.resend(channel)
  } catch (error) {
    handle(error)
  }
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <div>
      <UButton
        icon="i-lucide-arrow-left"
        :label="t('auth.forgot.back')"
        to="/auth/login"
        color="neutral"
        variant="link"
        class="mb-4 px-0 rtl:[&_svg]:rotate-180"
        @click="auth.clearPending()"
      />
      <h1 class="text-2xl font-semibold tracking-tight text-highlighted">{{ t('auth.forgot.title') }}</h1>
      <p class="mt-1 text-sm text-muted">
        {{
          inReset && auth.pending.value
            ? t('auth.otp.desc', { destination: auth.pending.value.challenge.masked_destination })
            : t('auth.forgot.desc')
        }}
      </p>
    </div>

    <UForm
      v-if="!inReset"
      :schema="emailSchema"
      :state="emailState"
      class="flex flex-col gap-4"
      @submit="sendCode"
    >
      <UFormField :label="t('auth.fields.email')" name="email" required>
        <UInput v-model="emailState.email" type="email" autocomplete="email" class="w-full" autofocus />
      </UFormField>
      <UButton type="submit" :label="t('auth.forgot.send')" color="neutral" size="lg" block :loading="busy" />
    </UForm>

    <template v-else-if="auth.pending.value">
      <AuthOtpInput
        ref="otp"
        :challenge="auth.pending.value.challenge"
        :dev-code="auth.pending.value.devCode"
        :attempts-left="attemptsLeft"
        @complete="value => (code = value)"
        @resend="resend"
      />
      <UForm :schema="passwordSchema" :state="passwordState" class="flex flex-col gap-4" @submit="save">
        <UFormField :label="t('auth.fields.newPassword')" name="password" required>
          <AuthPasswordInput v-model="passwordState.password" autocomplete="new-password" />
          <AuthPasswordStrength :value="passwordState.password" />
        </UFormField>
        <UFormField :label="t('auth.fields.confirmPassword')" name="confirm" required>
          <AuthPasswordInput v-model="passwordState.confirm" autocomplete="new-password" />
        </UFormField>
        <UButton
          type="submit"
          :label="t('auth.forgot.save')"
          color="neutral"
          size="lg"
          block
          :loading="saving"
        />
      </UForm>
    </template>
  </div>
</template>
