<!--
  DataView toolbar (docs/design: "All Tasks" row): search · Filter popover · active filter chips ·
  date range · Sort · Table/Grid switch. Wraps on small screens. `/` focuses search.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'

const props = defineProps<{
  state: DataViewState<unknown>
  searchPlaceholder?: string
  sortOptions?: { label: string; value: string }[]
  dateRange?: boolean
  views?: boolean
}>()

const { t } = useI18n()
const search = ref(props.state.query.value.q)
const searchInput = useTemplateRef<{ inputRef: HTMLInputElement }>('searchInput')

watch(
  () => props.state.query.value.q,
  value => {
    if (value !== search.value.trim()) search.value = value
  },
)
const pushSearch = useDebounceFn((value: string) => props.state.setSearch(value), 300)
watch(search, value => pushSearch(value))

defineShortcuts({
  '/': () => searchInput.value?.inputRef?.focus(),
})

const activeCount = computed(() =>
  Object.values(props.state.query.value.filters).reduce((sum, values) => sum + values.length, 0),
)

const chips = computed(() =>
  props.state.filters.flatMap(filter =>
    props.state.query.value.filters[filter.key]!.map(value => ({
      filter,
      value,
      option: filter.options.find(option => option.value === value),
    })),
  ),
)

function removeChip(key: string, value: string) {
  props.state.setFilter(
    key,
    props.state.query.value.filters[key]!.filter(v => v !== value),
  )
}

const sortItems = computed<DropdownMenuItem[]>(() =>
  (props.sortOptions ?? []).map(option => ({
    label: option.label,
    type: 'checkbox' as const,
    checked: props.state.query.value.sort === option.value,
    onSelect: () => props.state.setSort(option.value),
  })),
)

function setView(value: string | number) {
  // eslint-disable-next-line vue/no-mutating-props -- the state object is shared on purpose; view is its writable ref
  props.state.view.value = value === 'grid' ? 'grid' : 'table'
}

const viewItems = computed(() => [
  { label: t('dataView.table'), value: 'table', icon: 'i-lucide-table-2' },
  { label: t('dataView.grid'), value: 'grid', icon: 'i-lucide-layout-grid' },
])
</script>

<template>
  <div class="flex flex-wrap items-center gap-2">
    <UInput
      ref="searchInput"
      v-model="search"
      icon="i-lucide-search"
      :placeholder="searchPlaceholder ?? t('dataView.search')"
      :aria-label="t('dataView.search')"
      class="w-full sm:w-64"
      @keydown.esc="search = ''"
    >
      <template v-if="!search" #trailing>
        <UKbd value="/" />
      </template>
    </UInput>

    <UPopover v-if="state.filters.length" :content="{ align: 'start' }">
      <UButton icon="i-lucide-list-filter" :label="t('dataView.filter')" color="neutral" variant="outline">
        <template v-if="activeCount" #trailing>
          <UBadge :label="activeCount" color="neutral" variant="solid" size="sm" />
        </template>
      </UButton>
      <template #content>
        <div class="flex w-72 flex-col gap-3 p-3">
          <UFormField v-for="filter in state.filters" :key="filter.key" :label="filter.label">
            <USelectMenu
              :model-value="state.query.value.filters[filter.key]"
              :items="filter.options"
              value-key="value"
              multiple
              :placeholder="t('dataView.any')"
              class="w-full"
              @update:model-value="(values: string[]) => state.setFilter(filter.key, values)"
            >
              <template #item-leading="{ item }">
                <span v-if="item.dot" class="size-2 shrink-0 rounded-[1px]" :class="item.dot" />
              </template>
            </USelectMenu>
          </UFormField>
        </div>
      </template>
    </UPopover>

    <UButton
      v-for="chip in chips"
      :key="`${chip.filter.key}:${chip.value}`"
      :label="chip.option?.label ?? chip.value"
      color="neutral"
      variant="outline"
      size="sm"
      trailing-icon="i-lucide-x"
      :aria-label="t('dataView.removeFilter', { name: chip.option?.label ?? chip.value })"
      @click="removeChip(chip.filter.key, chip.value)"
    >
      <template #leading>
        <span v-if="chip.option?.dot" class="size-2 shrink-0 rounded-[1px]" :class="chip.option.dot" />
        <UIcon v-else name="i-lucide-list-filter" class="size-3.5" />
      </template>
    </UButton>

    <UButton
      v-if="state.hasActiveFilters.value"
      :label="t('dataView.clearAll')"
      color="neutral"
      variant="link"
      size="sm"
      @click="state.reset()"
    />

    <div class="ms-auto flex flex-wrap items-center gap-2">
      <slot name="end" />
      <DataDateRangePicker
        v-if="dateRange"
        :from="state.query.value.from"
        :to="state.query.value.to"
        @change="(from, to) => state.setRange(from, to)"
      />
      <UDropdownMenu v-if="sortItems.length" :items="sortItems" :content="{ align: 'end' }">
        <UButton
          icon="i-lucide-arrow-up-down"
          :label="t('dataView.sort')"
          color="neutral"
          variant="outline"
        />
      </UDropdownMenu>
      <UTabs
        v-if="views"
        :model-value="state.view.value"
        :items="viewItems"
        :content="false"
        size="sm"
        color="neutral"
        :aria-label="t('dataView.view')"
        :ui="{ list: 'rounded-md', trigger: 'px-2.5' }"
        @update:model-value="setView"
      />
    </div>
  </div>
</template>
