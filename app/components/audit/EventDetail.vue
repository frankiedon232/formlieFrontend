<!-- Body of the event slide-over: who · when · where · item · before → after · technical details · related activity. -->
<script setup lang="ts">
import type { AuditEvent } from '#shared/types/audit'

const props = defineProps<{ event: AuditEvent }>()
const emit = defineEmits<{ open: [event: AuditEvent]; filter: [patch: Record<string, string>] }>()

const { t, te } = useI18n()
const { relative } = useFormat()
const format = useAuditFormat()
const { current } = useAppLocale()

const fullTime = computed(() =>
  new Intl.DateTimeFormat(current.value.language, { dateStyle: 'full', timeStyle: 'long' }).format(
    new Date(props.event.occurred_at),
  ),
)
const reasonText = computed(() =>
  props.event.reason && te(`errors.${props.event.reason}`) ? t(`errors.${props.event.reason}`) : null,
)
const link = computed(() => format.resourceLink(props.event.resource))
const metadata = computed(() => Object.entries(props.event.metadata))

interface Related {
  title: string
  filters: Record<string, string>
  patch: Record<string, string>
}

const related = computed((): Related | null => {
  const { resource, actor } = props.event
  if (resource?.id)
    return {
      title: t('audit.detail.moreItem'),
      filters: { 'filter[resource_id]': resource.id },
      patch: { q: resource.name ?? '' },
    }
  if (actor.id)
    return {
      title: t('audit.detail.morePerson'),
      filters: { 'filter[actor_id]': actor.id },
      patch: { actor_id: actor.id },
    }
  return null
})
</script>

<template>
  <div class="flex flex-col gap-6">
    <div class="flex flex-wrap items-center gap-2">
      <UBadge
        :label="format.outcomeLabel(props.event.outcome)"
        :color="format.outcomeColor(props.event.outcome)"
        variant="subtle"
        class="rounded-md"
      />
      <UBadge
        :label="format.areaLabel(props.event.area)"
        :icon="format.actionIcon(props.event.action)"
        color="neutral"
        variant="outline"
        class="rounded-md"
      />
    </div>

    <UAlert
      v-if="props.event.reason"
      :title="reasonText ?? props.event.reason"
      :description="reasonText ? props.event.reason : undefined"
      :color="props.event.outcome === 'blocked' ? 'error' : 'warning'"
      variant="subtle"
      icon="i-lucide-shield-alert"
      :ui="{ description: 'font-mono text-xs' }"
    />

    <section class="grid gap-5 sm:grid-cols-2">
      <div>
        <h3 class="mb-2 text-xs font-medium tracking-wide text-muted uppercase">
          {{ t('audit.detail.who') }}
        </h3>
        <UUser
          :name="props.event.actor.name"
          :description="format.actorDescription(props.event)"
          :avatar="{
            alt: props.event.actor.name,
            icon: props.event.actor.id ? undefined : 'i-lucide-user-x',
          }"
          size="md"
          :ui="{ name: 'break-all', description: 'break-all' }"
        />
      </div>
      <div>
        <h3 class="mb-2 text-xs font-medium tracking-wide text-muted uppercase">
          {{ t('audit.detail.when') }}
        </h3>
        <p class="text-sm text-highlighted">{{ fullTime }}</p>
        <p class="text-xs text-muted">
          {{ relative(props.event.occurred_at) }} ·
          <span dir="ltr"
            >{{ props.event.occurred_at.replace('T', ' ').slice(0, 19) }} {{ t('audit.detail.utc') }}</span
          >
        </p>
      </div>
      <div>
        <h3 class="mb-2 text-xs font-medium tracking-wide text-muted uppercase">
          {{ t('audit.detail.where') }}
        </h3>
        <p class="flex items-center gap-2 text-sm text-highlighted">
          <UIcon
            :name="
              props.event.location.country
                ? format.countryFlag(props.event.location.country)
                : 'i-lucide-map-pin-off'
            "
            class="size-4 shrink-0"
          />
          {{ format.place(props.event) }}
        </p>
        <p class="mt-1 flex items-center gap-2 text-sm text-default">
          <UIcon :name="format.deviceIcon(props.event.device)" class="size-4 shrink-0 text-muted" />
          {{ format.deviceLabel(props.event.device) }}
        </p>
        <p class="mt-1 font-mono text-xs text-muted">{{ props.event.location.ip }}</p>
      </div>
      <div v-if="props.event.resource">
        <h3 class="mb-2 text-xs font-medium tracking-wide text-muted uppercase">
          {{ t('audit.detail.item') }}
        </h3>
        <p class="text-xs text-muted">{{ format.resourceType(props.event.resource.type) }}</p>
        <p class="text-sm break-all text-highlighted">{{ props.event.resource.name ?? '-' }}</p>
        <UButton
          v-if="link"
          :label="t('audit.detail.open')"
          trailing-icon="i-lucide-arrow-up-right"
          color="neutral"
          variant="link"
          size="sm"
          class="px-0"
          :to="link"
        />
      </div>
    </section>

    <section v-if="props.event.changes.length">
      <h3 class="mb-2 text-xs font-medium tracking-wide text-muted uppercase">
        {{ t('audit.detail.changes') }}
      </h3>
      <ul class="divide-y divide-default rounded-lg border border-default">
        <li v-for="change in props.event.changes" :key="change.field" class="p-3">
          <p class="mb-2 text-sm font-medium text-highlighted">{{ format.fieldLabel(change.field) }}</p>
          <div class="grid items-center gap-2 sm:grid-cols-[1fr_auto_1fr]">
            <div class="rounded-md bg-error/10 px-2.5 py-1.5 text-sm break-all text-default">
              <span class="block text-[11px] text-muted">{{ t('audit.detail.before') }}</span>
              {{ format.changeValue(change.before) }}
            </div>
            <UIcon
              name="i-lucide-arrow-right"
              class="hidden size-4 text-muted sm:block rtl:rotate-180"
              aria-hidden="true"
            />
            <div class="rounded-md bg-success/10 px-2.5 py-1.5 text-sm break-all text-default">
              <span class="block text-[11px] text-muted">{{ t('audit.detail.after') }}</span>
              {{ format.changeValue(change.after) }}
            </div>
          </div>
        </li>
      </ul>
    </section>

    <section>
      <h3 class="mb-2 text-xs font-medium tracking-wide text-muted uppercase">
        {{ t('audit.detail.technical') }}
      </h3>
      <dl class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 font-mono text-xs">
        <template v-for="[key, value] in metadata" :key="key">
          <dt class="text-muted">{{ key }}</dt>
          <dd class="break-all text-default">{{ value }}</dd>
        </template>
        <dt class="text-muted">action</dt>
        <dd class="break-all text-default">{{ props.event.action }}</dd>
      </dl>
      <AppCopyField
        :value="props.event.request_id"
        :label="t('audit.detail.requestId')"
        monospace
        class="mt-3"
      />
    </section>

    <section v-if="related">
      <div class="mb-3 flex items-center justify-between gap-2">
        <h3 class="text-xs font-medium tracking-wide text-muted uppercase">{{ related.title }}</h3>
        <UButton
          :label="t('audit.detail.showAll')"
          icon="i-lucide-list-filter"
          color="neutral"
          variant="link"
          size="sm"
          class="px-0"
          @click="emit('filter', related.patch)"
        />
      </div>
      <AuditTimeline :filters="related.filters" :exclude-id="props.event.id" @open="emit('open', $event)" />
    </section>
  </div>
</template>
