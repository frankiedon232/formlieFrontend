<!--
  A calculation shown like a code snippet: name, "team only" when respondents don't see the
  result, a copy button, and the formula with light syntax colouring — field references, functions,
  text, numbers and operators. Field references show the question's label on hover.
-->
<script setup lang="ts">
import { FORMULA_FUNCTIONS } from '#shared/utils/forms/formula'

const props = defineProps<{ label: string; formula: string; internal?: boolean; fields?: Record<string, string> }>()
const { t } = useI18n()
const { copy, copied } = useClipboard({ legacy: true, copiedDuring: 1500 })

type Kind = 'field' | 'fn' | 'text' | 'num' | 'op' | 'plain'
const tokens = computed(() => {
  const out: { kind: Kind; text: string; title?: string }[] = []
  const re = /(\{[a-z][a-z0-9_]*\})|("[^"]*")|(\d+(?:\.\d+)?)|([a-z_]+)(?=\()|([+\-*/=<>!]+|[(),])|(\s+)|(.)/gi
  for (const m of props.formula.matchAll(re)) {
    if (m[1]) out.push({ kind: 'field', text: m[1], title: props.fields?.[m[1].slice(1, -1)] })
    else if (m[2]) out.push({ kind: 'text', text: m[2] })
    else if (m[3]) out.push({ kind: 'num', text: m[3] })
    else if (m[4]) out.push({ kind: (FORMULA_FUNCTIONS as readonly string[]).includes(m[4].toLowerCase()) ? 'fn' : 'plain', text: m[4] })
    else if (m[5]) out.push({ kind: 'op', text: m[5] })
    else out.push({ kind: 'plain', text: m[0] })
  }
  return out
})
const COLOUR: Record<Kind, string> = {
  field: 'text-sky-700 dark:text-sky-300',
  fn: 'text-violet-700 dark:text-violet-300 font-semibold',
  text: 'text-emerald-700 dark:text-emerald-300',
  num: 'text-amber-700 dark:text-amber-300',
  op: 'text-muted',
  plain: 'text-default',
}
</script>

<template>
  <figure class="overflow-hidden rounded-md border border-default">
    <figcaption class="flex items-center gap-2 border-b border-default bg-elevated/60 px-2.5 py-1.5">
      <UIcon name="i-lucide-calculator" class="size-3.5 shrink-0 text-muted" />
      <span class="min-w-0 flex-1 truncate text-xs font-medium text-highlighted">{{ label }}</span>
      <UTooltip v-if="internal" :text="t('templates.teamOnlyHint')">
        <UBadge :label="t('templates.teamOnly')" icon="i-lucide-eye-off" color="neutral" variant="soft" size="sm" />
      </UTooltip>
      <UButton
        :icon="copied ? 'i-lucide-check' : 'i-lucide-copy'"
        color="neutral"
        variant="ghost"
        size="xs"
        square
        :aria-label="t('templates.copyFormula', { name: label })"
        @click="copy(formula)"
      />
    </figcaption>
    <pre class="overflow-x-auto bg-default px-3 py-2 font-mono text-xs leading-relaxed whitespace-pre-wrap"><code><span
      v-for="(token, index) in tokens"
      :key="index"
      :class="COLOUR[token.kind]"
      :title="token.title"
    >{{ token.text }}</span></code></pre>
  </figure>
</template>
