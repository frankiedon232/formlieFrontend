import { describe, expect, it } from 'vitest'
import type { DataSourceAccessSettings } from '../../shared/types/datasources'
import { defaultSettings } from '../../shared/utils/datasources/engines'
import { finishedTest, planTest, testAt } from '../../server/mock/data/dataSourceSim'

const access: DataSourceAccessSettings = { mode: 'read_write', structure: true, schemas: [] }
const config = (settings: Record<string, string | number | boolean>, engine: 'postgresql' | 'sqlserver' = 'postgresql') => ({ engine, settings: { ...defaultSettings(engine), host: 'db.example.net', database: 'cases', username: 'formalie_app', ...settings }, access })

describe('mock connection test', () => {
  it('passes a well set up connection', () => {
    const test = finishedTest('t', planTest(config({}), { password: 'x' }), 0)
    expect(test.status).toBe('passed')
    expect(test.steps.find(step => step.key === 'ssh')!.status).toBe('skipped')
    expect(test.permissions.every(item => item.status === 'granted')).toBe(true)
  })

  it('stops at the failing step and skips the rest', () => {
    const test = finishedTest('t', planTest(config({}), { password: 'wrong' }), 0)
    expect(test.status).toBe('failed')
    expect(test.steps.map(step => step.status)).toEqual(['passed', 'skipped', 'passed', 'failed', 'skipped', 'skipped'])
    expect(test.steps[3]!.error_code).toBe('FRM-DEST-1002')
  })

  it('reports missing permissions and risky accounts', () => {
    const limited = finishedTest('t', planTest(config({ username: 'formalie_readonly' }), { password: 'x' }), 0)
    expect(limited.status).toBe('warning')
    expect(limited.permissions.filter(item => item.status === 'missing').map(item => item.operation)).toContain('insert')
    expect(finishedTest('t', planTest(config({ username: 'postgres' }), { password: 'x' }), 0).findings).toContain('admin_account')
    expect(finishedTest('t', planTest(config({ ssl_mode: 'disable' }), { password: 'x' }), 0).findings).toContain('tls_off')
  })

  it('reveals the steps over time', () => {
    const plan = planTest(config({}), { password: 'x' })
    const early = testAt('t', plan, 0, 100)
    expect(early.status).toBe('running')
    expect(early.steps[0]!.status).toBe('running')
    expect(early.permissions).toEqual([])
    expect(testAt('t', plan, 0, 60_000).status).toBe('passed')
  })
})
