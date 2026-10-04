<!--
  Search & link preview, drawn the way the link will look (F10 M3): as a link card in chats and
  social posts (WhatsApp, LinkedIn, email…: image on top, site, title, description) and as a search
  result (address, title, description). Long text is cut like those places cut it.
-->
<script setup lang="ts">
const props = defineProps<{ title: string; description: string; image: string | null; url: string; siteName: string; noindex: boolean }>()
const { t } = useI18n()

const view = ref<'card' | 'search'>('card')
const views = computed(() => [
  { value: 'card', label: t('share.seo.asCard'), icon: 'i-lucide-message-square' },
  { value: 'search', label: t('share.seo.asSearch'), icon: 'i-lucide-search' },
])
const host = computed(() => {
  try {
    return new URL(props.url).host
  } catch {
    return ''
  }
})
const path = computed(() => {
  try {
    return new URL(props.url).pathname.split('/').filter(Boolean).join(' › ')
  } catch {
    return ''
  }
})
</script>

<template>
  <div class="flex flex-col gap-2">
    <div class="flex items-center justify-between gap-2">
      <span class="text-xs font-medium text-muted uppercase">{{ t('share.seo.preview') }}</span>
      <UTabs v-model="view" :items="views" :content="false" color="neutral" size="xs" :ui="SEGMENTED_UI" :aria-label="t('share.seo.preview')" />
    </div>

    <!-- Link card (chats, social posts, email). -->
    <div v-if="view === 'card'" class="overflow-hidden rounded-lg border border-default bg-default" dir="auto">
      <div class="aspect-[1.91/1] w-full bg-elevated">
        <img v-if="image" :src="image" alt="" class="size-full object-cover">
        <div v-else class="flex size-full flex-col items-center justify-center gap-1 text-muted">
          <UIcon name="i-lucide-image" class="size-6" />
          <span class="text-xs">{{ t('share.seo.noImage') }}</span>
        </div>
      </div>
      <div class="flex flex-col gap-0.5 border-t border-default bg-elevated/40 px-3 py-2.5">
        <span class="truncate text-[11px] tracking-wide text-muted uppercase" dir="ltr">{{ host }}</span>
        <span class="line-clamp-2 text-sm font-semibold text-highlighted">{{ title }}</span>
        <span v-if="description" class="line-clamp-2 text-xs text-toned">{{ description }}</span>
      </div>
    </div>

    <!-- Search result. -->
    <div v-else class="rounded-lg border border-default bg-default p-3" dir="auto">
      <div v-if="noindex" class="flex items-center gap-2 text-xs text-muted">
        <UIcon name="i-lucide-eye-off" class="size-4" />{{ t('share.seo.hiddenFromSearch') }}
      </div>
      <template v-else>
        <div class="flex items-center gap-2">
          <span class="flex size-6 shrink-0 items-center justify-center rounded-full bg-elevated text-[10px] font-semibold text-highlighted">{{ siteName.slice(0, 1).toUpperCase() }}</span>
          <div class="min-w-0 leading-tight">
            <p class="truncate text-xs text-highlighted">{{ siteName }}</p>
            <p class="truncate text-[11px] text-muted" dir="ltr">{{ host }}<template v-if="path"> › {{ path }}</template></p>
          </div>
        </div>
        <p class="mt-1.5 line-clamp-1 text-base text-info">{{ title }}</p>
        <p v-if="description" class="line-clamp-2 text-xs text-toned">{{ description }}</p>
      </template>
    </div>
  </div>
</template>
