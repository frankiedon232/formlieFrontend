<!--
  Sign in. Workspace host: tenant branding, email + password, only the providers this tenant
  enabled → OTP. manage.*: "Continue to <last workspace>" or find your workspace by email.
-->
<script setup lang="ts">
import type { FormSubmitEvent } from '@nuxt/ui'

definePageMeta({ layout: 'auth', auth: 'guest', manage: true })

const { t } = useI18n()
const route = useRoute()
const tenant = useTenant()
const auth = useAuth()
const { busy, run } = useBusy()
useHead({ title: () => t('auth.login.title') })

const profile = tenant.profile
const isManage = tenant.isManage
const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : undefined
const usesPassword = computed(() => profile.value?.auth_providers.includes('password') ?? true)

const schema = computed(() => (isManage.value ? emailOnlySchema(t) : loginSchema(t)))
const state = reactive({
  email: typeof route.query.email === 'string' ? route.query.email : '',
  password: '',
})

const notice = computed(() => {
  if (route.query.expired) return { color: 'warning' as const, title: t('auth.login.expired') }
  if (route.query.oauth === 'unavailable') {
    return {
      color: 'neutral' as const,
      title: t('auth.login.oauthUnavailable', { provider: String(route.query.provider ?? '') }),
    }
  }
  if (route.query.reset) return { color: 'success' as const, title: t('auth.login.passwordReset') }
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
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <div>
      <h1 class="text-2xl font-semibold tracking-tight text-highlighted">
        {{ isManage ? t('auth.login.manageTitle') : t('auth.login.title') }}
      </h1>
      <p class="mt-1 text-sm text-muted">
        {{ isManage ? t('auth.login.manageDesc') : t('auth.login.desc', { workspace: profile?.name ?? '' }) }}
      </p>
    </div>

    <UAlert v-if="notice" :color="notice.color" variant="subtle" :title="notice.title" icon="i-lucide-info" />

    <UCard v-if="isManage && tenant.lastWorkspace.value" :ui="{ body: 'flex items-center gap-3 p-4 sm:p-4' }">
      <UAvatar :alt="tenant.lastWorkspace.value.name" size="md" />
      <div class="min-w-0 flex-1">
        <p class="truncate font-medium text-highlighted">{{ tenant.lastWorkspace.value.name }}</p>
        <p class="truncate text-xs text-muted">
          {{ tenant.lastWorkspace.value.subdomain }}.{{ $config.public.rootDomain }}
        </p>
      </div>
      <UButton
        :label="t('auth.login.continue')"
        trailing-icon="i-lucide-arrow-right"
        color="neutral"
        :to="tenant.hostUrl(tenant.lastWorkspace.value.subdomain, '/auth/login')"
        external
      />
    </UCard>

    <AuthProviders v-if="!isManage && profile" :providers="profile.auth_providers" />
    <USeparator
      v-if="!isManage && usesPassword && (profile?.auth_providers.length ?? 0) > 1"
      :label="t('auth.or')"
    />

    <UForm
      v-if="isManage || usesPassword"
      :schema="schema"
      :state="state"
      class="flex flex-col gap-4"
      @submit="onSubmit"
    >
      <UFormField :label="t('auth.fields.email')" name="email" required>
        <UInput v-model="state.email" type="email" autocomplete="email" class="w-full" autofocus />
      </UFormField>

      <UFormField v-if="!isManage" :label="t('auth.fields.password')" name="password" required>
        <template #hint>
          <ULink to="/auth/forgot-password" class="text-xs text-muted hover:text-highlighted">
            {{ t('auth.login.forgot') }}
          </ULink>
        </template>
        <AuthPasswordInput v-model="state.password" autocomplete="current-password" />
      </UFormField>

      <UButton
        type="submit"
        :label="isManage ? t('auth.login.findWorkspace') : t('auth.login.submit')"
        color="neutral"
        size="lg"
        block
        :loading="busy"
      />
    </UForm>

    <p class="text-center text-sm text-muted">
      <template v-if="isManage">
        {{ t('auth.login.noWorkspace') }}
        <ULink to="/auth/signup" class="font-medium text-highlighted">{{
          t('auth.login.createWorkspace')
        }}</ULink>
      </template>
      <template v-else>
        {{ t('auth.login.wrongWorkspace') }}
        <ULink :to="tenant.manageUrl('/auth/login')" external class="font-medium text-highlighted">
          {{ t('auth.login.findWorkspace') }}
        </ULink>
      </template>
    </p>
  </div>
</template>
