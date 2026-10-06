<!--
  How a receiver checks that a call came from Formalie (F13 M6): the headers sent, then the
  signature over `{timestamp}.{body}` with the webhook's secret, in a few languages (copy).
-->
<script setup lang="ts">
const { t } = useI18n()
const { copy } = useClipboard({ legacy: true })
const toast = useToast()
const language = useLocalStorage<'javascript' | 'python' | 'php'>('formalie:webhook-verify-language', 'javascript')
const languages = [
  { value: 'javascript', label: 'Node.js' },
  { value: 'python', label: 'Python' },
  { value: 'php', label: 'PHP' },
]
const CODE = {
  javascript: [
    "import { createHmac, timingSafeEqual } from 'node:crypto'",
    '',
    '// rawBody: the request body exactly as received (a string)',
    'function fromFormalie(headers, rawBody, secret) {',
    "  const timestamp = headers['x-formalie-timestamp']",
    "  const sent = (headers['x-formalie-signature'] ?? '').replace('sha256=', '')",
    '  if (Math.abs(Date.now() / 1000 - Number(timestamp)) > 300) return false',
    "  const expected = createHmac('sha256', secret).update(timestamp + '.' + rawBody).digest('hex')",
    '  return sent.length === expected.length && timingSafeEqual(Buffer.from(sent), Buffer.from(expected))',
    '}',
  ].join('\n'),
  python: [
    'import hashlib, hmac, time',
    '',
    'def from_formalie(headers, raw_body: bytes, secret: str) -> bool:',
    '    timestamp = headers["X-Formalie-Timestamp"]',
    '    sent = headers.get("X-Formalie-Signature", "").removeprefix("sha256=")',
    '    if abs(time.time() - int(timestamp)) > 300:',
    '        return False',
    '    expected = hmac.new(secret.encode(), timestamp.encode() + b"." + raw_body, hashlib.sha256).hexdigest()',
    '    return hmac.compare_digest(sent, expected)',
  ].join('\n'),
  php: [
    '<?php',
    'function fromFormalie(array $headers, string $rawBody, string $secret): bool {',
    "    $timestamp = $headers['X-Formalie-Timestamp'] ?? '';",
    "    $sent = str_replace('sha256=', '', $headers['X-Formalie-Signature'] ?? '');",
    '    if (abs(time() - (int) $timestamp) > 300) return false;',
    "    $expected = hash_hmac('sha256', $timestamp . '.' . $rawBody, $secret);",
    '    return hash_equals($expected, $sent);',
    '}',
  ].join('\n'),
}
const HEADERS = ['X-Formalie-Event: response.created', 'X-Formalie-Delivery: dlv_…', 'X-Formalie-Timestamp: 1767225600', 'X-Formalie-Signature: sha256=…'].join('\n')
function copyCode() {
  void copy(CODE[language.value])
  toast.add({ title: t('common.copied'), color: 'success', icon: 'i-lucide-check' })
}
</script>

<template>
  <div class="flex flex-col gap-3">
    <p class="text-sm text-muted">{{ t('integrations.webhooks.verify.text') }}</p>
    <pre class="overflow-x-auto rounded-lg border border-default bg-elevated/50 p-3 font-mono text-xs leading-relaxed text-highlighted" dir="ltr">{{ HEADERS }}</pre>
    <div class="flex items-center justify-between gap-2">
      <UTabs v-model="language" :items="languages" :content="false" color="neutral" size="xs" :ui="SEGMENTED_UI" :aria-label="t('apiService.docs.language')" />
      <UButton icon="i-lucide-copy" color="neutral" variant="ghost" size="xs" square :aria-label="t('common.copy')" @click="copyCode" />
    </div>
    <pre class="max-h-80 overflow-auto rounded-lg border border-default bg-elevated/50 p-3 font-mono text-xs leading-relaxed text-highlighted" dir="ltr">{{ CODE[language] }}</pre>
    <p class="text-xs text-muted">{{ t('integrations.webhooks.verify.answer') }}</p>
  </div>
</template>
