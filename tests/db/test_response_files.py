"""Files in responses (B8): a private 5-minute link to one file, served inline or as a download, only on the
workspace's own host, never from the public file address."""

from __future__ import annotations

import pytest

from app.modules.public import router as public_router
from tests.conftest import client_for
from tests.db.test_auth_flows import app, seeded, sign_in  # noqa: F401  (fixtures)
from tests.db.test_builder import with_field
from tests.db.test_public_forms import publish, session, solved
from tests.db.test_settings import PASSWORD, new_workspace
from tests.secure_client import SecureClient

pytestmark = pytest.mark.db


async def test_response_files(app, monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(public_router, "MIN_FILL_MS", 0)
    sub, email = await new_workspace(app)
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        form = await publish(owner, "Claims", lambda s: with_field(s, "receipt", "Receipt", type="file_upload",
                                                                  props={"accept": ".pdf", "max_files": 2}))
        key = form["public_key"]
        visitor = SecureClient(http)
        pdf = b"%PDF-1.4 a receipt"
        _, reply = await visitor.request("POST", f"/public/forms/{key}/uploads", body={
            "field": "receipt", "file_name": "receipt.pdf", "content_type": "application/pdf", "size": len(pdf)})
        ticket = reply["data"]
        assert (await http.put(ticket["upload_url"], content=pdf, headers={"content-type": "application/pdf"})).status_code == 204
        _, reply = await visitor.request("POST", f"/public/forms/{key}/uploads/{ticket['upload_id']}/complete", body={})
        status, reply = await visitor.request("POST", f"/public/forms/{key}/submit", body={
            "data": {"receipt": [reply["data"]]}, "challenge": await solved(visitor, key)}, headers=session())
        assert status == 201, reply
        response_id = reply["data"]["response_id"]

        _, reply = await owner.request("GET", f"/responses/{response_id}")
        assert reply["data"]["files_count"] == 1
        _, reply = await owner.request("POST", f"/responses/{response_id}/files", body={"field": "receipt", "index": 0})
        link = reply["data"]
        assert link["name"] == "receipt.pdf" and link["previewable"] is True and link["sample"] is False
        shown = await http.get(link["url"])
        assert shown.status_code == 200 and shown.content == pdf
        assert shown.headers["content-disposition"].startswith("inline") and shown.headers["cache-control"] == "private, no-store"
        saved = await http.get(link["download_url"])
        assert saved.headers["content-disposition"].startswith("attachment")
        assert (await http.get(link["url"][:-4] + "abcd")).status_code == 410
        _, reply = await owner.request("POST", f"/responses/{response_id}/files", body={"field": "receipt", "index": 1})
        assert reply["error"]["code"] == "FRM-GEN-1004"

    # Another workspace's host can't open the link
    other, _ = await new_workspace(app)
    async with client_for(app, host=f"{other}.formalie.dev") as http:
        assert (await http.get(link["url"])).status_code == 410
