<!--
  Help beside each step of Add connection: what to have ready, the addresses to allow, why a
  dedicated account, which encryption to choose for this engine, what least privilege means and
  what the test checks. Under the step on phones.
-->
<script setup lang="ts">
import type { DbEngine } from '#shared/types/datasources'

const props = defineProps<{ step: string; engine: DbEngine | null }>()
const { t, te } = useI18n()
/** Points are numbered keys (p1, p2, …); an engine can have its own (help.security.oracle.p1). */
const points = computed(() => {
  const base = props.engine && te(`dataSources.help.${props.step}.${props.engine}.p1`) ? `dataSources.help.${props.step}.${props.engine}` : `dataSources.help.${props.step}`
  const list: string[] = []
  for (let n = 1; te(`${base}.p${n}`); n++) list.push(t(`${base}.p${n}`))
  return list
})
</script>

<template>
  <div class="flex flex-col gap-3">
    <div class="flex flex-col gap-2 rounded-lg border border-default p-3 sm:p-4">
      <div class="flex items-center gap-2">
        <UIcon name="i-lucide-lightbulb" class="size-4 shrink-0 text-muted" />
        <h3 class="text-sm font-semibold text-highlighted">{{ t(`dataSources.help.${step}.title`) }}</h3>
      </div>
      <ul class="flex flex-col gap-1.5">
        <li v-for="(point, index) in points" :key="index" class="flex gap-2 text-xs text-muted">
          <UIcon name="i-lucide-check" class="mt-0.5 size-3.5 shrink-0 text-highlighted" />
          <span>{{ point }}</span>
        </li>
      </ul>
    </div>
    <DatasourcesEgressIps v-if="step === 'server' || step === 'engine'" />
  </div>
</template>
