<!-- Strength meter + policy checklist under a password field (shared policy: shared/utils/auth/password.ts). -->
<script setup lang="ts">
const props = defineProps<{ value: string }>()
const { t } = useI18n()

const score = computed(() => passwordScore(props.value))
const checks = computed(() => checkPassword(props.value))
const COLORS = ['neutral', 'error', 'warning', 'success', 'success'] as const
const LABELS = ['', 'weak', 'fair', 'good', 'strong'] as const
</script>

<template>
  <div v-if="value" class="mt-2 space-y-2" aria-live="polite">
    <div class="flex items-center gap-3">
      <UProgress :model-value="score" :max="4" :color="COLORS[score]" size="xs" class="flex-1" />
      <span class="w-14 text-end text-xs text-muted">{{
        t(`auth.password.${LABELS[score] || 'weak'}`)
      }}</span>
    </div>
    <ul class="grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
      <li
        v-for="check in checks"
        :key="check.key"
        class="flex items-center gap-1.5"
        :class="check.passed ? 'text-success' : 'text-muted'"
      >
        <UIcon
          :name="check.passed ? 'i-lucide-check' : check.required ? 'i-lucide-circle' : 'i-lucide-plus'"
          class="size-3.5 shrink-0"
        />
        {{ t(`auth.password.rule.${check.key}`, { min: PASSWORD_MIN_LENGTH }) }}
      </li>
    </ul>
  </div>
</template>
