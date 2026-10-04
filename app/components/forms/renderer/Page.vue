<!--
  A form page with its theme (F8): page background (colour, gradient, image + overlay), layout
  (card · plain · split with an image or a coloured side panel · full width), header (cover
  image, optional colour / gradient band, logo, title, subtitle), the form, and a footer (plain
  text or a coloured bar). The theme is applied as CSS variables on this root only, Nuxt UI
  controls inside pick them up; the portal around it never changes.
  Used by the designer preview, the builder preview and the public form (F10).
-->
<script setup lang="ts">
import type { RendererRespondent, RendererSubmitOutcome } from '#shared/types/public'
import type { FormSchemaV1 } from '#shared/utils/forms/schema'
import { allFields } from '#shared/utils/forms/build'
import { isInputField } from '#shared/utils/forms/fields'

const FormFrame = resolveComponent('FormsRendererFrame')
const props = defineProps<{
  schema: FormSchemaV1
  title: string
  preview?: boolean
  showThankYou?: boolean
  /** Public page: sends the answers (see renderer Form). */
  submit?: (answers: Record<string, unknown>, extra?: { trap?: string }) => Promise<RendererSubmitOutcome>
  /** Show the page frame around the form (public link and previews; never in embeds). */
  framed?: boolean
  /** Public page: already sent from this browser / start one for someone else (renderer Form). */
  respondent?: RendererRespondent
  /** Preview page: jump to a page or the thank-you screen (renderer Form). */
  goTo?: { at: number | 'thanks'; n: number }
  /** Forms in several languages (decision 99): the switcher above the form. */
  languages?: string[]
  language?: string
}>()
const emit = defineEmits<{ at: [at: number | 'thanks']; language: [code: string] }>()
// The title respondents see: the form name, or its version in the form language (settings.title).
const heading = computed(() => props.schema.settings?.title?.trim() || props.title)
const branding = useWorkspaceBranding()
const theme = useFormTheme(() => props.schema.theme)
provideControlStyle(theme)

const vars = computed(() => themeVars(theme.value))
const WIDTH: Record<string, string> = { sm: 'max-w-xl', md: 'max-w-2xl', lg: 'max-w-3xl', xl: 'max-w-5xl' }
const PAD: Record<string, string> = { sm: 'p-4 sm:p-5', md: 'p-5 sm:p-8', lg: 'p-6 sm:p-12' }
const RADIUS: Record<string, string> = { none: 'rounded-none', sm: 'rounded-sm', md: 'rounded-md', lg: 'rounded-xl', xl: 'rounded-3xl' }
const SHADOW: Record<string, string> = { none: 'shadow-none', sm: 'shadow-sm', md: 'shadow-lg', lg: 'shadow-2xl' }
const COVER: Record<string, string> = { sm: 'h-28', md: 'h-44', lg: 'h-64' }

const layout = computed(() => theme.value.layout)
const boxed = computed(() => layout.value === 'card' || layout.value === 'split')
const width = computed(() => WIDTH[theme.value.container.width])
/** Inner padding; full-width layouts keep their content at the chosen width. */
const inner = computed(() => (layout.value === 'full' ? `mx-auto w-full ${width.value} ${PAD[theme.value.container.padding]}` : PAD[theme.value.container.padding]))
// The page frame (public link) shows the organisation; spotlight and side also show the title,
// so the form card doesn't repeat them.
const frameStyle = computed(() => (props.framed ? theme.value.frame.style : null))
const frameOwnsLogo = computed(() => !!frameStyle.value && frameStyle.value !== 'minimal')
const frameOwnsTitle = computed(() => frameStyle.value === 'spotlight' || frameStyle.value === 'side')
const logo = computed(() => (!frameOwnsLogo.value && theme.value.header.show_logo ? theme.value.header.logo || branding.value.logo_url : null))
const footerLogo = computed(() => (theme.value.footer.show_logo ? theme.value.header.logo || branding.value.logo_url : null))
const hasHeader = computed(() => !frameOwnsTitle.value && !!(logo.value || theme.value.header.show_title || theme.value.header.subtitle))

const { profile } = useTenant()
const frameOrg = computed(() => ({
  name: profile.value?.name ?? '',
  logo: theme.value.header.logo || branding.value.logo_url,
  website: profile.value?.website ?? null,
}))
const questions = computed(
  () => allFields(props.schema).filter(f => isInputField(f.type) && f.type !== 'hidden' && f.type !== 'calculated').length,
)
const guide = computed(() => {
  const value = props.schema.settings?.guide
  return value?.enabled && value.html.replace(/<[^>]*>/g, '').trim() ? value : null
})
/** About 20 seconds a question, at least a minute. */
const minutes = computed(() => Math.max(1, Math.round((questions.value * 20) / 60)))

// Where the header goes: in a coloured side panel, on a band, or plain above the form.
const panel = computed(() => (layout.value === 'split' && theme.value.split.panel !== 'image' ? theme.value.split : null))
const band = computed(() => (!panel.value && theme.value.header.band !== 'none' && theme.value.header.band !== 'accent' ? theme.value.header : null))
const footerBand = computed(() => theme.value.footer.enabled && theme.value.footer.style === 'band')
const attachedFooter = computed(() => footerBand.value && boxed.value)

const containerClass = computed(() => [
  'w-full overflow-hidden',
  layout.value === 'full' ? '' : width.value,
  boxed.value ? [RADIUS[theme.value.container.radius], SHADOW[theme.value.container.shadow], theme.value.container.border ? 'border border-(--ui-border)' : ''] : '',
])
</script>

<template>
  <div
    class="flex min-h-full w-full flex-col text-default"
    :style="{ ...vars, background: pageBackground(theme), fontFamily: 'var(--form-font)', fontSize: 'var(--form-font-size)' }"
  >
    <component
      :is="framed ? FormFrame : 'div'"
      v-bind="framed ? { theme, title: heading, intro: theme.header.subtitle, questions, minutes, org: frameOrg } : {}"
      :class="framed ? 'flex-1' : 'contents'"
    >
    <div class="flex w-full flex-1 flex-col items-center" :class="layout === 'full' ? '' : 'px-3 py-6 sm:px-6 sm:py-10'">
      <main :class="containerClass" :style="{ background: layout === 'plain' ? 'transparent' : 'var(--form-container-bg)' }">
        <div :class="layout === 'split' ? 'grid @container md:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]' : ''">
          <!-- Split layout: image or coloured panel beside the form (above it on narrow screens). -->
          <div
            v-if="layout === 'split'"
            class="flex min-h-40 flex-col justify-center bg-cover bg-center md:min-h-full"
            :class="[theme.split.side === 'end' ? 'md:order-2' : '', panel ? PAD[theme.container.padding] : '']"
            :style="
              panel
                ? { background: fillBackground(panel.panel, panel.bg, panel.bg_to, 160) }
                : theme.split.image
                  ? { backgroundImage: `url(&quot;${theme.split.image}&quot;)` }
                  : { background: 'var(--ui-bg-elevated)' }
            "
            :role="panel ? undefined : 'img'"
            :aria-label="panel ? undefined : heading"
          >
            <FormsRendererPageHeader v-if="panel && hasHeader" :theme="theme" :title="heading" :logo="logo" :on="panel.bg" />
          </div>

          <div class="flex min-w-0 flex-col">
            <div
              v-if="theme.header.cover"
              class="w-full bg-cover bg-center"
              :class="COVER[theme.header.cover_height]"
              :style="{ backgroundImage: `url(&quot;${theme.header.cover}&quot;)` }"
              role="img"
              :aria-label="heading"
            />
            <!-- Header band -->
            <div v-if="band && hasHeader" :style="{ background: fillBackground(band.band, band.band_bg, band.band_to) }">
              <FormsRendererPageHeader :class="inner" :theme="theme" :title="heading" :logo="logo" :on="band.band_bg" />
            </div>

            <div class="flex-1" :class="inner">
              <div v-if="language && (languages?.length ?? 0) > 1" class="mb-4 flex justify-end">
                <FormsRendererLanguageSwitch :model-value="language" :languages="languages!" @update:model-value="emit('language', $event)" />
              </div>
              <FormsRendererPageHeader v-if="!band && !panel && hasHeader" class="mb-6" :theme="theme" :title="heading" :logo="logo" />
              <FormsRendererForm :schema="schema" :theme="theme" :preview="preview" :show-thank-you="showThankYou" :submit="submit" :respondent="respondent" :go-to="goTo" @at="emit('at', $event)" />
            </div>

            <FormsRendererPageFooter v-if="attachedFooter" :theme="theme" :logo="footerLogo" attached />
          </div>
        </div>
      </main>

      <FormsRendererPageFooter v-if="theme.footer.enabled && !footerBand" :theme="theme" :logo="footerLogo" :width-class="layout === 'full' ? 'pb-6' : width" />
    </div>

    <!-- Full-width footer bar under plain / full layouts -->
    <FormsRendererPageFooter v-if="footerBand && !attachedFooter" :theme="theme" :logo="footerLogo" :width-class="width" />
    </component>
    <!-- Help guide (creator turned it on and wrote one): floating "?" button. -->
    <FormsRendererGuide v-if="guide" :title="guide.title" :html="guide.html" />
    <!-- Public page: a small line on the form's own background. -->
    <slot name="after" />
  </div>
</template>
