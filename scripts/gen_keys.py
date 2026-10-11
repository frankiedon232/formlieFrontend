"""Prints new secret keys for .env (never commit them).

    fmly\\Scripts\\python.exe scripts\\gen_keys.py            # print the lines
    fmly\\Scripts\\python.exe scripts\\gen_keys.py --write    # add the missing ones to .env (existing ones are kept)

Rotating FERNET_KEYS: put a new key first and keep the old ones after it, comma separated, until every token
made with them has expired (refresh tokens: 7 days). Changing ID_REF_* changes every reference (old links break).
"""

from __future__ import annotations

import base64
import os
import re
import sys
from pathlib import Path

from cryptography.fernet import Fernet

ROOT = Path(__file__).resolve().parents[1]


def new_keys() -> dict[str, str]:
    return {
        "ID_REF_ENC_KEY": base64.b64encode(os.urandom(32)).decode(),
        "ID_REF_MAC_KEY": base64.b64encode(os.urandom(32)).decode(),
        "FERNET_KEYS": Fernet.generate_key().decode(),
    }


def main() -> None:
    keys = new_keys()
    if "--write" not in sys.argv:
        for name, value in keys.items():
            print(f"{name}={value}")
        return
    env = ROOT / ".env"
    text = env.read_text(encoding="utf-8") if env.exists() else ""
    added = []
    for name, value in keys.items():
        if re.search(rf"^{name}=\S", text, re.MULTILINE):
            continue
        if re.search(rf"^{name}=\s*$", text, re.MULTILINE):
            text = re.sub(rf"^{name}=\s*$", f"{name}={value}", text, flags=re.MULTILINE)
        else:
            text = text.rstrip("\n") + f"\n{name}={value}\n"
        added.append(name)
    env.write_text(text, encoding="utf-8")
    print("Added to .env: " + (", ".join(added) if added else "nothing (all present)"))


if __name__ == "__main__":
    main()
