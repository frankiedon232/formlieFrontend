<!--
  QR code for the form link (owner, 2026-10-03): branded card or plain code; colour from the form,
  the workspace brand, black, a few presets or any colour; download as PNG (sizes) or SVG. The
  branded card carries the organisation (name + logo / initials in the centre) when the workspace
  has its own subdomain, otherwise Formalie. Works before publishing — the code opens the form
  once it is live.
-->
<script setup lang="ts">
const props = defineProps<{ url: string; formName: string; accent?: string; live: boolean }>()
const open = defineModel<boolean>('open', { default: false })
const { t } = useI18n()
const toast = useToast()
const tenant = useTenant()
const branding = useWorkspaceBranding()

const qr = useTemplateRef<{ svgText: (logo?: string | null) => string; width: () => number; height: () => number }>('qr')

// Style
const style = ref<'branded' | 'plain'>('branded')
const styles = computed(() => [
  { value: 'branded', label: t('forms.qr.branded'), icon: 'i-lucide-badge-check' },
  { value: 'plain', label: t('forms.qr.plain'), icon: 'i-lucide-qr-code' },
])

// Colours: form, brand, black, presets, custom
const valid = (c?: string | null): c is string => !!c && /^#[0-9a-f]{6}$/i.test(c)
const PRESETS = ['#1d4ed8', '#047857', '#b91c1c', '#7c3aed', '#c2410c', '#0e7490']
const swatches = computed(() => [
  ...(valid(props.accent) ? [{ key: 'form', label: t('forms.qr.accent'), color: props.accent }] : []),
  ...(valid(branding.value.primary) && branding.value.primary !== props.accent ? [{ key: 'brand', label: t('forms.qr.brand'), color: branding.value.primary }] : []),
  { key: 'black', label: t('forms.qr.black'), color: '#18181b' },
  ...PRESETS.map(color => ({ key: color, label: color, color })),
])
const color = ref('#18181b')
watch(open, value => value && (color.value = swatches.value[0]!.color))

// Who the card shows
const org = computed(() =>
  tenant.profile.value?.subdomain ? { name: tenant.profile.value.name, logo: branding.value.logo_url } : null,
)
const host = computed(() => {
  try {
    return new URL(props.url).host.replace(/:\d+$/, '')
  } catch {
    return ''
  }
})

// Downloads
const pixels = ref('1024')
const sizes = [
  { value: '512', label: '512 px' },
  { value: '1024', label: '1024 px' },
  { value: '2048', label: '2048 px' },
]
const fileName = computed(() => `${props.formName.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'form'}-qr`)

/** The logo as a data URL, so the downloaded file has no outside links (same-origin image). */
function logoData(): Promise<string | null> {
  const src = org.value?.logo
  if (!src) return Promise.resolve(null)
  return new Promise(resolve => {
    const image = new Image()
    image.onload = () => {
      const canvas = document.createElement('canvas')
      canvas.width = image.naturalWidth || 256
      canvas.height = image.naturalHeight || 256
      canvas.getContext('2d')!.drawImage(image, 0, 0)
      try {
        resolve(canvas.toDataURL('image/png'))
      } catch {
        resolve(null)
      }
    }
    image.onerror = () => resolve(null)
    image.src = src
  })
}
function save(href: string, name: string) {
  const link = document.createElement('a')
  link.href = href
  link.download = name
  link.click()
}
const { busy, run } = useBusy()
async function download(kind: 'png' | 'svg') {
  await run(async () => {
    if (!qr.value) return
    const svg = qr.value.svgText(await logoData())
    const blobUrl = URL.createObjectURL(new Blob([svg], { type: 'image/svg+xml' }))
    try {
      if (kind === 'svg') save(blobUrl, `${fileName.value}.svg`)
      else {
        const width = Number(pixels.value)
        const height = Math.round((width * qr.value.height()) / qr.value.width())
        const image = new Image()
        await new Promise<void>((resolve, reject) => {
          image.onload = () => resolve()
          image.onerror = () => reject(new Error('render'))
          image.src = blobUrl
        })
        const canvas = document.createElement('canvas')
        canvas.width = width
        canvas.height = height
        canvas.getContext('2d')!.drawImage(image, 0, 0, width, height)
        save(canvas.toDataURL('image/png'), `${fileName.value}.png`)
      }
      toast.add({ title: t('forms.qr.downloaded'), icon: 'i-lucide-download', color: 'success' })
    } catch {
      toast.add({ title: t('forms.qr.failed'), icon: 'i-lucide-circle-alert', color: 'error' })
    } finally {
      setTimeout(() => URL.revokeObjectURL(blobUrl), 2000)
    }
  })
}
</script>

<template>
  <AppModal v-model:open="open" :title="t('forms.qr.title')" :description="t('forms.qr.desc')" :ui="{ content: 'sm:max-w-2xl' }">
    <template #body>
      <div class="flex flex-col gap-5 sm:flex-row sm:items-start">
        <div class="mx-auto w-full max-w-64 shrink-0 sm:mx-0" :class="style === 'plain' ? 'max-w-52 overflow-hidden rounded-lg border border-default' : ''">
          <FormsShareQrCode
            ref="qr"
            :value="url"
            :color="color"
            :branded="style === 'branded'"
            :org="org"
            :form-name="formName"
            :host="host"
            :scan-label="t('forms.qr.scan')"
            :label="t('forms.qr.alt', { name: formName })"
          />
        </div>

        <div class="flex min-w-0 flex-1 flex-col gap-4">
          <UAlert v-if="!live" icon="i-lucide-info" color="neutral" variant="soft" :description="t('forms.qr.notLive')" :ui="{ description: 'text-xs' }" />
          <UFormField :label="t('forms.qr.style')" :description="style === 'branded' ? (org ? t('forms.qr.brandedOrg') : t('forms.qr.brandedFormalie')) : t('forms.qr.plainHint')">
            <UTabs v-model="style" :items="styles" :content="false" color="neutral" size="xs" :ui="SEGMENTED_UI" class="w-full" />
          </UFormField>

          <UFormField :label="t('forms.qr.colour')">
            <div class="flex flex-wrap items-center gap-1.5" role="radiogroup" :aria-label="t('forms.qr.colour')">
              <UTooltip v-for="swatch in swatches" :key="swatch.key" :text="swatch.label">
                <button
                  type="button"
                  role="radio"
                  :aria-checked="color === swatch.color"
                  :aria-label="swatch.label"
                  class="size-7 rounded-full border-2 transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-(--ui-border-inverted)"
                  :class="color === swatch.color ? 'border-inverted scale-110' : 'border-default'"
                  :style="{ background: swatch.color }"
                  @click="color = swatch.color"
                />
              </UTooltip>
            </div>
          </UFormField>
          <FormsDesignerColorField :label="t('forms.qr.custom')" :model-value="color" against="#ffffff" @update:model-value="v => (color = v)" />

          <UFormField :label="t('forms.qr.pngSize')">
            <USelectMenu v-model="pixels" :items="sizes" value-key="value" :search-input="false" class="w-full" />
          </UFormField>
        </div>
      </div>
    </template>
    <template #footer>
      <div class="flex w-full flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <UButton :label="t('forms.qr.svg')" icon="i-lucide-file-code" color="neutral" variant="outline" class="justify-center" :loading="busy" @click="download('svg')" />
        <UButton :label="t('forms.qr.png')" icon="i-lucide-download" color="neutral" class="justify-center" :loading="busy" @click="download('png')" />
      </div>
    </template>
  </AppModal>
</template>
