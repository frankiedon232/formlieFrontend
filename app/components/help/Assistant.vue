<!--
  The help assistant (F25, owner 2026-10-10): a floating button on the Help pages opens a chat. It starts with
  every question people ask, by area; a question opens its answer in the chat, and anything typed is answered
  from the knowledge base (the best steps or paragraph, the articles to read, a matching question), with
  "email support" when nothing fits. Uses only the help centre, never the workspace's data, so it works for
  everyone. Esc closes; the conversation stays while you move around the help centre.
-->
<script setup lang="ts">
import { HELP_CATEGORIES, type HelpBlock, type HelpCategory, type HelpFaq, type HelpHome, type HelpSearchResult } from '#shared/types/help'
import { HELP_CATEGORY_ICONS, helpArticlePath } from '#shared/utils/help/categories'

interface Message {
  id: number
  from: 'you' | 'bot'
  text?: string
  blocks?: HelpBlock[]
  links?: { label: string; to: string }[]
  /** Nothing found: offer support. */
  support?: boolean
}

const { t, locale } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()

const open = ref(false)
const faqs = ref<HelpFaq[] | null>(null)
const areas = ref<Record<string, HelpCategory>>({})
const messages = ref<Message[]>([])
const question = ref('')
const thinking = ref(false)
const area = ref<HelpCategory | null>(null)
const supportEmail = ref<string | null>(null)
let counter = 0
const say = (message: Omit<Message, 'id'>) => messages.value.push({ ...message, id: ++counter })

async function load() {
  if (faqs.value) return
  try {
    const [list, index, home] = await Promise.all([api.get<HelpFaq[]>('/help/faqs', { lang: locale.value }, { background: true }), api.get<{ id: string; category: HelpCategory }[]>('/help/articles', { lang: locale.value }, { background: true }), api.get<HelpHome>('/help/home', { lang: locale.value }, { background: true })])
    faqs.value = list.data
    supportEmail.value = home.data.support.email
    areas.value = Object.fromEntries(index.data.map(item => [item.id, item.category]))
  } catch (error) {
    handle(error, { silent: true })
    faqs.value = []
  }
}
watch(open, value => value && void load())
watch(locale, () => ((faqs.value = null), open.value && void load()))

const groups = computed(() => HELP_CATEGORIES.map(key => ({ key, items: (faqs.value ?? []).filter(item => item.category === key) })).filter(group => group.items.length && (!area.value || group.key === area.value)))
const articleLink = (id: string | null) => (id && areas.value[id] ? helpArticlePath({ id, category: areas.value[id]! }) : null)

const list = useTemplateRef<HTMLElement>('list')
const scrollDown = () => nextTick(() => list.value?.scrollTo({ top: list.value.scrollHeight, behavior: 'smooth' }))

function pick(faq: HelpFaq) {
  say({ from: 'you', text: faq.question })
  const link = articleLink(faq.article)
  say({ from: 'bot', text: faq.answer, links: link ? [{ label: t('help.readMore'), to: link }] : [] })
  void scrollDown()
}

async function ask() {
  const text = question.value.trim()
  if (!text || thinking.value) return
  question.value = ''
  say({ from: 'you', text })
  void scrollDown()
  thinking.value = true
  try {
    const { data } = await api.get<HelpSearchResult>('/help/search', { q: text, lang: locale.value }, { background: true })
    const links = [...(data.answer ? [{ label: data.answer.article.title, to: helpArticlePath(data.answer.article) }] : []), ...data.articles.filter(item => item.id !== data.answer?.article.id).slice(0, 2).map(item => ({ label: item.title, to: helpArticlePath(item) }))]
    if (data.answer) say({ from: 'bot', text: t('help.bot.found'), blocks: data.answer.blocks, links })
    else if (data.faqs[0]) say({ from: 'bot', text: data.faqs[0].answer, links: [...(articleLink(data.faqs[0].article) ? [{ label: t('help.readMore'), to: articleLink(data.faqs[0].article)! }] : []), ...links] })
    else if (links.length) say({ from: 'bot', text: t('help.bot.maybe'), links })
    else say({ from: 'bot', text: t('help.bot.none'), support: true })
  } catch (error) {
    handle(error)
    say({ from: 'bot', text: t('help.bot.failed') })
  } finally {
    thinking.value = false
    void scrollDown()
  }
}
const reset = () => ((messages.value = []), (area.value = null))
</script>

<template>
  <div>
    <UTooltip :text="t('help.bot.open')">
      <UButton
        icon="i-lucide-bot-message-square"
        color="neutral"
        size="xl"
        class="fixed end-5 bottom-5 z-40 rounded-full shadow-xl sm:end-8 sm:bottom-8"
        :aria-label="t('help.bot.open')"
        :aria-expanded="open"
        @click="open = true"
      />
    </UTooltip>

    <USlideover v-model:open="open" :title="t('help.bot.title')" :description="t('help.bot.desc')" :ui="{ content: 'w-full sm:max-w-md', body: 'flex min-h-0 flex-col gap-0 p-0 sm:p-0' }">
      <template #body>
        <div ref="list" class="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-4" aria-live="polite">
          <!-- Hello, and every question people ask -->
          <div class="flex items-start gap-2">
            <span class="flex size-7 shrink-0 items-center justify-center rounded-full bg-inverted text-inverted"><UIcon name="i-lucide-bot" class="size-4" /></span>
            <div class="flex min-w-0 flex-col gap-2 rounded-2xl rounded-ss-sm bg-elevated px-3 py-2 text-sm text-default">{{ t('help.bot.hello') }}</div>
          </div>
          <div v-if="!faqs" class="flex flex-col gap-1.5 ps-9"><USkeleton v-for="n in 5" :key="n" class="h-7 w-full rounded-full" /></div>
          <div v-else class="flex flex-col gap-3 ps-9">
            <div class="-mx-1 flex gap-1.5 overflow-x-auto px-1 pb-1" role="group" :aria-label="t('help.areas')">
              <UButton :label="t('help.faq.all')" color="neutral" :variant="area ? 'outline' : 'solid'" size="xs" class="shrink-0 rounded-full" @click="area = null" />
              <UButton v-for="key in HELP_CATEGORIES.filter(item => faqs!.some(faq => faq.category === item))" :key="key" :label="t(`help.category.${key}.name`)" :icon="HELP_CATEGORY_ICONS[key]" color="neutral" :variant="area === key ? 'solid' : 'outline'" size="xs" class="shrink-0 rounded-full" :aria-pressed="area === key" @click="area = area === key ? null : key" />
            </div>
            <section v-for="group in groups" :key="group.key" class="flex flex-col gap-1.5">
              <h3 class="text-[11px] font-medium text-muted uppercase">{{ t(`help.category.${group.key}.name`) }}</h3>
              <UButton v-for="faq in group.items" :key="faq.id" :label="faq.question" color="neutral" variant="outline" size="xs" class="justify-start rounded-2xl text-start whitespace-normal" @click="pick(faq)" />
            </section>
          </div>

          <!-- The conversation -->
          <template v-for="message in messages" :key="message.id">
            <div v-if="message.from === 'you'" class="flex justify-end">
              <p class="max-w-[85%] rounded-2xl rounded-se-sm bg-inverted px-3 py-2 text-sm text-inverted">{{ message.text }}</p>
            </div>
            <div v-else class="flex items-start gap-2">
              <span class="flex size-7 shrink-0 items-center justify-center rounded-full bg-inverted text-inverted"><UIcon name="i-lucide-bot" class="size-4" /></span>
              <div class="flex min-w-0 max-w-[85%] flex-col gap-2 rounded-2xl rounded-ss-sm bg-elevated px-3 py-2 text-sm text-default">
                <p v-if="message.text">{{ message.text }}</p>
                <HelpBlocks v-if="message.blocks?.length" :blocks="message.blocks" compact @show="open = false" />
                <div v-if="message.links?.length" class="flex flex-col items-start gap-1">
                  <UButton v-for="link in message.links" :key="link.to" :label="link.label" trailing-icon="i-lucide-arrow-right" color="neutral" variant="link" size="xs" class="px-0 text-start whitespace-normal" :to="link.to" @click="open = false" />
                </div>
                <UButton v-if="message.support && supportEmail" :label="t('help.support.email')" icon="i-lucide-mail" color="neutral" variant="outline" size="xs" class="self-start" :to="`mailto:${supportEmail}`" />
                <span v-if="message.blocks?.length" class="flex items-center gap-1 text-[11px] text-muted"><UIcon name="i-lucide-sparkles" class="size-3" />{{ t('ai.label.made') }}</span>
              </div>
            </div>
          </template>
          <div v-if="thinking" class="flex items-center gap-2 ps-9 text-xs text-muted" role="status"><UIcon name="i-lucide-loader-circle" class="size-3.5 animate-spin" />{{ t('help.bot.thinking') }}</div>
        </div>

        <form class="flex items-center gap-2 border-t border-default p-3" @submit.prevent="ask">
          <UButton v-if="messages.length" icon="i-lucide-rotate-ccw" color="neutral" variant="ghost" square :aria-label="t('help.bot.reset')" @click="reset" />
          <UInput v-model="question" :placeholder="t('help.bot.placeholder')" :maxlength="200" class="min-w-0 flex-1" autofocus :aria-label="t('help.bot.placeholder')" />
          <UButton type="submit" icon="i-lucide-send-horizontal" color="neutral" square :loading="thinking" :disabled="!question.trim()" :aria-label="t('help.bot.send')" />
        </form>
      </template>
    </USlideover>
  </div>
</template>
