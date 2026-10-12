"""Single sign-on (B11) end to end: settings with the mock's rules, the real test against a fake identity provider
(httpx.MockTransport, nothing leaves the machine), OpenID Connect with a signed ID token, SAML with a signed answer
(keys and certificate made here), the sign-in page, "required" domains (FRM-AUTH-1019), the usual second step,
new accounts, the plan, the audit trail and another workspace."""

from __future__ import annotations

import base64
import re
import time
import uuid
import zlib
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from app.core import outbound
from app.modules.sso.service import quiet_jose
from tests.conftest import client_for
from tests.db.test_auth_flows import app, audit_actions, last_code, seeded, sign_in  # noqa: F401  (fixtures)
from tests.db.test_data_sources import on_plan
from tests.db.test_settings import PASSWORD, new_workspace
from tests.secure_client import SecureClient

pytestmark = pytest.mark.db

ISSUER = "https://idp.example.test"
IDP_ENTITY = "https://saml.example.test/metadata"
IDP_SSO = "https://saml.example.test/sso"


def _key_and_cert() -> tuple[str, str]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "idp.example.test")])
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(datetime.now(UTC) - timedelta(days=1))
            .not_valid_after(datetime.now(UTC) + timedelta(days=30)).sign(key, hashes.SHA256()))
    pem_key = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                serialization.NoEncryption()).decode()
    return pem_key, cert.public_bytes(serialization.Encoding.PEM).decode()


KEY, CERT = _key_and_cert()
CERT_BODY = "".join(line for line in CERT.splitlines() if "-----" not in line)


class FakeIdp:
    """Discovery, token, keys (OIDC) and metadata (SAML)."""

    def __init__(self) -> None:
        self.issuer = ISSUER
        self.claims: dict[str, Any] = {}
        self.nonce = ""
        self.sign_with = KEY
        self.down = False

    def id_token(self, client_id: str) -> str:
        jose = quiet_jose()
        claims = {"iss": ISSUER, "aud": client_id, "sub": "okta-123", "iat": int(time.time()),
                  "exp": int(time.time()) + 300, "nonce": self.nonce, **self.claims}
        return jose.jwt.encode({"alg": "RS256", "kid": "k1"}, claims, self.sign_with).decode()

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if self.down:
            return httpx.Response(503)
        path = request.url.path
        if path == "/.well-known/openid-configuration":
            return httpx.Response(200, json={"issuer": self.issuer, "authorization_endpoint": f"{ISSUER}/authorize",
                                             "token_endpoint": f"{ISSUER}/token", "jwks_uri": f"{ISSUER}/keys",
                                             "token_endpoint_auth_methods_supported": ["client_secret_basic"]})
        if path == "/token":
            assert request.headers["authorization"].startswith("Basic ")
            form = parse_qs(request.content.decode())
            assert form["code_verifier"][0] and form["code"] == ["code-1"]
            return httpx.Response(200, json={"access_token": "at", "token_type": "Bearer",
                                             "id_token": self.id_token("client-1")})
        if path == "/keys":
            jose = quiet_jose()
            public = serialization.load_pem_private_key(KEY.encode(), None).public_key().public_bytes(
                serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
            jwk = jose.JsonWebKey.import_key(public, {"kty": "RSA", "kid": "k1", "use": "sig"}).as_dict()
            return httpx.Response(200, json={"keys": [jwk]})
        if path == "/metadata":
            return httpx.Response(200, text=f"""<?xml version="1.0"?>
<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata" entityID="{IDP_ENTITY}">
  <md:IDPSSODescriptor protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
    <md:KeyDescriptor use="signing"><ds:KeyInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#"><ds:X509Data>
      <ds:X509Certificate>{CERT_BODY}</ds:X509Certificate></ds:X509Data></ds:KeyInfo></md:KeyDescriptor>
    <md:SingleSignOnService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect" Location="{IDP_SSO}"/>
  </md:IDPSSODescriptor>
</md:EntityDescriptor>""")
        return httpx.Response(404)


@pytest.fixture
def idp(monkeypatch: pytest.MonkeyPatch) -> Iterator[FakeIdp]:
    fake = FakeIdp()
    monkeypatch.setattr(outbound, "transport", httpx.MockTransport(fake))
    yield fake


def oidc_body(sub: str, **extra: Any) -> dict[str, Any]:
    return {"provider": "okta", "label": "Okta", "oidc": {"issuer": ISSUER, "client_id": "client-1",
                                                          "client_secret": "top-secret"},
            "domains": [f"@{sub}.test"], "enforce": False, "auto_create": False, "default_role": "member", **extra}


async def business_workspace(app: Any, owner_dsn: str) -> tuple[str, str]:  # noqa: ANN401
    sub, email = await new_workspace(app)
    await on_plan(owner_dsn, sub, "business")
    return sub, email


async def test_settings_test_status_and_the_plan(app, owner_dsn, idp, superuser) -> None:  # noqa: ANN001
    starter, starter_email = await new_workspace(app)
    async with client_for(app, host=f"{starter}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, starter_email, PASSWORD)
        status, reply = await owner.request("PUT", "/settings/sso", body=oidc_body(starter))
        assert (status, reply["error"]["code"]) == (402, "FRM-PLAN-1002")

    sub, email = await business_workspace(app, owner_dsn)
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        status, reply = await owner.request("GET", "/settings/sso")
        assert status == 200 and reply["data"]["connection"] is None
        assert reply["data"]["service_provider"] == {
            "entity_id": f"https://{sub}.formalie.dev/api/v1/auth/sso/saml/metadata",
            "acs_url": f"https://{sub}.formalie.dev/api/v1/auth/sso/saml/acs",
            "metadata_url": f"https://{sub}.formalie.dev/api/v1/auth/sso/saml/metadata",
            "redirect_uri": f"https://{sub}.formalie.dev/api/v1/auth/sso/oidc/callback",
            "signout_url": f"https://{sub}.formalie.dev/api/v1/auth/sso/signout"}

        # The mock's checks
        _, reply = await owner.request("PUT", "/settings/sso", body=oidc_body(sub, oidc={"issuer": "http://idp.test",
                                                                                         "client_id": "c"}))
        assert reply["error"]["details"] == [{"field": "oidc.issuer", "message": "https"}]
        _, reply = await owner.request("PUT", "/settings/sso", body=oidc_body(sub, default_role="owner"))
        assert reply["error"]["details"] == [{"field": "default_role", "message": "role"}]
        _, reply = await owner.request("PUT", "/settings/sso", body=oidc_body(sub, domains=[], enforce=True))
        assert reply["error"]["details"] == [{"field": "domains", "message": "required"}]
        _, reply = await owner.request("PUT", "/settings/sso", body=oidc_body(sub, domains=["not a domain"]))
        assert reply["error"]["details"] == [{"field": "domains.0", "message": "domain"}]

        status, reply = await owner.request("PUT", "/settings/sso", body=oidc_body(sub))
        assert status == 200, reply
        connection = reply["data"]["connection"]
        assert connection["protocol"] == "oidc" and connection["status"] == "draft" and connection["domains"] == [f"{sub}.test"]
        assert connection["oidc"] == {"issuer": ISSUER, "client_id": "client-1", "has_secret": True}
        assert "top-secret" not in str(reply)
        _, reply = await owner.request("POST", "/settings/sso/status", body={"active": True})
        assert (reply["error"]["code"]) == "FRM-AUTH-1020"

        # The provider's own issuer must match
        idp.issuer = "https://elsewhere.example.test"
        _, reply = await owner.request("POST", "/settings/sso/test")
        assert reply["data"]["connection"]["problem"] == "issuer_mismatch" and reply["data"]["connection"]["status"] == "draft"
        idp.issuer, idp.down = ISSUER, True
        _, reply = await owner.request("POST", "/settings/sso/test")
        assert reply["data"]["connection"]["problem"] == "unreachable"
        idp.down = False
        _, reply = await owner.request("POST", "/settings/sso/test")
        assert reply["data"]["connection"]["status"] == "tested" and reply["data"]["connection"]["tested_at"]
        _, reply = await owner.request("POST", "/settings/sso/status", body={"active": True})
        assert reply["data"]["connection"]["status"] == "active"

        # The sign-in page shows it
        _, reply = await owner.request("GET", "/tenants/public")
        assert reply["data"]["sso"] == {"provider": "okta", "label": "Okta", "domains": [f"{sub}.test"], "enforce": False}

        # Saving the same set-up keeps it on; a different client goes back to draft
        _, reply = await owner.request("PUT", "/settings/sso", body={**oidc_body(sub, label="Okta SSO"),
                                                                     "oidc": {"issuer": ISSUER, "client_id": "client-1"}})
        assert reply["data"]["connection"]["status"] == "active" and reply["data"]["connection"]["oidc"]["has_secret"]
        _, reply = await owner.request("PUT", "/settings/sso", body={**oidc_body(sub),
                                                                     "oidc": {"issuer": ISSUER, "client_id": "client-2"}})
        assert reply["data"]["connection"]["status"] == "draft"

        _, trail = await owner.request("GET", "/audit-logs", query={"filter[action]": "settings.updated"})
        fields = {c["field"] for e in trail["data"] if e["resource"]["name"] == "Single sign-on" for c in e["changes"]}
        assert fields == {"sso", "sso_test", "sso_status"}

    # Another workspace has none of it
    other, other_email = await business_workspace(app, owner_dsn)
    async with client_for(app, host=f"{other}.formalie.dev") as http:
        stranger = SecureClient(http)
        await sign_in(stranger, other_email, PASSWORD)
        _, reply = await stranger.request("GET", "/settings/sso")
        assert reply["data"]["connection"] is None
        _, reply = await stranger.request("POST", "/settings/sso/test")
        assert reply["error"]["code"] == "FRM-GEN-1004"

    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        _, reply = await owner.request("DELETE", "/settings/sso")
        assert reply["data"]["connection"] is None
    row = superuser.execute("SELECT s.deleted_at IS NOT NULL, s.client_secret_enc FROM formaly.sso_connections s JOIN "
                            "platform.tenants t ON t.id = s.tenant_id WHERE t.subdomain = %s", (sub,)).fetchone()
    assert row == (True, None)  # soft deleted, the secret gone


async def _activate(owner: SecureClient, body: dict[str, Any]) -> None:
    status, reply = await owner.request("PUT", "/settings/sso", body=body)
    assert status == 200, reply
    _, reply = await owner.request("POST", "/settings/sso/test")
    assert reply["data"]["connection"]["status"] == "tested", reply
    _, reply = await owner.request("POST", "/settings/sso/status", body={"active": True})
    assert reply["data"]["connection"]["status"] == "active"


async def _finish_sign_in(http: httpx.AsyncClient, location: str, email: str) -> dict[str, Any]:
    """Back on /auth/login with the challenge: pick it up and enter the emailed code, like the page does."""
    query = parse_qs(urlsplit(location).query)
    assert query.get("provider") == ["sso"], location
    page = SecureClient(http)
    status, reply = await page.request("GET", "/auth/oauth/challenge", query={"challenge_id": query["oauth_challenge"][0]})
    assert status == 200, reply
    assert reply["data"]["provider"] == "sso" and reply["data"]["email"] == email
    status, reply = await page.request("POST", "/auth/otp/verify", body={
        "challenge_id": reply["data"]["challenge"]["challenge_id"], "code": last_code(email)})
    assert status == 200, reply
    return reply["data"]


async def test_openid_connect_sign_in(app, owner_dsn, idp, superuser) -> None:  # noqa: ANN001
    sub, email = await business_workspace(app, owner_dsn)
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        await _activate(owner, oidc_body(sub, enforce=True))

        # Required for its domain: no password here
        status, reply = await SecureClient(http).request("POST", "/auth/login", body={"email": email, "password": PASSWORD})
        assert (status, reply["error"]["code"]) == (403, "FRM-AUTH-1019")
        assert "auth.login.blocked" in audit_actions(superuser, email)

        async def through_provider(claims: dict[str, Any], code: str = "code-1") -> str:
            start = await http.get("/api/v1/auth/sso/start")
            assert start.status_code == 302, start.text
            target = urlsplit(start.headers["location"])
            assert f"{target.scheme}://{target.netloc}{target.path}" == f"{ISSUER}/authorize"
            params = parse_qs(target.query)
            assert params["code_challenge_method"] == ["S256"] and params["client_id"] == ["client-1"]
            assert params["redirect_uri"] == [f"https://{sub}.formalie.dev/api/v1/auth/sso/oidc/callback"]
            idp.nonce, idp.claims = params["nonce"][0], claims
            back = await http.get("/api/v1/auth/sso/oidc/callback", params={"code": code, "state": params["state"][0]})
            assert back.status_code == 302
            return back.headers["location"]

        # The owner, through the provider, then the usual code
        location = await through_provider({"email": email, "email_verified": True, "given_name": "Olu"})
        tokens = await _finish_sign_in(http, location, email)
        assert tokens["user"]["email"] == email
        identity = superuser.execute("SELECT provider, provider_user_id FROM formaly.user_identities i JOIN formaly.users u "
                                     "ON u.id = i.user_id WHERE u.email = %s", (email,)).fetchall()
        assert identity == [("sso", "okta-123")]

        # Someone new from the domain: refused without auto-create
        newcomer = f"new.person@{sub}.test"
        location = await through_provider({"sub": "okta-456", "email": newcomer})
        assert parse_qs(urlsplit(location).query)["code"] == ["FRM-AUTH-1022"]
        # An address outside the connection's domains
        location = await through_provider({"sub": "okta-789", "email": "someone@elsewhere.test"})
        assert parse_qs(urlsplit(location).query)["code"] == ["FRM-AUTH-1014"]
        # A token signed with another key, a reused state
        idp.sign_with = _key_and_cert()[0]
        location = await through_provider({"email": email})
        assert parse_qs(urlsplit(location).query)["code"] == ["FRM-AUTH-1023"]
        idp.sign_with = KEY
        back = await http.get("/api/v1/auth/sso/oidc/callback", params={"code": "code-1", "state": "used-or-unknown"})
        assert parse_qs(urlsplit(back.headers["location"]).query)["code"] == ["FRM-AUTH-1023"]

        # With auto-create: an account with the default role
        await owner.request("PUT", "/settings/sso", body={**oidc_body(sub, enforce=True, auto_create=True),
                                                          "oidc": {"issuer": ISSUER, "client_id": "client-1"}})
        location = await through_provider({"sub": "okta-456", "email": newcomer, "given_name": "Nia",
                                           "family_name": "Obi"})
        tokens = await _finish_sign_in(http, location, newcomer)
        assert tokens["user"]["role"] == "member" and tokens["user"]["first_name"] == "Nia"
        assert "users.joined" in audit_actions(superuser, newcomer)

    # Without single sign-on in the plan: the start says unavailable
    starter, _ = await new_workspace(app)
    async with client_for(app, host=f"{starter}.formalie.dev") as http:
        start = await http.get("/api/v1/auth/sso/start")
        assert start.headers["location"] == "/auth/login?sso=unavailable"


def _saml_response(acs: str, sp_entity: str, request_id: str, email: str, *, audience: str | None = None) -> str:
    from onelogin.saml2.utils import OneLogin_Saml2_Utils

    now = datetime.now(UTC)

    def stamp(value: datetime) -> str:
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")
    xml = f"""<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol" xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion" ID="_r{uuid.uuid4().hex}" Version="2.0" IssueInstant="{stamp(now)}" Destination="{acs}" InResponseTo="{request_id}"><saml:Issuer>{IDP_ENTITY}</saml:Issuer><samlp:Status><samlp:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:Success"/></samlp:Status><saml:Assertion ID="_a{uuid.uuid4().hex}" Version="2.0" IssueInstant="{stamp(now)}"><saml:Issuer>{IDP_ENTITY}</saml:Issuer><saml:Subject><saml:NameID Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress">{email}</saml:NameID><saml:SubjectConfirmation Method="urn:oasis:names:tc:SAML:2.0:cm:bearer"><saml:SubjectConfirmationData NotOnOrAfter="{stamp(now + timedelta(minutes=5))}" Recipient="{acs}" InResponseTo="{request_id}"/></saml:SubjectConfirmation></saml:Subject><saml:Conditions NotBefore="{stamp(now - timedelta(minutes=1))}" NotOnOrAfter="{stamp(now + timedelta(minutes=5))}"><saml:AudienceRestriction><saml:Audience>{audience or sp_entity}</saml:Audience></saml:AudienceRestriction></saml:Conditions><saml:AuthnStatement AuthnInstant="{stamp(now)}" SessionIndex="_s1"><saml:AuthnContext><saml:AuthnContextClassRef>urn:oasis:names:tc:SAML:2.0:ac:classes:Password</saml:AuthnContextClassRef></saml:AuthnContext></saml:AuthnStatement><saml:AttributeStatement><saml:Attribute Name="firstName"><saml:AttributeValue>Ada</saml:AttributeValue></saml:Attribute><saml:Attribute Name="lastName"><saml:AttributeValue>Lovelace</saml:AttributeValue></saml:Attribute></saml:AttributeStatement></saml:Assertion></samlp:Response>"""
    signed = OneLogin_Saml2_Utils.add_sign(xml, KEY, CERT, sign_algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
                                           digest_algorithm="http://www.w3.org/2001/04/xmlenc#sha256")
    return base64.b64encode(signed if isinstance(signed, bytes) else signed.encode()).decode()


async def test_saml_sign_in(app, owner_dsn, idp, superuser) -> None:  # noqa: ANN001
    sub, email = await business_workspace(app, owner_dsn)
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        body = {"provider": "google_workspace", "label": "Google", "saml": {"metadata_url": "https://saml.example.test/metadata"},
                "domains": [f"{sub}.test"], "enforce": False, "auto_create": False, "default_role": "member"}
        # Hand-entered values: an incomplete certificate fails the test
        _, reply = await owner.request("PUT", "/settings/sso", body={**body, "saml": {
            "entity_id": IDP_ENTITY, "sso_url": IDP_SSO, "certificate": "MIIBnot-a-cert"}})
        _, reply = await owner.request("POST", "/settings/sso/test")
        assert reply["data"]["connection"]["problem"] == "incomplete"
        _, reply = await owner.request("PUT", "/settings/sso", body={**body, "saml": {
            "entity_id": IDP_ENTITY, "sso_url": IDP_SSO, "certificate": CERT}})
        _, reply = await owner.request("POST", "/settings/sso/test")
        assert reply["data"]["connection"]["status"] == "tested"
        # Not metadata at that address
        _, reply = await owner.request("PUT", "/settings/sso", body={**body, "saml": {"metadata_url": "https://saml.example.test/nope"}})
        _, reply = await owner.request("POST", "/settings/sso/test")
        assert reply["data"]["connection"]["problem"] == "unreachable"
        await _activate(owner, body)
        _, reply = await owner.request("GET", "/settings/sso")
        provider = reply["data"]["service_provider"]
        connection = reply["data"]["connection"]
        assert connection["protocol"] == "saml" and connection["saml"]["metadata_url"] == "https://saml.example.test/metadata"

        # Formalie's own metadata for the provider
        metadata = await http.get("/api/v1/auth/sso/saml/metadata")
        assert metadata.status_code == 200 and provider["acs_url"] in metadata.text and provider["entity_id"] in metadata.text

        async def start() -> tuple[str, str]:
            reply_ = await http.get("/api/v1/auth/sso/start")
            assert reply_.status_code == 302, reply_.text
            target = urlsplit(reply_.headers["location"])
            assert f"{target.scheme}://{target.netloc}{target.path}" == IDP_SSO
            params = parse_qs(target.query)
            request = zlib.decompress(base64.b64decode(params["SAMLRequest"][0]), -15).decode()
            request_id = re.search(r'ID="([^"]+)"', request).group(1)  # type: ignore[union-attr]
            return request_id, params["RelayState"][0]

        request_id, relay = await start()
        answer = _saml_response(provider["acs_url"], provider["entity_id"], request_id, email.upper())
        back = await http.post("/api/v1/auth/sso/saml/acs", data={"SAMLResponse": answer, "RelayState": relay})
        assert back.status_code == 302, back.text
        tokens = await _finish_sign_in(http, back.headers["location"], email)
        assert tokens["user"]["email"] == email

        # The same answer again (its state is used), another audience, a tampered answer
        again = await http.post("/api/v1/auth/sso/saml/acs", data={"SAMLResponse": answer, "RelayState": relay})
        assert "FRM-AUTH-1023" in again.headers["location"]
        request_id, relay = await start()
        wrong = _saml_response(provider["acs_url"], provider["entity_id"], request_id, email, audience="https://other.test")
        back = await http.post("/api/v1/auth/sso/saml/acs", data={"SAMLResponse": wrong, "RelayState": relay})
        assert "FRM-AUTH-1023" in back.headers["location"]
        request_id, relay = await start()
        good = base64.b64decode(_saml_response(provider["acs_url"], provider["entity_id"], request_id, email)).decode()
        tampered = base64.b64encode(good.replace(email, f"ceo@{sub}.test").encode()).decode()
        back = await http.post("/api/v1/auth/sso/saml/acs", data={"SAMLResponse": tampered, "RelayState": relay})
        assert "FRM-AUTH-1023" in back.headers["location"]
