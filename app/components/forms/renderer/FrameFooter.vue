<!-- Public form page footer: © organisation · its website, and the secure-by-Formalie line. -->
<script setup lang="ts">
defineProps<{
  org: { name: string }
  website: string | null
  websiteHost: string
  year: number
  /** Minimal style: one centred line. */
  slim?: boolean
}>()
</script>

<template>
  <footer class="border-t border-(--ui-border) text-xs text-(--ui-text-muted)">
    <div
      class="mx-auto flex max-w-5xl gap-2 px-4 py-5 @xl:px-6"
      :class="
        slim
          ? 'flex-col items-center text-center'
          : 'flex-col items-center text-center @xl:flex-row @xl:justify-between @xl:text-start'
      "
    >
      <p v-if="!slim" class="flex flex-wrap items-center justify-center gap-x-2 gap-y-1">
        <span>© {{ year }} {{ org.name }}</span>
        <template v-if="website">
          <span aria-hidden="true">·</span>
          <a
            :href="website"
            target="_blank"
            rel="noopener noreferrer"
            class="inline-flex items-center gap-1 font-medium text-(--ui-text) underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-(--ui-primary)"
          >
            {{ websiteHost }}<UIcon name="i-lucide-arrow-up-right" class="size-3" />
          </a>
        </template>
      </p>
      <FormsRendererFrameSecured />
    </div>
  </footer>
</template>
