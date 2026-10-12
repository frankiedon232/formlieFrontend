"""Records the frontend's help centre rules and the mock's answers (B14) into tests/vectors/help_rules.json:

- shared/types/help.ts (`HELP_CATEGORIES`) and shared/utils/help/categories.ts (icons, `helpArticlePath`),
  shared/utils/help/routes.ts (`routeMatches`),
- the mock's search rules in server/mock/routes/help.ts (`words`, the little words `STOP`, `answerFor`) and
  helpStore.ts (`articleText`), and what its routes answer: home, the article lists, every article, FAQs, the
  glossary (sorted in the reader's language), the tours, help in context for many pages, and searches.

Full answers are kept for English; for every language a SHA-256 of each answer (canonical
JSON: keys sorted, no spaces) so the content parity covers all 20 languages without a huge file.

    fmly\\Scripts\\python.exe scripts\\dump_help_rules.py [path\\to\\formalieFrontend]

The mock's route and store files are copied into a temporary folder with their mock-only imports (auth, the
persisted store, Nitro's helpers) replaced by stubs; nothing in the frontend is changed. tests/parity/test_help_rules.py
holds the ports (app/modules/help/rules.py) to these answers; tests/db/test_help.py holds the API to them.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dump_frontend_rules import FRONTEND, ROOT, run_in_node  # noqa: E402

OUT = ROOT / "tests" / "vectors" / "help_rules.json"
MOCK = FRONTEND / "server" / "mock"

STUBS = {
    "auth.ts": "export const requireAuth = (event) => event.auth\n",
    "respond.ts": "export class MockError extends Error { constructor(code) { super(code); this.code = code } }\n"
                  "export const ok = (data) => data\n",
    "route.ts": "export const defineMockRoute = (fn) => fn\n",
    "validate.ts": "export const parseBody = (_schema, body) => body\n",
    "persist.ts": "export const loadPersisted = (_name, fallback) => fallback\nexport const savePersisted = () => {}\n",
    "platformStore.ts": "export const platformSupport = () => ({ email: 'support@formalie.com', url: null })\n",
    "zod.ts": "const chain = new Proxy(function () {}, { get: () => chain, apply: () => chain })\nexport const z = chain\n",
}


def copies(folder: Path) -> Path:
    """help.ts and helpStore.ts with their imports pointed at the stubs; `words`, `STOP` and `answerFor` exported."""
    for name, text in STUBS.items():
        (folder / name).write_text(text, encoding="utf-8")
    stub = lambda name: (folder / name).as_posix()  # noqa: E731
    store = (MOCK / "data" / "helpStore.ts").read_text(encoding="utf-8")
    store = store.replace("from '../core/persist'", f"from '{stub('persist.ts')}'")
    (folder / "helpStore.ts").write_text(store, encoding="utf-8")
    route = (MOCK / "routes" / "help.ts").read_text(encoding="utf-8")
    for old, new in (("from 'zod'", f"from '{stub('zod.ts')}'"),
                     ("from '../core/auth'", f"from '{stub('auth.ts')}'"),
                     ("from '../core/respond'", f"from '{stub('respond.ts')}'"),
                     ("from '../core/route'", f"from '{stub('route.ts')}'"),
                     ("from '../core/validate'", f"from '{stub('validate.ts')}'"),
                     ("from '../data/helpStore'", f"from '{stub('helpStore.ts')}'"),
                     ("from '../data/platformStore'", f"from '{stub('platformStore.ts')}'")):
        if old not in route:
            raise SystemExit(f"help.ts no longer imports {old}: update scripts/dump_help_rules.py")
        route = route.replace(old, new)
    route += "\nexport { words, STOP, answerFor }\n"
    path = folder / "help.ts"
    path.write_text(route, encoding="utf-8")
    return path


ENTRY = r"""
import { createHash } from 'node:crypto'
import { HELP_CATEGORIES } from '__SHARED__/types/help.ts'
import { HELP_CATEGORY_ICONS, helpArticlePath } from '__SHARED__/utils/help/categories.ts'
import { routeMatches } from '__SHARED__/utils/help/routes.ts'
import { APP_LOCALES } from '__SHARED__/utils/i18n/locales.ts'
import * as R from '__ROUTE__'
import { helpContent, articleText } from '__STORE__'

process.chdir('__FRONTEND__')
globalThis.getRouterParam = (event, name) => event.params?.[name]
const event = (params = {}) => ({ auth: { user: { id: 'u1' }, tenant: { id: 't1' } }, params })
const call = (handler, query = {}, params = {}) => handler({ event: event(params), query, body: null })

const canonical = value => Array.isArray(value) ? `[${value.map(canonical).join(',')}]`
  : value && typeof value === 'object' ? `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}`
  : JSON.stringify(value ?? null)
const sha = value => createHash('sha256').update(canonical(value)).digest('hex')

const LANGS = APP_LOCALES.map(locale => locale.code)
const FULL = ['en']
const en = helpContent('en')
const ids = en.articles.map(article => article.id)

// Pages for help in context: every article's and tour's page (any form id), plus pages with no help
const pages = [...new Set([...en.articles.map(a => a.route).filter(Boolean), ...en.tours.map(t => t.route)])]
  .map(route => route.replace(/:[a-z]+/g, 'f_123'))
pages.push('/', '/nowhere', '/forms/', '/forms?view=grid', '/forms/f_1/build/extra', '/help/start/welcome', '/FORMS')

const answers = {}
const hashes = {}
for (const lang of LANGS) {
  const out = {
    home: call(R.helpHome, { lang }),
    articles: call(R.listHelpArticles, { lang }),
    by_category: Object.fromEntries([...HELP_CATEGORIES, 'nope'].map(key => [key, call(R.listHelpArticles, { lang, category: key })])),
    article: Object.fromEntries(ids.map(id => [id, call(R.getHelpArticle, { lang }, { id })])),
    faqs: call(R.listHelpFaqs, { lang }),
    faqs_by_category: Object.fromEntries(HELP_CATEGORIES.map(key => [key, call(R.listHelpFaqs, { lang, category: key })])),
    glossary: call(R.listHelpGlossary, { lang }),
    tours: call(R.helpTours, { lang }),
    context: Object.fromEntries(pages.map(path => [path, call(R.helpContext, { lang, path })])),
  }
  hashes[lang] = Object.fromEntries(Object.entries(out).map(([key, value]) =>
    [key, value && typeof value === 'object' && !Array.isArray(value) && key !== 'home'
      ? Object.fromEntries(Object.entries(value).map(([k, v]) => [k, sha(v)])) : sha(value)]))
  if (FULL.includes(lang)) answers[lang] = out
}
// Unknown and missing languages answer in English
const fallback = { unknown: sha(call(R.helpHome, { lang: 'xx' })), none: sha(call(R.helpHome, {})) }

// Search: the mock's answers for chosen questions (our search is PostgreSQL full text; these hold snippets,
// answers and the word rules, and the best article for questions both should agree on)
const englishQueries = ['create a form', 'How do I share a form?', 'invite people', 'export responses', 'webhook',
  'api token', 'conditional logic', 'theme colours', 'two-step sign-in', 'templates', 'folder', 'translate my form',
  'audit trail', 'calculations', 'embed', 'versions', 'trash', 'roles', 'data sources', 'how', 'the', 'xyzzy plugh', '',
  'respon', 'keyboard shortcuts', 'landing page', 'password', 'AI analysis', 'publish', 'where are my forms']
const searches = []
for (const lang of ['en', 'ar', 'zh-CN', 'fr', 'ru', 'ja', 'hi', 'de']) {
  const content = helpContent(lang)
  const queries = lang === 'en' ? englishQueries
    : [...content.articles.slice(0, 16).map(a => a.title), ...content.articles.slice(0, 16).map(a => a.keywords[0]), 'webhook', 'create a form']
  for (const q of queries) {
    const meaningful = R.words(q).filter(word => !R.STOP.has(word))
    const result = call(R.searchHelp, { lang, q })
    searches.push({ lang, q, asked: meaningful.length ? meaningful : R.words(q), query: result.query,
      articles: result.articles.map(a => [a.id, a.snippet]), faqs: result.faqs.map(f => f.id), terms: result.terms.map(t => t.id),
      answer: result.answer && { article: result.answer.article.id, blocks: result.answer.blocks } })
  }
}

// The word rules
const texts = ['Hello, World!', "Don't panic: it's fine", 'Crème brûlée à la carte', 'Ünïcödé façade naïve', 'ÉCOLE École',
  'a b cd e', 'Ctrl + K', '2-step sign-in', 'İstanbul ŞEHİR', 'Москва и Санкт-Петербург', 'Київ, Україна', 'مرحبًا بك في Formalie',
  'أنشئ نموذجك الأول', 'फ़ॉर्म बनाएँ', 'ফর্ম তৈরি করুন', '创建你的第一个表单', 'フォームを作成します', '양식을 만드세요', 'Tạo biểu mẫu đầu tiên',
  'ﬁnancial ﬂow', '½ x²', 'e-mail@example.com', '  spaced   out  ', '', 'émoji 🎉 test', 'Ǆ ǅ ǆ', 'ß Straße STRASSE', 'Ωμέγα ΣΟΦΟΣ']
const wordCases = texts.map(text => ({ text, words: R.words(text) }))

// articleText of every article in every language (hash) and in English (in full)
const articleTexts = Object.fromEntries(LANGS.map(lang => [lang, sha(helpContent(lang).articles.map(a => articleText(a)))]))
const articleTextEn = Object.fromEntries(en.articles.map(a => [a.id, articleText(a)]))

// answerFor: questions against chosen articles
const answerCases = []
for (const lang of ['en', 'fr', 'ru', 'ar']) {
  const content = helpContent(lang)
  for (const q of ['how do I create a form', 'How to share', 'where is the trash', 'what is a theme', 'comment créer', 'как создать',
    'steps to export', 'roles and access', 'webhook retries', 'Cómo publicar', 'HOW', 'set up two-step', 'nothing matches here']) {
    const meaningful = R.words(q).filter(word => !R.STOP.has(word))
    const asked = meaningful.length ? meaningful : R.words(q)
    for (const id of ['first-form', 'share-a-form', 'trash', 'themes', 'webhooks', 'roles-and-access', 'welcome', 'nope']) {
      const answer = R.answerFor(q, asked, id, content.articles)
      answerCases.push({ lang, q, asked, id, answer: answer ? { article: answer.article.id, blocks: answer.blocks } : null })
    }
  }
}

// routeMatches over every pattern and page
const patterns = [...new Set([...en.articles.map(a => a.route).filter(Boolean), ...en.tours.map(t => t.route), '/a.b', '/x/:id/:tab'])]
const routeCases = []
for (const pattern of patterns) for (const path of [...pages, '/a.b', '/axb', '/x/1/2', '/x/1/2/', '/x//2', '/forms\n']) routeCases.push({ pattern, path, match: routeMatches(pattern, path) })

console.log(JSON.stringify({
  categories: HELP_CATEGORIES, icons: HELP_CATEGORY_ICONS,
  paths: en.articles.map(a => ({ id: a.id, category: a.category, path: helpArticlePath(a) })),
  stop: [...R.STOP], words: wordCases, route_matches: routeCases,
  article_text_en: articleTextEn, article_text: articleTexts, answers_for: answerCases,
  counts: Object.fromEntries(LANGS.map(lang => { const c = helpContent(lang); return [lang, { articles: c.articles.length, faqs: c.faqs.length, glossary: c.glossary.length, tours: c.tours.length, translated: c.articles.filter(a => a.language === lang).length }] })),
  pages, full: answers, hashes, fallback, searches,
}))
"""


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="formalie-help-") as tmp:
        route = copies(Path(tmp))
        entry = (ENTRY.replace("__ROUTE__", route.as_posix())
                 .replace("__STORE__", (Path(tmp) / "helpStore.ts").as_posix())
                 .replace("__FRONTEND__", FRONTEND.as_posix()))
        data = run_in_node(entry)
    data["about"] = "Recorded from the frontend's help rules and mock by scripts/dump_help_rules.py. Do not edit."
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}: {len(data['searches'])} searches, {len(data['answers_for'])} answers, "
          f"{len(data['route_matches'])} route matches, {len(data['pages'])} pages, {len(data['hashes'])} languages")


if __name__ == "__main__":
    main()
