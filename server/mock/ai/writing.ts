/**
 * The mock assistant's writing help (F19 M5; translating is in translator.ts), built in (no outside service, decided 2026-10-10):
 *
 *   rewrite(text, tone)   plain words for officialese, long sentences split, all-capitals calmed, and the tone
 *                         asked for (friendly adds "please" to instructions, formal drops contractions).
 *   readingAge(texts)     an estimate (Flesch-Kincaid grade + 5) to show the effect.
 */
import type { AiRewriteReason } from '#shared/types/ai'

const PLAIN: [RegExp, string][] = [
  [/\butili[sz]e\b/gi, 'use'],
  [/\bcommence\b/gi, 'start'],
  [/\bprior to\b/gi, 'before'],
  [/\bin order to\b/gi, 'to'],
  [/\bterminate\b/gi, 'end'],
  [/\bsufficient\b/gi, 'enough'],
  [/\bapproximately\b/gi, 'about'],
  [/\bpurchase\b/gi, 'buy'],
  [/\bendeavou?r\b/gi, 'try'],
  [/\badditional\b/gi, 'more'],
  [/\bdemonstrate\b/gi, 'show'],
  [/\bfacilitate\b/gi, 'help'],
  [/\bindividuals\b/gi, 'people'],
  [/\bindividual\b/gi, 'person'],
  [/\bobtain\b/gi, 'get'],
  [/\bregarding\b/gi, 'about'],
  [/\bin the event that\b/gi, 'if'],
  [/\bat this point in time\b/gi, 'now'],
  [/\bwhilst\b/gi, 'while'],
  [/\bnumerous\b/gi, 'many'],
  [/\bascertain\b/gi, 'find out'],
  [/\bin respect of\b/gi, 'about'],
  [/\bin accordance with\b/gi, 'under'],
  [/\bkindly\b/gi, 'please'],
  [/\bstate\b(?= (your|the|whether))/gi, 'tell us'],
  [/\bprovide details of\b/gi, 'tell us about'],
  [/\bis required to be\b/gi, 'must be'],
  [/\bit is requested that you\b/gi, 'please'],
]
const CONTRACTIONS: [RegExp, string][] = [
  [/\bdon['’]t\b/gi, 'do not'],
  [/\bcan['’]t\b/gi, 'cannot'],
  [/\bwon['’]t\b/gi, 'will not'],
  [/\bisn['’]t\b/gi, 'is not'],
  [/\baren['’]t\b/gi, 'are not'],
  [/\bdidn['’]t\b/gi, 'did not'],
  [/\bwe['’]ll\b/gi, 'we will'],
  [/\byou['’]ll\b/gi, 'you will'],
  [/\bwe['’]re\b/gi, 'we are'],
  [/\byou['’]re\b/gi, 'you are'],
  [/\bit['’]s\b/gi, 'it is'],
]
const IMPERATIVE = /^(enter|give|tell|choose|select|pick|add|upload|describe|list|write|provide|confirm|sign)\b/i

const keepCase = (original: string, replacement: string) => (original[0] === original[0]?.toUpperCase() ? replacement[0]!.toUpperCase() + replacement.slice(1) : replacement)
const words = (text: string) => text.split(/\s+/).filter(word => /\p{L}/u.test(word))

/** A plainer version of one text in the tone asked for, with why it changed (unchanged = no reasons). */
export function rewrite(text: string, tone: 'plain' | 'friendly' | 'formal', english = true): { text: string; reasons: AiRewriteReason[] } {
  const reasons = new Set<AiRewriteReason>()
  let out = text
  if (out.length > 6 && out === out.toUpperCase() && /\p{L}/u.test(out)) {
    out = out.charAt(0) + out.slice(1).toLowerCase()
    reasons.add('caps')
  }
  // Plain words and tone are English word lists; other languages get the language-neutral checks only
  for (const [pattern, plain] of english ? PLAIN : []) {
    if (pattern.test(out)) {
      out = out.replace(pattern, match => keepCase(match, plain))
      reasons.add('plain_words')
    }
    pattern.lastIndex = 0
  }
  // One idea per sentence: a long sentence splits at "; " or ", and"
  out = out
    .split(/(?<=[.!?])\s+/)
    .map(sentence => {
      if (words(sentence).length <= 25) return sentence
      const parts = sentence.split(/;\s+|,\s+and\s+/)
      if (parts.length < 2) return sentence
      reasons.add('long_sentence')
      return parts.map((part, index) => `${index ? part.charAt(0).toUpperCase() + part.slice(1) : part}`.replace(/[.;,]?$/, '.')).join(' ')
    })
    .join(' ')
  if (/\b(is|are|was|were|be) (required|expected|requested)\b/i.test(out)) reasons.add('passive')
  if (english && tone === 'friendly' && IMPERATIVE.test(out) && !/^please\b/i.test(out)) {
    out = `Please ${out.charAt(0).toLowerCase()}${out.slice(1)}`
    reasons.add('tone_friendly')
  }
  if (english && tone === 'formal')
    for (const [pattern, full] of CONTRACTIONS)
      if (pattern.test(out)) {
        out = out.replace(pattern, match => keepCase(match, full))
        reasons.add('tone_formal')
      }
  return { text: out, reasons: out === text ? [] : [...reasons] }
}

const syllables = (word: string) => {
  const w = word.toLowerCase().replace(/[^a-z]/g, '')
  if (!w) return 0
  const groups = w.replace(/(?:[^laeiouy]es|ed|[^laeiouy]e)$/, '').replace(/^y/, '').match(/[aeiouy]{1,2}/g)
  return Math.max(1, groups?.length ?? 1)
}

/** Reading age (years) of a set of texts: Flesch-Kincaid grade + 5, at least 6. */
export function readingAge(texts: string[]): number {
  const all = texts.join(' ').replace(/<[^>]+>/g, ' ')
  const list = words(all)
  if (!list.length) return 6
  // Each text (a question, an option, a help line) is at least one sentence of its own
  const sentences = Math.max(1, texts.reduce((sum, text) => sum + Math.max(1, text.replace(/<[^>]+>/g, ' ').split(/[.!?]+\s/).filter(part => words(part).length).length), 0))
  const grade = 0.39 * (list.length / sentences) + 11.8 * (list.reduce((sum, word) => sum + syllables(word), 0) / list.length) - 15.59
  return Math.max(6, Math.round(grade + 5))
}
