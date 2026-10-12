"""Records the frontend's AI assistant rules (B13) into tests/vectors/ai_rules.json:

- shared/types/ai.ts and shared/utils/ai/kinds.ts (kinds, statuses, sources, keep days, credits, permissions),
- the mock's `maskText` (server/mock/data/aiStore.ts),
- the mock's local engines (server/mock/ai/*): questions.ts, formEngine.ts, builderEngine.ts, themeEngine.ts,
  writing.ts, textAnalysis.ts and analysisEngine.ts (its response store replaced by plain {at, status, data}),
  with the clock held at a chosen moment,
- shared/utils/forms/translations.ts (`formTexts`, `staleKeys`) and shared/templates (`schemaStats`).

    fmly\\Scripts\\python.exe scripts\\dump_ai_rules.py [path\\to\\formalieFrontend]

tests/parity/test_ai_rules.py and tests/parity/test_ai_engines.py hold the ports (app/modules/ai/) to these answers.
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dump_frontend_rules import FRONTEND, ROOT, run_in_node  # noqa: E402

OUT = ROOT / "tests" / "vectors" / "ai_rules.json"


def engine_copy(folder: Path) -> tuple[str, str]:
    """analysisEngine.ts and aiStore's maskText in a form esbuild can bundle on its own (no mock store)."""
    ai = (FRONTEND / "server" / "mock" / "ai").as_posix()
    text = (FRONTEND / "server" / "mock" / "ai" / "analysisEngine.ts").read_text(encoding="utf-8")
    text = text.replace("from './textAnalysis'", f"from '{ai}/textAnalysis.ts'")
    text = re.sub(r"import \{ answersOf, responseSchema, type IndexedResponse \} from '../data/responseData'\n",
                  "type IndexedResponse = { at: number; status: string; data: Record<string, unknown> }\n"
                  "const answersOf = (_form: unknown, entry: IndexedResponse) => entry.data\n"
                  "const responseSchema = (form: { schema: unknown }) => form.schema as never\n", text)
    text = text.replace("import type { StoredForm } from '../data/formStore'\n", "type StoredForm = any\n")
    path = folder / "analysisEngine.ts"
    path.write_text(text, encoding="utf-8")
    store = (FRONTEND / "server" / "mock" / "data" / "aiStore.ts").read_text(encoding="utf-8")
    mask = store[store.index("export const maskText"):]
    mask_path = folder / "mask.ts"
    mask_path.write_text(mask, encoding="utf-8")
    return path.as_posix(), mask_path.as_posix()


ENTRY = r"""
import { AI_KINDS, AI_STATUSES, AI_SOURCES, AI_KEEP_DAYS, AI_ASSIST_ACTIONS, AI_THEMES, AI_TONES } from '__SHARED__/types/ai.ts'
import { AI_KIND_META, AI_DEFAULT_MONTHLY_CREDITS } from '__SHARED__/utils/ai/kinds.ts'
import { formTexts, staleKeys, textHash } from '__SHARED__/utils/forms/translations.ts'
import { schemaStats } from '__SHARED__/templates/index.ts'
import { buildSchema } from '__SHARED__/templates/kit.ts'
import { cleanLabel, seedFor } from '__AI__/questions.ts'
import { draftForm, rankTemplates, titleFrom, listedItems, documentQuestions } from '__AI__/formEngine.ts'
import { assistForm } from '__AI__/builderEngine.ts'
import { themesFromColour, readable, contrast } from '__AI__/themeEngine.ts'
import { rewrite, readingAge } from '__AI__/writing.ts'
import { textOf, themesOf, sentimentOf, periodIn } from '__AI__/textAnalysis.ts'
import { analyse, ask, summarise } from '__ANALYSIS__'
import { maskText } from '__MASK__'

const NOW = Date.UTC(2026, 9, 12, 15, 30)
const RealDate = Date
class HeldDate extends RealDate {
  constructor(...args) { if (args.length) super(...args); else super(NOW) }
  static now() { return NOW }
}
globalThis.Date = HeldDate
const DAY = 86_400_000

// Random ids in suggestions are compared by shape only
const plain = value => JSON.parse(JSON.stringify(value).replace(/"(sg|fld_ai|rule_ai)[0-9a-z_-]*"/g, '"$1"'))

const masks = ['Call me on +44 7700 900123 or mail ana.silva@example.com', 'Reference 2026-03-14 and 2026-03-14T10:20:30Z',
  'Card 4111 1111 1111 1111', 'Phone (020) 7946-0958 please', 'short 12345', 'a.b+c@sub.example.co.uk, x@y', 'Order 1234567890 shipped',
  'Meet at 10:30 on 14/03/2026', '+1 (555) 010-9999', 'nothing personal here']

const phrases = ['name', 'Full name', 'Company name', 'Your email', 'phone number', 'date of birth', 'age', 'signature', 'agree to the site rules',
  'a photo', 'CV upload', 'home address', 'country', 'preferred language', 'website', 'arrival time', 'time of visit', 'start date', 'from when to when',
  'how long', 'budget', 'how many people', 'percentage done', 'how likely to recommend us', 'rating of the service', 'statements', 'priority',
  'department', 'gender', 'T-shirt size', 'dietary needs', 'how did you hear about us', 'best way to contact', 'any allergies', 'employer',
  'comments', 'favourite colour', 'What did you like most about the event?', 'Why did you choose us over other providers in the area today?',
  '- the arrival time;', '  and the reason', 'résumé', 'Event name', 'username']
const prompts = [
  'A sign-in form for visitors at reception: name, company, who they are visiting, arrival time, a photo and agreement to the site rules.',
  'Customer feedback survey', 'An order form with product, quantity, price and delivery address', 'job application for new starters with CV and cover letter',
  'Register for our event: name, email, dietary needs, any allergies, details of allergies', 'I need something', 'Incident report for staff including date, time, location, description, witnesses, photos',
  'Equipment loan request', 'A booking form for appointments including date and time, service, notes', 'Volunteer sign-up form for our volunteers',
  'name, email, phone, company, message, how did you hear about us', 'Expense claim with amount, receipt, date, category, approval and signature, plus comments',
  'Make a quiz', 'Patient intake questionnaire with date of birth, allergies, medications, emergency contact, insurance, consent and signature, gender, address, phone',
  'Hotel guest checkout feedback', 'A newsletter sign up: email and name and interests']
const documents = [
  'Name: ____\nEmail: ____\nShift: Morning / Afternoon / Night\nDo you need parking? ( ) Yes ( ) No\nComments?',
  '# About you\nFull name:\nPhone:\n# Your visit\nDate of visit:\nWhich services did you use? [ ] Cleaning [ ] Repairs [ ] Garden\nQuantity:\nPrice:\nRate us:',
  'SECTION ONE\n1. What is your name?\n2. What is your role?\nSECTION TWO\n- Any concerns?\n- Please give details',
  'This document has no questions at all. It is just prose about policies.']
const drafts = []
for (const prompt of prompts) for (const pages of ['auto', 'one', 'several']) for (const variant of [0, 1, 2]) {
  const r = draftForm({ prompt, pages, variant })
  drafts.push({ prompt, document: null, pages, variant, name: r.def.name, description: r.def.description, schema: buildSchema(r.def), notes: r.notes, based_on: r.based_on, source: r.source, template_pages: r.source === 'template' ? r.def.pages.length : null })
}
for (const document of documents) for (const pages of ['auto', 'one']) {
  const r = draftForm({ prompt: 'Form from the attached document', document, pages, variant: 0 })
  drafts.push({ prompt: 'Form from the attached document', document, pages, variant: 0, name: r.def.name, description: r.def.description, schema: buildSchema(r.def), notes: r.notes, based_on: r.based_on, source: r.source, template_pages: null })
}

const field = (id, type, label, extra = {}) => ({ id, key: id.replace(/^f_/, ''), type, label, width: 12, required: false, ...extra })
const page = (id, title, fields) => ({ id, title, rows: fields.map((f, i) => ({ id: `${id}_r${i}`, fields: [f] })) })
const yesno = [{ value: 'yes', label: 'Yes' }, { value: 'no', label: 'No' }]
const schemas = [
  { schema_version: 1, settings: { language: 'en' }, pages: [page('p1', 'Visitor', [field('f_name', 'full_name', 'Full name'), field('f_company', 'short_text', 'Company'),
    field('f_email', 'short_text', 'Your email'), field('f_phone', 'short_text', 'Mobile phone'), field('f_when', 'short_text', 'Date of visit'),
    field('f_count', 'short_text', 'How many guests'), field('f_park', 'toggle', 'Do you need parking?'), field('f_park_d', 'long_text', 'Please give details'),
    field('f_rate', 'rating', 'How was your visit?', { props: { max: 5 } }), field('f_rate_why', 'long_text', 'What could be better?'),
    field('f_source', 'radio', 'How did you hear about us?', { options: [{ value: 'web', label: 'Website' }, { value: 'other', label: 'Other' }] }),
    field('f_source_o', 'short_text', 'Where else?'), field('f_pic', 'image', '', { props: { src: 'x' } })])], logic: [], thank_you: {} },
  { schema_version: 1, settings: { language: 'en' }, pages: [page('p1', 'Feedback', [field('f_a', 'short_text', 'Comments'), field('f_b', 'short_text', 'Comments'),
    field('f_c', 'dropdown', 'Pick one', { options: [{ value: 'x', label: 'X' }] }), field('f_d', 'long_text', 'A'.repeat(100) + '. Tell us more about it please. Thanks.'),
    field('f_e', 'file_upload', 'Receipt', { props: { max_mb: 5 } }), field('f_f', 'scale', 'Score', { props: { min: 1, max: 7 } }), field('f_g', 'short_text', 'Reference number'),
    field('f_h', 'url', 'Website', { help: 'Already has help' }), field('f_i', 'date', 'Date of birth')]),
    page('p2', 'More', Array.from({ length: 13 }, (_, i) => field(`f_m${i}`, 'checkbox', `Choice ${i}`, { options: yesno })))], logic: [{ id: 'r1', when: { all: [] }, then: [{ action: 'show', target: 'f_d' }] }], thank_you: {} },
]
const names = ['Visitor sign-in form', 'Customer Feedback', 'Untitled', 'Job application']
const assists = []
for (const [s, schema] of schemas.entries()) for (const name of names) for (const action of AI_ASSIST_ACTIONS) assists.push({ schema: s, name, action, suggestions: plain(assistForm(action, schema, name)) })

const colours = ['#0f766e', '#FACC15', '#ffffff', '#000000', '#2563eb', 'nonsense', '#7c3aed', '#f97316']
const moods = ['', 'calm and friendly', 'bold event', 'formal legal', 'playful but minimal']
const themes = []
for (const colour of colours) for (const mood of moods) themes.push({ colour, mood, suggestions: themesFromColour(colour, mood, { logo_url: null }) })
const readables = colours.filter(c => /^#[0-9a-f]{6}$/i.test(c)).map(c => ({ colour: c, readable: readable(c), contrast: contrast(c, '#ffffff') }))

const texts = ['PLEASE COMPLETE ALL FIELDS', 'Kindly utilise this form in order to obtain additional assistance.', 'Provide details of the incident',
  'Enter your name', 'Please enter your name', "Don't forget: we'll call you, it's free and you can't miss it", 'Applicants are required to be over 18.',
  'Describe what happened in as much detail as possible; include the time, the place and the people involved, and anything else you remember that may help us understand.',
  'Short.', 'State your reason prior to commencing', 'In the event that you cannot attend, please call.', 'Ok', '<p>Hello there</p>']
const rewrites = []
for (const text of texts) for (const tone of AI_TONES) for (const english of [true, false]) rewrites.push({ text, tone, english, out: rewrite(text, tone, english) })
const ages = [texts, texts.slice(0, 3), [], ['a'], ['The quick brown fox jumps over the lazy dog. It was not amused.'], ['Information regarding organisational responsibilities.']].map(list => ({ texts: list, age: readingAge(list) }))

const sentences = ['The staff were friendly and quick', 'Waiting time was too long and slow', 'Price is fair', 'The app on my phone was confusing',
  'Delivery arrived late, parcel broken', 'Nothing to add', 'Great experience, thanks!', 'Parking at the building was hard to find', 'took a moment to load',
  'Booking a morning slot was easy', 'I would recommend you to anyone', 'Email replies were missing']
const labels = sentences.map(text => ({ text, themes: themesOf(text), sentiment: sentimentOf(text) }))
const questions = ['How many responses last month?', 'responses this week', 'last week', 'today', 'yesterday', 'this year', 'last year', 'in March', 'past 7 days',
  'last 30 days', 'What happened in December?', 'show everything', 'in may', 'this month']
const periods = questions.map(q => ({ q, period: periodIn(q) }))

const form = { id: 'form1', name: 'Client survey', schema: { schema_version: 1, settings: {}, pages: [page('p1', 'Survey', [
  field('f_name', 'full_name', 'Full name'), field('f_email', 'email', 'Email'), field('f_office', 'radio', 'Which office did you visit?', { options: [{ value: 'riverside', label: 'Riverside' }, { value: 'harbour', label: 'Harbour' }, { value: 'central', label: 'Central' }] }),
  field('f_services', 'checkbox', 'Services used', { options: [{ value: 'tax', label: 'Tax' }, { value: 'audit', label: 'Audit' }, { value: 'payroll', label: 'Payroll' }] }),
  field('f_again', 'toggle', 'Would you come again?'), field('f_rating', 'rating', 'Overall rating', { props: { max: 5 } }), field('f_nps', 'scale', 'How likely are you to recommend us?', { props: { min: 0, max: 10 } }),
  field('f_spend', 'currency', 'Amount spent'), field('f_when', 'date', 'Visit date'), field('f_comments', 'long_text', 'Comments'), field('f_job', 'short_text', 'Job title'),
  field('f_extra', 'short_text', 'Anything to improve'), field('f_hidden', 'hidden', 'Source'), field('f_phone', 'phone', 'Phone'), field('f_addr', 'address', 'Address')])] } }
const offices = ['riverside', 'harbour', 'central']
const statuses = ['new', 'reviewed', 'approved', 'rejected']
const entries = []
for (let i = 0; i < 90; i++) {
  const at = NOW - Math.floor(i * 1.9) * DAY - (i * 37 % 24) * 3_600_000
  entries.push({ id: `r${i}`, number: 90 - i, at, status: statuses[i % 4], data: {
    full_name: `Person ${i}`, email: `p${i}@example.com`, office: offices[(i * 7) % 3], services: i % 5 === 0 ? [] : ['tax', 'audit', 'payroll'].slice(0, 1 + (i % 3)),
    again: i % 3 !== 0, rating: i % 6 === 0 ? null : 1 + (i * 3) % 5, nps: (i * 7) % 11, spend: i % 4 ? 10 + i * 2.5 : '', when: '2026-09-0' + (1 + i % 9),
    comments: i % 4 === 0 ? '' : sentences[i % sentences.length] + (i % 7 === 0 ? ' Call me on +44 7700 900' + String(100 + i) : ''), job: 'Manager',
    extra: i % 5 === 1 ? 'Faster replies by email please' : 'ok', phone: '+44 7700 900111', addr: { line1: '1 High Street', city: 'Town' },
  } })
}
const ranges = [[NOW - 29 * DAY, NOW], [NOW - 6 * DAY, NOW], [NOW - 90 * DAY, NOW - 60 * DAY], [NOW - 200 * DAY, NOW], [NOW, NOW]].map(([a, b]) => [Date.parse(new RealDate(a).toISOString().slice(0, 10)), Date.parse(new RealDate(b).toISOString().slice(0, 10))])
const analyses = ranges.map(([from, to]) => ({ from, to, masked: analyse(form, entries, from, to, maskText), plain: analyse(form, entries, from, to, t => t) }))
const asks = ['How many responses last month?', 'Which office had the most requests?', 'What is the average rating?', 'Average rating per month', 'responses per week',
  'How many said Riverside?', 'top services this year', 'how many new responses', 'average amount spent last 30 days', 'trend by day', 'What is the average?',
  'Which is most popular?', 'count approved this month', 'How many would come again?', 'average score over time', 'breakdown of services in harbour']
  .map(question => ({ question, answer: ask(form, entries, question) }))
const summaries = entries.slice(0, 12).map(entry => ({ id: entry.id, masked: summarise(form, entry, maskText), plain: summarise(form, entry, t => t) }))
const written = entries.slice(0, 12).map(entry => ({ id: entry.id, texts: textOf(form.schema.pages[0].rows.flatMap(r => r.fields), entry.data) }))

const translatable = { ...structuredClone(schemas[0]), settings: { language: 'en', title: 'Visit', guide: { enabled: true, title: 'Before you start', html: '<p>Read <b>this</b></p>' } },
  theme: { header: { subtitle: 'Welcome' } }, thank_you: { title: 'Thanks!', message: 'We got it.' },
  translations: { fr: { 'field.f_name.label': 'Nom complet', 'field.f_company.label': 'Société' } }, translated_from: { fr: { 'field.f_name.label': textHash('Full name'), 'field.f_company.label': 'zzz' } } }
translatable.pages[0].rows.push({ id: 'calc', fields: [field('f_calc', 'calculated', 'Result', { props: { formula: 'if({f_rate} > 3, "Pass", "Fail") & ({f_park} = "yes")' } })] },
  { id: 'x', fields: [field('f_url', 'short_text', 'https://example.com'), field('f_m', 'matrix', 'Rate', { props: { rows: ['Speed', '', '42'] } })] })
const texts_ = formTexts(translatable)

console.log(JSON.stringify({
  catalogue: { kinds: AI_KINDS, statuses: AI_STATUSES, sources: AI_SOURCES, keep_days: AI_KEEP_DAYS, assist: AI_ASSIST_ACTIONS, themes: AI_THEMES, tones: AI_TONES, meta: AI_KIND_META, default_credits: AI_DEFAULT_MONTHLY_CREDITS },
  masks: masks.map(text => ({ text, out: maskText(text) })),
  phrases: phrases.map(p => ({ phrase: p, clean: cleanLabel(p), seed: seedFor(p) })),
  titles: prompts.map(p => ({ prompt: p, title: titleFrom(p, 'Fallback'), items: listedItems(p), ranked: rankTemplates(p).slice(0, 6).map(r => ({ key: r.def.key, score: r.score })) })),
  documents: documents.map(d => ({ document: d, pages: documentQuestions(d).pages })),
  drafts, schemas, assists, themes, readables, rewrites, ages, labels, periods, now: NOW,
  form, entries, analyses, asks, summaries, written,
  translations: { schema: translatable, texts: texts_, stale: [...staleKeys(translatable, 'fr', texts_)], stats: schemaStats(translatable) },
}))
"""


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="formalie-ai-") as tmp:
        analysis, mask = engine_copy(Path(tmp))
        entry = (ENTRY.replace("__AI__", (FRONTEND / "server" / "mock" / "ai").as_posix())
                 .replace("__ANALYSIS__", analysis).replace("__MASK__", mask))
        data = run_in_node(entry)
    data["about"] = "Recorded from the frontend's shared/ code and the mock's AI engines by scripts/dump_ai_rules.py. Do not edit."
    OUT.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}: {len(data['drafts'])} drafts, {len(data['assists'])} assists, "
          f"{len(data['themes'])} theme sets, {len(data['rewrites'])} rewrites, {len(data['asks'])} questions")


if __name__ == "__main__":
    main()
