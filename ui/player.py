"""
Audio player and take display UI.
"""

import streamlit as st

from strings import t
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
    st.subheader(t("player_label"))
    st.write(f"**{current_work['title']}** — {current_work.get('composer','')}")
    st.caption(f"{t('takes_label')}{len(versions)}")

    # Global stop button (useful for stopping any current playback)
    if st.session_state.now_playing:
        if st.button(t("stop_all_button"), width="stretch", type="secondary"):
            st.session_state.paused_videos.add(st.session_state.now_playing)  # Mark as paused
            st.session_state.now_playing = None
            st.rerun()

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
            st.markdown(f'<div style="background-color: #d4edda; padding: 20px; border-radius: 8px; margin-bottom: 10px; border-left: 4px solid #28a745;"><h3 style="margin-top: 0;">Take {idx} ✓</h3></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="background-color: #e7f3ff; padding: 20px; border-radius: 8px; margin-bottom: 10px; border-left: 4px solid #0066cc;"><h3 style="margin-top: 0;">Take {idx}</h3></div>', unsafe_allow_html=True)

        # Single button per take - Play/Stop/Resume functionality
        if st.session_state.now_playing == vid:
            # Currently playing this take - show Stop button
            if st.button(t("stop_button"), key=f"stop_{nk}", width="stretch", type="secondary"):
                st.session_state.now_playing = None
                st.session_state.paused_videos.add(vid)  # Mark as paused
                st.rerun()
        else:
            # Not playing this take - show Play/Resume buttons
            is_paused = vid in st.session_state.paused_videos
            
            if is_paused:
                # Show Resume and Play from beginning options
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(t("resume_button"), key=f"resume_{nk}", width="stretch", type="primary"):
                        # Validate video exists before playing
                        meta = yt_oembed(vid)
                        if not meta:
                            st.error(t("video_broken_error", idx=idx))
                        else:
                            st.session_state.now_playing = vid
                            st.session_state.paused_videos.discard(vid)  # Clear paused state
                            st.rerun()
                with col2:
                    if st.button(t("play_from_beginning_button"), key=f"restart_{nk}", width="stretch", type="secondary"):
                        # Validate video exists before playing
                        meta = yt_oembed(vid)
                        if not meta:
                            st.error(t("video_broken_error", idx=idx))
                        else:
                            st.session_state.now_playing = vid
                            st.session_state.paused_videos.discard(vid)  # Clear paused state
                            played_set.add(vid)
                            st.rerun()
            else:
                # Normal play button
                button_label = t("play_button") if not is_played else t("play_again_button")
                button_type = "primary" if not is_played else "secondary"
                if st.button(button_label, key=f"listen_{nk}", width="stretch", type=button_type):
                    # Validate video exists before playing
                    meta = yt_oembed(vid)
                    if not meta:
                        st.error(t("video_broken_error", idx=idx))
                    else:
                        st.session_state.now_playing = vid
                        played_set.add(vid)
                        st.rerun()

        if st.session_state.now_playing == vid:
            yt_audio_only(vid, autoplay=True)

        # Return note data for questionnaire module to handle
        yield {
            "nk": nk,
            "vid": vid,
            "saved": saved,
            "idx": idx,
        }

        with st.expander(t("reveal_label")):
            meta = yt_oembed(vid)
            if meta:
                st.markdown(f"**{t('title_label')}** {meta.get('title', '—')}")
                st.markdown(f"**{t('channel_label')}** {meta.get('author_name', '—')}")
            st.write(t("youtube_label"), yt_url(vid))

        st.divider()
