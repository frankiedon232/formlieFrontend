<!--
  The statements a database administrator runs to give Formalie exactly the access this
  connection uses (F12, owner 2026-10-05: always tell people which permissions to grant). Written
  for this engine with the connection's own database, schemas and account; one block per level,
  each with Copy and short notes, plus Copy all. Oracle: 23ai and later grant per schema, earlier
  versions per table.
-->
<script setup lang="ts">
import type { DataSourceAccessSettings, DataSourceSettings } from '#shared/types/datasources'
import type { DbEngine } from '#shared/utils/integrations/databases'
import { grantScript, grantScriptText } from '#shared/utils/datasources/permissions'

const props = defineProps<{ engine: DbEngine; settings: DataSourceSettings; access: DataSourceAccessSettings }>()
const { t } = useI18n()
const toast = useToast()
const { copy } = useClipboard({ legacy: true })

const oracle23 = ref(true)
const blocks = computed(() => grantScript(props.engine, props.settings, props.access, { oracle23: oracle23.value }))
const copied = ref<string | null>(null)
function copyText(key: string, text: string) {
  void copy(text)
  copied.value = key
  toast.add({ title: t('dataSources.grant.copied'), color: 'success', icon: 'i-lucide-check' })
  setTimeout(() => copied.value === key && (copied.value = null), 1500)
}
</script>

<template>
  <div class="flex flex-col gap-3">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <p class="text-xs text-muted">{{ t('dataSources.grant.intro') }}</p>
      <UButton :label="t('dataSources.grant.copyAll')" :icon="copied === 'all' ? 'i-lucide-check' : 'i-lucide-copy'" color="neutral" variant="outline" size="xs" @click="copyText('all', grantScriptText(blocks))" />
    </div>
    <USwitch v-if="engine === 'oracle'" v-model="oracle23" :label="t('dataSources.grant.oracle23')" :description="t('dataSources.grant.oracle23Desc')" size="sm" />

    <section v-for="block in blocks" :key="block.key" class="overflow-hidden rounded-lg border border-default">
      <header class="flex items-center justify-between gap-2 bg-elevated/50 px-3 py-1.5">
        <h4 class="text-xs font-semibold text-highlighted">{{ t(`dataSources.grant.block.${block.key}`) }}</h4>
        <UButton v-if="block.sql" :icon="copied === block.key ? 'i-lucide-check' : 'i-lucide-copy'" color="neutral" variant="ghost" size="xs" :aria-label="t('common.copy')" @click="copyText(block.key, block.sql)" />
      </header>
      <pre v-if="block.sql" class="overflow-x-auto px-3 py-2.5 font-mono text-[11px] leading-relaxed text-default" dir="ltr" tabindex="0" :aria-label="t(`dataSources.grant.block.${block.key}`)">{{ block.sql }}</pre>
      <ul v-if="block.notes.length" class="flex flex-col gap-1 px-3 py-2" :class="block.sql ? 'border-t border-default' : ''">
        <li v-for="note in block.notes" :key="note" class="flex gap-1.5 text-xs text-muted">
          <UIcon name="i-lucide-info" class="mt-0.5 size-3.5 shrink-0" />
          <span>{{ t(`dataSources.grant.note.${note}`) }}</span>
        </li>
      </ul>
    </section>
  </div>
</template>
