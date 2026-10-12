"""Records the frontend's webhook rules (B10 step 2) into tests/vectors/webhook_rules.json: which addresses may receive
deliveries (with and without the development switch for localhost), the retry waits, the pause after failures, the
time-out, the status of a webhook and the event label keys (shared/utils/integrations/webhooks.ts).

    fmly\\Scripts\\python.exe scripts\\dump_webhook_rules.py [path\\to\\formalieFrontend]

tests/parity/test_webhook_rules.py holds the port (app/modules/webhooks/rules.py) to these answers.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dump_frontend_rules import ROOT, run_in_node  # noqa: E402

OUT = ROOT / "tests" / "vectors" / "webhook_rules.json"

ENTRY = r"""
import * as W from '__SHARED__/utils/integrations/webhooks.ts'
import { WEBHOOK_EVENTS } from '__SHARED__/types/integrations.ts'

const urls = ['', '   ', 'https://hooks.example.com/formalie/crm', '  https://hooks.example.com/x  ', 'http://hooks.example.com/x', 'hooks.example.com/x',
  'https://', 'https://user:pw@hooks.example.com/x', 'https://user@hooks.example.com', 'ftp://hooks.example.com', 'mailto:someone@example.com', 'javascript:alert(1)',
  'https://formalie.com/hook', 'https://api.formalie.dev/x', 'https://myformalie.com/x', 'https://formalie.com.example.org/x', 'https://FORMALIE.DEV',
  'https://localhost/x', 'http://localhost:3000/hook', 'https://localhost:8443/hook', 'http://127.0.0.1:9000/hook', 'http://[::1]:9000/hook', 'https://[::1]/x',
  'https://app.localhost/x', 'https://127.0.0.5/x', 'https://0.0.0.0/x', 'https://10.1.2.3/x', 'https://172.16.0.1/x', 'https://172.32.0.1/x', 'https://192.168.1.1/x',
  'https://100.64.0.1/x', 'https://100.128.0.1/x', 'https://169.254.169.254/latest/meta-data', 'https://metadata.google.internal/x', 'https://224.0.0.1/x',
  'https://8.8.8.8/x', 'https://203.0.113.10/x', 'https://[fc00::1]/x', 'https://[fd12:3456::1]/x', 'https://[fe80::1]/x', 'https://[2001:db8::1]/x',
  'https://[2001:0db8:0000:0000:0000:0000:0000:0001]/x', 'https://[::ffff:10.0.0.1]/x', 'https://[::ffff:127.0.0.1]/x', 'https://[0:0:0:0:0:0:0:1]/x', 'https://[::]/x',
  'https://[gggg::1]/x', 'https://[::1/x', 'https://0x7f.1/x', 'https://2130706433/x', 'https://012.0.0.1/x', 'https://bücher.example/x', 'https://exa mple.com/x',
  'https://exa<mple.com/x', 'https://example.com:99999/x', 'https://example.com:8443/x', 'https://example.com./x', 'https:example.com/x', 'https:\\\\example.com\\x',
  'https://example.com?x=1#y', 'HTTPS://Hooks.Example.COM/Path', 'https://a.b.c.d.example.co.uk/x', 'https://ex_ample.com/x', 'https://xn--bcher-kva.example/x',
  'wss://example.com/x', 'http://localhost', 'http://app.localhost:3000/x', 'https://LOCALHOST/x']
const checks = urls.flatMap(value => [false, true].map(allowLocal => ({ value, allowLocal, problem: W.checkWebhookUrl(value, { allowLocal }) })))
const statuses = [true, false].flatMap(enabled => [0, 1, 5, 20].map(consecutive_failures => ({ enabled, consecutive_failures, status: W.webhookStatusOf({ enabled, consecutive_failures }) })))
const labels = [...WEBHOOK_EVENTS, 'ping'].map(event => ({ event, key: W.eventLabelKey(event) }))
const signed = [[0, ''], [1760270400, '{"a":1}'], [42, 'x.y']].map(([t, b]) => ({ timestamp: t, body: b, payload: W.signedPayload(t, b) }))

process.stdout.write(JSON.stringify({ about: 'Recorded from the frontend by scripts/dump_webhook_rules.py. Do not edit.',
  events: WEBHOOK_EVENTS, retry_minutes: W.WEBHOOK_RETRY_MINUTES, auto_pause: W.WEBHOOK_AUTO_PAUSE, timeout_ms: W.WEBHOOK_TIMEOUT_MS,
  checks, statuses, labels, signed }))
"""


def main() -> None:
    result = run_in_node(ENTRY, {})
    OUT.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}: {len(result['checks'])} address checks, {len(result['statuses'])} statuses, "
          f"{len(result['labels'])} labels")


if __name__ == "__main__":
    main()
