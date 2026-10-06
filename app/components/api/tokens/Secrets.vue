<!--
  A token's secrets right after creating or rotating it (F13 M2): shown once, each with Copy, and
  how to use them (a bearer header, or client id + secret for short-lived tokens). Formalie keeps
  only a hash, so they can't be shown again; losing one means rotating.
-->
<script setup lang="ts">
import type { ApiToken, ApiTokenSecrets } from '#shared/types/apiService'

const props = defineProps<{ token: ApiToken; secrets: ApiTokenSecrets; base: string }>()
const { t } = useI18n()
const usage = computed(() =>
  props.token.kind === 'static'
    ? `Authorization: Bearer ${props.secrets.token ?? '<token>'}`
    : `POST ${props.base}/token\nContent-Type: application/json\n\n{ "client_id": "${props.token.client_id}", "client_secret": "<client secret>" }`,
)
</script>

<template>
  <div class="flex flex-col gap-4">
    <UAlert icon="i-lucide-triangle-alert" color="warning" variant="subtle" :title="t('apiService.tokens.once.title')" :description="t('apiService.tokens.once.desc')" />
    <AppCopyField v-if="secrets.token" :value="secrets.token" :label="t('apiService.tokens.secret.token')" monospace />
    <template v-if="token.kind === 'client'">
      <AppCopyField :value="token.client_id ?? ''" :label="t('apiService.tokens.secret.clientId')" monospace />
      <AppCopyField v-if="secrets.client_secret" :value="secrets.client_secret" :label="t('apiService.tokens.secret.clientSecret')" monospace />
    </template>
    <AppCopyField v-if="secrets.signing_secret" :value="secrets.signing_secret" :label="t('apiService.tokens.secret.signing')" monospace />
    <div class="flex flex-col gap-1.5">
      <span class="text-xs font-medium text-muted">{{ t('apiService.tokens.howToUse') }}</span>
      <pre class="overflow-x-auto rounded-lg border border-default bg-elevated/50 p-3 font-mono text-xs leading-relaxed text-highlighted" dir="ltr">{{ usage }}</pre>
      <p v-if="token.kind === 'client'" class="text-xs text-muted">{{ t('apiService.tokens.clientHint', { n: token.lifetime_minutes ?? 15 }) }}</p>
      <p v-if="token.signing" class="text-xs text-muted">{{ t('apiService.tokens.signingHint') }}</p>
    </div>
  </div>
</template>
