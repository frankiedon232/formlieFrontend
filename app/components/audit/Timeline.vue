<!--
  Latest audit events for one item or person (PROGRESS.md F4 → reusable activity). Drop it into any
  page: <AuditTimeline :filters="{ 'filter[resource_id]': form.id }" :view-all="`/audit?q=${form.name}`" />
-->
<script setup lang="ts">
import type { TimelineItem } from '@nuxt/ui'
import type { AuditEvent } from '#shared/types/audit'

const props = withDefaults(
  defineProps<{
    filters: Record<string, string>
    limit?: number
    /** Event to leave out (e.g. the one already on screen). */
    excludeId?: string
    viewAll?: string
  }>(),
  { limit: 5, excludeId: undefined, viewAll: undefined },
)
const emit = defineEmits<{ open: [event: AuditEvent] }>()

const { t } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()
const { relative, dateTime } = useFormat()
const format = useAuditFormat()

const events = shallowRef<AuditEvent[]>([])
const loading = ref(true)
const failed = ref(false)

async function load() {
  loading.value = true
  failed.value = false
  try {
    const { data } = await api.list<AuditEvent>('/audit-logs', {
      ...props.filters,
      page_size: props.limit + 1,
    })
    events.value = data.filter(event => event.id !== props.excludeId).slice(0, props.limit)
  } catch (error) {
    handle(error, { silent: true })
    failed.value = true
  } finally {
    loading.value = false
  }
}
watch(() => [props.filters, props.excludeId], load, { immediate: true, deep: true })

const items = computed<(TimelineItem & { event: AuditEvent })[]>(() =>
  events.value.map(event => ({
    value: event.id,
    icon: format.actionIcon(event.action),
    title: format.actionLabel(event.action),
    description: event.actor.name,
    date: relative(event.occurred_at),
    event,
  })),
)
</script>

<template>
  <div>
    <div v-if="loading" class="space-y-4" :aria-label="t('common.loading')">
      <div v-for="n in 3" :key="n" class="flex gap-3">
        <USkeleton class="size-8 rounded-full" />
        <div class="flex-1 space-y-2">
          <USkeleton class="h-3 w-24" />
          <USkeleton class="h-4 w-2/3" />
        </div>
      </div>
    </div>
    <p v-else-if="failed" class="text-sm text-muted">
      {{ t('dataView.errorTitle') }} ·
      <UButton
        :label="t('common.retry')"
        color="neutral"
        variant="link"
        size="sm"
        class="p-0"
        @click="load"
      />
    </p>
    <p v-else-if="!items.length" class="text-sm text-muted">{{ t('audit.timeline.empty') }}</p>
    <template v-else>
      <UTimeline :items="items" color="neutral" size="xs" :ui="{ title: 'text-sm', description: 'text-xs' }">
        <template #title="{ item }">
          <UButton
            :label="item.title"
            color="neutral"
            variant="link"
            size="sm"
            class="p-0 font-medium text-highlighted"
            @click="emit('open', item.event)"
          />
        </template>
        <template #date="{ item }">
          <UTooltip :text="dateTime(item.event.occurred_at)">
            <span>{{ item.date }}</span>
          </UTooltip>
        </template>
      </UTimeline>
      <UButton
        v-if="props.viewAll"
        :label="t('audit.timeline.viewAll')"
        trailing-icon="i-lucide-arrow-right"
        color="neutral"
        variant="link"
        size="sm"
        class="mt-2 px-0"
        :to="props.viewAll"
      />
    </template>
  </div>
</template>
