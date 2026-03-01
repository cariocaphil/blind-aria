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
    for w in works:
        w["_search"] = " ".join([w.get("title", ""), w.get("composer", ""), *w.get("aliases", [])]).lower()
    return works


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
