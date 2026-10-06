<!--
  Publish → what changes for the API (owner, 2026-10-06). The endpoints that follow this form's
  latest version start using the new version at once: new questions are accepted and returned,
  newly required ones become required for API calls too, removed ones are no longer accepted.
  Label and design changes keep the keys, so apps keep working. Endpoints pinned to a version
  stay as they are (pin one in the endpoint to update apps first).
-->
<script setup lang="ts">
import type { ApiEndpoint } from '#shared/types/apiService'
import type { apiChanges } from '#shared/utils/apiService/endpoints'

defineProps<{ endpoints: ApiEndpoint[]; changes: ReturnType<typeof apiChanges>; changed: boolean }>()
const { t } = useI18n()
</script>

<template>
  <section class="flex flex-col gap-3 rounded-lg border border-default p-3" :aria-label="t('builder.publish.api.title')">
    <div class="flex items-start gap-2">
      <UIcon name="i-lucide-code-xml" class="mt-0.5 size-4 shrink-0 text-highlighted" />
      <div class="flex min-w-0 flex-col gap-1">
        <span class="text-sm font-medium text-highlighted">{{ t('builder.publish.api.title') }}</span>
        <span class="text-xs text-muted">{{ t('builder.publish.api.text', { n: endpoints.length }, endpoints.length) }}</span>
        <div class="flex flex-wrap gap-1">
          <code v-for="item in endpoints" :key="item.id" class="rounded bg-elevated px-1.5 py-0.5 font-mono text-[11px] text-highlighted" dir="ltr">/{{ item.name }}</code>
        </div>
      </div>
    </div>
    <p v-if="!changed" class="flex items-start gap-2 text-xs text-muted"><UIcon name="i-lucide-circle-check" class="mt-0.5 size-3.5 shrink-0 text-success" />{{ t('builder.publish.api.same') }}</p>
    <ul v-else class="flex flex-col gap-1.5 text-xs">
      <li v-if="changes.added.length" class="flex items-start gap-2 text-muted">
        <UIcon name="i-lucide-plus" class="mt-0.5 size-3.5 shrink-0 text-success" />
        <span>{{ t('builder.publish.api.added') }} <code v-for="item in changes.added" :key="item.key" class="me-1 font-mono text-highlighted" dir="ltr">{{ item.key }}</code></span>
      </li>
      <li v-if="changes.nowRequired.length || changes.added.some(item => item.required)" class="flex items-start gap-2 text-warning">
        <UIcon name="i-lucide-triangle-alert" class="mt-0.5 size-3.5 shrink-0" />
        <span>{{ t('builder.publish.api.required') }} <code v-for="item in [...changes.nowRequired, ...changes.added.filter(entry => entry.required)]" :key="item.key" class="me-1 font-mono" dir="ltr">{{ item.key }}</code></span>
      </li>
      <li v-if="changes.removed.length" class="flex items-start gap-2 text-warning">
        <UIcon name="i-lucide-minus" class="mt-0.5 size-3.5 shrink-0" />
        <span>{{ t('builder.publish.api.removed') }} <code v-for="item in changes.removed" :key="item.key" class="me-1 font-mono" dir="ltr">{{ item.key }}</code></span>
      </li>
      <li class="flex items-start gap-2 text-muted"><UIcon name="i-lucide-pin" class="mt-0.5 size-3.5 shrink-0" />{{ t('builder.publish.api.pin') }}</li>
    </ul>
  </section>
</template>
