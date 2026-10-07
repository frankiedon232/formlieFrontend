<!--
  Settings → Appearance (F14 M6): a small picture of the portal in the look being edited (rail, menu,
  header, a list and a dialog button), beside the real portal that changes too. Decorative.
-->
<script setup lang="ts">
import type { AppearanceSettings } from '#shared/types/appearance'

const props = defineProps<{ look: AppearanceSettings; name: string }>()
const { t } = useI18n()
const ROWS = [72, 54, 86, 40]
const pad = computed(() => (props.look.density === 'compact' ? 'p-2 gap-1.5' : 'p-3 gap-2'))
</script>

<template>
  <div aria-hidden="true" class="flex h-56 overflow-hidden rounded-xl border border-default bg-default text-[9px] shadow-sm">
    <div class="flex w-8 shrink-0 flex-col items-center gap-2 border-e border-default bg-default py-2" :class="look.rail === 'dark' ? 'dark' : ''">
      <span class="size-4 rounded-(--ui-radius) bg-inverted" />
      <span v-for="n in 3" :key="n" class="size-3.5 rounded-(--ui-radius) bg-elevated" />
    </div>
    <div class="flex w-24 shrink-0 flex-col gap-1.5 border-e border-default bg-default p-2 text-default" :class="look.menu === 'dark' ? 'dark' : ''">
      <span class="truncate font-semibold text-highlighted">{{ name || t('app.name') }}</span>
      <span v-for="(item, i) in ['forms', 'responses', 'analytics']" :key="item" class="flex items-center justify-between rounded-(--ui-radius) px-1 py-0.5" :class="i === 0 ? 'bg-elevated text-highlighted' : 'text-muted'">
        {{ t(`nav.${item}`) }}<span v-if="look.menu_badges" class="rounded-full bg-elevated px-1 text-[8px]">{{ 12 - i * 4 }}</span>
      </span>
    </div>
    <div class="flex min-w-0 flex-1 flex-col">
      <div class="flex items-center justify-between gap-2 border-b border-default px-2 py-1.5">
        <span class="flex min-w-0 flex-col"><span class="truncate text-[10px] font-semibold text-highlighted">{{ t('nav.forms') }}</span><span v-if="look.header.breadcrumbs" class="text-[8px] text-muted">{{ t('nav.forms') }} › …</span></span>
        <span class="flex items-center gap-1">
          <span v-if="look.header.search" class="h-3.5 w-12 rounded-(--ui-radius) border border-default" />
          <span class="rounded-(--ui-radius) bg-primary px-1.5 py-0.5 text-[8px] font-medium text-inverted">{{ t('nav.newForm') }}</span>
        </span>
      </div>
      <div class="flex min-h-0 flex-1 flex-col" :class="[pad, look.content_width === 'centred' ? 'px-5' : '']">
        <div v-for="(width, i) in ROWS" :key="i" class="flex items-center gap-2 rounded-(--ui-radius) border border-default bg-default px-2 py-1.5">
          <span class="size-2 rounded-full" :class="i % 2 ? 'bg-amber-500' : 'bg-primary'" />
          <span class="h-1.5 rounded-full bg-(--ui-border-accented)" :style="{ width: `${width}%` }" />
        </div>
      </div>
      <div v-if="look.footer" class="border-t border-default px-2 py-1 text-[8px] text-muted">© {{ t('app.name') }}</div>
    </div>
  </div>
</template>
