<!--
  Connections (owner 2026-10-08: "visible connections in every API details panel, easy to trace"):
  what a service, endpoint, token or access rule is linked to, each a chip that opens it. Tokens and
  rules say how they reach the item: made for this endpoint, for its service, or for everything.
  Missing links offer the next step (a token for this endpoint / service).
-->
<script setup lang="ts">
import type { ApiConnections as Links, ApiReach } from '#shared/types/apiService'

const props = defineProps<{ type: 'service' | 'endpoint' | 'token' | 'rule'; id: string }>()
const { t } = useI18n()
const { can } = useCan()
const api = useApi()

const links = ref<Links | null>(null)
const failed = ref(false)
async function load() {
  failed.value = false
  try {
    links.value = (await api.get<Links>('/api-service/connections', { type: props.type, id: props.id }, { background: true })).data
  } catch {
    failed.value = true
  }
}
watch(() => [props.type, props.id], () => void load(), { immediate: true })
defineExpose({ load })

const REACH_ICON: Record<ApiReach, string> = { endpoint: 'i-lucide-route', service: 'i-lucide-boxes', all: 'i-lucide-globe' }
const ruleLabel = (rule: Links['rules'][number]) => `${t(`apiService.access.action.${rule.action}`)} · ${rule.values.join(', ')}`
/** Tokens for this item first, then for its service, then for everything. */
const ORDER: Record<ApiReach, number> = { endpoint: 0, service: 1, all: 2 }
const tokens = computed(() => [...(links.value?.tokens ?? [])].sort((a, b) => ORDER[a.reach] - ORDER[b.reach]))
const newToken = computed(() => (props.type === 'endpoint' ? { path: '/api-service/auth', query: { new: '1', endpoint: props.id } } : { path: '/api-service/auth', query: { new: '1' } }))
const showEndpoints = computed(() => props.type !== 'endpoint')
const showTokens = computed(() => props.type === 'service' || props.type === 'endpoint')
</script>

<template>
  <section class="flex flex-col gap-3" :aria-label="t('apiService.connections.title')">
    <h3 class="flex items-center gap-1.5 text-xs font-medium text-muted uppercase"><UIcon name="i-lucide-share-2" class="size-3.5" />{{ t('apiService.connections.title') }}</h3>
    <AppEmpty v-if="failed" size="xs" icon="i-lucide-cloud-alert" :title="t('apiService.connections.failed')" :actions="[{ label: t('common.retry'), icon: 'i-lucide-rotate-cw', color: 'neutral', variant: 'outline', size: 'xs', onClick: load }]" />
    <div v-else-if="!links" class="flex flex-col gap-2"><USkeleton v-for="n in 3" :key="n" class="h-7 w-full" /></div>
    <dl v-else class="grid gap-3 sm:grid-cols-[8rem_minmax(0,1fr)]">
      <template v-if="links.service">
        <dt class="text-xs text-muted sm:pt-1.5">{{ t('apiService.connections.service') }}</dt>
        <dd><UButton :label="links.service.name" icon="i-lucide-boxes" color="neutral" variant="soft" size="xs" :to="{ path: '/api-service/services', query: { service: links.service.id } }" /></dd>
      </template>
      <template v-if="links.form">
        <dt class="text-xs text-muted sm:pt-1.5">{{ t('apiService.connections.form') }}</dt>
        <dd><UButton :label="links.form.name" icon="i-lucide-file-text" color="neutral" variant="soft" size="xs" :to="`/forms/${links.form.id}`" /></dd>
      </template>
      <template v-if="showEndpoints">
        <dt class="text-xs text-muted sm:pt-1.5">{{ t('apiService.connections.endpoints', { n: links.endpoints.length }) }}</dt>
        <dd class="flex flex-wrap gap-1.5">
          <UButton v-for="item in links.endpoints" :key="item.id" :label="`/${item.name}`" icon="i-lucide-route" color="neutral" variant="soft" size="xs" class="font-mono" :to="`/api-service/endpoints/${item.id}`" :title="item.service" />
          <span v-if="!links.endpoints.length" class="text-xs text-muted sm:pt-1.5">{{ t('apiService.connections.none') }}</span>
        </dd>
      </template>
      <template v-if="showTokens">
        <dt class="text-xs text-muted sm:pt-1.5">{{ t('apiService.connections.tokens', { n: tokens.length }) }}</dt>
        <dd class="flex flex-col gap-1.5">
          <div class="flex flex-wrap gap-1.5">
            <UTooltip v-for="item in tokens" :key="item.id" :text="t(`apiService.connections.reach.${item.reach}`)">
              <UButton :label="item.name" :icon="REACH_ICON[item.reach]" color="neutral" :variant="item.reach === 'all' ? 'outline' : 'soft'" size="xs" :to="{ path: '/api-service/auth', query: { token: item.id } }">
                <template #trailing><UBadge :label="t(`apiService.tokens.mode.${item.mode}`)" :color="item.mode === 'live' ? 'success' : 'neutral'" variant="subtle" size="sm" /></template>
              </UButton>
            </UTooltip>
          </div>
          <UButton v-if="can('api.tokens') && !tokens.some(item => item.reach !== 'all')" :label="type === 'endpoint' ? t('apiService.setup.token.action') : t('apiService.connections.newToken')" icon="i-lucide-plus" color="neutral" variant="link" size="xs" class="w-fit px-0" :to="newToken" />
        </dd>
        <dt class="text-xs text-muted sm:pt-1.5">{{ t('apiService.connections.rules', { n: links.rules.length }) }}</dt>
        <dd class="flex flex-wrap gap-1.5">
          <UButton v-for="item in links.rules" :key="item.id" :label="ruleLabel(item)" :icon="item.action === 'block' ? 'i-lucide-shield-x' : 'i-lucide-shield-check'" color="neutral" variant="soft" size="xs" :class="item.enabled ? '' : 'opacity-60'" class="max-w-full truncate" :to="{ path: '/api-service/access', query: { rule: item.id } }" />
          <span v-if="!links.rules.length" class="text-xs text-muted sm:pt-1.5">{{ t('apiService.connections.noRules') }}</span>
        </dd>
      </template>
    </dl>
  </section>
</template>
