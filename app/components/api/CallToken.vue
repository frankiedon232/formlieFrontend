<!--
  Under an example call (endpoint panel, Docs): which of the workspace's tokens the example shows and how
  it signs in (owner, 2026-10-06: two ways, never both). A bearer token is sent as it is; a client id and
  secret first get a short-lived token at /token (the example then shows that step). The name opens the
  token in Tokens & headers; with no token that may call it, a link to make one.
-->
<script setup lang="ts">
import type { ApiToken } from '#shared/types/apiService'

defineProps<{ token: ApiToken | null; endpointId: string; dark?: boolean }>()
const { t } = useI18n()
</script>

<template>
  <p class="flex flex-wrap items-center gap-x-1.5 gap-y-1 text-xs" :class="dark ? 'text-neutral-400' : 'text-muted'">
    <UIcon :name="token?.kind === 'client' ? 'i-lucide-key-square' : 'i-lucide-key-round'" class="size-3.5 shrink-0" />
    <template v-if="token">
      <span>{{ token.kind === 'client' ? t('apiService.call.signsClient') : t('apiService.call.signsBearer') }}</span>
      <ULink :to="{ path: '/api-service/auth', query: { token: token.id } }" class="font-medium underline-offset-2 hover:underline" :class="dark ? 'text-neutral-100' : 'text-highlighted'">{{ token.name }}</ULink>
      <UBadge :label="t(`apiService.tokens.mode.${token.mode}`)" color="neutral" variant="outline" size="xs" class="rounded-md" />
      <span>{{ token.kind === 'client' ? t('apiService.call.whereClient') : t('apiService.call.tokenWhere') }}</span>
    </template>
    <template v-else>
      <span>{{ t('apiService.call.noToken') }}</span>
      <ULink :to="{ path: '/api-service/auth', query: { new: '1', endpoint: endpointId } }" class="font-medium underline-offset-2 hover:underline" :class="dark ? 'text-neutral-100' : 'text-highlighted'">{{ t('apiService.call.makeToken') }}</ULink>
    </template>
  </p>
</template>
