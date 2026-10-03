<!--
  Public form page footer: © organisation · Terms · Data Privacy Policy (Formalie's legal pages,
  runtimeConfig.public.legal), and the secure-by-Formalie line. Links open in the in-app browser
  so the form stays.
-->
<script setup lang="ts">
defineProps<{
  org: { name: string }
  year: number
  /** Minimal style: centred lines. */
  slim?: boolean
}>()
const { t } = useI18n()
// Platform settings (super admin) when the public page loaded them; the app's config otherwise.
const config = useRuntimeConfig().public.legal
const fromPlatform = useState<{ terms_url: string; privacy_url: string } | null>('public:legal', () => null)
const legal = computed(() => ({
  termsUrl: fromPlatform.value?.terms_url || config.termsUrl,
  privacyUrl: fromPlatform.value?.privacy_url || config.privacyUrl,
}))
const linkClass = 'font-medium text-(--ui-text) underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-(--ui-primary)'
</script>

<template>
  <footer class="border-t border-(--ui-border) text-xs text-(--ui-text-muted)">
    <div
      class="mx-auto flex max-w-5xl gap-2 px-4 py-5 @xl:px-6"
      :class="slim ? 'flex-col items-center text-center' : 'flex-col items-center text-center @xl:flex-row @xl:justify-between @xl:text-start'"
    >
      <p class="flex flex-wrap items-center justify-center gap-x-2 gap-y-1">
        <span>© {{ year }} {{ org.name }}</span>
        <span aria-hidden="true">·</span>
        <FormsRendererFrameLink :href="legal.termsUrl" :title="t('public.frame.terms')" :class="linkClass">{{ t('public.frame.terms') }}</FormsRendererFrameLink>
        <span aria-hidden="true">·</span>
        <FormsRendererFrameLink :href="legal.privacyUrl" :title="t('public.frame.privacy')" :class="linkClass">{{ t('public.frame.privacy') }}</FormsRendererFrameLink>
      </p>
      <FormsRendererFrameSecured />
    </div>
  </footer>
</template>
