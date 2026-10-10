<!--
  Designer → Custom CSS (F8, leftovers L5, owner 2026-10-10), on plans that include it. What people write is
  kept as written; the form only ever gets the cleaned version (shared sanitiseCss, the same on the server),
  fenced to the form box. Below the editor: what was left out and why, the characters used, and the hooks to
  target (h1, label, a question by its key with [data-field="…"], a type with [data-field-type="…"]).
-->
<script setup lang="ts">
import { CUSTOM_CSS_MAX, sanitiseCss } from '#shared/utils/forms/custom-css'

const { t } = useI18n()
const d = useDesigner()
const { allows } = usePlanAccess()
const { number } = useFormat()

const allowed = computed(() => allows('custom_css'))
const value = computed(() => d.theme.value.custom_css ?? '')
const cleaned = computed(() => sanitiseCss(value.value))
const EXAMPLE = 'h2 { letter-spacing: .02em; }\n[data-field="email"] input { font-weight: 600; }'
</script>

<template>
  <div class="flex flex-col gap-3">
    <p class="text-xs text-muted">{{ t('designer.css.hint') }}</p>
    <BillingLocked v-if="!allowed" feature="custom_css" />
    <UTextarea
      :model-value="value"
      :rows="10"
      autoresize
      :maxrows="24"
      :maxlength="CUSTOM_CSS_MAX"
      :disabled="!allowed"
      :placeholder="EXAMPLE"
      spellcheck="false"
      class="w-full"
      :ui="{ base: 'font-mono text-xs leading-relaxed' }"
      :aria-label="t('designer.css.label')"
      @update:model-value="v => d.setCustomCss(String(v ?? ''))"
    />
    <div class="flex items-center justify-between gap-2 text-[11px] text-muted">
      <span>{{ t('designer.css.count', { n: number(value.length), max: number(CUSTOM_CSS_MAX) }) }}</span>
      <span v-if="value && !cleaned.issues.length" class="flex items-center gap-1 text-success"><UIcon name="i-lucide-shield-check" class="size-3.5" />{{ t('designer.css.clean') }}</span>
    </div>
    <div v-if="cleaned.issues.length" class="flex flex-col gap-1.5 rounded-md border border-warning/40 bg-warning/5 p-2.5" role="status">
      <p class="flex items-center gap-1.5 text-xs font-medium text-highlighted"><UIcon name="i-lucide-shield-alert" class="size-3.5 text-warning" />{{ t('designer.css.leftOut', { n: cleaned.issues.length }, cleaned.issues.length) }}</p>
      <ul class="flex flex-col gap-1">
        <li v-for="(issue, i) in cleaned.issues.slice(0, 8)" :key="i" class="flex min-w-0 flex-col text-[11px]">
          <span class="text-default">{{ t(`designer.css.issue.${issue.kind}`) }}</span>
          <code class="truncate text-muted">{{ issue.text }}</code>
        </li>
      </ul>
    </div>
    <details class="group text-xs text-muted">
      <summary class="flex cursor-pointer list-none items-center gap-1.5 font-medium text-default">
        <UIcon name="i-lucide-circle-help" class="size-3.5" />{{ t('designer.css.guideTitle') }}
        <UIcon name="i-lucide-chevron-down" class="ms-auto size-3.5 transition-transform group-open:rotate-180" />
      </summary>
      <ul class="mt-2 flex list-disc flex-col gap-1 ps-4">
        <li>{{ t('designer.css.guideScope') }}</li>
        <li>{{ t('designer.css.guideHooks') }}</li>
        <li>{{ t('designer.css.guideBlocked') }}</li>
        <li>{{ t('designer.css.guidePlan') }}</li>
      </ul>
    </details>
  </div>
</template>
