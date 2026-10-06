<!--
  The part of the docs every endpoint shares (F13 M5): the address, signing in with a token, the
  Formalie-Key, sending files (upload first, then the id in the JSON), signed requests and the
  errors with their codes. Short tiles of equal height, the error list below.
-->
<script setup lang="ts">
import type { ApiEndpointDetail } from '#shared/types/apiService'
import { ERROR_CODES, type ErrorCode } from '#shared/utils/errors/codes'
import type { SnippetCall } from '#shared/utils/apiService/snippets'

const props = defineProps<{ base: string; endpoint: ApiEndpointDetail | null }>()
const { t } = useI18n()

const fileField = computed(() => props.endpoint?.fields.find(field => field.accept && (field.type === 'file_upload' || field.type === 'image_upload')) ?? null)
const tokenCall = computed<SnippetCall>(() => ({ method: 'POST', url: `${props.base}/token`, headers: { 'Content-Type': 'application/json' }, body: { client_id: '<client id>', client_secret: '<client secret>' } }))
const fileCall = computed(() => `curl -X POST "${props.endpoint?.url ?? `${props.base}/<endpoint>`}/files?field=${fileField.value?.key ?? '<question key>'}" \\\n  -H "Authorization: Bearer <token>" \\\n  -F "file=@cv.pdf"`)
const tiles = computed(() => [
  { key: 'auth', icon: 'i-lucide-key-round' },
  { key: 'key', icon: 'i-lucide-fingerprint' },
  { key: 'files', icon: 'i-lucide-paperclip' },
  { key: 'signing', icon: 'i-lucide-signature' },
])
const codes: ErrorCode[] = ['FRM-API-1006', 'FRM-API-1007', 'FRM-API-1008', 'FRM-API-1009', 'FRM-API-1010', 'FRM-API-1011', 'FRM-API-1012', 'FRM-API-1013', 'FRM-API-1014', 'FRM-API-1015', 'FRM-RESP-1001', 'FRM-GEN-1029']
</script>

<template>
  <section class="flex flex-col gap-4" :aria-label="t('apiService.docs.guide')">
    <div class="flex flex-col gap-2 rounded-lg border border-default p-4 sm:p-5">
      <h3 class="text-sm font-semibold text-highlighted">{{ t('apiService.docs.baseUrl') }}</h3>
      <p class="text-sm text-muted">{{ t('apiService.docs.baseUrlHint') }}</p>
      <AppCopyField :value="base" monospace />
    </div>

    <div class="grid gap-4 md:grid-cols-2">
      <article v-for="tile in tiles" :key="tile.key" class="flex h-full min-w-0 flex-col gap-3 rounded-lg border border-default p-4 sm:p-5">
        <div class="flex items-center gap-2">
          <span class="flex size-8 shrink-0 items-center justify-center rounded-md bg-elevated"><UIcon :name="tile.icon" class="size-4 text-highlighted" /></span>
          <h3 class="text-sm font-semibold text-highlighted">{{ t(`apiService.docs.${tile.key}.title`) }}</h3>
        </div>
        <p class="text-sm text-muted">{{ t(`apiService.docs.${tile.key}.text`) }}</p>
        <ApiDocsSnippets v-if="tile.key === 'auth'" :call="tokenCall" />
        <pre v-else-if="tile.key === 'files'" class="overflow-auto rounded-lg border border-default bg-elevated/50 p-3 font-mono text-xs leading-relaxed text-highlighted" dir="ltr">{{ fileCall }}</pre>
        <pre v-else-if="tile.key === 'key'" class="overflow-auto rounded-lg border border-default bg-elevated/50 p-3 font-mono text-xs leading-relaxed text-highlighted" dir="ltr">Formalie-Key: 6f1c2a90-3d4b-4e8f-9a17-0c5d2b7e8f41</pre>
        <pre v-else class="overflow-auto rounded-lg border border-default bg-elevated/50 p-3 font-mono text-xs leading-relaxed text-highlighted" dir="ltr">X-Formalie-Timestamp: 1767225600
X-Formalie-Signature: sha256=HMAC(secret, "{timestamp}.{METHOD}.{path}.{body}")</pre>
        <p v-if="tile.key === 'files'" class="mt-auto text-xs text-muted">{{ t('apiService.docs.files.then') }}</p>
      </article>
    </div>

    <div class="flex flex-col gap-2 rounded-lg border border-default p-4 sm:p-5">
      <h3 class="text-sm font-semibold text-highlighted">{{ t('apiService.docs.errors.title') }}</h3>
      <p class="text-sm text-muted">{{ t('apiService.docs.errors.text') }}</p>
      <pre class="overflow-auto rounded-lg border border-default bg-elevated/50 p-3 font-mono text-xs text-default" dir="ltr">{ "error": { "code": "FRM-API-1010", "message": "…", "details": null } }</pre>
      <ul class="divide-y divide-default text-sm">
        <li v-for="code in codes" :key="code" class="flex items-baseline gap-3 py-1.5">
          <span class="w-10 shrink-0 font-mono text-xs text-muted tabular-nums">{{ ERROR_CODES[code].status }}</span>
          <code class="w-28 shrink-0 font-mono text-xs text-highlighted">{{ code }}</code>
          <span class="min-w-0 text-muted">{{ t(`errors.${code}`) }}</span>
        </li>
      </ul>
    </div>
  </section>
</template>
