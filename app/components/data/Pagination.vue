<!-- DataView footer: "Showing 1–20 of 57" · page size · pages. -->
<script setup lang="ts">
import type { ListMeta } from '#shared/types/api'

const props = defineProps<{ meta: ListMeta }>()
const emit = defineEmits<{ page: [page: number]; pageSize: [size: number] }>()
const { t } = useI18n()
const { number } = useFormat()

const from = computed(() => (props.meta.total ? (props.meta.page - 1) * props.meta.page_size + 1 : 0))
const to = computed(() => Math.min(props.meta.total, props.meta.page * props.meta.page_size))
const sizes = PAGE_SIZES.map(size => ({ label: String(size), value: size }))
</script>

<template>
  <div class="flex flex-col items-center justify-between gap-3 sm:flex-row">
    <p class="text-sm text-muted" aria-live="polite">
      {{ t('dataView.showing', { from: number(from), to: number(to), total: number(meta.total) }) }}
    </p>
    <div class="flex items-center gap-3">
      <div class="flex items-center gap-2 text-sm text-muted">
        <span class="hidden sm:inline">{{ t('dataView.perPage') }}</span>
        <USelect
          :model-value="meta.page_size"
          :items="sizes"
          size="sm"
          class="w-20"
          :aria-label="t('dataView.perPage')"
          @update:model-value="(value: number) => emit('pageSize', value)"
        />
      </div>
      <UPagination
        :page="meta.page"
        :total="meta.total"
        :items-per-page="meta.page_size"
        :sibling-count="1"
        size="sm"
        show-edges
        @update:page="(page: number) => emit('page', page)"
      />
    </div>
  </div>
</template>
