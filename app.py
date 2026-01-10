import json
import random
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

# =========================
# Configuration
# =========================
DATA_PATH = Path(__file__).parent / "data" / "works.json"

st.set_page_config(
    page_title="Blind Aria Trainer",
    layout="centered"
)

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


def pick_versions(work, count: int):
    videos = work.get("videos", [])
    if len(videos) <= count:
        vids = videos[:]
        random.shuffle(vids)
        return vids
    return random.sample(videos, count)


# =========================
# App State
# =========================

if "current_work_id" not in st.session_state:
    st.session_state.current_work_id = None

if "now_playing" not in st.session_state:
    st.session_state.now_playing = None

if "shuffle_seed" not in st.session_state:
    st.session_state.shuffle_seed = 0

# =========================
# UI Header
# =========================

st.title("Blind Aria Trainer")
st.caption("Listen first. No faces. No names. Reveal only when ready.")

works = load_catalog()
if not works:
    st.error("No works found in data/works.json")
    st.stop()

# =========================
# Controls
# =========================

c1, c2 = st.columns([1, 1])

with c1:
    mode = st.radio(
        "Mode",
        ["Random aria", "Search"],
        horizontal=True
    )

with c2:
    versions_count = st.number_input(
        "Number of versions",
        min_value=2,
        max_value=10,
        value=5,
        step=1
    )

st.divider()

# =========================
# Mode Logic
# =========================

def set_random_work():
    work = random.choice(works)
    st.session_state.current_work_id = work["id"]
    st.session_state.shuffle_seed += 1
    st.session_state.now_playing = None


if mode == "Random aria":
    b1, b2 = st.columns([1, 1])
    with b1:
        if st.button("🎲 New random aria", use_container_width=True):
            set_random_work()
    with b2:
        if st.button("🔀 Reshuffle versions", use_container_width=True):
            st.session_state.shuffle_seed += 1
            st.session_state.now_playing = None

    if st.session_state.current_work_id is None:
        set_random_work()

else:
    query = st.text_input(
        "Search aria / opera / composer",
        placeholder="e.g. Sempre libera, Don Giovanni, Mozart"
    )

    matches = []
    if query.strip():
        q = query.lower().strip()
        matches = [w for w in works if q in w["_search"]]

    if query.strip() and not matches:
        st.info("No matches found.")

    if matches:
        labels = {
            f'{w["title"]} — {w.get("composer","")}': w["id"]
            for w in matches
        }
        selection = st.selectbox("Select work", list(labels.keys()))
        st.session_state.current_work_id = labels[selection]
        st.session_state.shuffle_seed += 1
        st.session_state.now_playing = None

# =========================
# Resolve Current Work
# =========================

current = next(
    (w for w in works if w["id"] == st.session_state.current_work_id),
    None
)

if not current:
    st.stop()

# =========================
# Version Selection
# =========================

random.seed(f"{current['id']}-{st.session_state.shuffle_seed}")
versions = pick_versions(current, int(versions_count))
random.shuffle(versions)

# =========================
# Playback Controls
# =========================

if st.button("⏹ Stop playback", use_container_width=True):
    st.session_state.now_playing = None

st.subheader("Blind set")
st.write("Listen without knowing who is singing. Reveal only after listening.")

# =========================
# Versions Loop
# =========================

for idx, v in enumerate(versions, start=1):
    vid = v["yt"]

    st.markdown(f"### Version {idx}")

    c1, c2 = st.columns([1, 1])

    with c1:
        if st.button("🎧 Listen", key=f"listen_{idx}", use_container_width=True):
            st.session_state.now_playing = vid

    with c2:
        if st.button("⏹ Stop", key=f"stop_{idx}", use_container_width=True):
            if st.session_state.now_playing == vid:
                st.session_state.now_playing = None

    if st.session_state.now_playing == vid:
        yt_audio_only(vid, autoplay=True)

    with st.expander("Reveal"):
        st.write("Work:", f'{current["title"]} — {current.get("composer","")}')
        st.write("YouTube:", yt_url(vid))

    st.divider()

# =========================
# Optional Work Info
# =========================

with st.expander("Show work information"):
    st.write("Title:", current["title"])
    st.write("Composer:", current.get("composer", ""))
    st.write("Aliases:", ", ".join(current.get("aliases", [])))
    st.write("Total versions in catalog:", len(current.get("videos", [])))
