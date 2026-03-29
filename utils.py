"""
Utility functions for Blind Aria Trainer.
"""

import json
import random
from pathlib import Path
from typing import Optional

import requests
import streamlit as st
import streamlit.components.v1 as components

from config import DATA_PATH, MIN_VERSIONS_REQUIRED


# =========================
# Catalog Loading
# =========================
@st.cache_data
def load_catalog():
    """Load and index the catalog of works."""
    if not DATA_PATH.exists():
        st.error(f"Missing catalog file at: {DATA_PATH}")
        st.stop()

    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    works = data.get("works", [])
    
    # Filter out any non-dict elements and ensure they have required fields
    valid_works = []
    for w in works:
        if isinstance(w, dict) and "id" in w and "title" in w:
            aliases = w.get("aliases") or []
            w["_search"] = " ".join([w.get("title", ""), w.get("composer", ""), *aliases]).lower()
            valid_works.append(w)
        else:
            print(f"Warning: Skipping invalid work entry: {type(w)} - {w}")
    
    return valid_works


# =========================
# YouTube Operations
# =========================
def yt_url(video_id: str) -> str:
    """Generate YouTube URL from video ID."""
    return f"https://www.youtube.com/watch?v={video_id}"


def yt_audio_only(video_id: str, autoplay: bool = True):
    """Embed YouTube video audio only (hidden player)."""
    auto = "1" if autoplay else "0"
    html = f"""
    <div style="height:0; overflow:hidden;">
      <iframe
        src="https://www.youtube.com/embed/{video_id}?autoplay={auto}&controls=0&rel=0&modestbranding=1"
        width="1" height="1"
        frameborder="0"
        allow="autoplay"
        style="opacity:0; pointer-events:none;"
      ></iframe>
    </div>
    """
    components.html(html, height=0)


@st.cache_data(ttl=24 * 3600)
def yt_oembed(video_id: str) -> Optional[dict]:
    """Fetch YouTube oEmbed metadata for a video."""
    try:
        r = requests.get(
            "https://www.youtube.com/oembed",
            params={"url": yt_url(video_id), "format": "json"},
            timeout=10,
        )
        if r.status_code != 200:
            return None
        return r.json()
    except requests.RequestException:
        return None


# =========================
# Work Selection & Versions
# =========================
def valid_video_ids(work: dict) -> list[str]:
    """Get all valid YouTube video IDs for a work."""
    return [v.get("yt") for v in work.get("videos", []) if v.get("yt")]


def has_min_versions(work: dict, n: int = MIN_VERSIONS_REQUIRED) -> bool:
    """Check if a work has minimum required versions."""
    return len(valid_video_ids(work)) >= n


def pick_versions_from_ids(video_ids: list[str], count: int) -> list[str]:
    """Pick a random subset of video IDs."""
    ids = [x for x in video_ids if x]
    if len(ids) <= count:
        random.shuffle(ids)
        return ids
    return random.sample(ids, count)


def pick_versions(work: dict, count: int) -> list[str]:
    """Pick random versions for a work."""
    return pick_versions_from_ids(valid_video_ids(work), count)


# =========================
# Keys and Identifiers
# =========================
def note_key_for(work_id: str, video_id: str) -> str:
    """Generate a unique key for a note (work + video combo)."""
    return f"{work_id}::{video_id}"


# =========================
# Query Parameters
# =========================
def get_session_param() -> Optional[str]:
    """Get session ID from URL query params."""
    try:
        val = st.query_params.get("session")
        if isinstance(val, list):
            return val[0] if val else None
        return val
    except Exception:
        qp = st.experimental_get_query_params()
        vals = qp.get("session")
        return vals[0] if vals else None


def set_session_param(session_id: str) -> None:
    """Set session ID in URL query params."""
    try:
        st.query_params["session"] = session_id
    except Exception:
        st.experimental_set_query_params(session=session_id)


def clear_session_param() -> None:
    """Clear session ID from URL query params."""
    try:
        if "session" in st.query_params:
            st.query_params.pop("session")
    except Exception:
        st.experimental_set_query_params()


# =========================
# Checkbox Groups
# =========================
def checkbox_group(title: str, options: list[str], selected: list[str], key_prefix: str):
    """Render a group of checkboxes with a title."""
    st.markdown(f"**{title}**")
    out = []
    for opt in options:
        k = f"{key_prefix}::{opt}"
        default = opt in (selected or [])
        if st.checkbox(opt, value=default, key=k):
            out.append(opt)
    return out


# =========================
# Admin Functions
# =========================
def is_admin_user() -> bool:
    """Check if current user is an admin based on email whitelist."""
    from config import ADMIN_EMAILS
    
    auth = st.session_state.get("sb_auth") or {}
    user_email = auth.get("email", "").lower()
    
    # Check if email is in admin whitelist
    return user_email in [email.lower() for email in ADMIN_EMAILS]


def load_catalog_file() -> dict:
    """
    Load the raw catalog JSON file.
    
    TODO: In the future, this could be replaced with:
    - Supabase table query
    - API call to external catalogue service
    - Cloud storage read
    
    Returns a dict with structure: {"works": [work1, work2, ...]}
    """
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Catalog file not found at: {DATA_PATH}")
    
    try:
        return json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"Catalog JSON is invalid: {e}")


def save_catalog_file(catalog_data: dict) -> None:
    """
    Save the catalog JSON file with proper formatting.
    
    TODO: In the future, this could be replaced with:
    - Supabase table insert/update
    - API call to external catalogue service
    - Cloud storage write
    
    Args:
        catalog_data: dict with structure {"works": [work1, work2, ...]}
    
    Raises:
        IOError if file write fails
    """
    try:
        content = json.dumps(catalog_data, indent=3, ensure_ascii=False)
        DATA_PATH.write_text(content, encoding="utf-8")
    except Exception as e:
        raise IOError(f"Failed to save catalog file: {e}")


def normalize_aliases(aliases: list[str]) -> list[str]:
    """
    Clean and deduplicate aliases.
    - Remove empty strings
    - Remove duplicates
    - Strip whitespace
    """
    cleaned = [a.strip() for a in (aliases or []) if a and a.strip()]
    return list(dict.fromkeys(cleaned))  # Remove duplicates while preserving order


def normalize_video_ids(video_ids: list[str]) -> list[dict]:
    """
    Convert list of video ID strings to the proper schema format.
    - Remove empty strings
    - Convert to [{"yt": "id"}, ...]
    """
    valid_ids = [vid.strip() for vid in (video_ids or []) if vid and vid.strip()]
    return [{"yt": vid} for vid in valid_ids]


def validate_work_entry(
    title: str,
    composer: str,
    work_id: str,
    aliases: list[str],
    video_ids: list[str],
    existing_ids: list[str],
) -> tuple[bool, str]:
    """
    Validate a work entry before saving.
    
    Args:
        title: Work title
        composer: Composer name
        work_id: Unique work ID
        aliases: List of alternative names
        video_ids: List of YouTube video IDs
        existing_ids: List of IDs already in catalogue (for uniqueness check)
    
    Returns:
        (is_valid, error_message)
    """
    # Required fields
    if not title or not title.strip():
        return False, "Title is required."
    
    if not composer or not composer.strip():
        return False, "Composer is required."
    
    if not work_id or not work_id.strip():
        return False, "ID is required."
    
    # Unique ID check
    if work_id.strip() in existing_ids:
        return False, f"ID '{work_id}' already exists in catalogue."
    
    # Video count validation
    valid_videos = normalize_video_ids(video_ids)
    if len(valid_videos) < MIN_VERSIONS_REQUIRED:
        return False, f"Need at least {MIN_VERSIONS_REQUIRED} YouTube IDs. Currently have {len(valid_videos)}."
    
    return True, ""


def create_work_entry(
    title: str,
    composer: str,
    work_id: str,
    aliases: list[str],
    video_ids: list[str],
) -> dict:
    """
    Create a work entry in the correct schema format.
    
    This ensures consistency with existing catalogue entries.
    
    Args:
        title: Work title
        composer: Composer name
        work_id: Unique work ID
        aliases: List of alternative names
        video_ids: List of YouTube video IDs
    
    Returns:
        Work dict with schema: {
            "id": str,
            "title": str,
            "composer": str,
            "aliases": list[str],
            "videos": [{"yt": str}, ...]
        }
    """
    return {
        "id": work_id.strip(),
        "title": title.strip(),
        "composer": composer.strip(),
        "aliases": normalize_aliases(aliases),
        "videos": normalize_video_ids(video_ids),
    }


def add_work_to_catalog(
    title: str,
    composer: str,
    work_id: str,
    aliases: list[str],
    video_ids: list[str],
) -> tuple[bool, str]:
    """
    Add a new work to the catalogue and persist it.
    
    Performs validation, then appends to works.json and saves.
    
    Args:
        title, composer, work_id, aliases, video_ids: Work data
    
    Returns:
        (success, message)
    """
    try:
        # Load current catalogue
        catalog = load_catalog_file()
        existing_ids = [w.get("id") for w in catalog.get("works", [])]
        
        # Validate
        is_valid, error_msg = validate_work_entry(
            title, composer, work_id, aliases, video_ids, existing_ids
        )
        if not is_valid:
            return False, error_msg
        
        # Create entry
        new_work = create_work_entry(title, composer, work_id, aliases, video_ids)
        
        # Append and save
        catalog["works"].append(new_work)
        save_catalog_file(catalog)
        
        # Clear the cached catalogue so next load picks up the new work
        st.cache_data.clear()
        
        return True, f"✓ Added '{title}' to catalogue."
    
    except FileNotFoundError as e:
        return False, f"Error: {e}"
    except ValueError as e:
        return False, f"Error: {e}"
    except IOError as e:
        return False, f"Error: {e}"
