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
    get_session_members,
)
from strings import t
from utils import load_catalog, pick_versions, set_session_param


def create_session_ui(sb) -> str:
    """
    Display UI for creating a new party session.
    
    Returns:
        session_id of the created session, or None if not created
    """
    st.subheader(t("party_mode_label"))
    st.write(t("party_mode_description"))
    title = st.text_input(t("session_title_label"), value=t("session_title_default"))
    versions_count = st.number_input(t("number_of_takes_label"), min_value=3, max_value=10, value=5, step=1)

    choice_mode = st.radio(t("choose_aria_label"), [t("random"), t("search")], horizontal=True)
    chosen_work = None
    
    works = load_catalog()
    eligible_works = [w for w in works if len([v.get("yt") for v in w.get("videos", []) if v.get("yt")]) >= MIN_VERSIONS_REQUIRED]

    if choice_mode == t("random"):
        chosen_work = random.choice(eligible_works)
        st.info(f"{t('random_pick_prefix')}**{chosen_work['title']} — {chosen_work.get('composer','')}**")
    else:
        q = st.text_input(t("search"), placeholder=t("search_placeholder"))
        matches = [w for w in eligible_works if q.strip().lower() in w["_search"]] if q.strip() else []
        if matches:
            labels = {f'{w["title"]} — {w.get("composer","")}': w for w in matches}
            sel = st.selectbox("Select", list(labels.keys()))
            chosen_work = labels[sel]
        elif q.strip():
            st.warning(f"No eligible matches (need ≥ {MIN_VERSIONS_REQUIRED} versions).")

    if chosen_work and st.button(t("create_session_button"), width="stretch"):
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


def owner_controls_ui(sb, party_session_id: str, party_user_id: str, party_session: dict, current_work: dict, versions: list[str], is_invite_link: bool = False):
    """Display session control options for owner or anyone who joined via invite link."""
    is_owner = party_session.get("owner_id") == party_user_id
    can_control = is_owner or is_invite_link

    with st.expander(t("session_controls_label"), expanded=False):
        # Show session members
        members = get_session_members(sb, party_session_id)
        if members:
            st.subheader(t("session_members_label"))
            for member in members:
                role_icon = t("owner_icon") if member.get("role") == "owner" else t("member_icon")
                st.write(f"{role_icon} {member.get('user_id', 'Unknown')}")
            st.divider()

        cA, cB = st.columns([1, 1])
        with cA:
            if st.button(t("refresh_button"), width="stretch"):
                st.rerun()
        with cB:
            if can_control:
                st.caption("You can change aria / reshuffle.")
            else:
                st.caption("Owner can change aria / reshuffle.")

        if not can_control:
            st.info("You're a member. Ask the owner to change the aria.")
        else:
            new_count = st.number_input(t("number_of_takes_label"), min_value=3, max_value=10, value=max(3, len(versions)), step=1)

            pick_mode = st.radio("Pick new aria", [t("random"), t("search")], horizontal=True, key="owner_pick_mode")
            selected_work = None
            
            works = load_catalog()
            eligible_works = [w for w in works if len([v.get("yt") for v in w.get("videos", []) if v.get("yt")]) >= MIN_VERSIONS_REQUIRED]

            if pick_mode == t("random"):
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
                if st.button(t("reshuffle_button"), width="stretch"):
                    new_vids = pick_versions(current_work, int(new_count))
                    try:
                        update_party_session_takes(sb, party_session_id, new_vids)
                        st.session_state.now_playing = None
                        st.success(t("reshuffled_success"))
                        st.rerun()
                    except Exception as e:
                        st.error(t("reshuffled_error", error=str(e)))
