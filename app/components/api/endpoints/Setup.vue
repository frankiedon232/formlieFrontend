<!--
  What an endpoint still needs before real apps can use it (guided setup, owner 2026-10-06): its
  service switched on and its form published; a token that may call it (test tokens to try it,
  live tokens for real calls); access rules (optional); a test; then Go live. Each item says why
  and offers the button that does it. Shown after creating an endpoint and in its panel until done.
-->
<script setup lang="ts">
import type { ApiEndpointDetail } from '#shared/types/apiService'

const props = defineProps<{ endpoint: ApiEndpointDetail; busy?: boolean }>()
const emit = defineEmits<{ test: []; live: [on: boolean] }>()
const { t } = useI18n()
const s = computed(() => props.endpoint.setup)
const items = computed(() => [
  {
    key: 'basics',
    icon: 'i-lucide-boxes',
    done: s.value.service_active && s.value.form_published,
    title: t('apiService.setup.basics.title'),
    text: !s.value.service_active ? t('apiService.setup.basics.serviceOff', { name: props.endpoint.service.name }) : !s.value.form_published ? t('apiService.setup.basics.formOff') : t('apiService.setup.basics.ok', { service: props.endpoint.service.name, form: props.endpoint.form.name }),
    action: !s.value.service_active ? { label: t('apiService.actions.openService'), to: { path: '/api-service/services', query: { service: props.endpoint.service.id } } } : !s.value.form_published ? { label: t('apiService.actions.openForm'), to: `/forms/${props.endpoint.form.id}` } : null,
  },
  {
    key: 'token',
    icon: 'i-lucide-key-round',
    done: s.value.tokens_live + s.value.tokens_test > 0,
    title: t('apiService.setup.token.title'),
    text: s.value.tokens_live + s.value.tokens_test > 0 ? t('apiService.setup.token.ok', { live: s.value.tokens_live, test: s.value.tokens_test }) : t('apiService.setup.token.text'),
    action: { label: t('apiService.setup.token.action'), to: { path: '/api-service/auth', query: { new: '1', endpoint: props.endpoint.id } } },
  },
  {
    key: 'access',
    icon: 'i-lucide-shield-check',
    done: s.value.rules > 0,
    optional: true,
    title: t('apiService.setup.access.title'),
    text: s.value.rules ? t('apiService.setup.access.ok', { n: s.value.rules }, s.value.rules) : t('apiService.setup.access.text'),
    action: { label: t('apiService.setup.access.action'), to: { path: '/api-service/access', query: { new: '1', endpoint: props.endpoint.id } } },
  },
  {
    key: 'test',
    icon: 'i-lucide-flask-conical',
    done: false,
    title: t('apiService.setup.test.title'),
    text: t('apiService.setup.test.text'),
    action: null,
  },
])
const ready = computed(() => s.value.service_active && s.value.form_published)
</script>

<template>
  <section class="flex flex-col gap-3" :aria-label="t('apiService.setup.title')">
    <div class="flex items-center justify-between gap-2">
      <h3 class="text-sm font-semibold text-highlighted">{{ t('apiService.setup.title') }}</h3>
      <UBadge :label="s.live ? t('apiService.setup.isLive') : t('apiService.setup.notLive')" :color="s.live ? 'success' : 'neutral'" variant="subtle" size="sm" class="rounded-md" />
    </div>
    <ol class="flex flex-col gap-2">
      <li v-for="(item, i) in items" :key="item.key" class="flex gap-3 rounded-lg border border-default p-3">
        <span class="flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold" :class="item.done ? 'bg-inverted text-inverted' : 'border border-default text-muted'">
          <UIcon v-if="item.done" name="i-lucide-check" class="size-3.5" />
          <span v-else>{{ i + 1 }}</span>
        </span>
        <div class="flex min-w-0 flex-1 flex-col gap-1">
          <span class="flex flex-wrap items-center gap-1.5">
            <UIcon :name="item.icon" class="size-4 text-muted" />
            <span class="text-sm font-medium text-highlighted">{{ item.title }}</span>
            <UBadge v-if="item.optional" :label="t('apiService.optional')" color="neutral" variant="soft" size="xs" class="rounded-md" />
          </span>
          <p class="text-xs text-muted">{{ item.text }}</p>
          <div class="mt-1 flex flex-wrap gap-2">
            <UButton v-if="item.action" :label="item.action.label" :to="item.action.to" color="neutral" :variant="item.done ? 'outline' : 'solid'" size="xs" trailing-icon="i-lucide-arrow-right" />
            <UButton v-if="item.key === 'test'" :label="t('apiService.docs.tryIt')" icon="i-lucide-play" color="neutral" variant="outline" size="xs" :disabled="!ready" @click="emit('test')" />
          </div>
        </div>
      </li>
      <li class="flex gap-3 rounded-lg border p-3" :class="s.live ? 'border-default' : 'border-(--ui-border-inverted) bg-elevated/40'">
        <span class="flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold" :class="s.live ? 'bg-inverted text-inverted' : 'border-2 border-(--ui-border-inverted) text-highlighted'">
          <UIcon v-if="s.live" name="i-lucide-check" class="size-3.5" />
          <span v-else>5</span>
        </span>
        <div class="flex min-w-0 flex-1 flex-col gap-1">
          <span class="flex items-center gap-1.5"><UIcon name="i-lucide-rocket" class="size-4 text-muted" /><span class="text-sm font-medium text-highlighted">{{ t('apiService.setup.live.title') }}</span></span>
          <p class="text-xs text-muted">{{ s.live ? t('apiService.setup.live.on') : t('apiService.setup.live.text') }}</p>
          <p v-if="!s.live && !s.tokens_live" class="text-xs text-warning">{{ t('apiService.setup.live.noLiveToken') }}</p>
          <USwitch :model-value="s.live" :label="s.live ? t('apiService.setup.isLive') : t('apiService.setup.live.action')" :disabled="busy || !ready" class="mt-1" @update:model-value="value => emit('live', !!value)" />
        </div>
      </li>
    </ol>
  </section>
</template>
