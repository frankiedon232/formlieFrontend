<!--
  Docs → Getting started → Sign in (owner, 2026-10-06): the two ways a token signs in, side by side, and
  that they never mix (a token is one kind, chosen when it is made). A bearer token is sent as it is; a
  client id and secret are traded at /token for a short-lived token that is then sent as Bearer. Below,
  how each of this service's endpoints signs in, found from the tokens that may call it.
-->
<script setup lang="ts">
import type { ApiEndpointDetail } from '#shared/types/apiService'
import type { SnippetCall } from '#shared/utils/apiService/snippets'

const props = defineProps<{ base: string; endpoints: ApiEndpointDetail[] }>()
const { t } = useI18n()
const callers = useCallerToken()
void callers.load()

const tokenCall = computed<SnippetCall>(() => ({ method: 'POST', url: `${props.base}/token`, headers: { 'Content-Type': 'application/json' }, body: { client_id: '<client id>', client_secret: '<client secret>' } }))
const WAYS = [
  { kind: 'static', icon: 'i-lucide-key-round' },
  { kind: 'client', icon: 'i-lucide-key-square' },
] as const
const rows = computed(() => props.endpoints.map(endpoint => ({ endpoint, kinds: callers.kindsFor(endpoint, endpoint.methods) })))
const names = (list: { name: string }[]) => (list.length > 2 ? `${list.slice(0, 2).map(item => item.name).join(', ')} +${list.length - 2}` : list.map(item => item.name).join(', '))
</script>

<template>
  <section id="guide-auth" data-docs-section class="scroll-mt-4 grid overflow-hidden rounded-xl border border-default lg:grid-cols-2">
    <div class="flex min-w-0 flex-col gap-4 p-4 sm:p-5">
      <div class="flex items-center gap-2">
        <span class="flex size-8 items-center justify-center rounded-md bg-elevated"><UIcon name="i-lucide-key-round" class="size-4 text-highlighted" /></span>
        <h3 class="text-base font-semibold text-highlighted">{{ t('apiService.docs.auth.title') }}</h3>
      </div>
      <p class="text-sm text-muted">{{ t('apiService.docs.auth.text') }}</p>
      <div class="grid gap-2 sm:grid-cols-2">
        <div v-for="(way, i) in WAYS" :key="way.kind" class="flex h-full flex-col gap-1.5 rounded-lg border border-default p-3">
          <span class="flex items-center gap-2 text-sm font-semibold text-highlighted">
            <span class="flex size-5 items-center justify-center rounded-full bg-inverted text-[11px] text-inverted tabular-nums">{{ i + 1 }}</span>
            <UIcon :name="way.icon" class="size-4 text-muted" />{{ t(`apiService.tokens.kind.${way.kind}`) }}
          </span>
          <p class="text-xs text-muted">{{ t(`apiService.docs.auth.${way.kind}`) }}</p>
        </div>
      </div>
      <UAlert icon="i-lucide-triangle-alert" color="warning" variant="subtle" :title="t('apiService.docs.auth.never')" :description="t('apiService.docs.auth.neverText')" />

      <div class="flex flex-col gap-2">
        <h4 class="text-xs font-semibold tracking-wide text-muted uppercase">{{ t('apiService.docs.auth.yours') }}</h4>
        <div v-if="!callers.tokens.value" class="flex flex-col gap-1.5"><USkeleton v-for="n in 3" :key="n" class="h-9 rounded-md" /></div>
        <ul v-else class="divide-y divide-default overflow-hidden rounded-lg border border-default">
          <li v-for="row in rows" :key="row.endpoint.id" class="flex flex-col gap-1 px-3 py-2 sm:flex-row sm:items-center sm:gap-3">
            <code class="shrink-0 font-mono text-xs font-semibold text-highlighted sm:w-44 sm:truncate" dir="ltr">/{{ row.endpoint.name }}</code>
            <div class="flex min-w-0 flex-1 flex-wrap items-center gap-1.5">
              <template v-for="way in WAYS" :key="way.kind">
                <UTooltip v-if="row.kinds[way.kind].length" :text="names(row.kinds[way.kind])">
                  <UBadge :label="t(`apiService.tokens.kind.${way.kind}`)" :icon="way.icon" color="neutral" :variant="way.kind === 'static' ? 'outline' : 'soft'" size="sm" class="rounded-md" />
                </UTooltip>
              </template>
              <span v-if="row.kinds.static.length && row.kinds.client.length" class="text-[11px] text-muted">{{ t('apiService.docs.auth.both') }}</span>
              <ULink v-if="!row.kinds.static.length && !row.kinds.client.length" :to="{ path: '/api-service/auth', query: { new: '1', endpoint: row.endpoint.id } }" class="text-xs text-muted underline-offset-2 hover:underline">{{ t('apiService.call.noToken') }} {{ t('apiService.call.makeToken') }}</ULink>
            </div>
          </li>
        </ul>
      </div>
    </div>
    <div class="flex min-w-0 flex-col justify-center gap-2 border-t border-default bg-neutral-950 p-4 sm:p-5 lg:border-s lg:border-t-0">
      <span class="text-[11px] font-semibold tracking-wide text-neutral-400 uppercase">1 · {{ t('apiService.tokens.kind.static') }}</span>
      <pre class="overflow-auto rounded-lg bg-neutral-900 p-3 font-mono text-xs leading-relaxed text-neutral-100" dir="ltr">Authorization: Bearer formalie_live_…</pre>
      <span class="mt-2 text-[11px] font-semibold tracking-wide text-neutral-400 uppercase">2 · {{ t('apiService.tokens.kind.client') }}</span>
      <ApiDocsSnippets :call="tokenCall" dark />
      <pre class="overflow-auto rounded-lg bg-neutral-900 p-3 font-mono text-xs leading-relaxed text-neutral-100" dir="ltr"># → { "access_token": "formalie_live_access_…", "token_type": "Bearer", "expires_in": 900 }
Authorization: Bearer formalie_live_access_…</pre>
    </div>
  </section>
</template>
