<!--
  What a run produced (F12 M4): the results grid for reading statements; for changes, how many rows
  and how long; the database's problem with the line it points at; a calm start state with the
  shortcut; a slim progress bar while it runs (old results stay, dimmed).
-->
<script setup lang="ts">
defineProps<{ state: RunState }>()
const emit = defineEmits<{ page: [page: number]; line: [line: number] }>()
const { t } = useI18n()
const { number } = useFormat()
</script>

<template>
  <div class="relative flex min-h-0 flex-1 flex-col" :aria-busy="state.running">
    <UProgress v-if="state.running" animation="swing" color="neutral" size="2xs" class="absolute inset-x-0 top-0 z-20" />
    <AppEmpty
      v-if="state.problem"
      size="sm"
      :icon="state.problem.line ? 'i-lucide-circle-x' : 'i-lucide-octagon-alert'"
      :title="state.problem.title"
      :description="state.problem.description"
      :actions="state.problem.line ? [{ label: t('query.goToLine', { n: state.problem.line }), icon: 'i-lucide-corner-down-right', color: 'neutral', variant: 'outline', onClick: () => emit('line', state.problem!.line!) }] : undefined"
    />
    <template v-else-if="state.result">
      <div class="flex min-h-0 flex-1 flex-col transition-opacity" :class="state.running ? 'opacity-60' : ''">
        <QueryResults v-if="state.result.kind === 'read'" :result="state.result" @page="page => emit('page', page)" />
        <AppEmpty
          v-else
          size="sm"
          :icon="state.result.notice ? 'i-lucide-info' : 'i-lucide-circle-check'"
          :title="state.result.notice ? t('query.structurePreview') : t(`query.done.${state.result.kind}`, { n: number(state.result.rows_affected ?? 0) }, state.result.rows_affected ?? 0)"
          :description="t('query.took', { ms: number(state.result.duration_ms) })"
        />
      </div>
    </template>
    <AppEmpty v-else-if="!state.running" size="sm" icon="i-lucide-square-terminal" :title="t('query.startTitle')" :description="t('query.startDesc')" />
  </div>
</template>
