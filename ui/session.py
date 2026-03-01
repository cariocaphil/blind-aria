"""
Party session creation and management UI.
"""

import random

import streamlit as st

from config import MIN_VERSIONS_REQUIRED
from db import (
    create_party_session, 
    get_authed_client, 
    get_user_id, 
    load_party_session,
    update_party_session_work,
    update_party_session_takes,
)
from utils import load_catalog, pick_versions, set_session_param


def create_session_ui(sb) -> str:
    """
    Display UI for creating a new party session.
    
    Returns:
        session_id of the created session, or None if not created
    """
    st.subheader("Party mode")
    st.write("Create a shared listening session and send the link to a friend.")
    title = st.text_input("Session title", value="Blind listening session")
    versions_count = st.number_input("Number of takes", min_value=3, max_value=10, value=5, step=1)

    choice_mode = st.radio("Choose aria", ["Random", "Search"], horizontal=True)
    chosen_work = None
    
    works = load_catalog()
    eligible_works = [w for w in works if len([v.get("yt") for v in w.get("videos", []) if v.get("yt")]) >= MIN_VERSIONS_REQUIRED]

    if choice_mode == "Random":
        chosen_work = random.choice(eligible_works)
        st.info(f"Random pick: **{chosen_work['title']} — {chosen_work.get('composer','')}**")
    else:
        q = st.text_input("Search", placeholder="e.g. Don Giovanni, Vissi d'arte, Mozart")
        matches = [w for w in eligible_works if q.strip().lower() in w["_search"]] if q.strip() else []
        if matches:
            labels = {f'{w["title"]} — {w.get("composer","")}': w for w in matches}
            sel = st.selectbox("Select", list(labels.keys()))
            chosen_work = labels[sel]
        elif q.strip():
            st.warning(f"No eligible matches (need ≥ {MIN_VERSIONS_REQUIRED} versions).")

    if chosen_work and st.button("Create shared session", width="stretch"):
        vids = pick_versions(chosen_work, int(versions_count))
        if len(vids) < MIN_VERSIONS_REQUIRED:
            st.error("Not enough versions in this work.")
            st.stop()
        try:
            new_id = create_party_session(sb, title.strip() or "Blind listening session", chosen_work["id"], vids)
            st.session_state.active_session_id = new_id
            set_session_param(new_id)
            st.success("Session created. Share the URL (it includes ?session=...).")
            st.rerun()
        except Exception as e:
            st.error(f"Could not create session: {e}")

    st.stop()


def owner_controls_ui(sb, party_session_id: str, party_user_id: str, party_session: dict, current_work: dict, versions: list[str]):
    """Display session control options for owner."""
    is_owner = party_session.get("owner_id") == party_user_id

    with st.expander("Session controls", expanded=False):
        cA, cB = st.columns([1, 1])
        with cA:
            if st.button("🔄 Refresh session", width="stretch"):
                st.rerun()
        with cB:
            st.caption("Owner can change aria / reshuffle.")

        if not is_owner:
            st.info("You're a member. Ask the owner to change the aria.")
        else:
            new_count = st.number_input("Number of takes", min_value=3, max_value=10, value=max(3, len(versions)), step=1)

            pick_mode = st.radio("Pick new aria", ["Random", "Search"], horizontal=True, key="owner_pick_mode")
            selected_work = None
            
            works = load_catalog()
            eligible_works = [w for w in works if len([v.get("yt") for v in w.get("videos", []) if v.get("yt")]) >= MIN_VERSIONS_REQUIRED]

            if pick_mode == "Random":
                selected_work = random.choice(eligible_works)
                st.write(f"Next: **{selected_work['title']} — {selected_work.get('composer','')}**")
            else:
                qq = st.text_input("Search catalogue", key="owner_search", placeholder="Type aria/opera/composer…")
                candidates = [w for w in eligible_works if qq.strip().lower() in w["_search"]] if qq.strip() else []
                if candidates:
                    labels = {f'{w["title"]} — {w.get("composer","")}': w for w in candidates}
                    sel = st.selectbox("Select aria", list(labels.keys()), key="owner_select_work")
                    selected_work = labels[sel]
                elif qq.strip():
                    st.warning("No eligible match (needs ≥ 3 takes).")

            col1, col2 = st.columns([1, 1])
            with col1:
                if selected_work and st.button("✅ Change aria now", width="stretch"):
                    new_vids = pick_versions(selected_work, int(new_count))
                    try:
                        update_party_session_work(sb, party_session_id, selected_work["id"], new_vids)
                        st.session_state.now_playing = None
                        st.success("Aria changed.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not update session: {e}")

            with col2:
                if st.button("🔀 Reshuffle takes (same aria)", width="stretch"):
                    new_vids = pick_versions(current_work, int(new_count))
                    try:
                        update_party_session_takes(sb, party_session_id, new_vids)
                        st.session_state.now_playing = None
                        st.success("Takes reshuffled.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not reshuffle takes: {e}")
