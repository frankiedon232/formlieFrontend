<!--
  Docs navigation (F13 M7 redesign, owner 2026-10-06): the service at the top, then Getting started
  (address, tokens, the three headers, Formalie-Key, files, token expiry, errors) and every endpoint with its methods
  in their colours. The part on screen is marked as you scroll; a click scrolls there. Sticky beside
  the docs on wide screens; on smaller ones a sliding row of the endpoints instead.
-->
<script setup lang="ts">
import type { ApiEndpointDetail, ApiService } from '#shared/types/apiService'
import type { ApiMethod } from '#shared/utils/urls/public'

const props = defineProps<{ service: ApiService | null; endpoints: ApiEndpointDetail[]; active: string | null }>()
const emit = defineEmits<{ go: [anchor: string] }>()
const { t } = useI18n()
const GUIDE = [
  { anchor: 'guide-address', icon: 'i-lucide-link', key: 'baseUrl' },
  { anchor: 'guide-auth', icon: 'i-lucide-key-round', key: 'auth.title' },
  { anchor: 'guide-headers', icon: 'i-lucide-list-checks', key: 'callHeaders.title' },
  { anchor: 'guide-key', icon: 'i-lucide-fingerprint', key: 'key.title' },
  { anchor: 'guide-files', icon: 'i-lucide-paperclip', key: 'files.title' },
  { anchor: 'guide-manage', icon: 'i-lucide-settings-2', key: 'manage.title' },
  { anchor: 'guide-expiry', icon: 'i-lucide-calendar-clock', key: 'expiry.title' },
  { anchor: 'guide-errors', icon: 'i-lucide-octagon-alert', key: 'errors.title' },
]
const methodAnchor = (endpoint: ApiEndpointDetail, method: ApiMethod) => `ep-${endpoint.id}-${method}`
const isIn = (endpoint: ApiEndpointDetail) => !!props.active?.startsWith(`ep-${endpoint.id}`)
</script>

<template>
  <nav class="flex flex-col gap-5 text-sm" :aria-label="t('apiService.docs.navTitle')">
    <div v-if="service" class="flex flex-col gap-1 rounded-lg border border-default p-3">
      <span class="flex items-center gap-2 font-semibold text-highlighted"><UIcon name="i-lucide-boxes" class="size-4" />{{ service.name }}</span>
      <span class="text-xs text-muted">{{ t('apiService.endpointsCount', { n: endpoints.length }, endpoints.length) }}</span>
    </div>

    <div class="flex flex-col gap-0.5">
      <span class="px-2 pb-1 text-[11px] font-semibold tracking-wide text-muted uppercase">{{ t('apiService.docs.gettingStarted') }}</span>
      <button
        v-for="item in GUIDE"
        :key="item.anchor"
        type="button"
        class="flex items-center gap-2 rounded-md px-2 py-1.5 text-start transition-colors hover:bg-elevated focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
        :class="active === item.anchor ? 'bg-elevated font-medium text-highlighted' : 'text-muted'"
        :aria-current="active === item.anchor ? 'location' : undefined"
        @click="emit('go', item.anchor)"
      >
        <UIcon :name="item.icon" class="size-4 shrink-0" />
        <span class="truncate">{{ t(`apiService.docs.${item.key}`) }}</span>
      </button>
    </div>

    <div class="flex flex-col gap-0.5">
      <span class="px-2 pb-1 text-[11px] font-semibold tracking-wide text-muted uppercase">{{ t('nav.apiEndpoints') }}</span>
      <div v-for="endpoint in endpoints" :key="endpoint.id" class="flex flex-col">
        <button
          type="button"
          class="flex items-center justify-between gap-2 rounded-md px-2 py-1.5 text-start transition-colors hover:bg-elevated focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
          :class="isIn(endpoint) ? 'font-medium text-highlighted' : 'text-default'"
          @click="emit('go', `ep-${endpoint.id}`)"
        >
          <span class="truncate font-mono text-xs" dir="ltr">/{{ endpoint.name }}</span>
          <span class="size-1.5 shrink-0 rounded-full" :class="endpoint.status === 'active' ? 'bg-success' : 'bg-(--ui-border-accented)'" :title="endpoint.status === 'active' ? t('apiService.setup.isLive') : t('apiService.setup.notLive')" />
        </button>
        <div class="ms-3 flex flex-col border-s border-default ps-2">
          <button
            v-for="method in endpoint.methods"
            :key="method"
            type="button"
            class="flex items-center gap-2 rounded-md px-2 py-1 text-start text-xs transition-colors hover:bg-elevated focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
            :class="active === methodAnchor(endpoint, method) ? 'bg-elevated text-highlighted' : 'text-muted'"
            :aria-current="active === methodAnchor(endpoint, method) ? 'location' : undefined"
            @click="emit('go', methodAnchor(endpoint, method))"
          >
            <span class="w-12 shrink-0 font-mono text-[10px] font-semibold" :class="METHOD_TEXT[method]">{{ method }}</span>
            <span class="truncate">{{ t(`apiService.docs.op.${method}`) }}</span>
          </button>
        </div>
      </div>
    </div>
  </nav>
</template>
