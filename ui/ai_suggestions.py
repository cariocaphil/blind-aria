"""
AI-assisted YouTube suggestion helpers for the admin "Add Song" panel.

All functions are pure helpers — no Streamlit state is touched here.
The UI wiring lives in admin_panel.py.

TODO: replace mock search with real YouTube Data API v3
TODO: add caching layer (st.cache_data / Redis) once real API is in place
TODO: improve ranking with an actual language model scoring pass
"""

from __future__ import annotations

import os

import requests


# ---------------------------------------------------------------------------
# Query generation
# ---------------------------------------------------------------------------

def generate_search_queries(query: str) -> list[str]:
    """
    Return 3 progressively-specific search queries derived from *query*.

    The base string is lightly cleaned (extra spaces / punctuation that
    YouTube chokes on) and then combined with known high-quality suffixes
    for classical art-song recordings.

    Example
    -------
    >>> generate_search_queries("Schumann Die alten, bösen Lieder")
    [
        "Schumann Die alten bösen Lieder Lied",
        "Schumann Die alten bösen Lieder live recital",
        "Schumann Die alten bösen Lieder Lebendige Vergangenheit",
    ]
    """
    # Minimal cleaning: collapse whitespace, drop lone commas
    base = " ".join(query.replace(",", "").split()).strip()

    return [
        f"{base} Lied",
        f"{base} live recital",
        f"{base} Lebendige Vergangenheit",
        # f"{base} art song performance",   # optional 4th — uncomment if needed
    ]


# ---------------------------------------------------------------------------
# YouTube search (real API)
# ---------------------------------------------------------------------------

_YT_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"


def search_youtube(query: str) -> list[dict]:
    """
    Call the YouTube Data API v3 /search endpoint and return structured results.

    Each entry: {"videoId": str, "title": str, "channel": str}

    Reads the API key from the environment variable YOUTUBE_API_KEY.
    Returns an empty list (never raises) if:
      - the key is missing
      - the network request fails
      - the API returns an error (e.g. quota exceeded)

    TODO: add caching to reduce API usage
    TODO: increase maxResults if needed
    TODO: support advanced filters (duration, relevance)
    """
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        # Surface a visible warning in the Streamlit UI without crashing.
        # Import here to keep this module usable outside of Streamlit contexts.
        try:
            import streamlit as st
            st.warning(
                "YOUTUBE_API_KEY environment variable is not set. "
                "YouTube suggestions are unavailable."
            )
        except Exception:
            pass
        return []

    params: dict = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": 5,   # TODO: increase maxResults if needed
        "key": api_key,
    }

    try:
        response = requests.get(_YT_SEARCH_URL, params=params, timeout=10)
        response.raise_for_status()
    except requests.exceptions.HTTPError as exc:
        # 403 = quota exceeded or bad key; 4xx/5xx covered generically
        try:
            import streamlit as st
            st.warning(f"YouTube API error: {exc}")
        except Exception:
            pass
        return []
    except requests.RequestException:
        # Network-level failure — fail silently so the rest of the form works
        return []

    items: list[dict] = response.json().get("items", [])

    seen: set[str] = set()
    results: list[dict] = []
    for item in items:
        video_id: str = item.get("id", {}).get("videoId", "")
        if not video_id or video_id in seen:
            continue  # skip missing or duplicate IDs
        seen.add(video_id)
        snippet: dict = item.get("snippet", {})
        results.append({
            "videoId": video_id,
            "title":   snippet.get("title", ""),
            "channel": snippet.get("channelTitle", ""),
        })

    return results


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

# Terms that reliably indicate a non-vocal / non-performance recording.
_FILTER_TERMS: tuple[str, ...] = (
    "instrumental",
    "piano",
    "violin",
    "karaoke",
    "tutorial",
    "score",
    "sheet music",
    "backing track",
    "arrangement",
)


def filter_candidates(videos: list[dict]) -> list[dict]:
    """
    Remove videos whose title contains any of the known noise terms.

    Matching is case-insensitive and checks both *title* and *channel*.
    """
    def _is_noise(video: dict) -> bool:
        haystack = (video.get("title", "") + " " + video.get("channel", "")).lower()
        return any(term in haystack for term in _FILTER_TERMS)

    return [v for v in videos if not _is_noise(v)]


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------

# Scoring rubric (adjust weights freely):
_SCORE_RULES: list[tuple[int, tuple[str, ...]]] = [
    (+3, ("lebendige vergangenheit",)),
    (+2, ("preiser",)),
    (+1, ("live", "recital", "liederabend")),
]

# Any of these in a *passed* video lower its rank (soft penalty — not filtered)
_SOFT_PENALTY_TERMS: tuple[str, ...] = (
    "instrumental",
    "piano",
    "violin",
)


def rank_candidates(videos: list[dict]) -> list[dict]:
    """
    Score each video and return the list sorted descending by score.

    Scoring:
      +3  title/channel contains "lebendige vergangenheit"
      +2  title/channel contains "preiser"
      +1  title/channel contains "live" | "recital" | "liederabend"
      -2  title/channel still contains a soft-penalty term
    """
    def _score(video: dict) -> int:
        haystack = (video.get("title", "") + " " + video.get("channel", "")).lower()
        score = 0
        for points, terms in _SCORE_RULES:
            if any(t in haystack for t in terms):
                score += points
        if any(t in haystack for t in _SOFT_PENALTY_TERMS):
            score -= 2
        return score

    return sorted(videos, key=_score, reverse=True)


# ---------------------------------------------------------------------------
# Full pipeline (convenience wrapper)
# ---------------------------------------------------------------------------

def suggest_videos(query: str, max_results: int = 8) -> list[dict]:
    """
    Run the full suggestion pipeline for *query*.

    Steps:
      1. Generate varied search queries
      2. Fetch candidates from YouTube (or mock)
      3. De-duplicate by videoId
      4. Filter noise
      5. Rank
      6. Return top *max_results*

    Each returned dict has an extra "score" key for debugging.
    """
    queries = generate_search_queries(query)

    # Collect & de-duplicate
    seen: set[str] = set()
    all_videos: list[dict] = []
    for q in queries:
        for v in search_youtube(q):
            vid = v.get("videoId", "")
            if vid and vid not in seen:
                seen.add(vid)
                all_videos.append(v)

    filtered = filter_candidates(all_videos)
    ranked = rank_candidates(filtered)

    # Attach score for optional display
    def _score(video: dict) -> int:
        haystack = (video.get("title", "") + " " + video.get("channel", "")).lower()
        score = 0
        for points, terms in _SCORE_RULES:
            if any(t in haystack for t in terms):
                score += points
        if any(t in haystack for t in _SOFT_PENALTY_TERMS):
            score -= 2
        return score

    for v in ranked:
        v["_score"] = _score(v)

    return ranked[:max_results]


# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------

def find_similar_works(
    title: str,
    composer: str,
    works: list[dict],
) -> list[dict]:
    """
    Return any existing works that are suspiciously similar to the
    given *title* / *composer* pair.

    Uses a simple lower-case substring check — good enough without
    pulling in a fuzzy-match dependency.

    TODO: replace with fuzzy matching (e.g. rapidfuzz) for robustness
    """
    title_lower = title.strip().lower()
    composer_lower = composer.strip().lower()

    if not title_lower:
        return []

    matches: list[dict] = []
    for w in works:
        existing_title = w.get("title", "").lower()
        existing_composer = w.get("composer", "").lower()
        existing_search = w.get("_search", "").lower()

        title_hit = (
            title_lower in existing_title
            or existing_title in title_lower
        )
        composer_hit = (
            not composer_lower  # if no composer given, skip composer check
            or composer_lower in existing_composer
            or existing_composer in composer_lower
        )
        # Also check the pre-built _search index (covers aliases)
        search_hit = title_lower in existing_search

        if (title_hit and composer_hit) or search_hit:
            matches.append(w)

    return matches
