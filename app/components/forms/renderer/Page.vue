<!--
  A form page with its theme (F8): page background (colour, gradient, image + overlay), layout
  (card · plain · split with an image · full width), header (cover image, logo, title, subtitle),
  the form, and a footer (text, links, logo). The theme is applied as CSS variables on this root
  only — Nuxt UI controls inside pick them up; the portal around it never changes.
  Used by the designer preview, the builder preview and the public form (F9).
-->
<script setup lang="ts">
import type { FormSchemaV1 } from '#shared/utils/forms/schema'

const props = defineProps<{ schema: FormSchemaV1; title: string; preview?: boolean; showThankYou?: boolean }>()
const { t } = useI18n()
const branding = useWorkspaceBranding()
const theme = useFormTheme(() => props.schema.theme)
provideControlStyle(theme)

const vars = computed(() => themeVars(theme.value))
const WIDTH: Record<string, string> = { sm: 'max-w-xl', md: 'max-w-2xl', lg: 'max-w-3xl', xl: 'max-w-5xl' }
const PAD: Record<string, string> = { sm: 'p-4 sm:p-5', md: 'p-5 sm:p-8', lg: 'p-6 sm:p-12' }
const RADIUS: Record<string, string> = { none: 'rounded-none', sm: 'rounded-sm', md: 'rounded-md', lg: 'rounded-xl', xl: 'rounded-3xl' }
const SHADOW: Record<string, string> = { none: 'shadow-none', sm: 'shadow-sm', md: 'shadow-lg', lg: 'shadow-2xl' }
const COVER: Record<string, string> = { sm: 'h-28', md: 'h-44', lg: 'h-64' }
const WEIGHT: Record<string, string> = { medium: 'font-medium', semibold: 'font-semibold', bold: 'font-bold' }

const layout = computed(() => theme.value.layout)
const boxed = computed(() => layout.value === 'card' || layout.value === 'split')
const logo = computed(() => (theme.value.header.show_logo ? theme.value.header.logo || branding.value.logo_url : null))
const footerLogo = computed(() => (theme.value.footer.show_logo ? theme.value.header.logo || branding.value.logo_url : null))
const centred = computed(() => theme.value.header.align === 'center')
const containerClass = computed(() => [
  'w-full overflow-hidden',
  layout.value === 'full' ? '' : WIDTH[theme.value.container.width],
  boxed.value ? [RADIUS[theme.value.container.radius], SHADOW[theme.value.container.shadow], theme.value.container.border ? 'border border-(--ui-border)' : ''] : '',
])
</script>

<template>
  <div
    class="flex min-h-full w-full flex-col items-center text-default"
    :class="layout === 'full' ? '' : 'px-3 py-6 sm:px-6 sm:py-10'"
    :style="{ ...vars, background: pageBackground(theme), fontFamily: 'var(--form-font)', fontSize: 'var(--form-font-size)' }"
  >
    <main :class="containerClass" :style="{ background: layout === 'plain' ? 'transparent' : 'var(--form-container-bg)' }">
      <div :class="layout === 'split' ? 'grid @container md:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]' : ''">
        <!-- Split layout: image beside the form (above it on narrow screens). -->
        <div
          v-if="layout === 'split'"
          class="min-h-40 bg-cover bg-center md:min-h-full"
          :class="theme.split.side === 'end' ? 'md:order-2' : ''"
          :style="theme.split.image ? { backgroundImage: `url(&quot;${theme.split.image}&quot;)` } : { background: 'var(--ui-bg-elevated)' }"
          role="img"
          :aria-label="title"
        />

        <div class="min-w-0">
          <!-- Header: cover, logo, title, subtitle -->
          <div
            v-if="theme.header.cover"
            class="w-full bg-cover bg-center"
            :class="COVER[theme.header.cover_height]"
            :style="{ backgroundImage: `url(&quot;${theme.header.cover}&quot;)` }"
            role="img"
            :aria-label="title"
          />
          <div :class="layout === 'full' ? `mx-auto w-full ${WIDTH[theme.container.width]} ${PAD[theme.container.padding]}` : PAD[theme.container.padding]">
            <header
              v-if="logo || theme.header.show_title || theme.header.subtitle"
              class="mb-6 flex flex-col gap-3"
              :class="centred ? 'items-center text-center' : 'items-start'"
            >
              <img v-if="logo" :src="logo" :alt="t('renderer.page.logo')" class="max-h-12 w-auto max-w-48 object-contain" >
              <div v-if="theme.header.show_title || theme.header.subtitle" class="flex flex-col gap-1">
                <h1 v-if="theme.header.show_title" class="text-2xl text-highlighted" :class="WEIGHT[theme.typography.heading_weight]">
                  {{ title }}
                </h1>
                <p v-if="theme.header.subtitle" class="whitespace-pre-line text-muted">{{ theme.header.subtitle }}</p>
              </div>
            </header>

            <FormsRendererForm :schema="schema" :theme="theme" :preview="preview" :show-thank-you="showThankYou" />
          </div>
        </div>
      </div>
    </main>

    <!-- Footer -->
    <footer
      v-if="theme.footer.enabled"
      class="mt-6 flex w-full flex-col gap-2 px-4 text-xs text-muted"
      :class="[layout === 'full' ? 'pb-6' : WIDTH[theme.container.width], theme.footer.align === 'center' ? 'items-center text-center' : 'items-start']"
    >
      <img v-if="footerLogo" :src="footerLogo" :alt="t('renderer.page.logo')" class="max-h-6 w-auto object-contain opacity-80" >
      <p v-if="theme.footer.text" class="whitespace-pre-line">{{ theme.footer.text }}</p>
      <nav v-if="theme.footer.links.length" class="flex flex-wrap gap-x-4 gap-y-1" :aria-label="t('renderer.page.footerLinks')">
        <a
          v-for="link in theme.footer.links"
          :key="link.href + link.label"
          :href="link.href"
          target="_blank"
          rel="noopener noreferrer"
          class="underline-offset-2 hover:underline"
        >{{ link.label }}</a>
      </nav>
    </footer>
  </div>
</template>
