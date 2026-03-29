"""
Admin panel for managing the song catalogue.
Allows whitelisted admins to add new works without editing JSON directly.
"""

import streamlit as st

from auth import admin_login_block
from db import is_logged_in
from strings import t
from utils import (
    is_admin_user,
    add_work_to_catalog,
    load_catalog,
)
from ui.ai_suggestions import suggest_videos, find_similar_works


def _init_suggestion_state() -> None:
    """Initialise session-state keys used by the AI suggestion widget."""
    if "admin_suggest_results" not in st.session_state:
        st.session_state.admin_suggest_results = []   # list[dict] from suggest_videos()
    if "admin_suggest_selected" not in st.session_state:
        st.session_state.admin_suggest_selected = {}  # {videoId: bool}


def _render_suggestion_ui(title: str, composer: str) -> None:
    """
    Render the AI suggestion sub-panel.

    Reads/writes:
      st.session_state.admin_suggest_results   — cached pipeline output
      st.session_state.admin_suggest_selected  — checkbox state per videoId
      st.session_state.admin_videos            — the main form's video-ID list
    """
    st.markdown("---")
    st.markdown("**✨ AI-Assisted YouTube Suggestions** *(optional)*")

    # --- Query input (defaults to "Composer Title" if form fields are filled) ---
    default_query = " ".join(filter(None, [composer.strip(), title.strip()]))
    suggest_query = st.text_input(
        t("admin_suggest_query_label"),
        value=default_query,
        key="admin_suggest_query",
        help=t("admin_suggest_query_help"),
        placeholder="e.g. Schumann Die alten bösen Lieder",
    )

    if st.button(t("admin_suggest_button"), key="admin_suggest_run"):
        if not suggest_query.strip():
            st.warning("Enter a search query first.")
        else:
            with st.spinner(t("admin_suggest_loading")):
                results = suggest_videos(suggest_query.strip())
            st.session_state.admin_suggest_results = results
            # Pre-select the top 3–5 results
            st.session_state.admin_suggest_selected = {
                v["videoId"]: (i < 4)
                for i, v in enumerate(results)
            }

    results: list[dict] = st.session_state.admin_suggest_results

    if not results:
        return  # Nothing to show yet

    # --- Show results as checkboxes ---
    st.caption(t("admin_suggest_results_label"))

    if not results:
        st.info(t("admin_suggest_none_found"))
        return

    for video in results:
        vid_id = video["videoId"]
        label = f"{video['title']}  —  *{video['channel']}*"
        checked = st.session_state.admin_suggest_selected.get(vid_id, False)
        new_val = st.checkbox(label, value=checked, key=f"admin_suggest_cb_{vid_id}")
        st.session_state.admin_suggest_selected[vid_id] = new_val

    # --- Apply selection button ---
    if st.button(t("admin_suggest_use_button"), key="admin_suggest_apply"):
        chosen = [
            vid_id
            for vid_id, selected in st.session_state.admin_suggest_selected.items()
            if selected
        ]
        if not chosen:
            st.warning(t("admin_suggest_no_selection"))
        else:
            # Merge into the existing admin_videos list, avoiding duplicates
            existing = [v for v in st.session_state.admin_videos if v.strip()]
            for vid_id in chosen:
                if vid_id not in existing:
                    existing.append(vid_id)
            # Pad back to at least 5 slots so the manual form looks normal
            while len(existing) < 5:
                existing.append("")
            st.session_state.admin_videos = existing
            st.success(t("admin_suggest_added", n=len(chosen)))
            st.rerun()


def show_admin_panel():
    """
    Render the admin panel for adding songs to the catalogue.
    
    Always shown to indicate the feature exists.
    - If not logged in: shows login prompt
    - If logged in but not admin: shows "admin only" message
    - If logged in and admin: shows full form + optional AI suggestions

    UI flow:
    - Title and description
    - Form fields: title, composer, id, aliases, YouTube IDs
    - AI suggestion widget (optional, does not block manual workflow)
    - Duplicate warning (if similar work detected)
    - Preview of resulting JSON entry
    - Save button with validation
    """
    # =========================================================================
    # INITIALIZE ALL SESSION STATE BEFORE RENDERING ANY WIDGETS
    # =========================================================================
    # This must happen before any st.text_input, st.checkbox, etc. is created
    # to avoid Streamlit's "cannot mutate session_state after widget creation" error
    
    if "admin_title" not in st.session_state:
        st.session_state.admin_title = ""
    if "admin_composer" not in st.session_state:
        st.session_state.admin_composer = ""
    if "admin_id" not in st.session_state:
        st.session_state.admin_id = ""
    if "admin_aliases" not in st.session_state:
        st.session_state.admin_aliases = [""]
    if "admin_videos" not in st.session_state:
        st.session_state.admin_videos = ["", "", "", "", ""]
    
    # Initialize AI suggestion state
    _init_suggestion_state()
    
    st.divider()
    
    # Check auth status
    user_is_logged_in = is_logged_in()
    user_is_admin = is_admin_user() if user_is_logged_in else False
    
    if user_is_admin:
        # =========================
        # ADMIN INTERFACE (Full form)
        # =========================
        with st.expander(t("admin_panel_title"), expanded=False):
            st.markdown(t("admin_panel_description"))
            
            col1, col2 = st.columns(2)
            
            with col1:
                title = st.text_input(
                    t("admin_field_title"),
                    key="admin_title",
                    help=t("admin_help_title"),
                )
                composer = st.text_input(
                    t("admin_field_composer"),
                    key="admin_composer",
                    help=t("admin_help_composer"),
                )
                work_id = st.text_input(
                    t("admin_field_id"),
                    key="admin_id",
                    help=t("admin_help_id"),
                    placeholder="e.g., schubert_erlkoenig",
                )
            
            with col2:
                st.markdown(f"**{t('admin_field_aliases')}**")
                st.caption(t("admin_help_aliases"))
                
                # Dynamic aliases input (already initialized at top of function)
                aliases = []
                for idx, alias in enumerate(st.session_state.admin_aliases):
                    col_a, col_b = st.columns([8, 2])
                    with col_a:
                        new_alias = st.text_input(
                            f"{t('admin_field_alias')} {idx + 1}",
                            value=alias,
                            key=f"admin_alias_{idx}",
                            label_visibility="collapsed",
                        )
                        if new_alias:
                            aliases.append(new_alias)
                    with col_b:
                        if st.button("✕", key=f"admin_alias_remove_{idx}"):
                            st.session_state.admin_aliases.pop(idx)
                            st.rerun()
                
                if st.button(f"+ {t('admin_button_add_alias')}", key="admin_alias_add"):
                    st.session_state.admin_aliases.append("")
                    st.rerun()
            
            # ------------------------------------------------------------------
            # AI Suggestion widget
            # ------------------------------------------------------------------
            _render_suggestion_ui(title=title, composer=composer)

            st.markdown("---")
            
            # YouTube IDs section
            st.markdown(f"**{t('admin_field_videos')}**")
            st.caption(t("admin_help_videos"))
            
            video_ids = []
            for idx, video_id in enumerate(st.session_state.admin_videos):
                col_v, col_btn = st.columns([8, 2])
                with col_v:
                    new_video = st.text_input(
                        f"YouTube ID {idx + 1}",
                        value=video_id,
                        key=f"admin_video_{idx}",
                        label_visibility="collapsed",
                        placeholder="e.g., dQw4w9WgXcQ",
                    )
                    if new_video:
                        video_ids.append(new_video)
                with col_btn:
                    if st.button("✕", key=f"admin_video_remove_{idx}"):
                        st.session_state.admin_videos.pop(idx)
                        st.rerun()
            
            if st.button(f"+ {t('admin_button_add_video')}", key="admin_video_add"):
                st.session_state.admin_videos.append("")
                st.rerun()
            
            # ------------------------------------------------------------------
            # Duplicate detection warning
            # ------------------------------------------------------------------
            if title.strip() or composer.strip():
                existing_works = load_catalog()
                similar = find_similar_works(title, composer, existing_works)
                if similar:
                    st.warning(t("admin_duplicate_warning"))
                    for w in similar[:3]:  # cap at 3 to avoid wall-of-text
                        st.markdown(
                            f"- **{w['title']}** — {w.get('composer', '?')} "
                            f"(`{w['id']}`)"
                        )

            st.markdown("---")
            
            # Preview section
            st.markdown(f"**{t('admin_section_preview')}**")
            
            if title and composer and work_id:
                preview = {
                    "id": work_id.strip(),
                    "title": title.strip(),
                    "composer": composer.strip(),
                    "aliases": [a.strip() for a in aliases if a.strip()],
                    "videos": [{"yt": v.strip()} for v in video_ids if v.strip()],
                }
                st.json(preview)
            else:
                st.info(t("admin_preview_incomplete"))
            
            st.markdown("---")
            
            # Save button
            if st.button(t("admin_button_save"), key="admin_save", type="primary"):
                success, message = add_work_to_catalog(
                    title=title,
                    composer=composer,
                    work_id=work_id,
                    aliases=aliases,
                    video_ids=video_ids,
                )
                
                if success:
                    st.success(message)
                    # Reset form by clearing session_state values
                    # (these were initialized at function top, so safe to clear here)
                    st.session_state.admin_title = ""
                    st.session_state.admin_composer = ""
                    st.session_state.admin_id = ""
                    st.session_state.admin_aliases = [""]
                    st.session_state.admin_videos = ["", "", "", "", ""]
                    st.session_state.admin_suggest_results = []
                    st.session_state.admin_suggest_selected = {}
                    st.rerun()
                else:
                    st.error(message)
    
    else:
        # =========================
        # NON-ADMIN INTERFACE
        # =========================
        with st.expander(t("admin_panel_title"), expanded=False):
            if not user_is_logged_in:
                st.info(t("admin_panel_login_required"))
                st.markdown("---")
                # Show login form specifically for admin contribution
                admin_login_block()
            else:
                st.warning(t("admin_panel_not_authorized"))
