"""Runs the frontend's own shared/utils/crypto/envelope.ts against tests/vectors/envelope.json, both ways.

    fmly\\Scripts\\python.exe scripts\\check_envelope_vectors.py [path\\to\\formalieFrontend]

The frontend is only read: esbuild (from its node_modules) bundles envelope.ts into a temporary folder, and
Node 22+ runs it. Checks: the frontend derives the same session key, opens every envelope the backend sealed,
encodes the same header, and seals an envelope the backend then opens. Exit code 0 = they agree.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.security import envelope as env  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
VECTORS = ROOT / "tests" / "vectors" / "envelope.json"
FRONTEND = Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("FORMALIE_FRONTEND_DIR",
                                                                      r"C:\UNETPROJECTS\formalieFrontend"))

DRIVER = r"""
import { readFileSync } from 'node:fs'
import * as E from './envelope.mjs'

const v = JSON.parse(readFileSync(process.argv[2], 'utf8'))
const out = { opened: [], headers: [], sealed: null, errors: [] }
const priv = await crypto.subtle.importKey('jwk', v.client_private_jwk, { name: 'ECDH', namedCurve: 'P-256' }, false, ['deriveBits'])
const key = await E.deriveSessionKey(priv, v.server_public_key, v.salt)
for (const c of v.cases) {
  try { out.opened.push(await E.openEnvelope(key, c.envelope)) } catch (e) { out.errors.push(`open ${c.name}: ${e}`) }
  out.headers.push(E.encodeEnvelopeHeader(c.envelope))
  const back = E.decodeEnvelopeHeader(c.header)
  if (!back || back.ct !== c.envelope.ct) out.errors.push(`decodeEnvelopeHeader ${c.name}`)
}
out.sealed = await E.sealEnvelope(key, 'from-frontend-0000', { method: 'POST', path: '/api/v1/check', query: {}, body: { ok: true, text: 'naïve ✓' } })
process.stdout.write(JSON.stringify(out))
"""


def main() -> int:
    vectors = json.loads(VECTORS.read_text(encoding="utf-8"))
    esbuild = FRONTEND / "node_modules" / ".bin" / ("esbuild.cmd" if os.name == "nt" else "esbuild")
    source = FRONTEND / "shared" / "utils" / "crypto" / "envelope.ts"
    with tempfile.TemporaryDirectory(prefix="formalie-vectors-") as tmp:
        bundle = Path(tmp) / "envelope.mjs"
        subprocess.run([str(esbuild), str(source), "--bundle", "--format=esm", "--platform=neutral",
                        f"--outfile={bundle}", "--log-level=warning"], check=True, cwd=FRONTEND)
        driver = Path(tmp) / "driver.mjs"
        driver.write_text(DRIVER, encoding="utf-8")
        run = subprocess.run(["node", str(driver), str(VECTORS)], capture_output=True, text=True, encoding="utf-8")
    if run.returncode != 0:
        print(run.stderr)
        return 1
    result = json.loads(run.stdout)
    problems = list(result["errors"])
    for case, opened, header in zip(vectors["cases"], result["opened"], result["headers"], strict=False):
        if opened != case["payload"]:
            problems.append(f"{case['name']}: the frontend opened something else")
        if header != case["header"]:
            problems.append(f"{case['name']}: header encoding differs")
    key = bytes.fromhex(vectors["session_key_hex"])
    try:
        back = env.open_envelope(key, result["sealed"])
        if back["body"] != {"ok": True, "text": "naïve ✓"}:
            problems.append("the backend opened something else from the frontend's envelope")
    except env.EnvelopeError as exc:
        problems.append(f"the backend could not open the frontend's envelope: {exc}")
    if problems:
        print("MISMATCH:\n  " + "\n  ".join(problems))
        return 1
    print(f"OK: the frontend's envelope.ts and the backend agree on {len(vectors['cases'])} vectors, both ways.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
