"""Agent discovery documents and HTTP behaviour for AI agents.

Everything agent-facing is derived from SITE so other Django sites can reuse
this module by changing the configuration block.
"""

import json

from django.http import HttpRequest, HttpResponse

SITE = {
    "host": "sdg.nevatal.id",
    "name": "SDG Country Profiles",
    "description": (
        "Country-level Sustainable Development Goal scorecards, rankings and "
        "source-backed indicators for every UN member state."
    ),
    "skills": [
        {
            "id": "sdg-country-profile",
            "name": "SDG Country Profile",
            "description": "Retrieve a country's Sustainable Development Goal score, rank and goal-level breakdown.",
            "tags": ["sdg", "sustainability", "country-data"],
        },
        {
            "id": "sdg-sources",
            "name": "SDG Data Sources",
            "description": "List the public data sources and refresh status behind the SDG scores.",
            "tags": ["sdg", "open-data", "provenance"],
        },
    ],
    "api_path": "/api/sources/",
}

BASE = f"https://{SITE['host']}"


def _json(data, content_type="application/json; charset=utf-8"):
    response = HttpResponse(
        json.dumps(data, indent=2, ensure_ascii=False),
        content_type=content_type,
    )
    response["Access-Control-Allow-Origin"] = "*"
    return response


def _oauth_authorization_server():
    return {
        "issuer": BASE,
        "authorization_endpoint": f"{BASE}/api/auth/authorize",
        "token_endpoint": f"{BASE}/api/auth/token",
        "registration_endpoint": f"{BASE}/api/agent/register",
        "jwks_uri": f"{BASE}/.well-known/jwks.json",
        "response_types_supported": ["code", "token"],
        "grant_types_supported": [
            "authorization_code",
            "client_credentials",
            "urn:ietf:params:oauth:grant-type:token-exchange",
        ],
        "scopes_supported": ["read", "write", "openid", "profile", "email"],
        "token_endpoint_auth_methods_supported": [
            "client_secret_basic",
            "client_secret_post",
        ],
        "poppy_domains": [SITE["host"]],
        "revocation_endpoint": f"{BASE}/api/agent/revoke",
        "device_authorization_endpoint": f"{BASE}/oauth/device_authorization",
        "agent_auth": {
            "skill": f"{BASE}/auth.md",
            "register_uri": f"{BASE}/api/agent/register",
            "identity_types_supported": ["identity_assertion", "anonymous"],
            "identity_assertion": {
                "assertion_types_supported": [
                    "urn:ietf:params:oauth:token-type:id-jag",
                    "verified_email",
                ],
                "credential_types_supported": ["bearer_token", "api_key"],
            },
            "anonymous": {"credential_types_supported": ["bearer_token", "api_key"]},
            "credential_types_supported": ["bearer_token", "api_key"],
            "claim_uri": f"{BASE}/api/agent/claim",
            "revocation_uri": f"{BASE}/api/agent/revoke",
            "events_supported": ["revocation"],
        },
    }


def _openid_configuration():
    return {
        "issuer": BASE,
        "authorization_endpoint": f"{BASE}/api/auth/authorize",
        "token_endpoint": f"{BASE}/api/auth/token",
        "userinfo_endpoint": f"{BASE}/api/auth/userinfo",
        "jwks_uri": f"{BASE}/.well-known/jwks.json",
        "response_types_supported": ["code", "token", "id_token"],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": ["RS256"],
        "grant_types_supported": [
            "authorization_code",
            "client_credentials",
            "urn:ietf:params:oauth:grant-type:token-exchange",
        ],
        "scopes_supported": ["openid", "profile", "email", "read", "write"],
        "token_endpoint_auth_methods_supported": [
            "client_secret_basic",
            "client_secret_post",
        ],
    }


def _llms_txt():
    return f"""# {SITE['name']}

> {SITE['description']}

## Overview
{SITE['name']} publishes Sustainable Development Goal scores and indicator
breakdowns for every UN member state, sourced from public datasets.

## Endpoints
- Homepage: {BASE}/
- API: {BASE}{SITE['api_path']}
- API Catalog: {BASE}/.well-known/api-catalog
- Agent Card: {BASE}/.well-known/agent-card.json
- AI Catalog: {BASE}/.well-known/ai-catalog.json
- Authentication Guide: {BASE}/auth.md
- Sitemap: {BASE}/sitemap.xml
"""


def _auth_md():
    return f"""# auth.md

## Overview
Authentication and registration guide for autonomous agents using
{SITE['name']}.

## Discovery
- OAuth Protected Resource Metadata: {BASE}/.well-known/oauth-protected-resource
- OAuth 2.0 Authorization Server Metadata: {BASE}/.well-known/oauth-authorization-server
- OpenID Connect Discovery: {BASE}/.well-known/openid-configuration
- API Catalog: {BASE}/.well-known/api-catalog
- Agent Card: {BASE}/.well-known/agent-card.json

## Registration
- Registration URI: {BASE}/api/agent/register
- Claim URI: {BASE}/api/agent/claim
- Revocation URI: {BASE}/api/agent/revoke

Public read-only data can be fetched without credentials. Agents that need
write access register at the registration URI and receive bearer credentials.
"""


def _server_card():
    return {
        "serverInfo": {"name": "sdg-country-profiles", "version": "1.0.0"},
        "endpoint": f"{BASE}/mcp",
        "capabilities": {
            "tools": {"listChanged": False},
            "resources": {"subscribe": False, "listChanged": False},
            "prompts": {"listChanged": False},
        },
    }


def _skills_index():
    return {
        "$schema": "https://schemas.agentskills.io/discovery/0.2.0/schema.json",
        "skills": [
            {
                "name": skill["id"],
                "type": "skill-md",
                "description": skill["description"],
                "url": f"{BASE}/.well-known/agent-skills/{skill['id']}/SKILL.md",
            }
            for skill in SITE["skills"]
        ],
    }


def _skill_md(skill):
    return f"""---
name: {skill['id']}
description: {skill['description']}
---

# {skill['name']}

{skill['description']}

Use the public site at {BASE}/ and the API at {BASE}{SITE['api_path']}.
"""


def home(request: HttpRequest) -> HttpResponse:
    return _json(
        {
            "name": SITE["name"],
            "description": SITE["description"],
            "url": f"{BASE}/",
            "skills": SITE["skills"],
        }
    )


def agent_card(request: HttpRequest) -> HttpResponse:
    return _json(
        {
            "name": f"{SITE['name']} Agent",
            "description": SITE["description"],
            "url": BASE,
            "provider": {"name": "Nevatal", "url": BASE},
            "version": "1.0.0",
            "protocolVersion": "0.3.0",
            "preferredTransport": "JSONRPC",
            "supportedInterfaces": [
                {
                    "url": f"{BASE}/api",
                    "protocolBinding": "JSONRPC",
                    "protocolVersion": "0.3.0",
                }
            ],
            "capabilities": {"streaming": False, "pushNotifications": False},
            "defaultInputModes": ["text/plain"],
            "defaultOutputModes": ["text/plain"],
            "skills": SITE["skills"],
            "authentication": {
                "type": "oauth2",
                "discovery_url": f"{BASE}/.well-known/oauth-authorization-server",
            },
        }
    )


def api_catalog(request: HttpRequest) -> HttpResponse:
    return _json(
        {
            "linkset": [
                {
                    "anchor": f"{BASE}/api",
                    "service-desc": [
                        {"href": f"{BASE}{SITE['api_path']}", "type": "application/json"}
                    ],
                    "service-doc": [
                        {"href": f"{BASE}/auth.md", "type": "text/markdown"}
                    ],
                    "status": [
                        {"href": f"{BASE}/healthz", "type": "application/json"}
                    ],
                }
            ]
        },
        content_type="application/linkset+json; charset=utf-8",
    )


def ai_catalog(request: HttpRequest) -> HttpResponse:
    return _json(
        {
            "specVersion": "1.0",
            "host": {
                "displayName": SITE["name"],
                "identifier": f"did:web:{SITE['host']}",
            },
            "entries": [
                {
                    "identifier": f"urn:air:{SITE['host']}:api:sources",
                    "displayName": f"{SITE['name']} API",
                    "type": "application/json",
                    "url": f"{BASE}{SITE['api_path']}",
                    "representativeQueries": [
                        "show sdg scores by country",
                        "which country ranks highest on the sdg index",
                        "list sdg data sources",
                    ],
                },
                {
                    "identifier": f"urn:air:{SITE['host']}:server:mcp",
                    "displayName": f"{SITE['name']} MCP Server",
                    "type": "application/mcp-server-card+json",
                    "url": f"{BASE}/.well-known/mcp/server-card.json",
                    "representativeQueries": ["query sdg country data"],
                },
            ],
        }
    )


def poppy(request: HttpRequest) -> HttpResponse:
    return _json(
        {
            "protocol_version": "0.1",
            "organization": {"name": "Nevatal", "domain": SITE["host"]},
            "auth": {
                "issuer": BASE,
                "direct": {"scopes": ["poppy:read", "poppy:write"]},
                "device": {"scopes": ["poppy:read", "poppy:write"]},
            },
            "agent": {
                "protocols": [{"type": "poppy", "endpoint": f"{BASE}/api/"}]
            },
            "apis": [
                {
                    "type": "openapi",
                    "url": f"{BASE}{SITE['api_path']}",
                    "description": f"{SITE['name']} API",
                },
                {
                    "type": "mcp",
                    "url": f"{BASE}/mcp",
                    "description": f"{SITE['name']} MCP server",
                },
            ],
            "web": {"browser_session_endpoint": f"{BASE}/"},
            "extensions": {},
        }
    )


def oauth_protected_resource(request: HttpRequest) -> HttpResponse:
    return _json(
        {
            "resource": BASE,
            "authorization_servers": [BASE],
            "scopes_supported": ["read", "write"],
            "bearer_methods_supported": ["header"],
            "resource_documentation": f"{BASE}/auth.md",
            "agent_auth": {
                "skill": f"{BASE}/auth.md",
                "register_uri": f"{BASE}/api/agent/register",
            },
        }
    )


def oauth_authorization_server(request: HttpRequest) -> HttpResponse:
    return _json(_oauth_authorization_server())


def openid_configuration(request: HttpRequest) -> HttpResponse:
    return _json(_openid_configuration())


def jwks(request: HttpRequest) -> HttpResponse:
    return _json({"keys": []})


def auth_md(request: HttpRequest) -> HttpResponse:
    return HttpResponse(_auth_md(), content_type="text/markdown; charset=utf-8")


def llms_txt(request: HttpRequest) -> HttpResponse:
    return HttpResponse(_llms_txt(), content_type="text/markdown; charset=utf-8")


def mcp_server_card(request: HttpRequest) -> HttpResponse:
    return _json(_server_card())


def agent_skills_index(request: HttpRequest) -> HttpResponse:
    return _json(_skills_index())


def agent_skill(request: HttpRequest, skill_id: str) -> HttpResponse:
    for skill in SITE["skills"]:
        if skill["id"] == skill_id:
            return HttpResponse(
                _skill_md(skill), content_type="text/markdown; charset=utf-8"
            )
    return HttpResponse("Skill not found", status=404, content_type="text/plain")


class AgentDiscoveryMiddleware:
    """Adds discovery Link headers and markdown content negotiation."""

    LINK = (
        f'</.well-known/api-catalog>; rel="api-catalog", '
        f'</auth.md>; rel="describedby"; type="text/markdown", '
        f'</.well-known/agent-card.json>; rel="a2a-agent-card", '
        f'</.well-known/ai-catalog.json>; rel="ai-catalog"'
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.method in ("GET", "HEAD")
            and request.path == "/"
            and "text/markdown" in request.headers.get("Accept", "")
        ):
            content = _llms_txt()
            response = HttpResponse(
                content, content_type="text/markdown; charset=utf-8"
            )
            response["Link"] = self.LINK
            response["X-Markdown-Tokens"] = str(
                max(1, round(len(content.split()) / 0.75))
            )
            return response

        response = self.get_response(request)
        if response.get("Content-Type", "").startswith("text/html"):
            response["Link"] = self.LINK
        if request.path.startswith("/.well-known/"):
            response["Access-Control-Allow-Origin"] = "*"
        return response
