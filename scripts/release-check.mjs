#!/usr/bin/env node
/**
 * Release check (PRODUCTION-CHECKLIST, build-time reminder): no development address may be left in
 * a production build. Searches the static build (`.output/public`) and the Worker bundle
 * (`.output/edge`, when made with `wrangler deploy --dry-run --outdir .output/edge`) and exits 1
 * with every hit. Run after `pnpm generate --dotenv .env.production`:  pnpm release:check
 *
 * The matcher is exported for test/edge/release-check.test.ts.
 */
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs'
import { join, relative } from 'node:path'
import { fileURLToPath } from 'node:url'

/** What must never ship: dev hosts, dev ports, local addresses and local certificate tooling. */
export const FORBIDDEN = [
  { label: 'formalie.dev', pattern: /formalie\.dev/gi },
  // Development ports (``: `:22020` is another number).
  { label: ':2202', pattern: /:2202\b/g },
  { label: ':3033', pattern: /:3033\b/g },
  { label: ':5004', pattern: /:5004\b/g },
  { label: ':5005', pattern: /:5005\b/g },
  // Lower case only: linkifyjs (rich text editor) names a token `LOCALHOST`, which is no address.
  { label: 'localhost', pattern: /localhost/g },
  { label: '127.0.0.1', pattern: /127\.0\.0\.1/g },
  { label: 'mkcert', pattern: /mkcert/gi },
  { label: 'devcerts', pattern: /devcerts/gi },
]

/**
 * Known safe matches, each one explained. A hit is ignored only when the characters right around it
 * match; an address (`//localhost`, `localhost:2202`, `http://127.0.0.1`) never does.
 */
export const ALLOWED = [
  {
    // A bare host name in a string literal, compared in validation code: the request-forgery guards
    // refuse it (webhooks, database connections), customers may list `http://localhost` as an allowed
    // origin or embed website for their own testing (API service, Share → Embed), the host resolver
    // knows it, and linkifyjs (rich text editor) recognises it. Never an address the app calls.
    labels: ['localhost', '127.0.0.1'],
    before: /[`'"]\.?$/,
    after: /^[`'"]/,
  },
  {
    // The same check written as a regular expression: /^(localhost|127\.0\.0\.1)$/ (embed websites).
    labels: ['localhost'],
    before: /\^\($/,
    after: /^\|/,
  },
]

/** Is this match one of the known safe ones? */
function allowed(label, text, start, end) {
  const before = text.slice(Math.max(0, start - 3), start)
  const after = text.slice(end, end + 3)
  return ALLOWED.some(
    rule => rule.labels.includes(label) && rule.before.test(before) && rule.after.test(after),
  )
}

/** Text files worth searching (images and fonts can't hold an address we wrote). */
const TEXT_FILE = /\.(?:html?|js|mjs|cjs|css|json|txt|xml|webmanifest|map|svg|md)$|^_headers$|^_redirects$/i

/** Every forbidden match in one file's text, with a little context. */
export function findHits(text, file = '') {
  const hits = []
  for (const { label, pattern } of FORBIDDEN) {
    for (const match of text.matchAll(pattern)) {
      const end = match.index + match[0].length
      if (allowed(label, text, match.index, end)) continue
      const context = text.slice(Math.max(0, match.index - 40), end + 40).replace(/\s+/g, ' ')
      hits.push({ file, label, context })
    }
  }
  return hits
}

function* walk(dir) {
  for (const name of readdirSync(dir)) {
    const path = join(dir, name)
    if (statSync(path).isDirectory()) yield* walk(path)
    else if (TEXT_FILE.test(name)) yield path
  }
}

/** Searches the given folders (those that exist); returns the hits and how many files were read. */
export function checkFolders(root, folders) {
  const hits = []
  let files = 0
  for (const folder of folders) {
    const dir = join(root, folder)
    if (!existsSync(dir)) continue
    for (const path of walk(dir)) {
      files++
      hits.push(...findHits(readFileSync(path, 'utf8'), relative(root, path).replaceAll('\\', '/')))
    }
  }
  return { hits, files }
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const root = join(fileURLToPath(new URL('.', import.meta.url)), '..')
  if (!existsSync(join(root, '.output/public/index.html'))) {
    console.error(
      'release:check: no .output/public/index.html, run `pnpm generate --dotenv .env.production` first.',
    )
    process.exit(1)
  }
  const { hits, files } = checkFolders(root, ['.output/public', '.output/edge'])
  if (hits.length) {
    console.error(
      `release:check: ${hits.length} development address(es) in the build (${files} files searched):`,
    )
    for (const hit of hits) console.error(`  ${hit.file}  [${hit.label}]  …${hit.context}…`)
    console.error('Fix them at the source (runtime config), rebuild, then run the check again.')
    process.exit(1)
  }
  console.log(`release:check: clean, no development address in ${files} files.`)
}
