from django.urls import path

from . import discovery
from .views import (
    about,
    ads_txt,
    country,
    country_api,
    goal,
    healthz,
    home,
    info_score,
    robots,
    search,
    sitemap,
    sources_api,
)

urlpatterns = [
    path("", home, name="home"),
    path("sitemap.xml", sitemap, name="sitemap"),
    path("robots.txt", robots, name="robots"),
    path("ads.txt", ads_txt, name="ads_txt"),
    path("about/", about, name="about"),
    path("search/", search, name="search"),
    path("country/<str:country_name>/", country, name="country"),
    path("goal/<int:number>/", goal, name="goal"),
    path("api/country/<str:country_name>/", country_api, name="country_api"),
    path("api/sources/", sources_api, name="sources_api"),
    path("healthz", healthz, name="healthz"),
    path(".well-known/agent-card.json", discovery.agent_card, name="agent-card"),
    path(".well-known/ai-catalog.json", discovery.ai_catalog, name="ai-catalog"),
    path(".well-known/api-catalog", discovery.api_catalog, name="api-catalog"),
    path(".well-known/poppy.json", discovery.poppy, name="poppy"),
    path(
        ".well-known/oauth-protected-resource",
        discovery.oauth_protected_resource,
        name="oauth-protected-resource",
    ),
    path(
        ".well-known/oauth-authorization-server",
        discovery.oauth_authorization_server,
        name="oauth-authorization-server",
    ),
    path(
        ".well-known/openid-configuration",
        discovery.openid_configuration,
        name="openid-configuration",
    ),
    path(".well-known/jwks.json", discovery.jwks, name="jwks"),
    path(
        ".well-known/mcp/server-card.json",
        discovery.mcp_server_card,
        name="mcp-server-card",
    ),
    path(
        ".well-known/mcp/server-cards.json",
        discovery.mcp_server_card,
        name="mcp-server-cards",
    ),
    path(
        ".well-known/agent-skills/index.json",
        discovery.agent_skills_index,
        name="agent-skills-index",
    ),
    path(
        ".well-known/agent-skills/<str:skill_id>/SKILL.md",
        discovery.agent_skill,
        name="agent-skill",
    ),
    path("auth.md", discovery.auth_md, name="auth-md"),
    path("llms.txt", discovery.llms_txt, name="llms-txt"),
    # The original URL shape, kept so existing links keep working.
    path("info_score/<str:country_name>", info_score, name="info_score"),
]
