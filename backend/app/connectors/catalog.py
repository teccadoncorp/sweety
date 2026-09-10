from __future__ import annotations

from dataclasses import dataclass, field

from app.core.config import get_settings


@dataclass
class ProviderSpec:
    id: str
    label: str
    auth: str
    description: str
    connect_hint: str
    scopes: list[str] = field(default_factory=list)
    manual_fields: list[str] = field(default_factory=list)
    oauth_ready: bool = False
    env_ready: bool = False


def _settings_flags() -> dict[str, bool]:
    s = get_settings()
    return {
        "reddit": bool(s.reddit_client_id and s.reddit_client_secret),
        "twitter": bool(s.twitter_client_id and s.twitter_client_secret),
        "linkedin": bool(s.linkedin_client_id and s.linkedin_client_secret),
        "facebook": bool(s.facebook_client_id and s.facebook_client_secret),
        "instagram": bool(s.facebook_client_id and s.facebook_client_secret),
        "heygen": bool(s.heygen_api_key),
        "tavily": bool(s.tavily_api_key),
        "brave": bool(s.brave_api_key),
        "openrouter": bool(s.openrouter_api_key),
    }


def provider_specs() -> list[ProviderSpec]:
    flags = _settings_flags()
    return [
        ProviderSpec(
            id="reddit",
            label="Reddit",
            auth="oauth",
            description="Login with Reddit and grant submit access, or paste an app token.",
            connect_hint="Create a Reddit web app. Redirect URI must be {api}/api/v1/connectors/callback/reddit",
            scopes=["identity", "submit", "read"],
            manual_fields=["access_token", "refresh_token", "subreddit"],
            oauth_ready=flags["reddit"],
        ),
        ProviderSpec(
            id="twitter",
            label="X / Twitter",
            auth="oauth",
            description="Login with X (OAuth 2.0 + PKCE) to post tweets.",
            connect_hint="X developer portal → User authentication. Callback {api}/api/v1/connectors/callback/twitter",
            scopes=["tweet.read", "tweet.write", "users.read", "offline.access"],
            manual_fields=["access_token", "refresh_token"],
            oauth_ready=flags["twitter"],
        ),
        ProviderSpec(
            id="linkedin",
            label="LinkedIn",
            auth="oauth",
            description="Login with LinkedIn to publish member posts (w_member_social).",
            connect_hint="LinkedIn app → Auth. Redirect {api}/api/v1/connectors/callback/linkedin. Product: Share on LinkedIn.",
            scopes=["openid", "profile", "w_member_social"],
            manual_fields=["access_token", "person_urn"],
            oauth_ready=flags["linkedin"],
        ),
        ProviderSpec(
            id="facebook",
            label="Facebook Pages",
            auth="oauth",
            description=f"Login with Facebook, then pick the Page {get_settings().app_name} should post to.",
            connect_hint="Meta app with Facebook Login. Redirect {api}/api/v1/connectors/callback/facebook",
            scopes=["pages_show_list", "pages_manage_posts", "pages_read_engagement"],
            manual_fields=["access_token", "page_id"],
            oauth_ready=flags["facebook"],
        ),
        ProviderSpec(
            id="instagram",
            label="Instagram",
            auth="oauth",
            description="Uses Facebook Login. Requires a professional IG account linked to a Page.",
            connect_hint="Same Meta app as Facebook. After login, pick the Instagram business account. Image URLs must be publicly reachable.",
            scopes=[
                "pages_show_list",
                "pages_read_engagement",
                "instagram_basic",
                "instagram_content_publish",
            ],
            manual_fields=["access_token", "ig_user_id"],
            oauth_ready=flags["instagram"],
        ),
        ProviderSpec(
            id="heygen",
            label="HeyGen video",
            auth="api_key",
            description="Avatar videos from a script. Set HEYGEN_API_KEY or paste a key per brand.",
            connect_hint="HeyGen dashboard → API token. Optional default avatar and voice IDs in .env.",
            manual_fields=["api_key", "avatar_id", "voice_id"],
            env_ready=flags["heygen"],
        ),
        ProviderSpec(
            id="tavily",
            label="Tavily search",
            auth="api_key",
            description="Optional extra search index. OpenRouter web search is already primary.",
            connect_hint="https://tavily.com API key. Leave empty to use OpenRouter only.",
            manual_fields=["api_key"],
            env_ready=flags["tavily"],
        ),
    ]


def spec_map() -> dict[str, ProviderSpec]:
    return {p.id: p for p in provider_specs()}
