"""Records the frontend's design rules into tests/vectors/design_rules.json (B6):

- the theme tokens' validation (shared/utils/forms/theme.ts themeSchema) and page design tokens (page-design.ts);
- the workspace default theme for several brandings, every system theme (presets and template category designs)
  and every system page design as the mock builds them (server/mock/routes/themes.ts, pageDesigns.ts);
- theme patches (applyPatch) over odd inputs; the lists behind them (fonts, presets, categories).

    fmly\\Scripts\\python.exe scripts\\dump_design_rules.py [path\\to\\formalieFrontend]

Then scripts/gen_frontend_catalogues.py writes app/modules/design/catalogues.py, and
tests/parity/test_design_rules.py holds the port to these answers.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dump_frontend_rules import ROOT, run_in_node  # noqa: E402

OUT = ROOT / "tests" / "vectors" / "design_rules.json"

ENTRY = r"""
import * as T from '__SHARED__/utils/forms/theme.ts'
import { THEME_FONTS } from '__SHARED__/utils/forms/fonts.ts'
import { PAGE_PRESETS, pageDesignSchema, presetTokens } from '__SHARED__/utils/forms/page-design.ts'
import { TEMPLATE_CATEGORIES } from '__SHARED__/templates/index.ts'

const clone = v => JSON.parse(JSON.stringify(v))
const run = (schema, input) => {
  const r = schema.safeParse(input)
  return r.success ? { input, ok: true, data: r.data } : { input, ok: false, issues: r.error.issues.map(i => ({ path: i.path.join('.'), message: i.message })) }
}
const at = (base, path, value) => {
  const out = clone(base)
  const keys = path.split('.')
  let node = out
  for (const k of keys.slice(0, -1)) node = node[k]
  if (value === '__DELETE__') delete node[keys.at(-1)]
  else node[keys.at(-1)] = value
  return out
}
const capital = key => key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, ' ')

const brandings = [
  { logo_url: null, primary: null },
  { logo_url: '/api/v1/files/AbCdEfGhIjKlMnOpQrStUvWxYz0', primary: '#1A2b3C' },
  { logo_url: null, primary: 'red' },
  { logo_url: 'https://cdn.example/logo.png', primary: null },
]
const systemThemes = b => {
  const base = T.defaultTheme(b)
  return [
    ...T.THEME_PRESETS.filter(p => p.key !== 'workspace').map(p => ({ id: `sys_preset_${p.key}`, name: capital(p.key), tokens: T.applyPatch(base, p.patch) })),
    ...TEMPLATE_CATEGORIES.map(c => ({ id: `sys_category_${c.key}`, name: `${capital(c.key)} design`, tokens: T.applyPatch(base, c.design) })),
  ]
}
const systemPages = b => PAGE_PRESETS.map(p => ({ id: `sys_page_${p.key}`, name: capital(p.key), tokens: presetTokens(T.defaultTheme(b), p.patch) }))

const base = T.defaultTheme(brandings[1])
const themeCases = [base, ...[
  ['layout', 'split'], ['layout', 'grid'], ['page.bg', '#FFF'], ['page.bg', '#abcdef'], ['page.gradient_angle', 361], ['page.overlay', 81],
  ['page.bg_image', 'https://img.example/a.png'], ['page.bg_image', '/api/v1/files/abc-123'], ['page.bg_image', 'http://img.example/a.png'],
  ['page.bg_image', 'javascript:alert(1)'], ['container.width', 'xxl'], ['typography.font', 'lora'], ['typography.font', 'comic_sans'],
  ['colors.primary', 'blue'], ['header.subtitle', 'x'.repeat(301)], ['header.band', 'accent'],
  ['footer.links', [{ label: 'Privacy', href: 'https://acme.example/privacy' }, { label: 5, href: 'http://bad.example' },
                    { label: 'x'.repeat(61), href: 'htt' }, { label: 'Typing', href: 'https://' }, { label: 'JS', href: 'javascript:x' }]],
  ['footer.links', Array.from({ length: 7 }, () => ({ label: 'a', href: 'https://a.example' }))],
  ['footer.text', 'x'.repeat(501)], ['blocks.divider', 'wave'], ['frame.style', 'floating'], ['frame.tone', 'neon'],
  ['thank_you', '__DELETE__'], ['extra', 1], ['colors.extra', 1],
].map(([p, v]) => at(base, p, v)), 'nonsense', null, {}]

const page = presetTokens(T.defaultTheme(brandings[0]), PAGE_PRESETS[0].patch)
const pageCases = [page, at(page, 'frame.style', 'nope'), at(page, 'page.bg', 'x'), at(page, 'frame', '__DELETE__'), at(page, 'extra', 1), null]

const patches = [
  {}, null, 'text', [1, 2], { colors: { primary: '#000000', nope: 'x' } }, { nope: { a: 1 } }, { header: 'flat' },
  { footer: { links: [{ label: 'a', href: 'https://a.example' }] } }, { colors: { primary: undefined } }, { page: { bg_image: null } },
]

process.stdout.write(JSON.stringify({
  theme_fonts: THEME_FONTS, theme_layouts: T.THEME_LAYOUTS, theme_frames: T.THEME_FRAMES,
  theme_presets: T.THEME_PRESETS, template_categories: TEMPLATE_CATEGORIES.map(c => ({ key: c.key, icon: c.icon, design: c.design ?? {} })),
  page_presets: PAGE_PRESETS,
  brandings: brandings.map(b => ({ branding: b, default: T.defaultTheme(b), themes: systemThemes(b), pages: systemPages(b) })),
  theme_cases: themeCases.map(i => run(T.themeSchema, i)),
  page_cases: pageCases.map(i => run(pageDesignSchema, i)),
  patches: patches.map(p => ({ patch: p, result: T.applyPatch(T.defaultTheme(brandings[0]), p) })),
}))
"""


def main() -> None:
    data = run_in_node(ENTRY)
    data["about"] = "Recorded from the frontend's shared/ code by scripts/dump_design_rules.py. Do not edit."
    OUT.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}: {len(data['theme_cases'])} theme cases, "
          f"{len(data['brandings'][0]['themes'])} system themes, {len(data['brandings'][0]['pages'])} page designs")


if __name__ == "__main__":
    main()
