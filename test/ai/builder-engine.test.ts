import { describe, expect, it } from 'vitest'
import { buildSchema, opts, page, q, row } from '../../shared/templates/kit'
import { assistForm } from '../../server/mock/ai/builderEngine'

const schema = buildSchema({
  key: 't',
  category: 'business',
  icon: '',
  minutes: 1,
  name: 'Customer feedback',
  description: '',
  pages: [
    page('One', [
      q('full_name', 'Full name'),
      q('short_text', 'Email'),
      q('short_text', 'Email'),
      q('toggle', 'Did anything go wrong?'),
      q('long_text', 'Please give details'),
      q('rating', 'How was the service?'),
      q('long_text', 'What could we do better?'),
      row(q('radio', 'Where did you hear about us?', { options: opts('Search', 'Friend', 'Other') }), q('short_text', 'Where exactly?')),
      q('image', 'Logo'),
    ]),
  ],
})

describe('AI builder help (mock)', () => {
  it('finds problems and offers fixes', () => {
    const found = assistForm('check', schema, 'Customer feedback')
    const problems = found.map(item => (item.kind === 'fix' ? item.problem : null))
    expect(problems).toContain('email_type')
    expect(problems).toContain('duplicate')
    expect(problems).toContain('image_alt')
    expect(problems).toContain('no_required')
  })

  it('adds follow-ups after a yes, a low rating and Other', () => {
    const rules = assistForm('logic', schema, 'Customer feedback').map(item => (item.kind === 'add_rule' ? item.note.code : null))
    expect(rules).toEqual(expect.arrayContaining(['follow_up', 'low_rating', 'other_option']))
  })

  it('writes help only where a kind of question has a useful one', () => {
    const help = assistForm('help', schema, 'Customer feedback')
    expect(help.some(item => item.kind === 'set_help' && item.label === 'How was the service?')).toBe(true)
    expect(help.every(item => item.kind === 'set_help' && item.help.length > 5)).toBe(true)
  })

  it('suggests fields the form is missing, never ones it has', () => {
    const fields = assistForm('fields', schema, 'Customer feedback survey')
    expect(fields.length).toBeGreaterThan(0)
    for (const item of fields) if (item.kind === 'add_field') expect(item.field.type).not.toBe('full_name')
    expect(fields.some(item => item.kind === 'add_field' && item.field.type === 'consent')).toBe(true)
  })
})

describe('AI builder help: follow-ups', () => {
  it('does not tie an unrelated question to a yes / no', () => {
    const job = buildSchema({ key: 'j', category: 'hr', icon: '', minutes: 1, name: 'Job application', description: '', pages: [page('One', [q('toggle', 'Do you need sponsorship to work in this country?'), q('file_upload', 'CV / résumé')])] })
    expect(assistForm('logic', job, 'Job application')).toEqual([])
  })
})
