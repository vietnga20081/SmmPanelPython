"""Rule-based classifier: raw provider text -> standard Platform + Category.

Given a provider's raw category/name/description (very inconsistent, emoji-
laden, mixed Vietnamese/English free text), decide which standard Platform
and Category it belongs to. Pure functions, no DB access — the service layer
does the get-or-create against the Platform/Category tables.
"""
import unicodedata

# Order matters: more specific / less ambiguous platforms are checked first.
PLATFORM_RULES: list[tuple[str, list[str]]] = [
    ("TikTok", ["tiktok", "tik tok"]),
    ("Instagram", ["instagram", " ig ", "insta"]),
    ("Facebook", ["facebook", " fb "]),
    ("YouTube", ["youtube", " yt "]),
    ("Telegram", ["telegram"]),
    ("Threads", ["threads"]),
    ("X (Twitter)", ["twitter", " x (twitter)", "retweet"]),
    ("Shopee", ["shopee"]),
    ("Lazada", ["lazada"]),
    ("Spotify", ["spotify"]),
    ("LinkedIn", ["linkedin"]),
    ("Reddit", ["reddit"]),
    ("Pinterest", ["pinterest"]),
    ("Twitch", ["twitch"]),
    ("Discord", ["discord"]),
    ("Kwai", ["kwai"]),
    ("Bigo", ["bigo"]),
    ("Zalo", ["zalo"]),
    ("Google", ["google map", "google-map", "google review", "google"]),
    ("Website", ["website", "traffic web", "web traffic"]),
]

# Checked in this order; earlier rules win on overlapping keywords
# (e.g. "livestream viewers" contains "view" but must classify as Livestream).
CATEGORY_RULES: list[tuple[str, list[str]]] = [
    ("Livestream", ["livestream", "live stream", "live-stream"]),
    ("Watch Time", ["watch time", "watchtime", "gio xem"]),
    ("Subscribe", ["subscriber", "subscribe", " sub "]),
    ("Follow", ["follow", "theo doi"]),
    ("Member", ["member", "thanh vien"]),
    ("Like", ["like", "tym", "cam xuc", "yeu thich", "favorite"]),
    ("Comment", ["comment", "binh luan"]),
    ("Review", ["review", "danh gia", "rating"]),
    ("Share", ["share", "chia se", "repost", "retweet"]),
    ("Story", ["story"]),
    ("Traffic", ["traffic"]),
    ("Plays", [" play", "plays"]),
    ("Message", ["message", "nhan tin"]),
    ("View", ["view", "luot xem", "xem video"]),
]

DEFAULT_PLATFORM = "Khác"
DEFAULT_CATEGORY = "Khác"


def _normalize(text: str) -> str:
    """Lowercase + strip Vietnamese diacritics for robust substring matching."""
    text = text.lower()
    decomposed = unicodedata.normalize("NFD", text)
    stripped = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    stripped = stripped.replace("đ", "d")
    return f" {stripped} "  # pad so ' fb ' / ' x ' style keyword checks work at edges


def classify_platform(category_raw: str, name: str, description: str = "") -> str:
    """Return the best-matching standard Platform name, or 'Khác' if none match."""
    combined = _normalize(f"{category_raw} {name} {description}")
    for platform_name, keywords in PLATFORM_RULES:
        if any(kw in combined for kw in keywords):
            return platform_name
    return DEFAULT_PLATFORM


def classify_category(category_raw: str, name: str, description: str = "") -> str:
    """Return the best-matching standard Category name, or 'Khác' if none match."""
    combined = _normalize(f"{category_raw} {name} {description}")
    for category_name, keywords in CATEGORY_RULES:
        if any(kw in combined for kw in keywords):
            return category_name
    return DEFAULT_CATEGORY


def slugify(text: str) -> str:
    """Simple ASCII slug for storing alongside display names."""
    normalized = _normalize(text).strip()
    slug = "-".join(normalized.split())
    return slug or "khac"
