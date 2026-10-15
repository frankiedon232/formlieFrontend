import { describe, expect, it } from 'vitest'
import type { FillEventInput } from '../../shared/utils/analytics/events'
import { answeredSince, createFillRecorder, hasAnswer } from '../../shared/utils/analytics/recorder'

const SESSION = 'visitAAAAAAAAAAAAAAAAAAA'

function recorder() {
  const sent: FillEventInput[] = []
  return { sent, rec: createFillRecorder(SESSION, 'embed', event => sent.push(event)) }
}

describe('fill-in recorder', () => {
  it('sends the view once', () => {
    const { sent, rec } = recorder()
    rec.view()
    rec.view()
    expect(sent).toEqual([{ session: SESSION, kind: 'view', channel: 'embed' }])
  })

  it('sends the start once, after the view', () => {
    const { sent, rec } = recorder()
    rec.start()
    rec.start()
    rec.view()
    expect(sent.map(event => event.kind)).toEqual(['view', 'start'])
  })

  it('sends each answer once and starts the visit first', () => {
    const { sent, rec } = recorder()
    rec.answer('name')
    rec.answer('name')
    rec.answer('email')
    rec.answer('')
    expect(sent.map(event => [event.kind, event.field])).toEqual([
      ['view', undefined],
      ['start', undefined],
      ['answer', 'name'],
      ['answer', 'email'],
    ])
  })

  it('sends each page once and ignores page numbers that are not whole and positive', () => {
    const { sent, rec } = recorder()
    rec.page(0)
    rec.page(1)
    rec.page(0)
    rec.page(-1)
    rec.page(1.5)
    expect(sent.map(event => event.page)).toEqual([0, 1])
  })
})

describe('answers', () => {
  it('knows when a question has a value', () => {
    expect(hasAnswer('')).toBe(false)
    expect(hasAnswer('  ')).toBe(false)
    expect(hasAnswer(null)).toBe(false)
    expect(hasAnswer(undefined)).toBe(false)
    expect(hasAnswer([])).toBe(false)
    expect(hasAnswer(false)).toBe(false)
    expect(hasAnswer({ first: '', last: '' })).toBe(false)
    expect(hasAnswer('a')).toBe(true)
    expect(hasAnswer(0)).toBe(true)
    expect(hasAnswer(true)).toBe(true)
    expect(hasAnswer(['x'])).toBe(true)
    expect(hasAnswer({ first: 'Ana', last: '' })).toBe(true)
  })

  it('lists questions answered since the form opened, never starting values', () => {
    const baseline = { country: 'GB', name: '' }
    const keys = ['name', 'country', 'email']
    expect(answeredSince({ country: 'GB', name: '' }, baseline, keys)).toEqual([])
    expect(answeredSince({ country: 'GB', name: 'Ana' }, baseline, keys)).toEqual(['name'])
    expect(answeredSince({ country: 'FR', name: 'Ana', email: '', other: 'x' }, baseline, keys)).toEqual(['name', 'country'])
  })
})
