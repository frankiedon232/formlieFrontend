<!--
  The API service in five steps (guided setup, owner 2026-10-06): service → endpoint → token →
  access rules (optional) → test and go live. Each step says what it is and why; done steps are
  ticked, the next one is marked and offers its button. Across on wide screens, stacked on phones.
  `focus` (the dialogs) shows a place in the flow instead: steps before it ticked, the rest open.
-->
<script setup lang="ts">
import type { ApiJourneyStep as JourneyStep, ApiSetupSummary } from '#shared/types/apiService'

const props = withDefaults(defineProps<{ summary: ApiSetupSummary | null; focus?: JourneyStep | null; compact?: boolean; actions?: boolean }>(), { focus: null, compact: false, actions: true })
const emit = defineEmits<{ step: [step: JourneyStep] }>()
const { t } = useI18n()

const STEPS: { key: JourneyStep; icon: string; to: string | { path: string; query?: Record<string, string> }; optional?: boolean }[] = [
  { key: 'service', icon: 'i-lucide-boxes', to: { path: '/api-service/services', query: { new: '1' } } },
  { key: 'endpoint', icon: 'i-lucide-route', to: '/api-service/endpoints/new' },
  { key: 'token', icon: 'i-lucide-key-round', to: { path: '/api-service/auth', query: { new: '1' } } },
  { key: 'access', icon: 'i-lucide-shield-check', to: { path: '/api-service/access', query: { new: '1' } }, optional: true },
  { key: 'live', icon: 'i-lucide-rocket', to: '/api-service/docs' },
]
const done = computed<Record<JourneyStep, boolean>>(() => {
  // With a focus (the dialogs): where you are in the flow, steps before it done, after it open
  if (props.focus) {
    const at = STEPS.findIndex(step => step.key === props.focus)
    return Object.fromEntries(STEPS.map((step, i) => [step.key, i < at])) as Record<JourneyStep, boolean>
  }
  const s = props.summary
  return {
    service: !!s?.services,
    endpoint: !!s?.endpoints,
    token: !!s && s.tokens_live + s.tokens_test > 0,
    access: !!s?.rules,
    live: !!s && s.endpoints_live > 0 && s.tokens_live > 0,
  }
})
const current = computed<JourneyStep | null>(() => props.focus ?? STEPS.find(step => !step.optional && !done.value[step.key])?.key ?? null)
const steps = computed(() => STEPS.map((step, i) => ({ ...step, n: i + 1, done: done.value[step.key], current: current.value === step.key })))
</script>

<template>
  <ol class="grid gap-2" :class="compact ? 'sm:grid-cols-5' : 'lg:grid-cols-5'" :aria-label="t('apiService.journey.title')">
    <li
      v-for="step in steps"
      :key="step.key"
      class="relative flex min-w-0 gap-3 rounded-lg border p-3 transition-colors"
      :class="[step.current ? 'border-(--ui-border-inverted) bg-elevated/40' : 'border-default', compact ? 'flex-row items-center sm:flex-col sm:items-start' : 'flex-row lg:flex-col']"
      :aria-current="step.current ? 'step' : undefined"
    >
      <span
        class="flex size-8 shrink-0 items-center justify-center rounded-full text-sm font-semibold tabular-nums"
        :class="step.done ? 'bg-inverted text-inverted' : step.current ? 'border-2 border-(--ui-border-inverted) text-highlighted' : 'border border-default text-muted'"
      >
        <UIcon v-if="step.done" name="i-lucide-check" class="size-4" />
        <span v-else>{{ step.n }}</span>
      </span>
      <div class="flex min-w-0 flex-1 flex-col gap-1">
        <span class="flex flex-wrap items-center gap-1.5">
          <UIcon :name="step.icon" class="size-4 shrink-0 text-muted" />
          <span class="text-sm font-semibold text-highlighted">{{ t(`apiService.journey.${step.key}.title`) }}</span>
          <UBadge v-if="step.optional" :label="t('apiService.optional')" color="neutral" variant="soft" size="xs" class="rounded-md" />
        </span>
        <p v-if="!compact" class="text-xs text-muted">{{ t(`apiService.journey.${step.key}.text`) }}</p>
        <UButton
          v-if="actions && step.current && !compact"
          :label="t(`apiService.journey.${step.key}.action`)"
          trailing-icon="i-lucide-arrow-right"
          color="neutral"
          size="xs"
          class="mt-1 self-start"
          :to="step.to"
          @click="emit('step', step.key)"
        />
      </div>
    </li>
  </ol>
</template>
