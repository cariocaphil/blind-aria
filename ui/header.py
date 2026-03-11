"""
Header and top navigation UI.
"""

import random

import streamlit as st

from config import MIN_VERSIONS_REQUIRED
from strings import t
from utils import clear_session_param, get_session_param, load_catalog, set_session_param
from db import is_logged_in


def show_header() -> tuple[bool, bool, str]:
    """
    Display header and top navigation.
    
    Returns:
        (party_mode, is_invite_link, session_param)
    """
    st.title(t("title"))
    st.caption(t("subtitle"))

    works = load_catalog()
    eligible_works = [w for w in works if len([v.get("yt") for v in w.get("videos", []) if v.get("yt")]) >= MIN_VERSIONS_REQUIRED]
    if not eligible_works:
        st.error(t("no_works_error", min_versions=MIN_VERSIONS_REQUIRED))
        st.stop()

    session_param = get_session_param()
    party_session_id = session_param or st.session_state.active_session_id

    is_invite_link = bool(session_param)
    party_mode = bool(party_session_id) or bool(st.session_state.wants_party_mode)

    # Top buttons (don't distract invite landing too much)
    if not is_invite_link:
        wants_party = st.session_state.get("wants_party_mode", False)
        if wants_party and is_logged_in():
            # User has chosen party mode and is logged in - don't show buttons, they'll see session creation UI
            pass
        else:
            b1, b2, b3 = st.columns([1, 1, 1])
            with b1:
                if st.button(t("solo_button"), width="stretch"):
                    st.session_state.wants_party_mode = False
                    st.session_state.active_session_id = None
                    clear_session_param()
                    st.rerun()
            with b2:
                if not wants_party:
                    if st.button(t("party_button"), width="stretch"):
                        st.session_state.wants_party_mode = True
                        st.rerun()
            with b3:
                if party_mode and is_logged_in():
                    if st.button(t("logout_button"), width="stretch"):
                        st.session_state.pop("sb_auth", None)
                        st.session_state.pop("otp_email_sent", None)
                        st.session_state.active_session_id = None
                        clear_session_param()
                        st.rerun()
    else:
        # Invite landing: show a single "Solo" escape hatch and login prompt
        c1, c2 = st.columns([1, 2])
        with c1:
            if st.button(t("use_solo_instead"), width="stretch"):
                st.session_state.wants_party_mode = False
                st.session_state.active_session_id = None
                clear_session_param()
                st.rerun()
        with c2:
            st.info(t("invite_link_notice"))

    st.divider()

    return party_mode, is_invite_link, session_param
