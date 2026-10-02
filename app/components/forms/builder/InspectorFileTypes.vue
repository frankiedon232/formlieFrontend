<!--
  Allowed file types for upload fields: "Any file" by default, or pick from a searchable,
  grouped list (whole families like "All images" or single types like .pdf). A type that isn't
  listed can be added by typing it (.xyz).
-->
<script setup lang="ts">
import type { SelectMenuItem } from '@nuxt/ui'
import { FILE_GROUP_ICONS, FILE_TYPE_GROUPS, normaliseFileType, parseAccept, type FileTypeGroup } from '#shared/utils/forms/file-types'

const props = defineProps<{ accept: string }>()
const emit = defineEmits<{ update: [accept: string] }>()
const { t } = useI18n()

const selected = computed(() => parseAccept(props.accept))
const custom = computed(() => {
  const known = new Set<string>(Object.values(FILE_TYPE_GROUPS).flat())
  return selected.value.filter(type => !known.has(type))
})
const items = computed<SelectMenuItem[][]>(() => [
  ...(Object.keys(FILE_TYPE_GROUPS) as FileTypeGroup[]).map(group => [
    { type: 'label' as const, label: t(`builder.files.group.${group}`) },
    ...FILE_TYPE_GROUPS[group].map(type => ({
      value: type,
      label: type.endsWith('/*') ? t(`builder.files.all.${group}`) : type,
      icon: FILE_GROUP_ICONS[group],
    })),
  ]),
  ...(custom.value.length
    ? [[{ type: 'label' as const, label: t('builder.files.custom') }, ...custom.value.map(value => ({ value, label: value, icon: 'i-lucide-file' }))]]
    : []),
])
const set = (types: string[]) => emit('update', [...new Set(types)].join(','))
function create(term: string) {
  const type = normaliseFileType(term)
  if (type) set([...selected.value, type])
}
const labelOf = (type: string) => {
  const group = (Object.keys(FILE_TYPE_GROUPS) as FileTypeGroup[]).find(g => type === FILE_TYPE_GROUPS[g][0] && type.endsWith('/*'))
  return group ? t(`builder.files.all.${group}`) : type
}
</script>

<template>
  <UFormField :label="t('builder.inspector.accept')" :description="t('builder.files.hint')">
    <div class="flex flex-col gap-2">
      <USelectMenu
        :model-value="selected"
        :items="items"
        value-key="value"
        multiple
        create-item
        icon="i-lucide-file-search"
        :placeholder="t('builder.files.any')"
        :search-input="{ placeholder: t('builder.files.search') }"
        :aria-label="t('builder.inspector.accept')"
        class="w-full"
        @update:model-value="v => set((v as string[]) ?? [])"
        @create="create"
      >
        <template #default>
          <span class="truncate">
            {{ selected.length ? t('builder.files.count', { count: selected.length }, selected.length) : t('builder.files.any') }}
          </span>
        </template>
      </USelectMenu>
      <div v-if="selected.length" class="flex flex-wrap gap-1">
        <UBadge
          v-for="type in selected"
          :key="type"
          :label="labelOf(type)"
          color="neutral"
          variant="outline"
          size="sm"
          class="rounded-md"
        >
          <template #trailing>
            <UButton
              icon="i-lucide-x"
              color="neutral"
              variant="link"
              size="xs"
              class="-me-1 p-0"
              :aria-label="t('builder.files.remove', { type: labelOf(type) })"
              @click="set(selected.filter(s => s !== type))"
            />
          </template>
        </UBadge>
        <UButton :label="t('builder.files.anyButton')" color="neutral" variant="link" size="xs" @click="set([])" />
      </div>
    </div>
  </UFormField>
</template>
