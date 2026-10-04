/**
 * Template categories (F9) — each with an icon, a colour for chips / bullets and a design family,
 * so the catalogue looks varied but every category is recognisable. Templates add their own accent
 * on top. Names live in i18n (`templates.categories.<key>`).
 */
import type { ThemePatch } from '../utils/forms/theme'

export const TEMPLATE_CATEGORY_KEYS = [
  'business',
  'hr',
  'health_safety',
  'events',
  'hospitality',
  'education',
  'operations_it',
  'finance_legal',
  'community',
  'real_estate',
  'sales',
] as const
export type TemplateCategoryKey = (typeof TEMPLATE_CATEGORY_KEYS)[number]

export interface TemplateCategory {
  key: TemplateCategoryKey
  icon: string
  /** Tailwind bg class for the colour bullet (filters, chips). */
  dot: string
  design: ThemePatch
}

export const TEMPLATE_CATEGORIES: TemplateCategory[] = [
  {
    key: 'business',
    icon: 'i-lucide-briefcase-business',
    dot: 'bg-indigo-500',
    design: {
      page: { bg_type: 'color', bg: '#f5f3ff' },
      container: { radius: 'xl', shadow: 'md', border: false },
      colors: { primary: '#4f46e5', input_border: '#ddd6fe' },
      inputs: { radius: 'md' },
      buttons: { radius: 'md' },
      header: { band: 'gradient', band_bg: '#4f46e5', band_to: '#9333ea', align: 'center' },
    },
  },
  {
    key: 'hr',
    icon: 'i-lucide-users-round',
    dot: 'bg-teal-500',
    design: {
      page: { bg_type: 'color', bg: '#f0fdfa' },
      container: { radius: 'lg', shadow: 'sm', border: true },
      colors: { primary: '#0f766e', input_border: '#ccfbf1' },
      typography: { heading_weight: 'bold' },
      header: { band: 'color', band_bg: '#115e59' },
    },
  },
  {
    key: 'health_safety',
    icon: 'i-lucide-shield-plus',
    dot: 'bg-red-500',
    design: {
      page: { bg_type: 'color', bg: '#f4f4f5' },
      container: { width: 'lg', radius: 'md', shadow: 'sm', border: true },
      colors: { primary: '#b91c1c' },
      typography: { font: 'system', heading_weight: 'bold' },
      header: { band: 'color', band_bg: '#7f1d1d' },
      footer: { enabled: true, style: 'band', bg: '#27272a', align: 'start' },
    },
  },
  {
    key: 'events',
    icon: 'i-lucide-calendar-heart',
    dot: 'bg-pink-500',
    design: {
      // Card with an accent header (owner, 2026-10-03: the side panel squeezed the form).
      layout: 'card',
      page: { bg_type: 'gradient', bg: '#fdf2f8', bg_to: '#eef2ff', gradient_angle: 135 },
      container: { width: 'lg', radius: 'xl', shadow: 'md', border: false },
      colors: { primary: '#db2777', input_bg: '#fdf4ff', input_border: '#f5d0fe' },
      typography: { font: 'rounded' },
      inputs: { style: 'soft', radius: 'lg' },
      buttons: { radius: 'full' },
      header: { band: 'accent', band_bg: '#db2777' },
    },
  },
  {
    key: 'hospitality',
    icon: 'i-lucide-concierge-bell',
    dot: 'bg-amber-600',
    design: {
      page: { bg_type: 'color', bg: '#faf7f2' },
      container: { radius: 'none', border: true, shadow: 'none', bg: '#fffdf9', padding: 'lg' },
      typography: { font: 'serif', heading_weight: 'medium' },
      colors: { primary: '#92400e', text: '#292524', muted: '#78716c', input_border: '#d6d3d1' },
      inputs: { radius: 'none', style: 'underline' },
      buttons: { radius: 'none', variant: 'solid' },
      header: { align: 'center', band: 'color', band_bg: '#44403c' },
    },
  },
  {
    key: 'education',
    icon: 'i-lucide-graduation-cap',
    dot: 'bg-sky-500',
    design: {
      page: { bg_type: 'gradient', bg: '#eff6ff', bg_to: '#f0fdf4', gradient_angle: 160 },
      container: { radius: 'xl', shadow: 'md', border: false },
      colors: { primary: '#0369a1', input_bg: '#f8fafc', input_border: '#bae6fd' },
      typography: { font: 'rounded' },
      inputs: { style: 'soft', radius: 'lg' },
      buttons: { radius: 'full' },
      header: { band: 'gradient', band_bg: '#0369a1', band_to: '#0d9488' },
    },
  },
  {
    key: 'operations_it',
    icon: 'i-lucide-server-cog',
    dot: 'bg-slate-600',
    design: {
      // Card with an accent header (owner, 2026-10-03: the side panel squeezed the form).
      layout: 'card',
      page: { bg_type: 'color', bg: '#e2e8f0' },
      container: { width: 'lg', radius: 'lg', shadow: 'lg', border: false },
      colors: { primary: '#0f172a', input_border: '#cbd5e1' },
      typography: { font: 'system' },
      header: { band: 'accent', band_bg: '#0f172a' },
    },
  },
  {
    key: 'finance_legal',
    icon: 'i-lucide-landmark',
    dot: 'bg-emerald-700',
    design: {
      page: { bg_type: 'color', bg: '#f8fafc' },
      container: { width: 'lg', radius: 'sm', shadow: 'sm', border: true },
      colors: { primary: '#065f46', input_border: '#cbd5e1' },
      typography: { font: 'serif', heading_weight: 'semibold' },
      inputs: { radius: 'sm' },
      buttons: { radius: 'sm' },
      header: { band: 'color', band_bg: '#064e3b' },
      footer: { enabled: true, style: 'plain', align: 'center' },
    },
  },
  {
    key: 'community',
    icon: 'i-lucide-hand-heart',
    dot: 'bg-lime-600',
    design: {
      layout: 'plain',
      page: { bg_type: 'color', bg: '#fafaf9' },
      colors: { primary: '#4d7c0f', input_border: '#d6d3d1' },
      typography: { font: 'rounded' },
      inputs: { style: 'soft', radius: 'md' },
      buttons: { radius: 'full', full_width: true },
      footer: { enabled: true, style: 'band', bg: '#365314', align: 'center' },
    },
  },
  {
    key: 'real_estate',
    icon: 'i-lucide-house',
    dot: 'bg-orange-600',
    design: {
      // Card with an accent header (owner, 2026-10-04: the side panel squeezed the form).
      layout: 'card',
      page: { bg_type: 'gradient', bg: '#fff7ed', bg_to: '#f5f5f4', gradient_angle: 160 },
      container: { width: 'lg', radius: 'lg', shadow: 'md', border: false },
      colors: { primary: '#c2410c', input_border: '#e7e5e4' },
      header: { band: 'accent', band_bg: '#9a3412' },
    },
  },
  {
    key: 'sales',
    icon: 'i-lucide-trending-up',
    dot: 'bg-cyan-600',
    design: {
      page: { bg_type: 'color', bg: '#0e7490' },
      container: { radius: 'md', shadow: 'lg', border: false },
      colors: { primary: '#0e7490' },
      typography: { heading_weight: 'bold' },
      buttons: { full_width: true, radius: 'md' },
      header: { align: 'center' },
    },
  },
]

export const categoryOf = (key: string) => TEMPLATE_CATEGORIES.find(category => category.key === key)
