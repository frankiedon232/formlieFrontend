/**
 * Help centre (F25, docs/API-CONTRACT.md → Help centre). Written and published by the Formalie team in the
 * platform admin, served read-only to every workspace in the reader's language (English when an article
 * isn't translated yet). Articles are simple blocks so the platform admin's editor writes the same thing.
 */

/** Knowledge base areas, in the order the help home shows them. */
export const HELP_CATEGORIES = ['start', 'forms', 'builder', 'design', 'templates', 'sharing', 'responses', 'analytics', 'lists', 'data', 'api', 'people', 'settings', 'audit', 'ai'] as const
export type HelpCategory = (typeof HELP_CATEGORIES)[number]

/**
 * One block of an article. Text may hold **bold** (shown bold, never as HTML).
 *   show   a "Show me" link that opens the real page (and, with `target`, highlights that control)
 *   media  a screenshot, GIF or short video the Formalie team added (videos with captions)
 */
export type HelpBlock =
  | { type: 'p'; text: string }
  | { type: 'h'; text: string }
  | { type: 'steps'; items: string[] }
  | { type: 'list'; items: string[] }
  | { type: 'tip' | 'note' | 'warning'; text: string }
  | { type: 'show'; label: string; to: string; target?: string }
  | { type: 'media'; kind: 'image' | 'gif' | 'video'; src: string; caption: string; captions_src?: string }

export interface HelpArticleSummary {
  id: string
  category: HelpCategory
  title: string
  summary: string
  /** Minutes to read. */
  minutes: number
  updated_at: string
  /** The language it is shown in (English when not translated yet). */
  language: string
}

export interface HelpArticle extends HelpArticleSummary {
  blocks: HelpBlock[]
  related: HelpArticleSummary[]
  /** The portal page it explains (help in context opens it there). */
  route: string | null
  /** This person's "Was this helpful?" answer, if they gave one. */
  helpful: boolean | null
}

export interface HelpHome {
  categories: { key: HelpCategory; count: number }[]
  /** "New here?": the getting-started path, in order. */
  start: HelpArticleSummary[]
  popular: HelpArticleSummary[]
  updated: HelpArticleSummary[]
  /** Where people get help from a person (from the platform settings). */
  support: { email: string | null; url: string | null }
}

export interface HelpFaq {
  id: string
  category: HelpCategory
  question: string
  answer: string
  article: string | null
}

export interface HelpTerm {
  id: string
  term: string
  definition: string
  article: string | null
}

export interface HelpSearchResult {
  query: string
  /** A short answer from the best article (F25 M4, shown by the AI assistant when it is on): its most relevant part. */
  answer: { article: HelpArticleSummary; blocks: HelpBlock[] } | null
  articles: (HelpArticleSummary & { snippet: string })[]
  faqs: HelpFaq[]
  terms: HelpTerm[]
}

/** A guided tour of a page: each step points at a control marked `data-help="<target>"`. */
export interface HelpTour {
  id: string
  route: string
  title: string
  steps: { target: string; title: string; text: string }[]
}

/** GET /help/context: help for the page someone is on. */
export interface HelpContext {
  article: HelpArticle | null
  more: HelpArticleSummary[]
  tour: HelpTour | null
}

/** What a Contact support request is about (Formalie's own "Contact support" form, shared/utils/platform/forms.ts). */
export const SUPPORT_TOPICS = ['question', 'problem', 'billing', 'account', 'idea', 'other'] as const
export type SupportTopic = (typeof SUPPORT_TOPICS)[number]

