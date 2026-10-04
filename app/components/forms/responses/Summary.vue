<!--
  Summary tab (F11): every question of the form summarised for the chosen period, two columns on
  wide screens. Questions people skipped most show it in their "answered" line.
-->
<script setup lang="ts">
import type { ResponseInsights } from '#shared/types/responses'

defineProps<{ insights: ResponseInsights }>()
const emit = defineEmits<{ open: [id: string] }>()
const { t } = useI18n()
</script>

<template>
  <UEmpty
    v-if="!insights.period.count"
    icon="i-lucide-chart-no-axes-column"
    :title="t('responses.summary.empty')"
    :description="t('responses.summary.emptyDesc')"
    variant="outline"
  />
  <div v-else class="grid items-start gap-4 lg:grid-cols-2">
    <FormsResponsesQuestion
      v-for="(question, index) in insights.questions"
      :key="question.key"
      :question="question"
      :index="index"
      :total="insights.period.count"
      @open="emit('open', $event)"
    />
  </div>
</template>
