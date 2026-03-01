"""
Blind Aria Trainer - Main Application
"""

import random

import streamlit as st

from auth import require_login_block
from config import MIN_VERSIONS_REQUIRED
from db import (
    get_authed_client,
    get_user_id,
    is_logged_in,
    load_party_session,
    ensure_member,
    get_member_role,
)
from state import init_session_state
from ui.header import show_header
from ui.session import create_session_ui, owner_controls_ui
from ui.player import show_player_ui
from ui.questionnaire import show_questionnaire_ui
from utils import (
    clear_session_param,
    get_session_param,
    load_catalog,
    pick_versions,
    set_session_param,
)


# =========================
# Page Config
# =========================
st.set_page_config(page_title="Blind Aria Trainer", layout="centered")


# =========================
# Initialize Session State
# =========================
init_session_state()


# =========================
# Header & Navigation
# =========================
party_mode, is_invite_link, session_param = show_header()

# Invite link + not logged in => show special invite login
if is_invite_link and not is_logged_in():
    require_login_block(invited=True)
    st.stop()

# Non-invite party mode + not logged in => normal login
if (party_mode and not is_invite_link) and not is_logged_in():
    require_login_block(invited=False)
    st.stop()


# =========================
# Party Session Load / Create
# =========================
party_session = None
party_user_id = None
sb = None
party_role = None

if party_mode:
    sb = get_authed_client()
    party_user_id = get_user_id()
    if not party_user_id:
        st.error("Logged in but user id missing.")
        st.stop()

    party_session_id = session_param or st.session_state.active_session_id

    if party_session_id:
        try:
            ensure_member(sb, party_session_id, party_user_id)
            party_role = get_member_role(sb, party_session_id, party_user_id)
            party_session = load_party_session(sb, party_session_id)

            st.session_state.active_session_id = party_session_id
            set_session_param(party_session_id)

        except Exception as e:
            st.error(f"Could not join/load session: {e}")
            st.stop()

    if not party_session:
        create_session_ui(sb)


# =========================
# Determine Current Work + Takes
# =========================
works = load_catalog()

if party_mode:
    work_id = party_session["work_id"]
    shared_video_ids = party_session.get("video_ids") or []
    current_work = next((w for w in works if w["id"] == work_id), None)
    if not current_work:
        st.error("Session work_id not found in local works.json.")
        st.stop()
    versions = [vid for vid in shared_video_ids if vid]
    mode_label = f"Party: {party_session.get('title', 'Blind session')}"
else:
    st.subheader("Solo mode")
    c1, c2 = st.columns([1, 1])
    with c1:
        solo_mode = st.radio("Mode", ["Random aria", "Search"], horizontal=True)
    with c2:
        versions_count = st.number_input("Number of takes (max)", min_value=3, max_value=10, value=5, step=1)

    def set_random_work_id():
        w = random.choice([w for w in works if len([v.get("yt") for v in w.get("videos", []) if v.get("yt")]) >= MIN_VERSIONS_REQUIRED])
        st.session_state["solo_work_id"] = w["id"]
        st.session_state.shuffle_seed += 1
        st.session_state.now_playing = None
        st.session_state.played_by_work[w["id"]] = set()

    if "solo_work_id" not in st.session_state:
        set_random_work_id()

    if solo_mode == "Random aria":
        x1, x2 = st.columns([1, 1])
        with x1:
            if st.button("🎲 New random aria", width="stretch"):
                set_random_work_id()
        with x2:
            if st.button("🔀 Reshuffle takes", width="stretch"):
                st.session_state.shuffle_seed += 1
                st.session_state.now_playing = None
    else:
        q = st.text_input("Search aria / opera / composer", placeholder="e.g. Sempre libera, Don Giovanni, Mozart")
        eligible_works = [w for w in works if len([v.get("yt") for v in w.get("videos", []) if v.get("yt")]) >= MIN_VERSIONS_REQUIRED]
        matches = [w for w in eligible_works if q.strip().lower() in w["_search"]] if q.strip() else []
        if matches:
            labels = {f'{w["title"]} — {w.get("composer","")}': w["id"] for w in matches}
            sel = st.selectbox("Select work", list(labels.keys()))
            st.session_state["solo_work_id"] = labels[sel]
            st.session_state.shuffle_seed += 1
            st.session_state.now_playing = None
            st.session_state.played_by_work[labels[sel]] = set()
        elif q.strip():
            st.info(f"No matches with ≥ {MIN_VERSIONS_REQUIRED} versions.")

    current_work = next((w for w in works if w["id"] == st.session_state["solo_work_id"]), None)
    if not current_work:
        st.stop()

    random.seed(f"{current_work['id']}-{st.session_state.shuffle_seed}")
    versions = pick_versions(current_work, int(versions_count))
    random.shuffle(versions)
    mode_label = "Solo"

if len(versions) < MIN_VERSIONS_REQUIRED:
    st.error("This selection has fewer than 3 takes.")
    st.stop()


# =========================
# Party Owner Controls
# =========================
if party_mode:
    owner_controls_ui(sb, st.session_state.active_session_id, party_user_id, party_session, current_work, versions)


# =========================
# Main Player UI + Questionnaire
# =========================
st.subheader(mode_label)

for note_data in show_player_ui(
    current_work, 
    versions, 
    party_mode=party_mode,
    sb=sb,
    party_session_id=st.session_state.active_session_id if party_mode else None,
    party_user_id=party_user_id if party_mode else None,
):
    # Display questionnaire for this note
    show_questionnaire_ui(
        note_data["nk"],
        note_data["saved"],
        party_mode=party_mode,
        sb=sb,
        party_session_id=st.session_state.active_session_id if party_mode else None,
        party_user_id=party_user_id if party_mode else None,
        work_id=current_work["id"],
        vid=note_data["vid"],
    )
