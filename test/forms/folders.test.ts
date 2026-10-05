import { describe, expect, it } from 'vitest'
import { folderColor, pickSidebarFolders } from '../../shared/utils/forms/folders'

const folders = ['a', 'b', 'c', 'd', 'e', 'f', 'g'].map((id, i) => ({ id, count: i }))

describe('sidebar folders', () => {
  it('shows pinned first, then recently opened, then the busiest, at most five', () => {
    const picked = pickSidebarFolders(folders, ['c'], ['a', 'c', 'b'], 5).map(folder => folder.id)
    expect(picked).toEqual(['c', 'a', 'b', 'g', 'f'])
  })

  it('never shows a folder twice and skips folders that are gone', () => {
    expect(pickSidebarFolders(folders, ['x', 'b'], ['b', 'zz'], 3).map(folder => folder.id)).toEqual(['b', 'g', 'f'])
  })

  it('falls back to the busiest folders for someone new', () => {
    expect(pickSidebarFolders(folders, [], [], 2).map(folder => folder.id)).toEqual(['g', 'f'])
  })

  it('maps unknown colours to ink', () => {
    expect(folderColor('teal').text).toContain('teal')
    expect(folderColor('neon')).toEqual(folderColor('ink'))
    expect(folderColor(null)).toEqual(folderColor('ink'))
  })
})
