"""B17 security review M10: with bodies kept, the API request log still never stores the token address's bodies
(client secret in, access token out) nor secret fields in other calls' bodies."""

from __future__ import annotations

import json

import pytest

from tests.conftest import client_for
from tests.db.test_api_gateway import API, call, key, setup
from tests.db.test_auth_flows import app, seeded, sign_in  # noqa: F401  (fixtures)
from tests.db.test_settings import PASSWORD, new_workspace
from tests.secure_client import SecureClient

pytestmark = pytest.mark.db


async def test_the_token_address_and_secret_fields_are_never_logged(app, superuser) -> None:  # noqa: ANN001, F811
    sub, email = await new_workspace(app)
    async with client_for(app, host=f"{sub}.formalie.dev") as http, client_for(app, host=API) as api:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        made = await setup(owner)
        _, reply = await owner.request("PUT", "/api-logs/settings", body={"keep_bodies": True, "days": 1})
        assert reply["data"]["keep_bodies"] is True
        _, reply, _ = await call(api, "POST", f"/{made['api_key']}/token", body={
            "client_id": made["client"]["client_id"], "client_secret": made["client_secret"]})
        access = reply["access_token"]
        status, _, _ = await call(api, "POST", made["path"], token=access, headers=key(),
                                  body={"first_name": "Lin", "password": "hunter2-secret"})
        assert status in (201, 422)

    tenant_id = superuser.execute("SELECT id FROM platform.tenants WHERE subdomain = %s", (sub,)).fetchone()[0]
    rows = superuser.execute("SELECT path, request_body, response_body FROM formaly.api_request_logs "
                             "WHERE tenant_id = %s", (tenant_id,)).fetchall()
    token_rows = [r for r in rows if r[0].endswith("/token")]
    assert token_rows and all(r[1] is None and r[2] is None for r in token_rows)
    dumped = json.dumps([[r[1], r[2]] for r in rows], default=str)
    assert made["client_secret"] not in dumped and access not in dumped and "hunter2-secret" not in dumped
