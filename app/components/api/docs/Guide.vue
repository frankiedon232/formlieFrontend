<!--
  Getting started, shared by every endpoint (F13 M5; redesigned in M7, owner 2026-10-06): the
  address, signing in with a token, the three headers every call sends, the Formalie-Key, sending files,
  the token's expiry in every answer and the errors.
  Each topic its own anchored section, text on the left and a dark code panel on the right (stacked
  on smaller screens); the error list underneath, grouped by status.
-->
<script setup lang="ts">
import type { ApiEndpointDetail } from '#shared/types/apiService'
import { ERROR_CODES, type ErrorCode } from '#shared/utils/errors/codes'
import type { SnippetCall } from '#shared/utils/apiService/snippets'

const props = defineProps<{ base: string; endpoint: ApiEndpointDetail | null }>()
const { t } = useI18n()

const fileField = computed(() => props.endpoint?.fields.find(field => field.accept && (field.type === 'file_upload' || field.type === 'image_upload')) ?? null)
const tokenCall = computed<SnippetCall>(() => ({ method: 'POST', url: `${props.base}/token`, headers: { 'Content-Type': 'application/json' }, body: { client_id: '<client id>', client_secret: '<client secret>' } }))
const topics = computed(() => [
  { id: 'guide-auth', icon: 'i-lucide-key-round', key: 'auth', code: null as string | null },
  { id: 'guide-headers', icon: 'i-lucide-list-checks', key: 'callHeaders', code: 'Authorization: Bearer <token>\nContent-Type: application/json\nFormalie-Key: 6f1c2a90-3d4b-4e8f-9a17-0c5d2b7e8f41' },
  { id: 'guide-key', icon: 'i-lucide-fingerprint', key: 'key', code: '# A new id for every call\nFormalie-Key: 6f1c2a90-3d4b-4e8f-9a17-0c5d2b7e8f41\n\n# The same POST sent again with the same key\n# answers with the first record, never a second one' },
  { id: 'guide-files', icon: 'i-lucide-paperclip', key: 'files', code: `# 1 · ${t('apiService.docs.files.step1')}\ncurl -X POST "${props.endpoint?.url ?? `${props.base}/<endpoint>`}/files?field=${fileField.value?.name ?? '<API name>'}" \\\n  -H "Authorization: Bearer <token>" \\\n  -H "Formalie-Key: $(uuidgen)" \\\n  -F "file=@cv.pdf"\n\n# → { "data": { "id": "f_9Qm…", "name": "cv.pdf", … } }\n\n# 2 · ${t('apiService.docs.files.step2')}\n{ "${fileField.value?.name ?? 'cv'}": ["f_9Qm…"] }` },
  {
    id: 'guide-manage',
    icon: 'i-lucide-settings-2',
    key: 'manage',
    code: [
      `# ${t('apiService.docs.manage.base')}`,
      `${props.base.replace(/\/[^/]+$/, '')}/v1`,
      '',
      'GET    /v1/forms                 forms:read',
      'GET    /v1/forms/{id}            forms:read',
      'PATCH  /v1/forms/{id}            forms:write',
      'GET    /v1/forms/{id}/responses  responses:read',
      'GET    /v1/responses/{id}        responses:read',
      'PATCH  /v1/responses/{id}        responses:write',
      'DELETE /v1/responses/{id}        responses:write',
      'GET    /v1/webhooks              webhooks:read',
      'GET    /v1/audit                 audit:read',
      '',
      'Authorization: Bearer <token>',
      'Content-Type: application/json',
      'Formalie-Key: <new unique id>',
    ].join('\n'),
  },
  { id: 'guide-expiry', icon: 'i-lucide-calendar-clock', key: 'expiry', code: 'HTTP/1.1 200\nFormalie-Token-Expires: 2027-01-01T00:00:00Z\n\n{\n  "data": { … },\n  "meta": {\n    "token_expires_at": "2027-01-01T00:00:00Z",\n    "token_expires_in_days": 87\n  }\n}' },
])
const codes: ErrorCode[] = ['FRM-GEN-1001', 'FRM-API-1006', 'FRM-API-1007', 'FRM-API-1008', 'FRM-API-1009', 'FRM-API-1010', 'FRM-API-1011', 'FRM-API-1013', 'FRM-API-1014', 'FRM-API-1015', 'FRM-RESP-1001', 'FRM-GEN-1029']
const dot = (status: number) => (status === 429 ? 'bg-warning' : status === 401 || status === 403 ? 'bg-secondary' : 'bg-error')
</script>

<template>
  <div class="flex flex-col gap-5">
    <section id="guide-address" data-docs-section class="scroll-mt-4 flex flex-col gap-3 rounded-xl border border-default p-4 sm:p-5">
      <div class="flex items-center gap-2">
        <span class="flex size-8 items-center justify-center rounded-md bg-elevated"><UIcon name="i-lucide-link" class="size-4 text-highlighted" /></span>
        <h3 class="text-base font-semibold text-highlighted">{{ t('apiService.docs.baseUrl') }}</h3>
      </div>
      <p class="text-sm text-muted">{{ t('apiService.docs.baseUrlHint') }}</p>
      <AppCopyField :value="base" monospace />
    </section>

    <section v-for="topic in topics" :id="topic.id" :key="topic.id" data-docs-section class="scroll-mt-4 grid overflow-hidden rounded-xl border border-default lg:grid-cols-2">
      <div class="flex min-w-0 flex-col gap-3 p-4 sm:p-5">
        <div class="flex items-center gap-2">
          <span class="flex size-8 items-center justify-center rounded-md bg-elevated"><UIcon :name="topic.icon" class="size-4 text-highlighted" /></span>
          <h3 class="text-base font-semibold text-highlighted">
            {{ t(`apiService.docs.${topic.key}.title`) }}
          </h3>
        </div>
        <p class="text-sm text-muted">{{ t(`apiService.docs.${topic.key}.text`) }}</p>
        <p v-if="topic.key === 'files'" class="text-sm text-muted">{{ t('apiService.docs.files.then') }}</p>
      </div>
      <div class="flex min-w-0 flex-col justify-center gap-2 border-t border-default bg-neutral-950 p-4 sm:p-5 lg:border-s lg:border-t-0">
        <ApiDocsSnippets v-if="topic.key === 'auth'" :call="tokenCall" dark />
        <pre v-else class="overflow-auto rounded-lg bg-neutral-900 p-3 font-mono text-xs leading-relaxed text-neutral-100" dir="ltr">{{ topic.code }}</pre>
      </div>
    </section>

    <section id="guide-errors" data-docs-section class="scroll-mt-4 grid overflow-hidden rounded-xl border border-default lg:grid-cols-2">
      <div class="flex min-w-0 flex-col gap-3 p-4 sm:p-5">
        <div class="flex items-center gap-2">
          <span class="flex size-8 items-center justify-center rounded-md bg-elevated"><UIcon name="i-lucide-octagon-alert" class="size-4 text-highlighted" /></span>
          <h3 class="text-base font-semibold text-highlighted">{{ t('apiService.docs.errors.title') }}</h3>
        </div>
        <p class="text-sm text-muted">{{ t('apiService.docs.errors.text') }}</p>
        <ul class="flex flex-col divide-y divide-default rounded-lg border border-default text-sm">
          <li v-for="code in codes" :key="code" class="flex items-baseline gap-3 px-3 py-2">
            <span class="flex w-12 shrink-0 items-center gap-1.5 font-mono text-xs text-muted tabular-nums"><span class="size-1.5 rounded-full" :class="dot(ERROR_CODES[code].status)" />{{ ERROR_CODES[code].status }}</span>
            <code class="w-28 shrink-0 font-mono text-xs text-highlighted">{{ code }}</code>
            <span class="min-w-0 text-muted">{{ t(`errors.${code}`) }}</span>
          </li>
        </ul>
      </div>
      <div class="flex min-w-0 flex-col gap-2 border-t border-default bg-neutral-950 p-4 sm:p-5 lg:border-s lg:border-t-0">
        <span class="text-[11px] font-semibold tracking-wide text-neutral-400 uppercase">{{ t('apiService.docs.errorShape') }}</span>
        <pre class="overflow-auto rounded-lg bg-neutral-900 p-3 font-mono text-xs leading-relaxed text-neutral-100" dir="ltr">HTTP/1.1 422
X-Request-Id: 9b2f…

{
  "error": {
    "code": "FRM-RESP-1001",
    "message": "Submission is invalid.",
    "details": [
      { "field": "email", "message": "email" }
    ]
  }
}</pre>
      </div>
    </section>
  </div>
</template>
