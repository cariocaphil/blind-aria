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
)


def show_admin_panel():
    """
    Render the admin panel for adding songs to the catalogue.
    
    Always shown to indicate the feature exists.
    - If not logged in: shows login prompt
    - If logged in but not admin: shows "admin only" message
    - If logged in and admin: shows full form
    
    UI flow:
    - Title and description
    - Form fields: title, composer, id, aliases, YouTube IDs
    - Preview of resulting JSON entry
    - Save button with validation
    """
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
                
                # Dynamic aliases input
                if "admin_aliases" not in st.session_state:
                    st.session_state.admin_aliases = [""]
                
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
            
            st.markdown("---")
            
            # YouTube IDs section
            st.markdown(f"**{t('admin_field_videos')}**")
            st.caption(t("admin_help_videos"))
            
            if "admin_videos" not in st.session_state:
                st.session_state.admin_videos = ["", "", "", "", ""]
            
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
                    # Reset form
                    st.session_state.admin_title = ""
                    st.session_state.admin_composer = ""
                    st.session_state.admin_id = ""
                    st.session_state.admin_aliases = [""]
                    st.session_state.admin_videos = ["", "", "", "", ""]
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
