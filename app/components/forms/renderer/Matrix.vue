<!-- Matrix / grid: one choice per row (rows in props.rows, columns = options). Scrolls sideways on phones. -->
<script setup lang="ts">
import type { FormField } from '#shared/utils/forms/build'

const props = defineProps<{ id: string; field: FormField; mode: 'builder' | 'live' }>()
const value = defineModel<unknown>()

const rows = computed(() => ((props.field.props?.rows as string[] | undefined) ?? []).filter(Boolean))
const columns = computed(() => props.field.options ?? [])
const answers = computed(() =>
  value.value && typeof value.value === 'object' ? (value.value as Record<string, string>) : {},
)
const pick = (row: string, column: string) => (value.value = { ...answers.value, [row]: column })
const disabled = computed(() => props.mode === 'builder')
</script>

<template>
  <div :id="id" class="overflow-x-auto rounded-md border border-default">
    <table class="w-full min-w-max text-sm">
      <thead class="bg-elevated/50">
        <tr>
          <th class="px-3 py-2" />
          <th
            v-for="column in columns"
            :key="column.value"
            scope="col"
            class="px-3 py-2 text-center font-medium text-default"
          >
            {{ column.label }}
          </th>
        </tr>
      </thead>
      <tbody class="divide-y divide-default">
        <tr v-for="row in rows" :key="row">
          <th scope="row" class="px-3 py-2 text-start font-normal text-default">{{ row }}</th>
          <td v-for="column in columns" :key="column.value" class="px-3 py-2 text-center">
            <URadioGroup
              :model-value="answers[row]"
              :items="[{ value: column.value, label: column.label }]"
              color="neutral"
              :disabled="disabled"
              :ui="{ label: 'sr-only', fieldset: 'justify-center' }"
              :aria-label="`${row}: ${column.label}`"
              @update:model-value="v => pick(row, String(v))"
            />
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
