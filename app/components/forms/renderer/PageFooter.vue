<!--
  Form page footer: text, links, logo. "Plain" is small muted text under the form; "band" is a
  coloured bar — attached to the bottom of the card, or full width under plain / full layouts.
-->
<script setup lang="ts">
import { visibleLinks, type FormTheme } from '#shared/utils/forms/theme'

const props = defineProps<{ theme: FormTheme; logo: string | null; attached?: boolean; widthClass?: string }>()
const { t } = useI18n()
const footer = computed(() => props.theme.footer)
const band = computed(() => footer.value.style === 'band')
const links = computed(() => visibleLinks(props.theme))
const empty = computed(() => !footer.value.text && !links.value.length && !props.logo)
</script>

<template>
  <footer
    class="flex w-full text-xs"
    :class="[
      band ? 'px-5 py-4 sm:px-8' : `mt-6 px-4 text-muted ${widthClass ?? ''}`,
      band && !attached ? 'mt-10 justify-center' : '',
    ]"
    :style="band ? { background: footer.bg, color: readableOn(footer.bg) } : undefined"
  >
    <div
      class="flex w-full flex-col gap-2"
      :class="[footer.align === 'center' ? 'items-center text-center' : 'items-start', band && !attached ? widthClass : '']"
    >
      <img v-if="logo" :src="logo" :alt="t('renderer.page.logo')" class="max-h-6 w-auto object-contain" :class="band ? '' : 'opacity-80'" >
      <p v-if="footer.text" class="whitespace-pre-line" :class="band ? 'opacity-90' : ''">{{ footer.text }}</p>
      <p v-else-if="band && empty" class="flex items-center gap-1.5 opacity-80">
        <UIcon name="i-lucide-lock" class="size-3.5" />
        {{ t('renderer.page.secure') }}
      </p>
      <nav v-if="links.length" class="flex flex-wrap gap-x-4 gap-y-1" :aria-label="t('renderer.page.footerLinks')">
        <a
          v-for="link in links"
          :key="link.href + link.label"
          :href="link.href"
          target="_blank"
          rel="noopener noreferrer"
          class="underline-offset-2 hover:underline"
          :class="band ? 'opacity-90' : ''"
        >{{ link.label }}</a>
      </nav>
    </div>
  </footer>
</template>
