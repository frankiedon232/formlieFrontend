"""Same cases as the frontend's test/tenant/host.test.ts (shared/utils/tenant/host.ts)."""

from __future__ import annotations

import pytest

from app.core.middleware.tenant import HostContext, is_valid_subdomain, normalise_host, resolve_host_context

pytestmark = pytest.mark.parity


def resolve(host: str, tenant_override: str | None = None) -> HostContext:
    return resolve_host_context(host, root_domain="formalie.dev", manage_subdomain="manage",
                                tenant_override=tenant_override)


@pytest.mark.parametrize(("raw", "expected"), [
    ("Manage.Formalie.dev:2202", "manage.formalie.dev"),
    ("formalie.dev.", "formalie.dev"),
    ("[::1]:2202", "::1"),
    ("127.0.0.1:2202", "127.0.0.1"),
])
def test_normalise_host(raw: str, expected: str) -> None:
    assert normalise_host(raw) == expected


def test_manage_entry_on_manage_root_and_www() -> None:
    assert (resolve("manage.formalie.dev:2202").kind, resolve("manage.formalie.dev:2202").reason) == ("manage", "manage")
    assert (resolve("formalie.dev:2202").kind, resolve("formalie.dev:2202").reason) == ("manage", "root")
    assert (resolve("www.formalie.dev").kind, resolve("www.formalie.dev").reason) == ("manage", "root")


def test_tenant_on_its_subdomain() -> None:
    assert resolve("remedylegal.formalie.dev:2202") == HostContext("tenant", "remedylegal.formalie.dev",
                                                                   subdomain="remedylegal")


def test_local_hosts_open_manage_or_a_tenant_via_override() -> None:
    for host in ("localhost:2202", "127.0.0.1:2202", "[::1]:2202", "192.168.0.180:2202"):
        ctx = resolve(host)
        assert (ctx.kind, ctx.reason) == ("manage", "local")
        ctx = resolve(host, "samathtax")
        assert (ctx.kind, ctx.subdomain) == ("tenant", "samathtax")
    ctx = resolve("localhost", "api")
    assert (ctx.kind, ctx.reason) == ("invalid", "reserved")


def test_star_localhost_works_without_hosts_entry() -> None:
    ctx = resolve("acme.localhost:2202")
    assert (ctx.kind, ctx.subdomain) == ("tenant", "acme")
    ctx = resolve("manage.localhost:2202")
    assert (ctx.kind, ctx.reason) == ("manage", "manage")


def test_forms_is_the_shared_public_forms_host() -> None:
    assert resolve("forms.formalie.dev") == HostContext("forms", "forms.formalie.dev")
    assert is_valid_subdomain("forms") is False


@pytest.mark.parametrize(("host", "reason"), [
    ("api.formalie.dev", "reserved"),
    ("www2.forms.formalie.dev", "nested"),
    ("a.b.formalie.dev", "nested"),
    ("-bad-.formalie.dev", "malformed"),
])
def test_reserved_nested_and_malformed_are_invalid(host: str, reason: str) -> None:
    ctx = resolve(host)
    assert (ctx.kind, ctx.reason) == ("invalid", reason)


def test_other_domains_are_custom() -> None:
    assert resolve("forms.customer.com") == HostContext("custom", "forms.customer.com")


def test_is_valid_subdomain() -> None:
    assert is_valid_subdomain("remedylegal") is True
    assert is_valid_subdomain("samath-tax2") is True
    assert is_valid_subdomain("admin") is False
    assert is_valid_subdomain("Bad_Name") is False
    assert is_valid_subdomain("-x") is False
