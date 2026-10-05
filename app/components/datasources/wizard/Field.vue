<!-- One connection setting (see Fields.vue): the right Nuxt UI control for its type. -->
<script setup lang="ts">
import type { EngineField } from '#shared/utils/datasources/engines'

const props = defineProps<{ field: EngineField; label: string; hint?: string; error?: string; items: { value: string; label: string }[]; saved: boolean; value: unknown; shown: boolean }>()
const emit = defineEmits<{ update: [value: unknown]; toggle: []; file: [] }>()
const { t } = useI18n()
// Optional text, secret and certificate fields say so beside their label (e.g. SQL Server's instance name).
const optional = computed(() => !props.field.required && ['text', 'secret', 'certificate'].includes(props.field.type))
const wide = computed(() => !props.field.half || props.field.type === 'certificate' || props.field.type === 'switch')
const technical = computed(() => ['host', 'port', 'pem', 'uuid', 'identifier'].includes(props.field.format ?? '') || ['username', 'database', 'descriptor', 'service_name', 'instance', 'time_zone'].includes(props.field.key))
</script>

<template>
  <div :class="wide ? 'sm:col-span-2' : ''">
    <USwitch v-if="field.type === 'switch'" :model-value="!!value" :label="label" :description="hint" @update:model-value="emit('update', $event)" />
    <UFormField v-else :label="label" :name="field.key" :description="field.type === 'certificate' ? undefined : hint" :help="field.type === 'certificate' ? hint : undefined" :error="error" :required="field.required && !saved" :hint="optional ? t('onboarding.optional') : undefined">
      <USelect v-if="field.type === 'select'" :model-value="String(value ?? '')" :items="items" value-key="value" class="w-full" @update:model-value="emit('update', $event)" />
      <UInput
        v-else-if="field.type === 'secret'"
        :model-value="String(value ?? '')"
        :type="shown ? 'text' : 'password'"
        autocomplete="new-password"
        :placeholder="saved ? t('dataSources.savedSecret') : undefined"
        class="w-full"
        dir="ltr"
        :ui="{ trailing: 'pe-1' }"
        @update:model-value="emit('update', $event)"
      >
        <template #leading><UIcon name="i-lucide-key-round" class="size-4 text-muted" /></template>
        <template #trailing>
          <UButton :icon="shown ? 'i-lucide-eye-off' : 'i-lucide-eye'" color="neutral" variant="link" size="sm" :aria-label="shown ? t('dataSources.hideSecret') : t('dataSources.showSecret')" :aria-pressed="shown" @click="emit('toggle')" />
        </template>
      </UInput>
      <div v-else-if="field.type === 'certificate'" class="flex flex-col gap-2">
        <UTextarea
          :model-value="String(value ?? '')"
          :rows="4"
          autoresize
          :maxrows="10"
          :placeholder="saved ? t('dataSources.savedSecret') : '-----BEGIN CERTIFICATE-----'"
          class="w-full"
          :ui="{ base: 'font-mono text-xs' }"
          dir="ltr"
          spellcheck="false"
          @update:model-value="emit('update', $event)"
        />
        <UButton :label="t('dataSources.loadFile')" icon="i-lucide-file-up" color="neutral" variant="outline" size="xs" class="w-fit" @click="emit('file')" />
      </div>
      <UInput
        v-else
        :model-value="value === undefined || value === null ? '' : String(value)"
        :type="field.type === 'number' ? 'number' : 'text'"
        :inputmode="field.type === 'number' ? 'numeric' : undefined"
        :placeholder="field.placeholder"
        autocomplete="off"
        spellcheck="false"
        class="w-full"
        :class="technical ? 'font-mono' : ''"
        :dir="technical ? 'ltr' : undefined"
        @update:model-value="emit('update', $event)"
      />
    </UFormField>
  </div>
</template>
