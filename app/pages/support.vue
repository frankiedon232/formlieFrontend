<!--
  Formalie support lands here (B16): `/support#ticket=…` from the platform admin. The ticket is read
  from the address's fragment and the fragment is cleared at once (it never reaches a server log or the
  history), then redeemed for a support session (memory only, no refresh cookie) and the dashboard
  opens. A wrong, used or expired ticket, and a session that ended, say so with the next step.
-->
<script setup lang="ts">
definePageMeta({ layout: 'auth', auth: false })

const { t } = useI18n()
const route = useRoute()
const auth = useAuth()
const { normalise } = useErrorHandler()
useHead({ title: () => t('support.page.title') })

type Ended = 'off' | 'time' | 'signed_out'
const ENDED: Ended[] = ['off', 'time', 'signed_out']
const ended = computed<Ended | null>(() => (ENDED.includes(route.query.ended as Ended) ? (route.query.ended as Ended) : null))
const failed = ref<'invalid' | 'error' | null>(null)

// Read the ticket, then remove it from the address before anything else happens
const ticket = import.meta.client ? supportTicketFromHash(window.location.hash) : null
if (import.meta.client && window.location.hash) history.replaceState(history.state, '', window.location.pathname + window.location.search)

onMounted(async () => {
  if (ended.value) return
  if (!ticket) {
    failed.value = 'invalid'
    return
  }
  try {
    await auth.redeemSupport(ticket)
    await navigateTo('/dashboard', { replace: true })
  } catch (error) {
    const code = normalise(error).code
    failed.value = code === 'FRM-AUTH-1010' || code === 'FRM-GEN-1002' ? 'invalid' : 'error'
  }
})

const state = computed(() => {
  if (ended.value) return { icon: ended.value === 'signed_out' ? 'i-lucide-log-out' : 'i-lucide-clock-alert', title: t(`support.page.ended.${ended.value}`), description: t('support.page.endedDesc'), tone: 'neutral' as const }
  if (failed.value === 'invalid') return { icon: 'i-lucide-link-2-off', title: t('support.page.invalid'), description: t('support.page.invalidDesc'), tone: 'error' as const }
  if (failed.value === 'error') return { icon: 'i-lucide-cloud-off', title: t('support.page.error'), description: t('support.page.errorDesc'), tone: 'error' as const }
  return null
})
</script>

<template>
  <div class="flex flex-col items-center gap-4 text-center">
    <AppEmpty v-if="state" :icon="state.icon" :title="state.title" :description="state.description" :tone="state.tone" variant="naked" :actions="[{ label: t('auth.login.submit'), to: '/auth/login', color: 'neutral', variant: 'outline' }]" />
    <template v-else>
      <UIcon name="i-lucide-loader-circle" class="size-8 animate-spin text-muted" />
      <h1 class="text-xl font-semibold text-highlighted">{{ t('support.page.title') }}</h1>
      <p class="text-sm text-muted" role="status">{{ t('support.page.desc') }}</p>
    </template>
  </div>
</template>
