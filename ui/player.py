"""
Audio player and take display UI.
"""

import streamlit as st

from utils import note_key_for, yt_audio_only, yt_oembed, yt_url


def show_player_ui(current_work: dict, versions: list[str], party_mode: bool = False, sb=None, party_session_id: str = None, party_user_id: str = None):
    """
    Display the main player UI with takes, buttons, and notes.
    
    Handles:
    - Colored sections for played/unplayed takes
    - Listen/Stop buttons
    - Note saving (delegated to questionnaire module)
    - Reveal metadata
    """
    st.subheader("Player")
    st.write(f"**{current_work['title']}** — {current_work.get('composer','')}")
    st.caption(f"Takes: {len(versions)}")

    if st.button("⏹ Stop playback", width="stretch"):
        st.session_state.now_playing = None

    st.divider()

    played_set = st.session_state.played_by_work.setdefault(current_work["id"], set())

    for idx, vid in enumerate(versions, start=1):
        nk = note_key_for(current_work["id"], vid)
        is_played = vid in played_set

        if party_mode:
            from db import load_note
            saved = load_note(sb, party_session_id, party_user_id, current_work["id"], vid) or {}
        else:
            saved = st.session_state.notes.get(nk, {})

        # Apply background color based on whether the take has been played
        if is_played:
            st.markdown(f'<div style="background-color: #d4edda; padding: 20px; border-radius: 8px; margin-bottom: 10px; border-left: 4px solid #28a745;"><h3 style="margin-top: 0;">Take {idx} ✅</h3></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="background-color: #e7f3ff; padding: 20px; border-radius: 8px; margin-bottom: 10px; border-left: 4px solid #0066cc;"><h3 style="margin-top: 0;">Take {idx}</h3></div>', unsafe_allow_html=True)

        c1, c2 = st.columns([1, 1])
        with c1:
            listen_label = "✅ Played" if is_played else "🎧 Listen"
            listen_type = "secondary" if is_played else "primary"
            if st.button(listen_label, key=f"listen_{nk}", width="stretch", type=listen_type):
                st.session_state.now_playing = vid
                played_set.add(vid)
                st.rerun()

        with c2:
            if st.button("⏹ Stop", key=f"stop_{nk}", width="stretch"):
                if st.session_state.now_playing == vid:
                    st.session_state.now_playing = None

        if st.session_state.now_playing == vid:
            yt_audio_only(vid, autoplay=True)

        # Return note data for questionnaire module to handle
        yield {
            "nk": nk,
            "vid": vid,
            "saved": saved,
            "idx": idx,
        }

        with st.expander("Reveal"):
            meta = yt_oembed(vid)
            if meta:
                st.markdown(f"**Title:** {meta.get('title', '—')}")
                st.markdown(f"**Channel:** {meta.get('author_name', '—')}")
            st.write("YouTube:", yt_url(vid))

        st.divider()
