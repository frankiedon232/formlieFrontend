<!--
  One answer in the response panel (F11): files as a sliding strip that opens the viewer, ratings as stars or
  a slim bar, a matrix as rows, long text as paragraphs, rich text rendered safely, the rest as text.
-->
<script setup lang="ts">
import type { FormField } from '#shared/utils/forms/build'

/** responseId: files open in the viewer (over private links). */
const props = defineProps<{ field: FormField; value: unknown; responseId?: string }>()
const { t } = useI18n()
const { number } = useFormat()
const { text } = useResponseFormat()

const empty = computed(() => props.value == null || props.value === '' || (Array.isArray(props.value) && !props.value.length))
const files = computed(() => (Array.isArray(props.value) ? props.value : []) as { name?: string; size?: number; type?: string; sample?: boolean }[])
const max = computed(() => Number(props.field.props?.max ?? (props.field.type === 'rating' ? 5 : props.field.type === 'scale' ? 10 : 100)))
const options = computed(() => new Map((props.field.options ?? []).map(option => [option.value, option.label])))
</script>

<template>
  <span v-if="empty" class="text-sm text-dimmed italic">{{ t('responses.detail.noAnswer') }}</span>

  <FormsResponsesFiles v-else-if="(field.type === 'file_upload' || field.type === 'image_upload') && responseId" :response-id="responseId" :field="field.key" :files="files" />

  <div v-else-if="field.type === 'rating'" class="flex items-center gap-1" :aria-label="text(field, value)">
    <svg v-for="n in max" :key="n" viewBox="0 0 24 24" class="size-4" :class="n <= Number(value) ? 'text-highlighted' : 'text-dimmed'" aria-hidden="true">
      <path
        d="M12 2.5l2.9 6.1 6.6.8-4.9 4.6 1.3 6.6L12 17.3l-5.9 3.3 1.3-6.6-4.9-4.6 6.6-.8z"
        :fill="n <= Number(value) ? 'currentColor' : 'none'"
        stroke="currentColor"
        stroke-width="1.6"
        stroke-linejoin="round"
      />
    </svg>
    <span class="ms-1.5 text-sm text-muted tabular-nums">{{ text(field, value) }}</span>
  </div>

  <div v-else-if="field.type === 'scale' || field.type === 'slider'" class="flex max-w-xs items-center gap-2">
    <div class="h-1.5 flex-1 overflow-hidden rounded-full bg-elevated">
      <div class="h-full rounded-full bg-inverted" :style="{ width: `${(Number(value) / max) * 100}%` }" />
    </div>
    <span class="text-sm font-medium text-highlighted tabular-nums">{{ number(Number(value)) }}</span>
    <span class="text-xs text-muted">/ {{ max }}</span>
  </div>

  <dl v-else-if="field.type === 'matrix'" class="grid grid-cols-[minmax(0,1fr)_auto] gap-x-4 gap-y-1 text-sm">
    <template v-for="(pick, row) in (value as Record<string, string>)" :key="row">
      <dt class="truncate text-muted">{{ row }}</dt>
      <dd class="text-default">{{ options.get(pick) ?? pick }}</dd>
    </template>
  </dl>

  <ul v-else-if="field.type === 'checkbox' || field.type === 'multi_select'" class="flex flex-wrap gap-1.5">
    <li v-for="pick in (value as string[])" :key="pick">
      <UBadge :label="options.get(pick) ?? pick" color="neutral" variant="soft" class="rounded-md" />
    </li>
  </ul>

  <FormsRendererRichView v-else-if="field.type === 'rich_text'" :html="String(value)" class="text-sm" />

  <p v-else class="text-sm whitespace-pre-line text-default" :dir="['email', 'phone', 'url', 'iban', 'ip_address'].includes(field.type) ? 'ltr' : undefined">{{ text(field, value) }}</p>
</template>
