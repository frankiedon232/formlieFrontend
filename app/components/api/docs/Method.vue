<!--
  One method of an endpoint in the docs (F13 M5): what it does, the address, what can be sent (each
  question with its key, type, whether it is required and its allowed values), the query options for
  GET, the answer, and the call as code. Built from the endpoint's own choices.
-->
<script setup lang="ts">
import type { ApiEndpointDetail } from '#shared/types/apiService'
import { exampleRecord } from '#shared/utils/apiService/endpoints'
import { endpointCalls, fieldSchema } from '#shared/utils/apiService/snippets'
import type { ApiMethod } from '#shared/utils/urls/public'

const props = defineProps<{ endpoint: ApiEndpointDetail; method: ApiMethod }>()
const emit = defineEmits<{ try: [method: ApiMethod] }>()
const { t } = useI18n()
const call = computed(() => endpointCalls(props.endpoint).find(item => item.method === props.method)!)
const writes = computed(() => props.method === 'POST' || props.method === 'PUT')
const accepted = computed(() => props.endpoint.fields.filter(field => field.accept))
const filters = computed(() => props.endpoint.fields.filter(field => field.filter))
const typeOf = (field: ApiEndpointDetail['fields'][number]) => {
  const schema = fieldSchema(field)
  return schema.type === 'array' ? `${(schema.items as { type: string }).type}[]` : String(schema.format ?? schema.type)
}
const answer = computed(() => {
  const record = exampleRecord(props.endpoint.fields)
  if (props.method === 'GET') return { status: '200', body: { data: [record], meta: { page: 1, per_page: Math.min(20, props.endpoint.page_size), total: 1, total_pages: 1 } } }
  if (props.method === 'POST') return { status: '201', body: { data: record } }
  if (props.method === 'PUT') return { status: '200', body: { data: record } }
  return { status: '200', body: { data: { id: record.id, deleted: true } } }
})
</script>

<template>
  <section class="flex flex-col gap-4 rounded-lg border border-default p-4 sm:p-5" :aria-label="`${method} /${endpoint.name}`">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <div class="flex min-w-0 items-center gap-2">
        <ApiMethods :methods="[method]" size="sm" />
        <code class="truncate font-mono text-sm text-highlighted" dir="ltr">/{{ endpoint.name }}{{ method === 'PUT' || method === 'DELETE' ? '/{id}' : '' }}</code>
      </div>
      <UButton :label="t('apiService.docs.tryIt')" icon="i-lucide-play" color="neutral" variant="outline" size="xs" @click="emit('try', method)" />
    </div>
    <p class="text-sm text-muted">{{ t(`apiService.wizard.method.${method}`) }}</p>

    <div v-if="writes" class="flex flex-col gap-2">
      <h4 class="text-xs font-semibold tracking-wide text-muted uppercase">{{ t('apiService.docs.body') }}</h4>
      <div class="overflow-x-auto rounded-lg border border-default">
        <table class="w-full min-w-[32rem] text-sm">
          <thead class="bg-elevated/50 text-xs text-muted">
            <tr><th class="px-3 py-2 text-start font-medium">{{ t('apiService.docs.col.key') }}</th><th class="px-3 py-2 text-start font-medium">{{ t('apiService.docs.col.type') }}</th><th class="px-3 py-2 text-start font-medium">{{ t('apiService.docs.col.values') }}</th></tr>
          </thead>
          <tbody class="divide-y divide-default">
            <tr v-for="field in accepted" :key="field.key">
              <td class="px-3 py-2 align-top">
                <code class="font-mono text-xs text-highlighted" dir="ltr">{{ field.key }}</code>
                <UBadge v-if="field.required && method === 'POST'" :label="t('apiService.fields.required')" color="neutral" variant="soft" size="xs" class="ms-1.5 rounded-md" />
                <p class="text-xs text-muted">{{ field.label }}</p>
              </td>
              <td class="px-3 py-2 align-top font-mono text-xs text-muted">{{ typeOf(field) }}</td>
              <td class="px-3 py-2 align-top text-xs text-muted">
                <span v-if="field.options?.length" class="flex flex-wrap gap-1"><code v-for="option in field.options.slice(0, 8)" :key="option.value" class="rounded bg-elevated px-1 font-mono text-highlighted" :title="option.label" dir="ltr">{{ option.value }}</code><span v-if="field.options.length > 8">+{{ field.options.length - 8 }}</span></span>
                <span v-else-if="field.type === 'file_upload' || field.type === 'image_upload'">{{ t('apiService.docs.fileValue') }}</span>
                <span v-else>–</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-if="method === 'PUT'" class="text-xs text-muted">{{ t('apiService.docs.putHint') }}</p>
      <p v-if="method === 'POST'" class="text-xs text-muted">{{ t('apiService.docs.keyHint') }}</p>
    </div>

    <div v-if="method === 'GET'" class="flex flex-col gap-2">
      <h4 class="text-xs font-semibold tracking-wide text-muted uppercase">{{ t('apiService.docs.query') }}</h4>
      <ul class="flex flex-col gap-1 text-sm">
        <li><code class="font-mono text-xs text-highlighted">page</code> <span class="text-muted">· {{ t('apiService.docs.page') }}</span></li>
        <li><code class="font-mono text-xs text-highlighted">per_page</code> <span class="text-muted">· {{ t('apiService.docs.perPage', { n: endpoint.page_size }) }}</span></li>
        <li><code class="font-mono text-xs text-highlighted">sort=submitted_at</code> <span class="text-muted">· {{ t('apiService.docs.sort') }}</span></li>
        <li v-for="field in filters" :key="field.key"><code class="font-mono text-xs text-highlighted" dir="ltr">{{ field.key }}=…</code> <span class="text-muted">· {{ t('apiService.docs.filterBy', { label: field.label }) }}</span></li>
      </ul>
    </div>

    <div class="grid gap-4 xl:grid-cols-2">
      <div class="flex min-w-0 flex-col gap-2">
        <h4 class="text-xs font-semibold tracking-wide text-muted uppercase">{{ t('apiService.docs.code') }}</h4>
        <ApiDocsSnippets :call="call" />
      </div>
      <div class="flex min-w-0 flex-col gap-2">
        <h4 class="text-xs font-semibold tracking-wide text-muted uppercase">{{ t('apiService.call.answer') }} · <span class="font-mono">{{ answer.status }}</span></h4>
        <pre class="max-h-80 overflow-auto rounded-lg border border-default bg-elevated/50 p-3 font-mono text-xs leading-relaxed text-default" dir="ltr">{{ JSON.stringify(answer.body, null, 2) }}</pre>
      </div>
    </div>
  </section>
</template>
