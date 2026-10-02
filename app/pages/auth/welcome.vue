<!-- Landing on a new workspace after signup: exchange the one-time ticket for a session. -->
<script setup lang="ts">
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
    // F4: onboarding wizard goes here.
    await navigateTo('/forms', { replace: true })
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
    <UEmpty
      v-else
      icon="i-lucide-link-2-off"
      :title="t('auth.welcome.failed')"
      :description="t('auth.welcome.failedDesc')"
      :actions="[{ label: t('auth.login.submit'), to: '/auth/login', color: 'neutral' }]"
      variant="naked"
    />
  </div>
</template>
