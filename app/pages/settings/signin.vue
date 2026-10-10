<!--
  Settings → Sign-in (F14 M3): the ways people sign in (only these show on the workspace sign-in page),
  single sign-on with the company's identity provider (Okta and others, owner 2026-10-10; saves on its own),
  the one-time code every sign-in asks for (by email; text message optional), how long it lasts, how many tries, and the email
  domains allowed to sign in. A live miniature of the sign-in page sits beside it. The server refuses a
  domain list without the admin's own domain (FRM-AUTH-1017); the page says so before saving.
-->
<script setup lang="ts">
import { isEmailDomain, signinSchema } from '#shared/utils/settings/schemas'

definePageMeta({ breadcrumb: 'settings.nav.signin' })
const { t } = useI18n()
useHead({ title: () => t('settings.nav.signin') })
const form = useSettingsForm('signin', { schema: signinSchema })
const { draft } = form
const store = useWorkspaceSettings()
const session = useSession()

const expiries = computed(() => ([5, 10, 15] as const).map(value => ({ value, label: t('settings.signin.minutes', { n: value }, value) })))
const attempts = computed(() => ([3, 5, 10] as const).map(value => ({ value, label: t('settings.signin.tries', { n: value }, value) })))

// Allowed domains: typed as people like ("@Example.com"), kept tidy
const domains = computed({
  get: () => draft.value?.allowed_domains ?? [],
  set: list => draft.value && (draft.value.allowed_domains = [...new Set(list.map(item => item.trim().toLowerCase().replace(/^@/, '')).filter(Boolean))]),
})
const badDomains = computed(() => domains.value.filter(item => !isEmailDomain(item)))
const ownDomain = computed(() => session.user.value?.email.split('@').pop()?.toLowerCase() ?? '')
const ownMissing = computed(() => !!domains.value.length && !!ownDomain.value && !domains.value.some(item => ownDomain.value === item || ownDomain.value.endsWith(`.${item}`)))
const addOwn = () => (domains.value = [...domains.value, ownDomain.value])

const brand = computed(() => store.settings.value?.branding)
const name = computed(() => store.settings.value?.company.display_name ?? '')
</script>

<template>
  <SettingsPage id="settings-signin" :title="t('settings.nav.signin')" :subtitle="t('settings.desc.signin')" icon="i-lucide-log-in" :form="{ dirty: form.dirty.value, saving: form.saving.value, updated: form.updated.value }" @save="form.save" @discard="form.discard">
    <AppEmpty v-if="form.failed.value && !draft" icon="i-lucide-cloud-off" :title="t('settings.loadFailed')" :actions="[{ label: t('common.retry'), icon: 'i-lucide-refresh-cw', color: 'neutral', variant: 'outline', onClick: () => form.reload() }]" />
    <div v-else-if="!draft" class="flex flex-col gap-6"><USkeleton v-for="n in 3" :key="n" class="h-36 rounded-lg" /></div>
    <div v-else class="grid gap-8 2xl:grid-cols-[minmax(0,1fr)_22rem]">
      <div class="flex min-w-0 flex-col gap-6">
        <SettingsBlock :title="t('settings.signin.methods')" :description="t('settings.signin.methodsHint')" icon="i-lucide-log-in">
          <SettingsSigninMethods v-model="draft.methods" />
          <p class="flex items-start gap-1.5 text-xs text-muted"><UIcon name="i-lucide-info" class="mt-0.5 size-3.5 shrink-0" />{{ t('settings.signin.providersNote') }}</p>
        </SettingsBlock>

        <SettingsBlock :title="t('settings.sso.title')" :description="t('settings.sso.titleHint')" icon="i-lucide-building-2">
          <SettingsSigninSso />
        </SettingsBlock>

        <SettingsBlock :title="t('settings.signin.codes')" :description="t('settings.signin.codesHint')" icon="i-lucide-shield-check">
          <div class="flex items-center gap-3 rounded-lg border border-default bg-elevated/40 p-3">
            <span class="flex size-9 shrink-0 items-center justify-center rounded-lg bg-inverted text-inverted"><UIcon name="i-lucide-shield-check" class="size-4.5" /></span>
            <span class="flex min-w-0 flex-1 flex-col gap-0.5">
              <span class="text-sm font-medium text-highlighted">{{ t('settings.signin.always') }}</span>
              <span class="text-xs text-muted">{{ t('settings.signin.alwaysHint') }}</span>
            </span>
            <UBadge :label="t('settings.signin.alwaysOn')" color="neutral" variant="outline" icon="i-lucide-lock" class="shrink-0" />
          </div>

          <div class="flex flex-col divide-y divide-default rounded-lg border border-default">
            <div class="flex items-center gap-3 px-3 py-2.5">
              <UIcon name="i-lucide-mail" class="size-4 shrink-0 text-muted" />
              <span class="flex min-w-0 flex-1 flex-col"><span class="text-sm text-highlighted">{{ t('settings.signin.email') }}</span><span class="text-xs text-muted">{{ t('settings.signin.emailHint') }}</span></span>
              <USwitch :model-value="true" disabled color="neutral" :aria-label="t('settings.signin.email')" />
            </div>
            <div class="flex items-center gap-3 px-3 py-2.5">
              <UIcon name="i-lucide-message-square" class="size-4 shrink-0 text-muted" />
              <span class="flex min-w-0 flex-1 flex-col"><span class="text-sm text-highlighted">{{ t('settings.signin.sms') }}</span><span class="text-xs text-muted">{{ t('settings.signin.smsHint') }}</span></span>
              <USwitch v-model="draft.code.sms" color="neutral" :aria-label="t('settings.signin.sms')" />
            </div>
          </div>

          <div class="grid gap-4 sm:grid-cols-2">
            <UFormField :label="t('settings.signin.expiry')" :description="t('settings.signin.expiryHint')">
              <USelect v-model="draft.code.expiry_minutes" :items="expiries" class="w-full" />
            </UFormField>
            <UFormField :label="t('settings.signin.attempts')" :description="t('settings.signin.attemptsHint')">
              <USelect v-model="draft.code.max_attempts" :items="attempts" class="w-full" />
            </UFormField>
          </div>
        </SettingsBlock>

        <SettingsBlock :title="t('settings.signin.domains')" :description="t('settings.signin.domainsHint')" icon="i-lucide-at-sign">
          <UFormField :label="t('settings.signin.domainsLabel')" :help="domains.length ? undefined : t('settings.signin.anyDomain')" :error="badDomains.length ? t('settings.signin.badDomain', { list: badDomains.join(', ') }) : undefined">
            <UInputTags v-model="domains" :placeholder="t('settings.signin.domainPlaceholder')" icon="i-lucide-at-sign" class="w-full" :add-on-blur="true" :add-on-paste="true" />
          </UFormField>
          <UAlert v-if="ownMissing" color="warning" variant="subtle" icon="i-lucide-triangle-alert" :title="t('settings.signin.ownMissing', { domain: ownDomain })" :description="t('settings.signin.ownMissingDesc')" :actions="[{ label: t('settings.signin.addOwn', { domain: ownDomain }), icon: 'i-lucide-plus', color: 'neutral', variant: 'outline', onClick: addOwn }]" />
        </SettingsBlock>
      </div>

      <aside class="w-full max-w-xl 2xl:sticky 2xl:top-0 2xl:max-w-none 2xl:self-start">
        <div class="flex flex-col gap-3 rounded-xl border border-default bg-elevated/30 p-4">
          <SettingsSigninPreview :name="name" :logo="brand?.logo_url ?? null" :logo-dark="brand?.logo_dark_url ?? null" :message="brand?.signin_message ?? null" :color="brand?.brand_color ?? null" :favicon="brand?.favicon_url ?? null" :methods="draft.methods" />
          <ul class="flex flex-col gap-1.5 text-xs text-muted">
            <li class="flex items-start gap-1.5"><UIcon name="i-lucide-log-in" class="mt-0.5 size-3.5 shrink-0" />{{ t('settings.signin.sumMethods', { n: draft.methods.length }, draft.methods.length) }}</li>
            <li class="flex items-start gap-1.5"><UIcon name="i-lucide-shield-check" class="mt-0.5 size-3.5 shrink-0" />{{ t('settings.signin.sumCode', { minutes: draft.code.expiry_minutes, tries: draft.code.max_attempts }) }}</li>
            <li class="flex items-start gap-1.5"><UIcon name="i-lucide-at-sign" class="mt-0.5 size-3.5 shrink-0" />{{ domains.length ? t('settings.signin.sumDomains', { list: domains.join(', ') }) : t('settings.signin.anyDomain') }}</li>
          </ul>
        </div>
      </aside>
    </div>
  </SettingsPage>
</template>
