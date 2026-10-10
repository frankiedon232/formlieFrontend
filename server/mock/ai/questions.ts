/**
 * The mock assistant's dictionary of common questions (F19 M2): words in a phrase → the field that asks
 * it best, with sensible options, checks and whether it is usually required. Specific patterns come
 * first ("date of birth" before "date"). Built in, no outside service (decided 2026-10-10).
 */
import type { FieldSeed } from '#shared/templates/kit'
import { agreeScale, opts } from '#shared/templates/kit'

interface Pattern {
  match: RegExp
  seed: (label: string) => Omit<FieldSeed, 'label'> & { label?: string }
}

export const QUESTION_PATTERNS: Pattern[] = [
  { match: /^(?!.*\b(company|organi[sz]ation|business|school|event|project|product|item|file|user ?name|site|venue|course)\b).*\b(full name|name|names)\b/i, seed: () => ({ type: 'full_name', label: 'Full name', required: true }) },
  { match: /\be-?mail/i, seed: () => ({ type: 'email', label: 'Email address', required: true }) },
  { match: /\b(phone|mobile|telephone|cell)\b/i, seed: () => ({ type: 'phone', label: 'Phone number' }) },
  { match: /\b(date of birth|birth ?date|birthday|dob)\b/i, seed: () => ({ type: 'date', label: 'Date of birth' }) },
  { match: /\b(age)\b/i, seed: () => ({ type: 'number', label: 'Age', validation: { min: 0, max: 130 } }) },
  { match: /\b(signature|sign(ed)? (here|below|off))\b/i, seed: () => ({ type: 'signature', label: 'Signature', required: true }) },
  { match: /\b(agree|agreement|consent|accept|terms|rules|policy|declaration|confirm that)\b/i, seed: label => ({ type: 'consent', label: label ? `I agree to ${label.replace(/^(agree(ment)? (to|with)|accept(ance of)?|consent to)\s+/i, '').replace(/^the\s+/i, 'the ')}` : 'I agree', required: true }) },
  { match: /\b(photos?|pictures?|images?|selfie|headshot)\b/i, seed: () => ({ type: 'image_upload', label: 'Photo' }) },
  { match: /\b(cv|resume|résumé|attachments?|documents?|files?|upload|receipts?|invoices? copy|evidence|certificates?)\b/i, seed: label => ({ type: 'file_upload', label: label || 'Attachment' }) },
  { match: /\b(address|where (do )?you live|street|postal)\b/i, seed: () => ({ type: 'address', label: 'Address' }) },
  { match: /\b(country|nationality)\b/i, seed: label => ({ type: 'country', label: label || 'Country' }) },
  { match: /\b(language)\b/i, seed: () => ({ type: 'language', label: 'Preferred language' }) },
  { match: /\b(website|url|link to|portfolio|linkedin)\b/i, seed: label => ({ type: 'url', label: label || 'Website' }) },
  { match: /\b(arrival|departure|check-?in|check-?out|start|end|meeting|appointment) (time|date and time)\b|\bdate and time\b|\bwhen (exactly)?\b/i, seed: label => ({ type: 'datetime', label: label || 'Date and time' }) },
  { match: /\b(time|hour)\b/i, seed: label => ({ type: 'time', label: label || 'Time' }) },
  { match: /\b(dates?|when|deadline|day)\b/i, seed: label => ({ type: 'date', label: label || 'Date' }) },
  { match: /\b(from .* to|period|date range|how long were|stay)\b/i, seed: label => ({ type: 'date_range', label: label || 'Dates' }) },
  { match: /\b(how long|duration)\b/i, seed: label => ({ type: 'duration', label: label || 'Duration' }) },
  { match: /\b(price|cost|amount|budget|salary|fee|total paid|expenses?|spend)\b/i, seed: label => ({ type: 'currency', label: label || 'Amount' }) },
  { match: /\b(quantity|how many|number of|count|qty)\b/i, seed: label => ({ type: 'number', label: label || 'Quantity', validation: { min: 0 } }) },
  { match: /\b(percent|percentage|%)\b/i, seed: label => ({ type: 'percentage', label: label || 'Percentage' }) },
  { match: /\b(nps|recommend us|how likely)\b/i, seed: () => ({ type: 'scale', label: 'How likely are you to recommend us to a friend or colleague?', props: { min: 0, max: 10, min_label: 'Not at all likely', max_label: 'Extremely likely' } }) },
  { match: /\b(rating|rate|stars?|score|satisf(ied|action)|how (good|happy|was))\b/i, seed: label => ({ type: 'rating', label: label || 'How would you rate it?', props: { max: 5 } }) },
  { match: /\b(agree or disagree|statements?)\b/i, seed: label => ({ type: 'radio', label: label || 'How much do you agree?', options: agreeScale() }) },
  { match: /\b(priority|urgency|how urgent)\b/i, seed: () => ({ type: 'radio', label: 'Priority', options: opts('Low', 'Medium', 'High', 'Urgent') }) },
  { match: /\b(department|team)\b/i, seed: label => ({ type: 'dropdown', label: label || 'Department', options: opts('Finance', 'Operations', 'People', 'Sales', 'Support', 'Technology') }) },
  { match: /\b(gender)\b/i, seed: () => ({ type: 'radio', label: 'Gender', options: opts('Woman', 'Man', 'Non-binary', 'Prefer to self-describe', 'Prefer not to say') }) },
  { match: /\b(size)\b/i, seed: label => ({ type: 'radio', label: label || 'Size', options: opts('XS', 'S', 'M', 'L', 'XL') }) },
  { match: /\b(dietary|allerg(y|ies)|food)\b/i, seed: () => ({ type: 'checkbox', label: 'Dietary requirements', options: opts('None', 'Vegetarian', 'Vegan', 'Halal', 'Kosher', 'Gluten free', 'Other') }) },
  { match: /\b(how did you (hear|find)|source|referr(al|ed))\b/i, seed: () => ({ type: 'dropdown', label: 'How did you hear about us?', options: opts('Search engine', 'Social media', 'Friend or colleague', 'Event', 'Advertisement', 'Other') }) },
  { match: /\b(contact (method|preference)|best way to contact)\b/i, seed: () => ({ type: 'radio', label: 'How should we contact you?', options: opts('Email', 'Phone', 'Text message') }) },
  { match: /\b(yes or no|whether|do you|have you|are you|is (there|it)|any)\b/i, seed: label => ({ type: 'toggle', label: label ? toQuestion(label) : 'Yes or no?' }) },
  { match: /\b(company|organi[sz]ation|employer|business)\b/i, seed: label => ({ type: 'short_text', label: label || 'Company' }) },
  { match: /\b(comments?|feedback|notes?|describe|description|details?|explain|reason|why|message|anything else|suggestions?|story|summary)\b/i, seed: label => ({ type: 'long_text', label: label || 'Comments' }) },
]

const SMALL_WORDS = /^(a|an|the|their|your|his|her|its|our|my|some|any|optional|required)\s+/i

/** "the arrival time" → "Arrival time"; trims list words and punctuation. */
export function cleanLabel(phrase: string): string {
  let text = phrase.trim().replace(/^[-*•\d.)\]\s]+/, '').replace(/[.;:,]+$/, '').trim()
  for (let i = 0; i < 3 && SMALL_WORDS.test(text); i++) text = text.replace(SMALL_WORDS, '')
  text = text.replace(/^(and|or|also|plus)\s+/i, '').trim()
  return text ? text[0]!.toUpperCase() + text.slice(1) : ''
}

/** "any allergies" → "Any allergies?" */
export const toQuestion = (label: string) => (/[?]$/.test(label) ? label : `${label}?`)

/** The field for one phrase: the first pattern that matches, else a short text answer. */
export function seedFor(phrase: string): FieldSeed {
  const label = cleanLabel(phrase)
  for (const pattern of QUESTION_PATTERNS) {
    if (!pattern.match.test(phrase)) continue
    const { label: fixed, ...seed } = pattern.seed(label)
    // A pattern's own label wins for well-known fields (Email address); otherwise the person's words stay
    return { ...seed, label: (fixed ?? label) || 'Question' } as FieldSeed
  }
  return { type: phrase.length > 60 || /\?$/.test(phrase) ? (/\b(what|how|why|describe|tell)\b/i.test(phrase) ? 'long_text' : 'short_text') : 'short_text', label: label || 'Question' }
}
