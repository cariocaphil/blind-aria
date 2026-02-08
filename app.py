import json
import random
from pathlib import Path

import requests
import streamlit as st
import streamlit.components.v1 as components

# =========================
# Configuration
# =========================
DATA_PATH = Path(__file__).parent / "data" / "works.json"
MIN_VERSIONS_REQUIRED = 3  # <-- enforce at least 3 versions

st.set_page_config(
    page_title="Blind Aria Trainer",
    layout="centered",
)

# =========================
# Questionnaire Options
# =========================
VOICE_PRODUCTION_OPTIONS = [
    "Clear diction",
    "Legato line",
    "Even vibrato",
    "Breath-driven phrasing",
    "Secure upper register",
    "Warm timbre",
    "Bright / metallic timbre",
    "Dark / covered timbre",
    "Heavy production",
    "Flexible / agile",
    "Nasal resonance audible",
    "Croaky / “froggish” quality",
]

LANGUAGE_OPTIONS = [
    "Text clearly understandable",
    "Consonants very present",
    "Vowels well shaped",
    "Non-native accent perceptible",
]

STYLE_OPTIONS = [
    "Bel canto oriented",
    "Verismo oriented",
    "Historically older style",
    "Modern / international style",
    "Dramatic / theatrical",
    "Intimate / inward",
]

MEANING_INTENT_OPTIONS = [
    "Musical intention feels clear",
    "Phrasing feels purposeful",
    "Dynamic shaping feels deliberate",
    "Rubato feels meaningful",
    "Text delivery feels intentional",
    "I sense a clear point of view",
]

SENSE_MAKING_OPTIONS = [
    "Dramatic situation feels clear",
    "Emotional arc is understandable",
    "The aria feels embedded in a story",
    "I understand why this aria exists",
]

TRANSMISSION_OPTIONS = [
    "Strongly reaches me",
    "Reaches me at moments",
    "Neutral",
    "Emotionally distant",
    "Feels mannered / performative",
]

ANCHOR_OPTIONS = ["Yes", "Unsure", "No"]

IMPRESSION_OPTIONS = ["Loved it", "Convincing", "Neutral", "Distracting", "Not for me"]


# =========================
# Helpers
# =========================
@st.cache_data
def load_catalog():
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    works = data.get("works", [])
    for w in works:
        w["_search"] = " ".join(
            [w.get("title", ""), w.get("composer", ""), *w.get("aliases", [])]
        ).lower()
    return works


def yt_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def yt_audio_only(video_id: str, autoplay: bool = True):
    """
    Invisible YouTube iframe: audio only.
    Autoplay generally works after a user interaction (button click).
    """
    auto = "1" if autoplay else "0"
    html = f"""
    <div style="height:0; overflow:hidden;">
      <iframe
        src="https://www.youtube.com/embed/{video_id}?autoplay={auto}&controls=0&rel=0&modestbranding=1"
        width="1"
        height="1"
        frameborder="0"
        allow="autoplay"
        style="opacity:0; pointer-events:none;"
      ></iframe>
    </div>
    """
    components.html(html, height=0)


@st.cache_data(ttl=24 * 3600)
def yt_oembed(video_id: str):
    """
    Fetch minimal metadata without API key (title + channel).
    Uses YouTube's oEmbed endpoint.
    """
    try:
        r = requests.get(
            "https://www.youtube.com/oembed",
            params={"url": yt_url(video_id), "format": "json"},
            timeout=10,
        )
        if r.status_code != 200:
            return None
        return r.json()
    except requests.RequestException:
        return None


def valid_video_ids(work: dict) -> list[str]:
    """Return non-empty yt IDs."""
    return [v.get("yt") for v in work.get("videos", []) if v.get("yt")]


def has_min_versions(work: dict, n: int = MIN_VERSIONS_REQUIRED) -> bool:
    return len(valid_video_ids(work)) >= n


def pick_versions(work: dict, count: int):
    videos = [v for v in work.get("videos", []) if v.get("yt")]
    if not videos:
        return []
    if len(videos) <= count:
        random.shuffle(videos)
        return videos
    return random.sample(videos, count)


def note_key_for(work_id: str, video_id: str) -> str:
    return f"{work_id}::{video_id}"


def checkbox_group(title: str, options: list[str], selected: list[str], key_prefix: str):
    """
    Renders a set of checkboxes (multi-answer multiple choice) and returns the selected options.
    """
    st.markdown(f"**{title}**")
    out = []
    for opt in options:
        k = f"{key_prefix}::{opt}"
        default = opt in selected
        if st.checkbox(opt, value=default, key=k):
            out.append(opt)
    return out


# =========================
# App State
# =========================
if "current_work_id" not in st.session_state:
    st.session_state.current_work_id = None

if "now_playing" not in st.session_state:
    st.session_state.now_playing = None

if "shuffle_seed" not in st.session_state:
    st.session_state.shuffle_seed = 0

if "played_by_work" not in st.session_state:
    # work_id -> set(video_id)
    st.session_state.played_by_work = {}

if "notes" not in st.session_state:
    # key: "work_id::video_id" -> questionnaire dict
    st.session_state.notes = {}

# =========================
# UI Header
# =========================
st.title("Blind Aria Trainer")
st.caption("Listen first. Reveal later. (Audio-only playback)")

works = load_catalog()
if not works:
    st.error("No works found in data/works.json")
    st.stop()

# Only allow works with at least MIN_VERSIONS_REQUIRED
eligible_works = [w for w in works if has_min_versions(w, MIN_VERSIONS_REQUIRED)]

if not eligible_works:
    st.error(
        f"No works have at least {MIN_VERSIONS_REQUIRED} versions. "
        "Add more YouTube IDs to your catalog."
    )
    st.stop()

# =========================
# Controls
# =========================
c1, c2 = st.columns([1, 1])

with c1:
    mode = st.radio("Mode", ["Random aria", "Search"], horizontal=True)

with c2:
    versions_count = st.number_input(
        "Number of versions (max)",
        min_value=2,
        max_value=10,
        value=5,
        step=1,
    )

st.divider()

# =========================
# Mode Logic
# =========================
def set_random_work():
    work = random.choice(eligible_works)
    st.session_state.current_work_id = work["id"]
    st.session_state.shuffle_seed += 1
    st.session_state.now_playing = None
    # reset played markers for new work
    st.session_state.played_by_work[work["id"]] = set()


if mode == "Random aria":
    b1, b2 = st.columns([1, 1])
    with b1:
        if st.button("🎲 New random aria", width="stretch"):
            set_random_work()
    with b2:
        if st.button("🔀 Reshuffle versions", width="stretch"):
            st.session_state.shuffle_seed += 1
            st.session_state.now_playing = None

    if st.session_state.current_work_id is None:
        set_random_work()

else:
    query = st.text_input(
        "Search aria / opera / composer",
        placeholder="e.g. Sempre libera, Don Giovanni, Mozart",
    )

    matches = []
    if query.strip():
        q = query.lower().strip()
        # Only show eligible works in search results
        matches = [w for w in eligible_works if q in w["_search"]]

    if query.strip() and not matches:
        st.info(f"No matches found with ≥ {MIN_VERSIONS_REQUIRED} versions.")

    if matches:
        labels = {f'{w["title"]} — {w.get("composer","")}': w["id"] for w in matches}
        selection = st.selectbox("Select work", list(labels.keys()))
        st.session_state.current_work_id = labels[selection]
        st.session_state.shuffle_seed += 1
        st.session_state.now_playing = None

        # reset played markers for newly selected work
        wid = st.session_state.current_work_id
        st.session_state.played_by_work[wid] = set()

# =========================
# Resolve Current Work
# =========================
current = next((w for w in eligible_works if w["id"] == st.session_state.current_work_id), None)
if not current:
    st.stop()

# =========================
# Build Blind Set
# =========================
random.seed(f"{current['id']}-{st.session_state.shuffle_seed}")
versions = pick_versions(current, int(versions_count))
random.shuffle(versions)

st.subheader("Blind set")
st.write("Listen without knowing who is singing. Tick boxes while staying blind.")
st.caption(
    f"{len(versions)} version(s) available for this aria in your catalog "
    f"(eligible: ≥ {MIN_VERSIONS_REQUIRED})."
)

# Playback stop
if st.button("⏹ Stop playback", width="stretch"):
    st.session_state.now_playing = None

st.divider()

# Played set for current work
played_set = st.session_state.played_by_work.setdefault(current["id"], set())

# =========================
# Versions Loop
# =========================
for idx, v in enumerate(versions, start=1):
    vid = v["yt"]
    is_played = vid in played_set
    nk = note_key_for(current["id"], vid)
    saved = st.session_state.notes.get(nk, {})

    st.markdown(f"### Take {idx}")

    c1, c2 = st.columns([1, 1])
    with c1:
        listen_label = "✅ Played" if is_played else "🎧 Listen"
        listen_type = "secondary" if is_played else "primary"

        if st.button(
            listen_label,
            key=f"listen_{current['id']}_{idx}",
            width="stretch",
            type=listen_type,
        ):
            st.session_state.now_playing = vid
            played_set.add(vid)

    with c2:
        if st.button(
            "⏹ Stop",
            key=f"stop_{current['id']}_{idx}",
            width="stretch",
        ):
            if st.session_state.now_playing == vid:
                st.session_state.now_playing = None

    if st.session_state.now_playing == vid:
        yt_audio_only(vid, autoplay=True)

    # -------------------------
    # Questionnaire Notepad (multi-answer)
    # -------------------------
    with st.expander("Notepad (blind questionnaire)", expanded=False):
        voice_prod = checkbox_group(
            "1) Voice production & timbre",
            VOICE_PRODUCTION_OPTIONS,
            saved.get("voice_production", []),
            key_prefix=f"vp_{nk}",
        )

        language = checkbox_group(
            "2) Language & articulation",
            LANGUAGE_OPTIONS,
            saved.get("language", []),
            key_prefix=f"lang_{nk}",
        )

        style = checkbox_group(
            "3) Style & aesthetic",
            STYLE_OPTIONS,
            saved.get("style", []),
            key_prefix=f"style_{nk}",
        )

        meaning_intent = checkbox_group(
            "4A) Meaning, intent & connection — intentional shaping",
            MEANING_INTENT_OPTIONS,
            saved.get("meaning_intent", []),
            key_prefix=f"mi_{nk}",
        )

        sense_making = checkbox_group(
            "4B) Meaning, intent & connection — sense-making",
            SENSE_MAKING_OPTIONS,
            saved.get("sense_making", []),
            key_prefix=f"sm_{nk}",
        )

        st.markdown("**4C) Transmission & connection (choose one)**")
        transmission_default = saved.get("transmission", "Neutral")
        transmission_idx = (
            TRANSMISSION_OPTIONS.index(transmission_default)
            if transmission_default in TRANSMISSION_OPTIONS
            else 2
        )
        transmission = st.radio(
            "How does it reach you?",
            TRANSMISSION_OPTIONS,
            index=transmission_idx,
            key=f"trans_{nk}",
        )

        st.markdown("**4D) Anchor reflection (choose one)**")
        anchor_default = saved.get("anchor", "Unsure")
        anchor_idx = (
            ANCHOR_OPTIONS.index(anchor_default) if anchor_default in ANCHOR_OPTIONS else 1
        )
        anchor = st.radio(
            "I feel the singer believes what they are singing.",
            ANCHOR_OPTIONS,
            index=anchor_idx,
            horizontal=True,
            key=f"anchor_{nk}",
        )

        st.markdown("**5) Overall impression (choose one)**")
        impr_default = saved.get("impression", "Neutral")
        impr_idx = (
            IMPRESSION_OPTIONS.index(impr_default)
            if impr_default in IMPRESSION_OPTIONS
            else 2
        )
        impression = st.radio(
            "Gut reaction",
            IMPRESSION_OPTIONS,
            index=impr_idx,
            horizontal=True,
            key=f"impr_{nk}",
        )

        st.markdown("**6) Free note (optional)**")
        comment = st.text_area(
            "What caught your ear?",
            value=saved.get("comment", ""),
            placeholder="e.g. 'Purposeful phrasing, but emotionally distant…'",
            key=f"comment_{nk}",
        )

        csave1, csave2 = st.columns([1, 1])
        with csave1:
            if st.button("💾 Save", key=f"save_{nk}", width="stretch"):
                st.session_state.notes[nk] = {
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
                st.success("Saved.")

        with csave2:
            if st.button("🧹 Clear", key=f"clear_{nk}", width="stretch"):
                st.session_state.notes.pop(nk, None)
                st.session_state.now_playing = None
                st.success("Cleared. (Re-open to see defaults reset.)")

    # -------------------------
    # Reveal
    # -------------------------
    with st.expander("Reveal"):
        st.write("Work:", f'{current["title"]} — {current.get("composer","")}')
        meta = yt_oembed(vid)
        if meta:
            st.markdown(f"**Title:** {meta.get('title', '—')}")
            st.markdown(f"**Channel:** {meta.get('author_name', '—')}")
        else:
            st.info("Could not fetch YouTube metadata (network/rate limit/removed video).")

        st.write("YouTube:", yt_url(vid))

        note = st.session_state.notes.get(nk)
        if note:
            st.markdown("---")
            st.markdown("#### Your blind notes (summary)")
            st.write("Voice production:", ", ".join(note.get("voice_production", [])) or "—")
            st.write("Language:", ", ".join(note.get("language", [])) or "—")
            st.write("Style:", ", ".join(note.get("style", [])) or "—")
            st.write("Intent:", ", ".join(note.get("meaning_intent", [])) or "—")
            st.write("Sense-making:", ", ".join(note.get("sense_making", [])) or "—")
            st.write("Transmission:", note.get("transmission", "—"))
            st.write("Anchor:", note.get("anchor", "—"))
            st.write("Impression:", note.get("impression", "—"))
            if note.get("comment"):
                st.write("Free note:", note["comment"])

    st.divider()

# =========================
# Optional Work Info
# =========================
with st.expander("Show work information"):
    st.write("Title:", current.get("title", ""))
    st.write("Composer:", current.get("composer", ""))
    st.write("Aliases:", ", ".join(current.get("aliases", [])))
    st.write(
        "Total versions in catalog:",
        len([v for v in current.get("videos", []) if v.get("yt")]),
    )
    st.write(f"Eligibility rule: ≥ {MIN_VERSIONS_REQUIRED} versions")

# =========================
# Optional Session Summary
# =========================
with st.expander("Session summary (this aria)", expanded=False):
    rows = []
    for idx, v in enumerate(versions, start=1):
        vid = v["yt"]
        nk = note_key_for(current["id"], vid)
        note = st.session_state.notes.get(nk)
        rows.append(
            {
                "Take": idx,
                "Played": "Yes" if vid in played_set else "No",
                "Impression": (note or {}).get("impression", ""),
                "Transmission": (note or {}).get("transmission", ""),
                "Anchor": (note or {}).get("anchor", ""),
                "Notes saved": "Yes" if note else "No",
            }
        )
    st.dataframe(rows, width="stretch")
