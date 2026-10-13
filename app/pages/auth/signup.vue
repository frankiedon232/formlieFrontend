<!--
  Create a workspace (manage.* only): Account (Google / Microsoft / Facebook or email) →
  Verify email → Workspace → new subdomain. Social signup skips the code step (provider-verified
  email, backend). The new workspace then enables more sign-in methods in Settings → Authentication.
  From the website (formalieSite docs/SIGNUP-FLOW.md, 2026-10-13): `?plan=` and `?period=` preselect a plan
  (Starter when missing, Enterprise goes to the website's enquiry). The choice is kept in sessionStorage so it
  survives a Google or Facebook round trip, and rides along on the hand-off: a paid plan's checkout opens once the
  workspace exists. The terms and privacy notice link to the website's legal pages.
-->
<script setup lang="ts">
import type { OtpChannel } from '#shared/types/auth'
import { isPaidSignup, signupPlanFrom, withSignupPlan, type SignupPlan } from '#shared/utils/billing/signupPlan'
import { enterpriseUrl, legalUrl } from '#shared/utils/urls/public'

definePageMeta({ layout: 'auth', auth: 'guest', manage: 'only' })

const { t, te } = useI18n()
const auth = useAuth()
const route = useRoute()
const tenant = useTenant()
const providers = computed(() => tenant.profile.value?.auth_providers ?? [])
const oauthNotice = computed(() => {
  if (route.query.oauth === 'unavailable')
    return t('auth.signup.oauthUnavailable', { provider: providerName(route.query.provider) })
  if (route.query.oauth === 'error' && typeof route.query.code === 'string')
    return te(`errors.${route.query.code}`) ? t(`errors.${route.query.code}`) : t('errors.FRM-AUTH-1023')
  return null
})
const { handle } = useErrorHandler()
const providerName = (value: unknown) => PROVIDER_NAMES[String(value ?? '') as SocialProvider] ?? String(value ?? '')

useHead({ title: () => t('auth.signup.title') })

// ── The plan picked on the website ────────────────────────────────────────────────────────────────────────────
const { siteUrl } = useRuntimeConfig().public
const CHOICE_KEY = 'formalie:signup-plan'
function rememberedChoice(): SignupPlan | null {
  try {
    const saved = sessionStorage.getItem(CHOICE_KEY)
    return saved ? signupPlanFrom(JSON.parse(saved) as Record<string, unknown>) : null
  } catch {
    return null
  }
}
const choice = ref<SignupPlan | null>(null)
onMounted(() => {
  const fromLink = route.query.plan !== undefined || route.query.period !== undefined
  if (!fromLink) {
    choice.value = rememberedChoice()
    return
  }
  const picked = signupPlanFrom(route.query)
  // Enterprise is arranged with Formalie, not signed up for here
  if (picked.plan === 'enterprise') {
    void navigateTo(enterpriseUrl(siteUrl), { external: true, replace: true })
    return
  }
  choice.value = picked
  try {
    sessionStorage.setItem(CHOICE_KEY, JSON.stringify(picked))
  } catch {
    // Private windows can refuse storage: the choice then lasts while this page is open
  }
})
const paidChoice = computed(() => (isPaidSignup(choice.value) ? choice.value : null))

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

// Back from Google, Microsoft or Facebook: the email is verified, so straight to the workspace step
const oauthChallenge = typeof route.query.oauth_challenge === 'string' ? route.query.oauth_challenge : null
if (oauthChallenge && import.meta.client) {
  onMounted(async () => {
    try {
      await auth.resumeOAuth(oauthChallenge)
      step.value = 2
    } catch (error) {
      handle(error)
    }
  })
}

function finish(url: string) {
  redirecting.value = true
  const next = withSignupPlan(url, choice.value)
  try {
    sessionStorage.removeItem(CHOICE_KEY)
  } catch {
    // Nothing kept
  }
  window.location.assign(next)
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <AuthHeading :title="t('auth.signup.title')" :description="t('auth.signup.desc')" class="!mb-2" />

    <div v-if="paidChoice" class="flex items-start gap-2.5 rounded-lg border border-default p-3 text-sm">
      <UIcon name="i-lucide-sparkles" class="mt-0.5 size-4 shrink-0 text-highlighted" />
      <span class="flex flex-col">
        <span class="font-medium text-highlighted">{{ t('auth.signup.planChosen', { plan: t(`billing.plan.${paidChoice.plan}.name`), period: t(`billing.periodName.${paidChoice.period}`) }) }}</span>
        <span class="text-xs text-muted">{{ t('auth.signup.planNext') }}</span>
      </span>
    </div>

    <UStepper
      :model-value="step"
      :items="steps"
      size="sm"
      color="neutral"
      disabled
      :ui="{ title: 'text-xs', description: 'hidden' }"
    />

    <template v-if="step === 0">
      <UAlert v-if="oauthNotice" color="neutral" icon="i-lucide-info" variant="subtle" :title="oauthNotice" />
      <AuthProviders :providers="providers" intent="signup" />
      <USeparator :label="t('auth.signup.orEmail')" :ui="{ label: 'text-xs text-muted' }" />
      <AuthSignupAccountStep @done="step = 1" />
      <i18n-t keypath="auth.signup.agree" tag="p" scope="global" class="text-center text-xs text-muted">
        <template #terms>
          <ULink :to="legalUrl(siteUrl, 'terms')" target="_blank" rel="noopener" class="underline underline-offset-2 hover:text-highlighted">{{ t('auth.signup.terms') }}</ULink>
        </template>
        <template #privacy>
          <ULink :to="legalUrl(siteUrl, 'privacy')" target="_blank" rel="noopener" class="underline underline-offset-2 hover:text-highlighted">{{ t('auth.signup.privacy') }}</ULink>
        </template>
      </i18n-t>
    </template>

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
