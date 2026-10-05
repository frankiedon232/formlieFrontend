<!-- Help beside each step of storing responses in a database (numbered points, p1, p2, …). -->
<script setup lang="ts">
const props = defineProps<{ step: string }>()
const { t, te } = useI18n()
const points = computed(() => {
  const list: string[] = []
  for (let n = 1; te(`destinations.help.${props.step}.p${n}`); n++) list.push(t(`destinations.help.${props.step}.p${n}`))
  return list
})
</script>

<template>
  <div class="flex flex-col gap-2 self-start rounded-lg border border-default p-3 sm:p-4">
    <div class="flex items-center gap-2">
      <UIcon name="i-lucide-lightbulb" class="size-4 shrink-0 text-muted" />
      <h3 class="text-sm font-semibold text-highlighted">{{ t(`destinations.help.${step}.title`) }}</h3>
    </div>
    <ul class="flex flex-col gap-1.5">
      <li v-for="(point, index) in points" :key="index" class="flex gap-2 text-xs text-muted">
        <UIcon name="i-lucide-check" class="mt-0.5 size-3.5 shrink-0 text-highlighted" />
        <span>{{ point }}</span>
      </li>
    </ul>
  </div>
</template>
