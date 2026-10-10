<!--
  What the workspace uses against its plan (F24): forms, the busiest form's responses, AI credits this month,
  databases, and the plan-only features (sign-in, domain, sending address). Slim black bars, amber near the
  limit and red at it; a feature the plan doesn't include links to the plans.
-->
<script setup lang="ts">
import type { BillingOverview } from '#shared/types/billing'

const props = defineProps<{ overview: BillingOverview }>()
const { t } = useI18n()
const { number } = useFormat()

const limits = computed(() => props.overview.plan.limits)
const usage = computed(() => props.overview.usage)
const meters = computed(() =>
  [
    { key: 'forms', icon: 'i-lucide-file-text', value: usage.value.forms, limit: limits.value.forms, hint: null as string | null },
    { key: 'responses', icon: 'i-lucide-inbox', value: usage.value.top_form?.responses ?? 0, limit: limits.value.responses_per_form, hint: usage.value.top_form ? t('billing.usage.busiest', { form: usage.value.top_form.name }) : null },
    { key: 'ai', icon: 'i-lucide-sparkles', value: usage.value.ai_credits_used, limit: limits.value.ai_credits, hint: t('billing.usage.thisMonth') },
  ].map(meter => ({ ...meter, ratio: meter.limit ? Math.min(1, meter.value / meter.limit) : 0 })),
)
const barColor = (ratio: number) => (ratio >= 1 ? 'bg-error' : ratio >= 0.8 ? 'bg-warning' : 'bg-inverted')
const features = computed(() => [
  { key: 'socialSignin', used: usage.value.social_signin, allowed: limits.value.social_signin },
  { key: 'sso', used: usage.value.sso, allowed: limits.value.sso },
  { key: 'customDomain', used: usage.value.custom_domain, allowed: limits.value.custom_domains !== 0 },
  { key: 'customEmail', used: usage.value.custom_email, allowed: limits.value.custom_email },
])
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="grid grid-cols-1 gap-3 md:grid-cols-3">
      <div v-for="meter in meters" :key="meter.key" class="flex h-full flex-col gap-2 rounded-lg border border-default p-3">
        <div class="flex items-center gap-2">
          <UIcon :name="meter.icon" class="size-4 text-muted" />
          <span class="flex-1 text-sm text-highlighted">{{ t(`billing.usage.${meter.key}`) }}</span>
          <span class="text-sm text-highlighted tabular-nums">{{ number(meter.value) }}<span class="text-muted"> / {{ meter.limit === null ? t('billing.unlimited') : number(meter.limit) }}</span></span>
        </div>
        <div class="h-1.5 overflow-hidden rounded-full bg-elevated" role="progressbar" :aria-valuenow="meter.value" :aria-valuemax="meter.limit ?? undefined" :aria-label="t(`billing.usage.${meter.key}`)">
          <div v-if="meter.limit !== null" class="h-full rounded-full transition-all" :class="barColor(meter.ratio)" :style="{ width: `${Math.max(meter.ratio * 100, meter.value ? 2 : 0)}%` }" />
        </div>
        <span v-if="meter.hint" class="mt-auto truncate text-xs text-muted">{{ meter.hint }}</span>
      </div>
    </div>

    <div class="flex flex-col gap-2 rounded-lg border border-default p-3">
      <div class="flex flex-wrap items-center gap-2">
        <UIcon name="i-lucide-database" class="size-4 text-muted" />
        <span class="text-sm text-highlighted">{{ t('billing.usage.databases') }}</span>
        <span class="flex flex-wrap gap-1.5">
          <UBadge v-for="engine in ['mysql', 'postgresql', 'mariadb', 'sqlserver', 'oracle'] as const" :key="engine" :label="t(`billing.db.${engine}`)" :icon="limits.databases.includes(engine) ? 'i-lucide-check' : 'i-lucide-lock'" :color="usage.databases.includes(engine) && !limits.databases.includes(engine) ? 'error' : 'neutral'" :variant="limits.databases.includes(engine) ? 'outline' : 'soft'" size="sm" />
        </span>
      </div>
      <div class="flex flex-wrap gap-2 border-t border-default pt-2">
        <span v-for="feature in features" :key="feature.key" class="flex items-center gap-1.5 text-xs" :class="feature.allowed ? 'text-default' : 'text-muted'">
          <UIcon :name="feature.allowed ? (feature.used ? 'i-lucide-circle-check' : 'i-lucide-circle') : 'i-lucide-lock'" class="size-3.5" :class="feature.allowed && feature.used ? 'text-success' : ''" />
          {{ t(`billing.compare.${feature.key}`) }}
          <span v-if="!feature.allowed" class="text-muted">· {{ t('billing.usage.upgradeFor') }}</span>
        </span>
      </div>
    </div>
  </div>
</template>
