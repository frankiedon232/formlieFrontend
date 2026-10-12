"""The dashboard (F21; API-CONTRACT → Dashboard; mock: routes/dashboard.ts, dashboardForms.ts, dashboardData.ts,
dashboardApi.ts). Reads only, from the read replica.

    GET /dashboard?from&to&group&folder&owner        Workspace view (any member)
    GET /dashboard/forms?from&to&group&folder&owner  Forms view
    GET /dashboard/data?from&to&group                Data sources view (data.view)
    GET /dashboard/api?from&to&group                 API service view (api.view)

`from` / `to` are days (default the last 30 days), `group` day · week · month · year (default: the one that fits;
weeks start on Monday). Days are the workspace's (Settings → Localisation time zone).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request

from app.core.responses import ok
from app.core.security.limits import rate_limit
from app.modules.auth.sessions import Principal, require_auth
from app.modules.dashboard.api_view import api_view
from app.modules.dashboard.data_view import data_view
from app.modules.dashboard.forms_view import forms_view
from app.modules.dashboard.workspace import workspace_view

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", dependencies=[rate_limit("dashboard", per_minute=120)])
async def workspace_dashboard(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    return ok(await workspace_view(principal, dict(request.query_params)))


@router.get("/dashboard/forms", dependencies=[rate_limit("dashboard", per_minute=120)])
async def forms_dashboard(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    return ok(await forms_view(principal, dict(request.query_params)))


@router.get("/dashboard/data", dependencies=[rate_limit("dashboard", per_minute=120)])
async def data_dashboard(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    return ok(await data_view(principal, dict(request.query_params)))


@router.get("/dashboard/api", dependencies=[rate_limit("dashboard", per_minute=120)])
async def api_dashboard(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    return ok(await api_view(principal, dict(request.query_params)))
