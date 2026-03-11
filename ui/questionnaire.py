"""
Questionnaire (notepad) and note-saving UI.
"""

import streamlit as st

from config import (
    ANCHOR_OPTIONS,
    IMPRESSION_OPTIONS,
    LANGUAGE_OPTIONS,
    MEANING_INTENT_OPTIONS,
    SENSE_MAKING_OPTIONS,
    STYLE_OPTIONS,
    TRANSMISSION_OPTIONS,
    VOICE_PRODUCTION_OPTIONS,
)
from strings import t
from utils import checkbox_group


def show_questionnaire_ui(nk: str, saved: dict, party_mode: bool = False, sb=None, party_session_id: str = None, party_user_id: str = None, work_id: str = None, vid: str = None):
    """
    Display the blind questionnaire expander and save notes.
    """
    with st.expander(t("notepad_label"), expanded=False):
        voice_prod = checkbox_group(t("voice_production_label"), VOICE_PRODUCTION_OPTIONS, saved.get("voice_production", []), key_prefix=f"vp_{nk}")
        language = checkbox_group(t("language_label"), LANGUAGE_OPTIONS, saved.get("language", []), key_prefix=f"lang_{nk}")
        style = checkbox_group(t("style_label"), STYLE_OPTIONS, saved.get("style", []), key_prefix=f"style_{nk}")
        meaning_intent = checkbox_group(t("meaning_intent_label"), MEANING_INTENT_OPTIONS, saved.get("meaning_intent", []), key_prefix=f"mi_{nk}")
        sense_making = checkbox_group(t("sense_making_label"), SENSE_MAKING_OPTIONS, saved.get("sense_making", []), key_prefix=f"sm_{nk}")

        transmission_default = saved.get("transmission", "Neutral")
        transmission_idx = TRANSMISSION_OPTIONS.index(transmission_default) if transmission_default in TRANSMISSION_OPTIONS else 2
        transmission = st.radio(t("transmission_label"), TRANSMISSION_OPTIONS, index=transmission_idx, key=f"trans_{nk}")

        anchor_default = saved.get("anchor", "Unsure")
        anchor_idx = ANCHOR_OPTIONS.index(anchor_default) if anchor_default in ANCHOR_OPTIONS else 1
        anchor = st.radio(t("anchor_label"), ANCHOR_OPTIONS, index=anchor_idx, horizontal=True, key=f"anchor_{nk}")

        impr_default = saved.get("impression", "Neutral")
        impr_idx = IMPRESSION_OPTIONS.index(impr_default) if impr_default in IMPRESSION_OPTIONS else 2
        impression = st.radio(t("impression_label"), IMPRESSION_OPTIONS, index=impr_idx, horizontal=True, key=f"impr_{nk}")

        st.markdown(f"**{t('free_note_label')}**")
        comment = st.text_area(t("free_note_placeholder"), value=saved.get("comment", ""), key=f"comment_{nk}")

        if st.button(t("save_notes_button"), key=f"save_{nk}", width="stretch"):
            payload = {
                "voice_production": voice_prod,
                "language": language,
                "style": style,
                "meaning_intent": meaning_intent,
                "sense_making": sense_making,
                "transmission": transmission,
                "anchor": anchor,
                "impression": impression,
                "comment": comment.strip(),
            }
            if party_mode:
                from db import upsert_note
                upsert_note(sb, party_session_id, party_user_id, work_id, vid, payload)
                st.success(t("saved_success"))
            else:
                st.session_state.notes[nk] = payload
                st.success(t("saved_locally_success"))
