"""
Session state initialization for Blind Aria Trainer.
"""

import streamlit as st


def init_session_state() -> None:
    """Initialize all session state variables."""
    if "now_playing" not in st.session_state:
        st.session_state.now_playing = None
    if "shuffle_seed" not in st.session_state:
        st.session_state.shuffle_seed = 0
    if "played_by_work" not in st.session_state:
        st.session_state.played_by_work = {}
    if "notes" not in st.session_state:
        st.session_state.notes = {}
    if "wants_party_mode" not in st.session_state:
        st.session_state.wants_party_mode = False
    if "active_session_id" not in st.session_state:
        st.session_state.active_session_id = None
