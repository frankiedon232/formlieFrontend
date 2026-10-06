<!--
  One column's settings (F12 M3 structure changes): name, kind of value with its size, can be
  empty, default; on a new table also primary key and numbered automatically. The engine's type
  shows beside the kind. A key column of an existing table only changes its name.
-->
<script setup lang="ts">
import { kindsFor, normaliseDbName, typeFor, DECIMAL_DEFAULT, TEXT_LENGTH_DEFAULT, type ColumnSpec } from '#shared/utils/datasources/ddl'
import type { DbEngine } from '#shared/utils/integrations/databases'

const props = defineProps<{ engine: DbEngine; errors?: Record<string, string>; newTable?: boolean; keyColumn?: boolean; compact?: boolean }>()
const spec = defineModel<ColumnSpec>({ required: true })
const { t } = useI18n()

const kinds = computed(() => kindsFor(props.engine).map(kind => ({ value: kind, label: t(`explorer.ddl.kind.${kind}`) })))
const set = (patch: Partial<ColumnSpec>) => (spec.value = { ...spec.value, ...patch })
const whole = computed(() => spec.value.kind === 'integer' || spec.value.kind === 'big_integer')
const engineType = computed(() => typeFor(props.engine, spec.value))
function setKind(kind: ColumnSpec['kind']) {
  set({ kind, length: kind === 'text' ? TEXT_LENGTH_DEFAULT : kind === 'decimal' ? DECIMAL_DEFAULT.length : null, scale: kind === 'decimal' ? DECIMAL_DEFAULT.scale : null, auto: kind === 'integer' || kind === 'big_integer' ? spec.value.auto : false })
}
const size = (value: string | number) => (value === '' ? null : Math.max(0, Math.round(Number(value))) || null)
</script>

<template>
  <div class="grid grid-cols-1 gap-3" :class="compact ? 'sm:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]' : 'sm:grid-cols-2'">
    <UFormField :label="t('explorer.ddl.columnName')" :error="errors?.name" required>
      <UInput
        :model-value="spec.name"
        :autofocus="!newTable"
        class="w-full font-mono"
        dir="ltr"
        :placeholder="engine === 'oracle' ? 'FULL_NAME' : 'full_name'"
        @update:model-value="value => set({ name: String(value) })"
        @blur="set({ name: normaliseDbName(engine, spec.name) })"
      />
    </UFormField>
    <UFormField :label="t('explorer.ddl.kindLabel')" :error="errors?.kind" :hint="engineType">
      <USelect :model-value="spec.kind" :items="kinds" value-key="value" class="w-full" :disabled="keyColumn" @update:model-value="value => setKind(value as ColumnSpec['kind'])" />
    </UFormField>
    <UFormField v-if="spec.kind === 'text' && !keyColumn" :label="t('explorer.ddl.length')" :error="errors?.length">
      <UInput :model-value="String(spec.length ?? '')" type="number" min="1" max="8000" class="w-full" @update:model-value="value => set({ length: size(value) })" />
    </UFormField>
    <div v-if="spec.kind === 'decimal' && !keyColumn" class="grid grid-cols-2 gap-3">
      <UFormField :label="t('explorer.ddl.digits')" :error="errors?.length">
        <UInput :model-value="String(spec.length ?? '')" type="number" min="1" max="38" class="w-full" @update:model-value="value => set({ length: size(value) })" />
      </UFormField>
      <UFormField :label="t('explorer.ddl.decimals')" :error="errors?.scale">
        <UInput :model-value="String(spec.scale ?? '')" type="number" min="0" max="30" class="w-full" @update:model-value="value => set({ scale: value === '' ? null : Math.max(0, Math.round(Number(value))) })" />
      </UFormField>
    </div>
    <UFormField v-if="!spec.auto && !keyColumn" :label="t('explorer.ddl.default')" :error="errors?.default" :hint="t('explorer.ddl.optional')">
      <USwitch v-if="spec.kind === 'boolean'" :model-value="spec.default === 'true'" :label="spec.default === 'true' ? t('dataSources.yes') : t('dataSources.no')" @update:model-value="value => set({ default: value ? 'true' : 'false' })" />
      <UInput v-else :model-value="spec.default ?? ''" class="w-full" dir="auto" :placeholder="spec.kind === 'date' ? 'YYYY-MM-DD' : undefined" @update:model-value="value => set({ default: String(value) || null })" />
    </UFormField>
    <div class="flex flex-wrap items-center gap-x-5 gap-y-2 sm:col-span-2">
      <USwitch v-if="!spec.primary && !keyColumn" :model-value="spec.nullable" :label="t('explorer.ddl.nullable')" size="sm" @update:model-value="value => set({ nullable: !!value })" />
      <UCheckbox v-if="newTable" :model-value="!!spec.primary" :label="t('explorer.ddl.primary')" @update:model-value="value => set({ primary: !!value, nullable: value ? false : spec.nullable, auto: value ? spec.auto : false })" />
      <USwitch v-if="newTable && spec.primary && whole" :model-value="!!spec.auto" :label="t('explorer.ddl.auto')" size="sm" @update:model-value="value => set({ auto: !!value, default: value ? null : spec.default })" />
      <p v-if="keyColumn" class="flex items-center gap-1.5 text-xs text-muted"><UIcon name="i-lucide-key-round" class="size-3.5" /> {{ t('explorer.ddl.keyColumnNote') }}</p>
    </div>
  </div>
</template>
