"""Records the frontend's public-link rules into tests/vectors/links_rules.json (B7): custom links (problems and
tidying), short codes, form addresses, the websites allowed to embed a form and the `frame-ancestors` rule
(shared/utils/urls/public.ts, embed-domains.ts).

    fmly\\Scripts\\python.exe scripts\\dump_links_rules.py [path\\to\\formalieFrontend]

tests/parity/test_links_rules.py holds the port (app/modules/links/urls.py) to these answers.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dump_frontend_rules import ROOT, run_in_node  # noqa: E402

OUT = ROOT / "tests" / "vectors" / "links_rules.json"

ENTRY = r"""
import * as P from '__SHARED__/utils/urls/public.ts'
import * as E from '__SHARED__/utils/urls/embed-domains.ts'

const links = ['feedback', 'procurement-request', 'ab', 'abc', 'a-b', 'a--b', '-abc', 'abc-', 'ABC', 'admin', 'forms', 's',
  'fill', 'x'.repeat(60), 'x'.repeat(61), 'café', 'with space', 'abc\n', '', '123', 'a_b', 'help-desk', 'www', 'new-form-2026']
const typed = ['  Procurement Request  ', 'Café Olé!', '---a---b---', 'x'.repeat(70), 'A'.repeat(59) + ' b', 'Ünïcödé', '', '!!!',
  'Already-fine', 'two  spaces', 'end-' + 'y'.repeat(57) + '--z', 'Ελληνικά']
const addresses = ['AbCdEfGh12', 'abcdefgh12', 'AbCdEfGh1', 'feedback', 'Feedback', 'AbCdEfGh12x', 'ab']
const codes = ['abcde', 'abcd0', 'abcdl', 'ab2z9', 'ABCDE', 'abcdef', 'abci5', 'ppppp', 'oxxxx']
const domains = ['https://www.example.com/contact', 'Example.com', '*.example.com', 'localhost:3000', '127.0.0.1:8080',
  'http://user:pw@shop.example.co.uk/path?q=1#x', 'example.com.', 'example', 'exa_mple.com', 'example.com:99999', 'a:b:c',
  '  WWW.Example.ORG  ', '', 'ftp://files.example.net', '*.www.example.com', 'www.localhost', 'example.com:80/x', 'sub.-bad.com',
  'xn--bcher-kva.example', 'a.b', 'localhost', '-a.com', 'https://', 'example.com?x', 'example.com#y']
const ancestorSets = [[], ['example.com'], ['*.example.com', 'localhost:3000'], ['shop.example.co.uk', 'example.com', 'example.com'],
  ['127.0.0.1:8080', 'www.example.org'], ['localhost']]

process.stdout.write(JSON.stringify({
  about: 'Recorded from the frontend by scripts/dump_links_rules.py. Do not edit.',
  custom_links: links.map(value => ({ value, problem: P.customLinkProblem(value), address: P.isFormAddress(value) })),
  tidy: typed.map(value => ({ value, tidy: P.tidyCustomLink(value) })),
  addresses: addresses.map(value => ({ value, address: P.isFormAddress(value), key: P.FORM_KEY_PATTERN.test(value) })),
  short_codes: codes.map(value => ({ value, ok: P.SHORT_CODE_PATTERN.test(value) })),
  embed_domains: domains.map(value => ({ value, domain: E.normaliseEmbedDomain(value) })),
  frame_ancestors: ancestorSets.map(domains => ({ domains, value: E.frameAncestors(domains, 'formalie.dev') })),
  max_embed_domains: E.MAX_EMBED_DOMAINS,
  reserved: [...P.RESERVED_LINKS].sort(),
}))
"""


def main() -> None:
    result = run_in_node(ENTRY, {})
    OUT.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
