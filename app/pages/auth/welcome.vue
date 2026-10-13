<!--
  Landing on a new workspace after signup: exchange the one-time ticket for a session. A paid plan picked on the
  website rides along (`&plan=&period=`, formalieSite docs/SIGNUP-FLOW.md): Settings → Plans opens its payment
  first; otherwise the set-up wizard (F5).
-->
<script setup lang="ts">
import { isPaidSignup, signupPlanFrom } from '#shared/utils/billing/signupPlan'

definePageMeta({ layout: 'auth', auth: false })

const { t } = useI18n()
const route = useRoute()
const auth = useAuth()
const { handle } = useErrorHandler()
const failed = ref(false)
useHead({ title: () => t('auth.welcome.title') })

onMounted(async () => {
  const ticket = typeof route.query.ticket === 'string' ? route.query.ticket : ''
  try {
    if (!ticket) throw new ApiError('FRM-AUTH-1010', 'Invalid token.')
    await auth.exchangeTicket(ticket)
    const choice = signupPlanFrom(route.query)
    if (route.query.plan !== undefined && isPaidSignup(choice)) await navigateTo({ path: '/settings/plans', query: { plan: choice.plan, period: choice.period } }, { replace: true })
    // A brand-new workspace continues with the set-up wizard (F5).
    else await navigateTo('/onboarding', { replace: true })
  } catch (error) {
    handle(error)
    failed.value = true
  }
})
</script>

<template>
  <div class="flex flex-col items-center gap-4 text-center">
    <template v-if="!failed">
      <UIcon name="i-lucide-loader-circle" class="size-8 animate-spin text-muted" />
      <h1 class="text-xl font-semibold text-highlighted">{{ t('auth.welcome.title') }}</h1>
      <p class="text-sm text-muted">{{ t('auth.welcome.desc') }}</p>
    </template>
    <AppEmpty
      v-else
      icon="i-lucide-link-2-off"
      :title="t('auth.welcome.failed')"
      :description="t('auth.welcome.failedDesc')"
      :actions="[{ label: t('auth.login.submit'), to: '/auth/login', color: 'neutral' }]"
      variant="naked"
    />
  </div>
</template>
