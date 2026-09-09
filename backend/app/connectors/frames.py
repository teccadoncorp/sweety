from __future__ import annotations

PLATFORM_FRAMES: dict[str, dict[str, str]] = {
    "instagram": {"ratio": "4:5", "size": "1080x1350", "label": "Instagram feed"},
    "instagram_feed": {"ratio": "4:5", "size": "1080x1350", "label": "Instagram feed"},
    "instagram_square": {"ratio": "1:1", "size": "1080x1080", "label": "Instagram square"},
    "instagram_story": {"ratio": "9:16", "size": "1080x1920", "label": "Instagram story"},
    "instagram_reel": {"ratio": "9:16", "size": "1080x1920", "label": "Instagram reel"},
    "facebook": {"ratio": "1.91:1", "size": "1200x630", "label": "Facebook feed"},
    "facebook_story": {"ratio": "9:16", "size": "1080x1920", "label": "Facebook story"},
    "twitter": {"ratio": "16:9", "size": "1600x900", "label": "X / Twitter"},
    "x": {"ratio": "16:9", "size": "1600x900", "label": "X / Twitter"},
    "linkedin": {"ratio": "1.91:1", "size": "1200x627", "label": "LinkedIn"},
    "reddit": {"ratio": "16:9", "size": "1920x1080", "label": "Reddit"},
    "pinterest": {"ratio": "2:3", "size": "1000x1500", "label": "Pinterest"},
    "tiktok": {"ratio": "9:16", "size": "1080x1920", "label": "TikTok"},
    "youtube": {"ratio": "16:9", "size": "1920x1080", "label": "YouTube"},
    "generic": {"ratio": "1:1", "size": "1080x1080", "label": "Square"},
}


def normalize_platform(name: str | None) -> str:
    key = (name or "").strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "ig": "instagram",
        "insta": "instagram",
        "ig_story": "instagram_story",
        "ig_reel": "instagram_reel",
        "reels": "instagram_reel",
        "stories": "instagram_story",
        "x_twitter": "twitter",
        "tweet": "twitter",
        "li": "linkedin",
        "fb": "facebook",
    }
    key = aliases.get(key, key)
    return key if key in PLATFORM_FRAMES else ""


def frame_for(platform: str | None) -> dict[str, str]:
    key = normalize_platform(platform)
    return PLATFORM_FRAMES.get(key, PLATFORM_FRAMES["generic"])
