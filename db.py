"""
Database operations for Blind Aria Trainer (Supabase integration).
"""

from typing import Optional

import streamlit as st


# =========================
# Supabase Client Setup
# =========================
def supabase_available() -> bool:
    """Check if Supabase package is installed."""
    try:
        import supabase  # noqa: F401
        return True
    except Exception:
        return False


def get_supabase_url_key():
    """Retrieve Supabase URL and key from Streamlit secrets."""
    url = st.secrets.get("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_ANON_KEY")
    if not url or not key:
        st.error("Missing SUPABASE_URL / SUPABASE_ANON_KEY in Streamlit secrets.")
        st.stop()
    return url, key


def create_sb_client(access_token: Optional[str] = None):
    """Create and return a Supabase client."""
    try:
        from supabase import create_client  # type: ignore
    except Exception:
        st.error("Supabase package not installed. Add `supabase>=2.0.0` to requirements.txt.")
        st.stop()

    url, anon_key = get_supabase_url_key()
    sb = create_client(url, anon_key)
    if access_token:
        sb.postgrest.auth(access_token)
        try:
            sb.storage.auth(access_token)
        except Exception:
            pass
    return sb


# =========================
# Session Management
# =========================
def create_party_session(sb, title: str, work_id: str, video_ids: list[str]) -> str:
    """Create a new party session in database."""
    res = sb.table("game_sessions").insert({"title": title, "work_id": work_id, "video_ids": video_ids}).execute()
    session_id = res.data[0]["id"]

    owner_id = get_user_id()
    if owner_id:
        sb.table("session_members").insert({"session_id": session_id, "user_id": owner_id, "role": "owner"}).execute()

    return session_id


def ensure_member(sb, session_id: str, user_id: str):
    """Ensure a user is a member of a session."""
    mem = sb.table("session_members").select("*").eq("session_id", session_id).eq("user_id", user_id).execute()
    if not mem.data:
        sb.table("session_members").insert({"session_id": session_id, "user_id": user_id, "role": "member"}).execute()


def get_member_role(sb, session_id: str, user_id: str) -> Optional[str]:
    """Get a user's role in a session."""
    mem = sb.table("session_members").select("role").eq("session_id", session_id).eq("user_id", user_id).execute()
    if mem.data:
        return mem.data[0].get("role")
    return None


def load_party_session(sb, session_id: str) -> dict:
    """Load session details from database."""
    return sb.table("game_sessions").select("*").eq("id", session_id).single().execute().data


def update_party_session_work(sb, session_id: str, work_id: str, video_ids: list[str]):
    """Update session with new work and video IDs."""
    sb.table("game_sessions").update({"work_id": work_id, "video_ids": video_ids}).eq("id", session_id).execute()


def update_party_session_takes(sb, session_id: str, video_ids: list[str]):
    """Update session video IDs (reshuffle takes)."""
    sb.table("game_sessions").update({"video_ids": video_ids}).eq("id", session_id).execute()


# =========================
# Notes (Questionnaire Responses)
# =========================
def upsert_note(sb, session_id: str, user_id: str, work_id: str, video_id: str, payload: dict):
    """Save or update a user's notes for a video in a session."""
    sb.table("session_notes").upsert(
        {"session_id": session_id, "user_id": user_id, "work_id": work_id, "video_id": video_id, "payload": payload},
        on_conflict="session_id,user_id,work_id,video_id",
    ).execute()


def load_note(sb, session_id: str, user_id: str, work_id: str, video_id: str) -> Optional[dict]:
    """Load a user's saved notes for a specific video."""
    res = (
        sb.table("session_notes")
        .select("payload")
        .eq("session_id", session_id)
        .eq("user_id", user_id)
        .eq("work_id", work_id)
        .eq("video_id", video_id)
        .execute()
    )
    if res.data:
        return res.data[0]["payload"]
    return None


# =========================
# Authentication & User Info
# =========================
def is_logged_in() -> bool:
    """Check if user is authenticated."""
    return bool(st.session_state.get("sb_auth"))


def get_user_id() -> Optional[str]:
    """Get current user ID from session state."""
    auth = st.session_state.get("sb_auth") or {}
    return auth.get("user_id")


def get_authed_client():
    """Get an authenticated Supabase client."""
    auth = st.session_state.get("sb_auth") or {}
    token = auth.get("access_token")
    if not token:
        return create_sb_client(None)
    return create_sb_client(token)
