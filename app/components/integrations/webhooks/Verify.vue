<!--
  How a receiver checks that a call came from Formalie (F13 M6; owner 2026-10-06: the same headers as the
  API, no signatures): the Authorization header must be the webhook's token (compared in constant time),
  and the Formalie-Key (the delivery id, the same on every retry) lets it skip a delivery it already has.
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
    "import { timingSafeEqual } from 'node:crypto'",
    '',
    '// token: the webhook token from Tokens & headers, kept on your server',
    'const seen = new Set() // use your database in real life',
    'function fromFormalie(headers, token) {',
    "  const sent = headers['authorization'] ?? ''",
    '  const expected = `Bearer ${token}`',
    '  if (sent.length !== expected.length || !timingSafeEqual(Buffer.from(sent), Buffer.from(expected))) return false',
    "  const key = headers['formalie-key']",
    '  if (seen.has(key)) return \'already handled\'',
    '  seen.add(key)',
    '  return true',
    '}',
  ].join('\n'),
  python: [
    'import hmac',
    '',
    '# token: the webhook token from Tokens & headers, kept on your server',
    'seen = set()  # use your database in real life',
    'def from_formalie(headers, token: str):',
    '    sent = headers.get("Authorization", "")',
    '    if not hmac.compare_digest(sent, f"Bearer {token}"):',
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
    'function fromFormalie(array $headers, string $token): bool {',
    "    $sent = $headers['Authorization'] ?? '';",
    "    if (!hash_equals('Bearer ' . $token, $sent)) return false;",
    "    // $headers['Formalie-Key'] is the delivery id: skip one you already handled",
    '    return true;',
    '}',
  ].join('\n'),
}
const HEADERS = ['Authorization: Bearer formalie_hook_live_…', 'Content-Type: application/json', 'Formalie-Key: dlv_…   (the same on every retry)'].join('\n')
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
