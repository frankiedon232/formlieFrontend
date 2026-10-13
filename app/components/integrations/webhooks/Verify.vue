<!--
  How a receiver checks that a call came from Formalie (F13 M6; signed since 2026-10-13, security review M16):
  Formalie-Signature is v1= and the hex HMAC-SHA256 of "{Formalie-Timestamp}.{raw body}", keyed with the
  webhook token. Compute it over the raw body, compare in constant time, refuse a timestamp more than 5 minutes
  old (a replay), and skip a Formalie-Key (the delivery id, the same on every retry) already handled. The
  Authorization: Bearer token is still sent and can be checked too.
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
    '// token: the webhook token from Tokens & headers, kept on your server',
    '// rawBody: the request body exactly as it arrived (a Buffer), before any JSON parsing',
    'const seen = new Set() // use your database in real life',
    'function fromFormalie(headers, rawBody, token) {',
    "  const timestamp = headers['formalie-timestamp'] ?? ''",
    '  // Missing, or more than 5 minutes old: refuse (a replay)',
    '  if (!/^\\d+$/.test(timestamp) || Math.abs(Date.now() / 1000 - Number(timestamp)) > 300) return false',
    "  const expected = 'v1=' + createHmac('sha256', token).update(`${timestamp}.`).update(rawBody).digest('hex')",
    "  const sent = headers['formalie-signature'] ?? ''",
    '  if (sent.length !== expected.length || !timingSafeEqual(Buffer.from(sent), Buffer.from(expected))) return false',
    "  const key = headers['formalie-key']",
    "  if (seen.has(key)) return 'already handled'",
    '  seen.add(key)',
    '  return true',
    '}',
  ].join('\n'),
  python: [
    'import hashlib, hmac, time',
    '',
    '# token: the webhook token from Tokens & headers, kept on your server',
    '# raw_body: the request body exactly as it arrived (bytes), before any JSON parsing',
    'seen = set()  # use your database in real life',
    'def from_formalie(headers, raw_body: bytes, token: str):',
    '    timestamp = headers.get("Formalie-Timestamp", "")',
    '    # Missing, or more than 5 minutes old: refuse (a replay)',
    '    if not timestamp.isdigit() or abs(time.time() - int(timestamp)) > 300:',
    '        return False',
    '    digest = hmac.new(token.encode(), timestamp.encode() + b"." + raw_body, hashlib.sha256).hexdigest()',
    '    if not hmac.compare_digest(headers.get("Formalie-Signature", ""), "v1=" + digest):',
    '        return False',
    '    key = headers.get("Formalie-Key")',
    '    if key in seen:',
    '        return "already handled"',
    '    seen.add(key)',
    '    return True',
  ].join('\n'),
  php: [
    '<?php',
    '// $token: the webhook token from Tokens & headers, kept on your server',
    "// $rawBody: file_get_contents('php://input'), before any json_decode",
    'function fromFormalie(array $headers, string $rawBody, string $token): bool {',
    "    $timestamp = $headers['Formalie-Timestamp'] ?? '';",
    '    // Missing, or more than 5 minutes old: refuse (a replay)',
    '    if (!ctype_digit($timestamp) || abs(time() - (int) $timestamp) > 300) return false;',
    "    $expected = 'v1=' . hash_hmac('sha256', $timestamp . '.' . $rawBody, $token);",
    "    if (!hash_equals($expected, $headers['Formalie-Signature'] ?? '')) return false;",
    "    // $headers['Formalie-Key'] is the delivery id: skip one you already handled",
    '    return true;',
    '}',
  ].join('\n'),
}
const HEADERS = [
  'Authorization: Bearer formalie_hook_live_…',
  'Content-Type: application/json',
  'Formalie-Key: dlv_…   (the same on every retry)',
  'Formalie-Timestamp: 1767225600   (this try, Unix seconds)',
  'Formalie-Signature: v1=…   (HMAC-SHA256 of "{timestamp}.{raw body}", key: your webhook token)',
].join('\n')
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
