<!--
  Sign in. Workspace host: workspace chip, providers this tenant enabled, email + password → OTP.
  manage.*: "Continue to <last workspace>" or find your workspace by email.
-->
<script setup lang="ts">
import type { FormSubmitEvent } from '@nuxt/ui'

definePageMeta({ layout: 'auth', auth: 'guest', manage: true })

const { t } = useI18n()
const route = useRoute()
const tenant = useTenant()
const auth = useAuth()
const { busy, run, error } = useBusy()
const providerName = (value: unknown) => PROVIDER_NAMES[String(value ?? '') as SocialProvider] ?? String(value ?? '')

useHead({ title: () => t('auth.login.title') })

const profile = tenant.profile
const isManage = tenant.isManage
const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : undefined
const usesPassword = computed(() => profile.value?.auth_providers.includes('password') ?? true)
const hasSocial = computed(() => (profile.value?.auth_providers ?? []).some(p => p !== 'password'))

const schema = computed(() => (isManage.value ? emailOnlySchema(t) : loginSchema(t)))
const state = reactive({
  // An accepted invitation brings the address along in app state (F16 M2)
  email: typeof route.query.email === 'string' ? route.query.email : (useState<string>('auth:join-email').value ?? ''),
  password: '',
})

const notice = computed(() => {
  if (route.query.expired)
    return { color: 'warning' as const, icon: 'i-lucide-clock-alert', title: t('auth.login.expired') }
  if (route.query.oauth === 'unavailable') {
    return {
      color: 'neutral' as const,
      icon: 'i-lucide-info',
      title: t('auth.login.oauthUnavailable', { provider: providerName(route.query.provider) }),
    }
  }
  if (route.query.joined)
    return { color: 'success' as const, icon: 'i-lucide-party-popper', title: t('people.join.done') }
  if (route.query.reset)
    return { color: 'success' as const, icon: 'i-lucide-circle-check', title: t('auth.login.passwordReset') }
  return null
})

async function onSubmit(event: FormSubmitEvent<{ email: string; password?: string }>) {
  if (isManage.value) {
    const ok = await run(async () => {
      await auth.findWorkspace(event.data.email)
      return true
    })
    if (ok) await navigateTo('/auth/find-workspace')
    return
  }
  const ok = await run(async () => {
    await auth.login(event.data.email, event.data.password ?? '', redirect)
    return true
  })
  if (ok) await navigateTo('/auth/otp')
  // The workspace's password rules ask for a new one (Settings → Security): straight to setting it
  else if (error.value?.code === 'FRM-AUTH-1015') {
    useState<string>('auth:reset-email').value = event.data.email
    await navigateTo({ path: '/auth/forgot-password', query: { expired: '1' } })
  }
}
</script>

<template>
  <div>
    <AuthHeading
      :title="isManage ? t('auth.login.manageTitle') : t('auth.login.heading')"
      :description="
        isManage ? t('auth.login.manageDesc') : t('auth.login.desc', { workspace: profile?.name ?? '' })
      "
      workspace
    />

    <UAlert
      v-if="notice"
      :color="notice.color"
      :icon="notice.icon"
      variant="subtle"
      :title="notice.title"
      class="mb-6"
    />

    <!-- manage.*: one-click back to the last workspace -->
    <NuxtLink
      v-if="isManage && tenant.lastWorkspace.value"
      :to="tenant.hostUrl(tenant.lastWorkspace.value.subdomain, '/auth/login')"
      external
      class="group mb-6 flex items-center gap-3 rounded-xl p-3 ring-1 ring-default transition hover:bg-elevated/50 hover:ring-accented focus-visible:outline-2 focus-visible:outline-primary"
    >
      <UAvatar :alt="tenant.lastWorkspace.value.name" size="md" class="bg-inverted text-inverted" />
      <span class="min-w-0 flex-1">
        <span class="block truncate font-medium text-highlighted">{{ tenant.lastWorkspace.value.name }}</span>
        <span class="block truncate font-mono text-xs text-muted">
          {{ tenant.lastWorkspace.value.subdomain }}.{{ $config.public.rootDomain }}
        </span>
      </span>
      <span class="text-sm font-medium text-highlighted">{{ t('auth.login.continue') }}</span>
      <UIcon
        name="i-lucide-arrow-right"
        class="size-4 text-muted transition group-hover:translate-x-0.5 rtl:rotate-180"
      />
    </NuxtLink>

    <template v-if="!isManage && profile">
      <AuthProviders :providers="profile.auth_providers" />
      <USeparator
        v-if="usesPassword && hasSocial"
        :label="t('auth.or')"
        class="my-6"
        :ui="{ label: 'text-xs text-muted' }"
      />
    </template>

    <UForm
      v-if="isManage || usesPassword"
      :schema="schema"
      :state="state"
      class="flex flex-col gap-5"
      @submit="onSubmit"
    >
      <UFormField :label="t('auth.fields.email')" name="email" size="lg">
        <UInput
          v-model="state.email"
          type="email"
          autocomplete="email"
          icon="i-lucide-mail"
          :placeholder="t('auth.fields.emailPlaceholder')"
          size="xl"
          class="w-full"
          autofocus
        />
      </UFormField>

      <UFormField v-if="!isManage" :label="t('auth.fields.password')" name="password" size="lg">
        <template #hint>
          <ULink to="/auth/forgot-password" class="text-sm font-medium text-muted hover:text-highlighted">
            {{ t('auth.login.forgot') }}
          </ULink>
        </template>
        <AuthPasswordInput
          v-model="state.password"
          autocomplete="current-password"
          size="xl"
          icon="i-lucide-lock-keyhole"
        />
      </UFormField>

      <UButton type="submit" color="neutral" size="xl" block class="group mt-1 font-semibold" :loading="busy">
        {{ isManage ? t('auth.login.findWorkspace') : t('auth.login.submit') }}
        <UIcon
          v-if="!busy"
          name="i-lucide-arrow-right"
          class="size-5 transition group-hover:translate-x-0.5 rtl:rotate-180 rtl:group-hover:-translate-x-0.5"
        />
      </UButton>
    </UForm>

    <p class="mt-6 flex items-center justify-center gap-1.5 text-xs text-muted">
      <UIcon name="i-lucide-shield-check" class="size-3.5 shrink-0" />
      {{ t('auth.login.secureNote') }}
    </p>

    <USeparator class="my-8" />

    <p class="text-center text-sm text-muted">
      <template v-if="isManage">
        {{ t('auth.login.noWorkspace') }}
        <ULink to="/auth/signup" class="font-semibold text-highlighted underline-offset-4 hover:underline">
          {{ t('auth.login.createWorkspace') }}
        </ULink>
      </template>
      <template v-else>
        {{ t('auth.login.wrongWorkspace') }}
        <ULink
          :to="tenant.manageUrl('/auth/login')"
          external
          class="font-semibold text-highlighted underline-offset-4 hover:underline"
        >
          {{ t('auth.login.findWorkspace') }}
        </ULink>
      </template>
    </p>
  </div>
</template>
