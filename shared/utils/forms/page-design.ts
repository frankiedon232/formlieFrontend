/**
 * Page designs (owner 2026-10-04: "add more pages, just like Themes"): the page around a form on
 * its public link, kept in its own library next to Themes. A page design is the part of a form's
 * design that shapes that page: the frame (style, tone, website link, quick facts) and the page
 * background. Applying one copies these tokens into the form's theme and remembers
 * `schema.page_design_id`, so changing or deleting a design never breaks a form.
 */
import { z } from 'zod'
import { themeSchema, type FormTheme } from './theme'

export const pageDesignSchema = z.object({
  frame: themeSchema.shape.frame,
  page: themeSchema.shape.page,
})
export type PageDesignTokens = z.infer<typeof pageDesignSchema>

/** A plain copy (works on reactive objects, which structured cloning refuses). */
const copy = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T

type PagePatch = { frame?: Partial<PageDesignTokens['frame']>; page?: Partial<PageDesignTokens['page']> }

/** Formalie's ready-made page designs (neutral, international). Names: `pages.preset.{key}`. */
export const PAGE_PRESETS: { key: string; patch: PagePatch }[] = [
  { key: 'clean', patch: { frame: { style: 'branded', tone: 'light' }, page: { bg_type: 'color', bg: '#f4f4f5' } } },
  { key: 'midnight_bar', patch: { frame: { style: 'branded', tone: 'dark' }, page: { bg_type: 'color', bg: '#e4e4e7' } } },
  { key: 'brand_bar', patch: { frame: { style: 'branded', tone: 'brand' }, page: { bg_type: 'color', bg: '#fafafa' } } },
  { key: 'spotlight', patch: { frame: { style: 'spotlight', tone: 'brand' }, page: { bg_type: 'color', bg: '#f4f4f5' } } },
  { key: 'spotlight_night', patch: { frame: { style: 'spotlight', tone: 'dark' }, page: { bg_type: 'color', bg: '#e4e4e7' } } },
  { key: 'side_brand', patch: { frame: { style: 'side', tone: 'brand' }, page: { bg_type: 'color', bg: '#fafafa' } } },
  { key: 'side_night', patch: { frame: { style: 'side', tone: 'dark' }, page: { bg_type: 'color', bg: '#f4f4f5' } } },
  { key: 'side_soft', patch: { frame: { style: 'side', tone: 'light' }, page: { bg_type: 'gradient', bg: '#eef2ff', bg_to: '#fdf2f8', gradient_angle: 135 } } },
  { key: 'minimal', patch: { frame: { style: 'minimal', tone: 'light', show_facts: false }, page: { bg_type: 'color', bg: '#ffffff' } } },
  { key: 'minimal_soft', patch: { frame: { style: 'minimal', tone: 'light' }, page: { bg_type: 'gradient', bg: '#f0fdf4', bg_to: '#ecfeff', gradient_angle: 160 } } },
]

/** The page tokens of a form's theme. */
export const pageTokensOf = (theme: FormTheme): PageDesignTokens => ({ frame: copy(theme.frame), page: copy(theme.page) })

/** A preset as full tokens, over a base theme (the workspace default). */
export const presetTokens = (base: FormTheme, patch: PagePatch): PageDesignTokens => ({
  frame: { ...base.frame, ...patch.frame },
  page: { ...base.page, ...patch.page },
})

/** A form's theme with a page design applied (only the page parts change). */
export const withPageDesign = (theme: FormTheme, tokens: PageDesignTokens): FormTheme => ({
  ...theme,
  frame: copy(tokens.frame),
  page: copy(tokens.page),
})
