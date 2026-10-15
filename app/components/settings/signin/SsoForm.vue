<!--
  Setting up single sign-on with one provider, in three short steps: (1) copy Formalie's values into the provider,
  (2) paste the provider's values here (OIDC: issuer, client ID and secret; SAML: two tabs, Metadata address or Enter
  by hand, owner 2026-10-15; Google Workspace opens on Enter by hand, as Google gives no metadata address), (3) who uses
  it (button text, email domains, required, new accounts and their role). The active tab decides what is saved.
  The client secret is write-only: a saved one shows as set, typing replaces it.
-->
<script setup lang="ts">
import { z } from 'zod'
import { SAML_PROVIDERS_EXAMPLES, SSO_ICONS, SSO_NAMES, SSO_PROTOCOL, ssoSamlByHand, ssoSaveRequest, type SsoConnection, type SsoFormValues, type SsoProvider, type SsoServiceProvider, type SsoSettings } from '#shared/types/sso'
import { isEmailDomain } from '#shared/utils/settings/schemas'

const props = defineProps<{ provider: SsoProvider; connection: SsoConnection | null; serviceProvider: SsoServiceProvider }>()
const emit = defineEmits<{ saved: [value: SsoSettings]; cancel: [] }>()
const { t } = useI18n()
const api = useApi()
const toast = useToast()
const session = useSession()
const { roles, refresh } = useRoles()
onMounted(() => refresh())

const protocol = computed(() => SSO_PROTOCOL[props.provider])
const saved = props.connection
const ownDomain = session.user.value?.email.split('@').pop()?.toLowerCase() ?? ''
const state = reactive<SsoFormValues>({
  label: saved?.label ?? SSO_NAMES[props.provider],
  metadata_url: saved?.saml.metadata_url ?? '',
  entity_id: saved?.saml.entity_id ?? '',
  sso_url: saved?.saml.sso_url ?? '',
  certificate: saved?.saml.certificate ?? '',
  issuer: saved?.oidc.issuer ?? '',
  client_id: saved?.oidc.client_id ?? '',
  client_secret: '',
  domains: saved?.domains ?? (ownDomain ? [ownDomain] : []),
  enforce: saved?.enforce ?? false,
  auto_create: saved?.auto_create ?? false,
  default_role: saved?.default_role ?? 'member',
})
// SAML: the metadata address or the values by hand, as two tabs; a different choice before saving starts on its own default
const samlByHand = ref(ssoSamlByHand(props.provider, saved))
watch(() => props.provider, provider => (samlByHand.value = ssoSamlByHand(provider, props.connection)))
const samlTabs = computed(() => [
  { value: 'metadata', label: t('settings.sso.tabMetadata'), icon: 'i-lucide-link' },
  { value: 'manual', label: t('settings.sso.tabByHand'), icon: 'i-lucide-pencil-line' },
])
const samlTab = computed({
  get: () => (samlByHand.value ? 'manual' : 'metadata'),
  set: value => (samlByHand.value = value === 'manual'),
})

// Only the fields that will be sent are checked: the active SAML tab, or OpenID Connect's issuer. A wrong value left on
// the other tab is never sent, so it never blocks saving from a field nobody can see.
const https = (message: string, checked: () => boolean) => z.string().trim().refine(value => !checked() || !value || /^https:\/\/\S+$/i.test(value), message)
const schema = computed(() =>
  z.object({
    label: z.string().trim().min(1, t('settings.sso.labelRequired')).max(40),
    metadata_url: https(t('settings.sso.httpsOnly'), () => protocol.value === 'saml' && !samlByHand.value),
    sso_url: https(t('settings.sso.httpsOnly'), () => protocol.value === 'saml' && samlByHand.value),
    issuer: https(t('settings.sso.httpsOnly'), () => protocol.value === 'oidc'),
    domains: z.array(z.string()).refine(list => list.every(isEmailDomain), t('settings.sso.badDomain')).refine(list => !state.enforce || list.length > 0, t('settings.sso.domainsForRequired')),
  }),
)

// Typed as people like ("@Example.com"), kept tidy
const domains = computed({
  get: () => state.domains,
  set: list => (state.domains = [...new Set(list.map(item => item.trim().toLowerCase().replace(/^@/, '')).filter(Boolean))]),
})
const roleItems = computed(() => roles.value.filter(role => role.built_in !== 'owner').map(role => ({ value: role.id, label: role.name })))
const lockOut = computed(() => state.enforce && !!ownDomain && state.domains.some(item => ownDomain === item || ownDomain.endsWith(`.${item}`)))

/** What to copy into the provider, for its protocol. */
const copyValues = computed(() =>
  protocol.value === 'oidc'
    ? [
        { label: t('settings.sso.redirectUri'), value: props.serviceProvider.redirect_uri },
        { label: t('settings.sso.signoutUrl'), value: props.serviceProvider.signout_url },
      ]
    : [
        { label: t('settings.sso.acsUrl'), value: props.serviceProvider.acs_url },
        { label: t('settings.sso.entityId'), value: props.serviceProvider.entity_id },
        { label: t('settings.sso.spMetadata'), value: props.serviceProvider.metadata_url },
      ],
)

const { busy, run } = useBusy()
async function save() {
  // Only the active tab's values (shared/types/sso.ts, tested)
  const body = ssoSaveRequest(props.provider, samlByHand.value, state)
  await run(async () => {
    emit('saved', (await api.put<SsoSettings>('/settings/sso', body)).data)
    toast.add({ title: t('settings.sso.saved'), description: t('settings.sso.savedNext'), color: 'success', icon: 'i-lucide-circle-check' })
  })
}
</script>

<template>
  <UForm :schema="schema" :state="state" class="flex flex-col gap-5 rounded-lg border border-default p-3 sm:p-4" @submit="save">
    <div class="flex items-center gap-2">
      <UIcon :name="SSO_ICONS[provider]" class="size-5 shrink-0 text-highlighted" />
      <span class="min-w-0 flex-1 truncate text-sm font-semibold text-highlighted">{{ SSO_NAMES[provider] }}</span>
      <UBadge :label="protocol === 'oidc' ? 'OpenID Connect' : 'SAML 2.0'" color="neutral" variant="outline" size="sm" />
    </div>

    <!-- 1. Into the provider -->
    <section class="flex flex-col gap-3">
      <h3 class="text-xs font-medium text-highlighted">{{ t('settings.sso.step1', { provider: SSO_NAMES[provider] }) }}</h3>
      <p class="text-xs text-muted">{{ t(`settings.sso.how.${provider}`, { providers: SAML_PROVIDERS_EXAMPLES.join(', ') }) }}</p>
      <div class="grid grid-cols-1 gap-3 lg:grid-cols-2">
        <AppCopyField v-for="item in copyValues" :key="item.label" :label="item.label" :value="item.value" monospace />
      </div>
    </section>

    <!-- 2. From the provider -->
    <section class="flex flex-col gap-3">
      <h3 class="text-xs font-medium text-highlighted">{{ t('settings.sso.step2', { provider: SSO_NAMES[provider] }) }}</h3>
      <template v-if="protocol === 'oidc'">
        <UFormField name="issuer" :label="t('settings.sso.issuer')" :help="t('settings.sso.issuerHelp')">
          <UInput v-model="state.issuer" placeholder="https://login.microsoftonline.com/…/v2.0" icon="i-lucide-globe" class="w-full" autocomplete="off" />
        </UFormField>
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <UFormField :label="t('settings.sso.clientId')">
            <UInput v-model="state.client_id" class="w-full font-mono" autocomplete="off" />
          </UFormField>
          <UFormField :label="t('settings.sso.clientSecret')" :help="connection?.oidc.has_secret ? t('settings.smtp.passwordKept') : undefined">
            <UInput v-model="state.client_secret" type="password" :placeholder="connection?.oidc.has_secret ? '••••••••' : ''" class="w-full" autocomplete="new-password" />
          </UFormField>
        </div>
      </template>
      <template v-else>
        <UTabs v-model="samlTab" :items="samlTabs" :content="false" color="neutral" size="sm" :ui="SEGMENTED_UI" class="w-fit max-w-full" :aria-label="t('settings.sso.step2', { provider: SSO_NAMES[provider] })" />
        <UFormField v-if="!samlByHand" name="metadata_url" :label="t('settings.sso.metadataUrl')" :help="t('settings.sso.metadataHelp')">
          <UInput v-model="state.metadata_url" placeholder="https://idp.example.com/metadata.xml" icon="i-lucide-link" class="w-full" autocomplete="off" />
        </UFormField>
        <template v-else>
          <p v-if="provider === 'google_workspace'" class="flex items-start gap-1.5 text-xs text-muted"><UIcon name="i-simple-icons-google" class="mt-0.5 size-3.5 shrink-0" />{{ t('settings.sso.googleByHand') }}</p>
          <UFormField :label="t('settings.sso.idpEntityId')">
            <UInput v-model="state.entity_id" class="w-full font-mono" autocomplete="off" />
          </UFormField>
          <UFormField name="sso_url" :label="t('settings.sso.idpSsoUrl')" :help="t('settings.sso.idpSsoUrlHelp')">
            <UInput v-model="state.sso_url" placeholder="https://idp.example.com/sso/saml" class="w-full" autocomplete="off" />
          </UFormField>
          <UFormField :label="t('settings.sso.certificate')" :help="t('settings.sso.certificateHelp')">
            <UTextarea v-model="state.certificate" :rows="4" placeholder="-----BEGIN CERTIFICATE-----" class="w-full font-mono text-xs" />
          </UFormField>
        </template>
      </template>
    </section>

    <!-- 3. Who uses it -->
    <section class="flex flex-col gap-3">
      <h3 class="text-xs font-medium text-highlighted">{{ t('settings.sso.step3') }}</h3>
      <UFormField name="label" :label="t('settings.sso.label')" :help="t('settings.sso.buttonShows', { label: state.label || SSO_NAMES[provider] })">
        <UInput v-model="state.label" :maxlength="40" class="w-full sm:max-w-xs" />
      </UFormField>
      <UFormField name="domains" :label="t('settings.sso.domains')" :help="state.domains.length ? t('settings.sso.domainsHelp') : t('settings.sso.domainsNone')">
        <UInputTags v-model="domains" :placeholder="t('settings.signin.domainPlaceholder')" icon="i-lucide-at-sign" class="w-full" :add-on-blur="true" :add-on-paste="true" />
      </UFormField>
      <div class="flex flex-col divide-y divide-default rounded-lg border border-default">
        <div class="flex items-center gap-3 px-3 py-2.5">
          <span class="flex min-w-0 flex-1 flex-col"><span class="text-sm text-highlighted">{{ t('settings.sso.enforce') }}</span><span class="text-xs text-muted">{{ t('settings.sso.enforceHint') }}</span></span>
          <USwitch v-model="state.enforce" color="neutral" :aria-label="t('settings.sso.enforce')" />
        </div>
        <div class="flex flex-col gap-2 px-3 py-2.5">
          <div class="flex items-center gap-3">
            <span class="flex min-w-0 flex-1 flex-col"><span class="text-sm text-highlighted">{{ t('settings.sso.autoCreate') }}</span><span class="text-xs text-muted">{{ t('settings.sso.autoCreateHint') }}</span></span>
            <USwitch v-model="state.auto_create" color="neutral" :aria-label="t('settings.sso.autoCreate')" />
          </div>
          <UFormField v-if="state.auto_create" :label="t('settings.sso.defaultRole')">
            <USelect v-model="state.default_role" :items="roleItems" class="w-full sm:max-w-xs" />
          </UFormField>
        </div>
      </div>
      <UAlert v-if="lockOut" color="warning" variant="subtle" icon="i-lucide-triangle-alert" :title="t('settings.sso.lockOut', { domain: ownDomain })" :description="t('settings.sso.lockOutDesc')" />
    </section>

    <div class="flex flex-wrap gap-2">
      <UButton type="submit" :label="t('common.save')" icon="i-lucide-check" color="neutral" :loading="busy" />
      <UButton :label="t('common.cancel')" color="neutral" variant="ghost" :disabled="busy" @click="emit('cancel')" />
    </div>
  </UForm>
</template>
