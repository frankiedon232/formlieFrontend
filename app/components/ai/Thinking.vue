<!--
  The assistant at work (F19, rule 5: never leave people wondering): its steps tick off one by one with a
  percentage while the request runs, then the result replaces it.
-->
<script setup lang="ts">
const props = defineProps<{ steps: string[] }>()
const { t } = useI18n()
const step = ref(0)
let timer: ReturnType<typeof setInterval> | undefined
onMounted(() => {
  timer = setInterval(() => {
    if (step.value < props.steps.length - 1) step.value += 1
  }, 450)
})
onBeforeUnmount(() => clearInterval(timer))
const percent = computed(() => Math.round(((step.value + 1) / (props.steps.length + 1)) * 100))
</script>

<template>
  <UCard variant="outline" :ui="{ body: 'flex flex-col gap-4 p-4 sm:p-6' }" role="status" :aria-label="t('ai.create.thinking')">
    <div class="flex items-center gap-3">
      <span class="flex size-10 items-center justify-center rounded-xl bg-inverted text-inverted"><UIcon name="i-lucide-sparkles" class="size-5 animate-pulse" /></span>
      <div class="flex min-w-0 flex-1 flex-col">
        <span class="text-sm font-semibold text-highlighted">{{ t('ai.create.thinking') }}</span>
        <span class="text-xs text-muted tabular-nums">{{ percent }}%</span>
      </div>
    </div>
    <UProgress :model-value="percent" size="sm" color="neutral" />
    <ul class="flex flex-col gap-2">
      <li v-for="(label, index) in steps" :key="label" class="flex items-center gap-2 text-sm" :class="index <= step ? 'text-default' : 'text-dimmed'">
        <UIcon :name="index < step ? 'i-lucide-check' : index === step ? 'i-lucide-loader-circle' : 'i-lucide-circle'" class="size-4 shrink-0" :class="index === step ? 'animate-spin' : ''" />
        {{ label }}
      </li>
    </ul>
    <div class="grid gap-2"><USkeleton class="h-6 w-1/2" /><USkeleton class="h-40 w-full rounded-lg" /></div>
  </UCard>
</template>
