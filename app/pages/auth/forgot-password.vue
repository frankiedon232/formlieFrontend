<!-- Workspace host: email → code + new password (the workspace's password rules) → back to sign in. `?expired=1` when sign-in said the password expired. -->
<script setup lang="ts">
import type { FormSubmitEvent } from '@nuxt/ui'
import type { OtpChannel } from '#shared/types/auth'

definePageMeta({ layout: 'auth', auth: 'guest' })

const { t } = useI18n()
const route = useRoute()
const auth = useAuth()
const policy = computed(() => useTenant().profile.value?.password_policy)
const { handle } = useErrorHandler()
const { busy, run } = useBusy()
useHead({ title: () => t('auth.forgot.title') })

const emailSchema = computed(() => emailOnlySchema(t))
// Sign-in said the password expired: the email comes along (app state, never the address bar)
const emailState = reactive({ email: route.query.expired ? (useState<string>('auth:reset-email').value ?? '') : '' })
const expired = computed(() => !!route.query.expired)
const passwordSchema = computed(() => resetSchema(t, policy.value))
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

function leave() {
  auth.clearPending()
  navigateTo('/auth/login')
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
    <AuthHeading
      :title="t('auth.forgot.title')"
      :description="
        inReset && auth.pending.value
          ? t('auth.otp.desc', { destination: auth.pending.value.challenge.masked_destination })
          : t('auth.forgot.desc')
      "
      :back="t('auth.forgot.back')"
      workspace
      class="!mb-2"
      @back="leave"
    />

    <UAlert v-if="expired && !inReset" color="warning" variant="subtle" icon="i-lucide-clock-alert" :title="t('auth.forgot.expired')" :description="t('auth.forgot.expiredDesc')" />

    <UForm
      v-if="!inReset"
      :schema="emailSchema"
      :state="emailState"
      class="flex flex-col gap-4"
      @submit="sendCode"
    >
      <UFormField :label="t('auth.fields.email')" name="email" required>
        <UInput
          v-model="emailState.email"
          type="email"
          autocomplete="email"
          :placeholder="t('auth.fields.emailPlaceholder')"
          icon="i-lucide-mail"
          size="xl"
          class="w-full"
          autofocus
        />
      </UFormField>
      <UButton
        type="submit"
        :label="t('auth.forgot.send')"
        color="neutral"
        size="xl"
        block
        :loading="busy"
        class="justify-center font-semibold"
      />
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
          <AuthPasswordInput
            v-model="passwordState.password"
            autocomplete="new-password"
            size="xl"
            icon="i-lucide-lock-keyhole"
          />
          <AuthPasswordStrength :value="passwordState.password" :policy="policy" />
        </UFormField>
        <UFormField :label="t('auth.fields.confirmPassword')" name="confirm" required>
          <AuthPasswordInput
            v-model="passwordState.confirm"
            autocomplete="new-password"
            size="xl"
            icon="i-lucide-lock-keyhole"
          />
        </UFormField>
        <UButton
          type="submit"
          :label="t('auth.forgot.save')"
          color="neutral"
          size="xl"
          block
          :loading="saving"
        />
      </UForm>
    </template>
  </div>
</template>
