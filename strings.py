"""
Centralized UI strings (i18n-style).

All user-facing text is defined here for easy maintenance and multi-language support.
"""

# =========================
# General
# =========================
STRINGS = {
    # Page config
    "page_title": "Blind Aria Trainer",
    
    # Header
    "title": "Blind Aria Trainer",
    "subtitle": "Solo: no login. Party: login + shareable session link.",
    
    # Mode selection
    "solo_button": "🎧 Solo (no login)",
    "party_button": "👥 Play with someone",
    "logout_button": "🚪 Log out",
    "use_solo_instead": "🎧 Use solo instead",
    "invite_link_notice": "Invite link detected: this URL points to a shared session.",
    
    # Solo mode
    "solo_mode_label": "Solo mode",
    "mode_selection": "Mode",
    "random_aria": "Random aria",
    "search": "Search",
    "search_placeholder": "e.g. Don Giovanni, Vissi d'arte, Mozart",
    
    # Party session creation
    "party_mode_label": "Party mode",
    "party_mode_description": "Create a shared listening session and send the link to a friend.",
    "session_title_label": "Session title",
    "session_title_default": "Blind listening session",
    "number_of_takes_label": "Number of takes",
    "choose_aria_label": "Choose aria",
    "random": "Random",
    "random_pick_prefix": "Random pick: ",
    "create_session_button": "Create session",
    "join_session_button": "Join session",
    
    # Player UI
    "player_label": "Player",
    "takes_label": "Takes: ",
    "stop_all_button": "⏹ Stop All Playback",
    "stop_button": "⏹ Stop",
    "play_button": "▶️ Play",
    "play_again_button": "▶️ Play Again",
    "resume_button": "▶️ Resume",
    "play_from_beginning_button": "🔄 Play from Beginning",
    "take_label": "Take ",
    "take_played_label": "Take {idx} ✓",
    
    # Video errors
    "video_broken_error": "❌ Take {idx}: Video link is broken or unavailable. Please try another take.",
    
    # Reveal section
    "reveal_label": "Reveal",
    "title_label": "Title: ",
    "channel_label": "Channel: ",
    "youtube_label": "YouTube: ",
    
    # Questionnaire
    "notepad_label": "Notepad (blind questionnaire)",
    "voice_production_label": "1) Voice production & timbre",
    "language_label": "2) Language & articulation",
    "style_label": "3) Style & aesthetic",
    "meaning_intent_label": "4A) Meaning, intent — intentional shaping",
    "sense_making_label": "4B) Meaning, intent — sense-making",
    "transmission_label": "4C) Transmission (choose one)",
    "anchor_label": "4D) Intentionality / empathy felt?",
    "impression_label": "5) Overall impression",
    "free_note_label": "Free note (optional)",
    "free_note_placeholder": "What caught your ear?",
    "save_notes_button": "💾 Save notes",
    "saved_success": "Saved.",
    "saved_locally_success": "Saved locally.",
    
    # Session controls
    "session_controls_label": "Session controls",
    "session_members_label": "Session Members",
    "refresh_button": "🔄 Refresh session",
    "reshuffle_button": "🔀 Reshuffle takes",
    "reshuffled_success": "Takes reshuffled.",
    "reshuffled_error": "Could not reshuffle takes: {error}",
    "owner_icon": "👑",
    "member_icon": "👤",
    
    # Admin panel
    "admin_panel_title": "📚 Catalogue Admin",
    "admin_panel_description": "Add a new aria to the catalogue. Fill in the metadata, provide at least 3 YouTube video IDs, and save.",
    "admin_panel_login_required": "👤 Log in to contribute to the catalogue. Contact an admin if you'd like to help expand the song collection.",
    "admin_panel_not_authorized": "🔒 Adding songs is admin-only. If you'd like to contribute, please contact the maintainers.",
    "admin_field_title": "Title",
    "admin_field_composer": "Composer",
    "admin_field_id": "ID (unique identifier)",
    "admin_field_aliases": "Aliases (alternative names)",
    "admin_field_alias": "Alias",
    "admin_field_videos": "YouTube Video IDs",
    "admin_help_title": "e.g., 'Fin ch'han dal vino'",
    "admin_help_composer": "e.g., 'Mozart'",
    "admin_help_id": "Unique identifier in lowercase with underscores. e.g., mozart_don_giovanni_champagne",
    "admin_help_aliases": "Alternative names for searching (e.g., 'Don Giovanni Champagne Aria', 'Champagne Aria')",
    "admin_help_videos": "YouTube video IDs. Need at least 3. Blank entries are ignored.",
    "admin_button_add_alias": "Add alias",
    "admin_button_add_video": "Add YouTube ID",
    "admin_section_preview": "Preview",
    "admin_preview_incomplete": "Fill in title, composer, and ID to see a preview.",
    "admin_button_save": "💾 Save to Catalogue",
    
    # Errors & Info
    "no_works_error": "No works have at least {min_versions} versions.",
    "fewer_takes_error": "This selection has fewer than {min_versions} takes.",
    "join_session_error": "Could not join/load session: {error}",
    "work_not_found_error": "Session work_id not found in local works.json.",
}


def t(key: str, **kwargs) -> str:
    """
    Get a translated string.
    
    Args:
        key: The string key to retrieve
        **kwargs: Format parameters (e.g., t("join_session_error", error="..."))
    
    Returns:
        The translated string, formatted with any kwargs
    """
    text = STRINGS.get(key, f"[MISSING: {key}]")
    if kwargs:
        try:
            return text.format(**kwargs)
        except KeyError as e:
            return f"[FORMAT ERROR: {key} - missing param {e}]"
    return text
