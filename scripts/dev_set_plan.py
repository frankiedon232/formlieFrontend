"""Development only: move a workspace to another plan, the way the platform admin does (B16 internal admin API), so
paid features such as single sign-on can be tried before payments (B15) exist.

    fmly\\Scripts\\python.exe scripts\\dev_set_plan.py acme                      # acme -> business
    fmly\\Scripts\\python.exe scripts\\dev_set_plan.py acme --plan professional
    fmly\\Scripts\\python.exe scripts\\dev_set_plan.py acme --plan starter       # back to the free plan

Plans: starter (free, no single sign-on), professional, business, enterprise (all three with single sign-on).
Calls POST /internal/admin/v1/tenants/{id}/plan, signed with the first PLATFORM_ADMIN_KEYS entry (see
scripts/dev_support_ticket.py for the set-up). The workspace's audit trail records it as Formalie support. Refuses
to run unless APP_ENV is development. Reload the portal afterwards so it reads the new plan.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402
from scripts.dev_support_ticket import call, lookup  # noqa: E402

PLANS = ("starter", "professional", "business", "enterprise")


def main() -> None:
    settings = get_settings()
    if not settings.is_development or settings.is_production:
        raise SystemExit("Development only (APP_ENV must be development)")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("subdomain")
    parser.add_argument("--plan", choices=PLANS, default="business")
    parser.add_argument("--api", default=f"https://{settings.root_domain}:{settings.server_port}",
                        help="the backend's own address (default https://formalie.dev:5004)")
    parser.add_argument("--insecure", action="store_true", help="skip TLS verification of the dev certificate")
    args = parser.parse_args()
    verify: bool | str = False if args.insecure else (os.environ.get("NODE_EXTRA_CA_CERTS") or True)

    tenant, _ = asyncio.run(lookup(args.subdomain))
    data = call(args.api, f"/tenants/{tenant}/plan", {"plan_id": args.plan}, "Development script",
                f"Development test: plan set to {args.plan}", verify)
    print(f"{args.subdomain} is now on {data.get('plan_id', args.plan)}. Reload the portal.")


if __name__ == "__main__":
    main()
