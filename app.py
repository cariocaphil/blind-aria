import json
import random
from pathlib import Path
from typing import Optional, List

import requests
import streamlit as st
import streamlit.components.v1 as components

# =========================
# Configuration
# =========================
DATA_PATH = Path(__file__).parent / "data" / "works.json"
MIN_VERSIONS_REQUIRED = 3

st.set_page_config(page_title="Blind Aria Trainer", layout="centered")


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
# Helpers (catalog + YouTube)
# =========================
@st.cache_data
def load_catalog() -> List[dict]:
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
    auto = "1" if autoplay else "0"
    html = f"""
    <div style="height:0; overflow:hidden;">
      <iframe
        src="https://www.youtube.com/embed/{video_id}?autoplay={auto}&controls=0&rel=0&modestbranding=1"
        width="1" height="1"
        frameborder="0"
        allow="autoplay"
        style="opacity:0; pointer-events:none;"
      ></iframe>
    </div>
    """
    components.html(html, height=0)


@st.cache_data(ttl=24 * 3600)
def yt_oembed(video_id: str):
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
    return [v.get("yt") for v in work.get("videos", []) if v.get("yt")]


def has_min_versions(work: dict, n: int = MIN_VERSIONS_REQUIRED) -> bool:
    return len(valid_video_ids(work)) >= n


def pick_versions_from_ids(video_ids: list[str], count: int) -> list[str]:
    ids = [x for x in video_ids if x]
    if len(ids) <= count:
        random.shuffle(ids)
        return ids
    return random.sample(ids, count)


def pick_versions(work: dict, count: int) -> list[str]:
    return pick_versions_from_ids(valid_video_ids(work), count)


def note_key_for(work_id: str, video_id: str) -> str:
    return f"{work_id}::{video_id}"


def checkbox_group(title: str, options: list[str], selected: list[str], key_prefix: str):
    st.markdown(f"**{title}**")
    out = []
    for opt in options:
        k = f"{key_prefix}::{opt}"
        default = opt in selected
        if st.checkbox(opt, value=default, key=k):
            out.append(opt)
    return out


# =========================
# Supabase (robust auth header client)
# =========================
def supabase_available() -> bool:
    try:
        import supabase  # noqa: F401
        return True
    except Exception:
        return False


def get_supabase_url_key():
    url = st.secrets.get("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_ANON_KEY")
    if not url or not key:
        st.error("Missing SUPABASE_URL / SUPABASE_ANON_KEY in Streamlit secrets.")
        st.stop()
    return url, key


def create_sb_client(access_token: Optional[str] = None):
    """
    Creates a Supabase client.
    If access_token is provided, it FORCE-sets Authorization header for PostgREST calls.
    """
    try:
        from supabase import create_client  # type: ignore
        from supabase.lib.client_options import ClientOptions  # type: ignore
    except Exception:
        st.error("Supabase package not installed. Add `supabase>=2.0.0` to requirements.txt.")
        st.stop()

    url, anon_key = get_supabase_url_key()

    if access_token:
        opts = ClientOptions(headers={"Authorization": f"Bearer {access_token}"})
        return create_client(url, anon_key, options=opts)

    return create_client(url, anon_key)


def is_logged_in() -> bool:
    return bool(st.session_state.get("sb_auth"))


def sb_user_id() -> Optional[str]:
    auth = st.session_state.get("sb_auth") or {}
    return auth.get("user_id")


def sb_authed_client():
    auth = st.session_state.get("sb_auth") or {}
    access_token = auth.get("access_token")
    if not access_token:
        return create_sb_client(None)
    return create_sb_client(access_token)


def require_login_block() -> None:
    st.subheader("Sign in to play with someone")
    st.caption("Solo mode needs no login. Party mode requires login (email code).")

    if not supabase_available():
        st.error("Missing dependency: add `supabase>=2.0.0` to requirements.txt and redeploy.")
        st.stop()

    sb = create_sb_client(None)

    email = st.text_input("Email", key="otp_email", placeholder="you@example.com")
    c1, c2 = st.columns([1, 1])

    with c1:
        if st.button("Send code", width="stretch"):
            if not email.strip():
                st.error("Enter an email.")
            else:
                try:
                    sb.auth.sign_in_with_otp({"email": email.strip()})
                    st.session_state["otp_email_sent"] = email.strip()
                    st.success("Email sent. Copy the code from the email and paste it below.")
                except Exception as e:
                    st.error(f"Could not send OTP: {e}")

    with c2:
        if st.button("Use solo mode instead", width="stretch"):
            st.session_state["wants_party_mode"] = False
            if "session" in st.query_params:
                st.query_params.pop("session")
            st.rerun()

    sent_email = st.session_state.get("otp_email_sent")
    if sent_email:
        code = st.text_input("Code", key="otp_code", placeholder="123456")
        if st.button("Verify code", width="stretch"):
            if not code.strip():
                st.error("Enter the code.")
            else:
                try:
                    resp = sb.auth.verify_otp(
                        {"email": sent_email, "token": code.strip(), "type": "email"}
                    )

                    session = getattr(resp, "session", None) or (resp.get("session") if isinstance(resp, dict) else None)
                    user = getattr(resp, "user", None) or (resp.get("user") if isinstance(resp, dict) else None)

                    access_token = None
                    refresh_token = None
                    user_id = None

                    if session is not None:
                        access_token = getattr(session, "access_token", None)
                        refresh_token = getattr(session, "refresh_token", None)
                        if isinstance(session, dict):
                            access_token = access_token or session.get("access_token")
                            refresh_token = refresh_token or session.get("refresh_token")

                    if user is not None:
                        user_id = getattr(user, "id", None)
                        if isinstance(user, dict):
                            user_id = user_id or user.get("id")

                    if not access_token or not user_id:
                        st.error("Login succeeded but access token/user_id missing. Check Supabase response.")
                        st.stop()

                    st.session_state["sb_auth"] = {
                        "user_id": user_id,
                        "email": sent_email,
                        "access_token": access_token,
                        "refresh_token": refresh_token,
                    }
                    st.success("Logged in.")
                    st.rerun()

                except Exception as e:
                    st.error(f"Verification failed: {e}")


# =========================
# Supabase DB operations
# =========================
def create_party_session(sb, owner_id: str, title: str, work_id: str, video_ids: list[str]) -> str:
    # IMPORTANT: insert MUST run with Authorization header set (sb_authed_client does this)
    res = sb.table("game_sessions").insert(
        {"owner_id": owner_id, "title": title, "work_id": work_id, "video_ids": video_ids}
    ).execute()
    session_id = res.data[0]["id"]

    sb.table("session_members").insert(
        {"session_id": session_id, "user_id": owner_id, "role": "owner"}
    ).execute()

    return session_id


def ensure_member(sb, session_id: str, user_id: str):
    mem = (
        sb.table("session_members")
        .select("*")
        .eq("session_id", session_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not mem.data:
        sb.table("session_members").insert(
            {"session_id": session_id, "user_id": user_id, "role": "member"}
        ).execute()


def load_party_session(sb, session_id: str) -> dict:
    res = sb.table("game_sessions").select("*").eq("id", session_id).single().execute()
    return res.data


def upsert_note(sb, session_id: str, user_id: str, work_id: str, video_id: str, payload: dict):
    sb.table("session_notes").upsert(
        {
            "session_id": session_id,
            "user_id": user_id,
            "work_id": work_id,
            "video_id": video_id,
            "payload": payload,
        },
        on_conflict="session_id,user_id,work_id,video_id",
    ).execute()


def load_note(sb, session_id: str, user_id: str, work_id: str, video_id: str) -> Optional[dict]:
    res = (
        sb.table("session_notes")
        .select("payload")
        .eq("session_id", session_id)
        .eq("user_id", user_id)
        .eq("work_id", work_id)
        .eq("video_id", video_id)
        .execute()
    )
    if res.data:
        return res.data[0]["payload"]
    return None


# =========================
# Streamlit State
# =========================
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


# =========================
# UI Header
# =========================
st.title("Blind Aria Trainer")
st.caption("Solo: no login. Party: login + shareable session link.")

works = load_catalog()
eligible_works = [w for w in works if has_min_versions(w, MIN_VERSIONS_REQUIRED)]
if not eligible_works:
    st.error(f"No works have at least {MIN_VERSIONS_REQUIRED} versions.")
    st.stop()

session_param = st.query_params.get("session")
party_mode = bool(session_param) or bool(st.session_state.wants_party_mode)

b1, b2, b3 = st.columns([1, 1, 1])
with b1:
    if st.button("🎧 Solo (no login)", width="stretch"):
        st.session_state.wants_party_mode = False
        if "session" in st.query_params:
            st.query_params.pop("session")
        st.rerun()
with b2:
    if st.button("👥 Play with someone", width="stretch"):
        st.session_state.wants_party_mode = True
        st.rerun()
with b3:
    if party_mode and is_logged_in():
        if st.button("🚪 Log out", width="stretch"):
            st.session_state.pop("sb_auth", None)
            st.session_state.pop("otp_email_sent", None)
            st.rerun()

st.divider()

if party_mode and not is_logged_in():
    require_login_block()
    st.stop()

# =========================
# Party session handling
# =========================
party_session = None
party_session_id = None
party_user_id = None
sb = None

if party_mode:
    sb = sb_authed_client()  # <- AUTH HEADER CLIENT
    party_user_id = sb_user_id()
    if not party_user_id:
        st.error("Logged in but user id missing.")
        st.stop()

    if session_param:
        party_session_id = session_param
        try:
            ensure_member(sb, party_session_id, party_user_id)
            party_session = load_party_session(sb, party_session_id)
        except Exception as e:
            st.error(f"Could not join/load session: {e}")
            st.stop()

    if not party_session:
        st.subheader("Party mode")
        st.write("Create a shared listening session and send the link to a friend.")
        title = st.text_input("Session title", value="Blind listening session")
        versions_count = st.number_input("Number of takes", min_value=3, max_value=10, value=5, step=1)

        choice_mode = st.radio("Choose aria", ["Random", "Search"], horizontal=True)
        chosen_work = None

        if choice_mode == "Random":
            chosen_work = random.choice(eligible_works)
            st.info(f"Random pick: **{chosen_work['title']} — {chosen_work.get('composer','')}**")
        else:
            q = st.text_input("Search", placeholder="e.g. Don Giovanni, Vissi d’arte, Mozart")
            matches = []
            if q.strip():
                qq = q.lower().strip()
                matches = [w for w in eligible_works if qq in w["_search"]]
            if matches:
                labels = {f'{w["title"]} — {w.get("composer","")}': w for w in matches}
                sel = st.selectbox("Select", list(labels.keys()))
                chosen_work = labels[sel]
            elif q.strip():
                st.warning(f"No eligible matches (need ≥ {MIN_VERSIONS_REQUIRED} versions).")

        if chosen_work and st.button("Create shared session", width="stretch"):
            vids = pick_versions(chosen_work, int(versions_count))
            if len(vids) < MIN_VERSIONS_REQUIRED:
                st.error("Not enough versions in this work.")
                st.stop()
            try:
                new_id = create_party_session(
                    sb=sb,
                    owner_id=party_user_id,
                    title=title.strip() or "Blind listening session",
                    work_id=chosen_work["id"],
                    video_ids=vids,
                )
                st.query_params["session"] = new_id
                st.success("Session created. Share the URL in your browser (it includes ?session=...).")
                st.rerun()
            except Exception as e:
                st.error(f"Could not create session: {e}")

        st.stop()

# =========================
# Determine work + takes list
# =========================
if party_mode:
    work_id = party_session["work_id"]
    shared_video_ids = party_session.get("video_ids") or []
    current_work = next((w for w in works if w["id"] == work_id), None)
    if not current_work:
        st.error("Session references a work_id not found in your local works.json.")
        st.stop()
    versions = [vid for vid in shared_video_ids if vid]
    mode_label = f"Party: {party_session.get('title', 'Blind session')}"
else:
    st.subheader("Solo mode")
    c1, c2 = st.columns([1, 1])
    with c1:
        solo_mode = st.radio("Mode", ["Random aria", "Search"], horizontal=True)
    with c2:
        versions_count = st.number_input("Number of takes (max)", min_value=3, max_value=10, value=5, step=1)

    def set_random_work_id():
        w = random.choice(eligible_works)
        st.session_state["solo_work_id"] = w["id"]
        st.session_state.shuffle_seed += 1
        st.session_state.now_playing = None
        st.session_state.played_by_work[w["id"]] = set()

    if "solo_work_id" not in st.session_state:
        set_random_work_id()

    if solo_mode == "Random aria":
        x1, x2 = st.columns([1, 1])
        with x1:
            if st.button("🎲 New random aria", width="stretch"):
                set_random_work_id()
        with x2:
            if st.button("🔀 Reshuffle takes", width="stretch"):
                st.session_state.shuffle_seed += 1
                st.session_state.now_playing = None
    else:
        q = st.text_input("Search aria / opera / composer", placeholder="e.g. Sempre libera, Don Giovanni, Mozart")
        matches = []
        if q.strip():
            qq = q.lower().strip()
            matches = [w for w in eligible_works if qq in w["_search"]]
        if matches:
            labels = {f'{w["title"]} — {w.get("composer","")}': w["id"] for w in matches}
            sel = st.selectbox("Select work", list(labels.keys()))
            st.session_state["solo_work_id"] = labels[sel]
            st.session_state.shuffle_seed += 1
            st.session_state.now_playing = None
            st.session_state.played_by_work[labels[sel]] = set()
        elif q.strip():
            st.info(f"No matches with ≥ {MIN_VERSIONS_REQUIRED} versions.")

    current_work = next((w for w in works if w["id"] == st.session_state["solo_work_id"]), None)
    if not current_work:
        st.stop()

    random.seed(f"{current_work['id']}-{st.session_state.shuffle_seed}")
    versions = pick_versions(current_work, int(versions_count))
    random.shuffle(versions)
    mode_label = "Solo"

if len(versions) < MIN_VERSIONS_REQUIRED:
    st.error("This selection has fewer than 3 takes. Add more video IDs in works.json.")
    st.stop()

# =========================
# Main UI
# =========================
st.subheader(mode_label)
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
        saved = load_note(sb, party_session_id, party_user_id, current_work["id"], vid) or {}
    else:
        saved = st.session_state.notes.get(nk, {})

    st.markdown(f"### Take {idx}")

    c1, c2 = st.columns([1, 1])
    with c1:
        listen_label = "✅ Played" if is_played else "🎧 Listen"
        listen_type = "secondary" if is_played else "primary"
        if st.button(listen_label, key=f"listen_{nk}", width="stretch", type=listen_type):
            st.session_state.now_playing = vid
            played_set.add(vid)

    with c2:
        if st.button("⏹ Stop", key=f"stop_{nk}", width="stretch"):
            if st.session_state.now_playing == vid:
                st.session_state.now_playing = None

    if st.session_state.now_playing == vid:
        yt_audio_only(vid, autoplay=True)

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

        transmission_default = saved.get("transmission", "Neutral")
        transmission_idx = TRANSMISSION_OPTIONS.index(transmission_default) if transmission_default in TRANSMISSION_OPTIONS else 2
        transmission = st.radio(
            "4C) Transmission & connection (choose one)",
            TRANSMISSION_OPTIONS,
            index=transmission_idx,
            key=f"trans_{nk}",
        )

        anchor_default = saved.get("anchor", "Unsure")
        anchor_idx = ANCHOR_OPTIONS.index(anchor_default) if anchor_default in ANCHOR_OPTIONS else 1
        anchor = st.radio(
            "4D) Anchor reflection",
            ANCHOR_OPTIONS,
            index=anchor_idx,
            horizontal=True,
            key=f"anchor_{nk}",
        )

        impr_default = saved.get("impression", "Neutral")
        impr_idx = IMPRESSION_OPTIONS.index(impr_default) if impr_default in IMPRESSION_OPTIONS else 2
        impression = st.radio(
            "5) Overall impression",
            IMPRESSION_OPTIONS,
            index=impr_idx,
            horizontal=True,
            key=f"impr_{nk}",
        )

    st.markdown("**Free note (optional)**")
    comment = st.text_area(
        "What caught your ear?",
        value=saved.get("comment", ""),
        placeholder="e.g. 'Great legato, but vowels blur in high notes…'",
        key=f"comment_{nk}",
    )

    if st.button("💾 Save notes", key=f"save_{nk}", width="stretch"):
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
            try:
                upsert_note(sb, party_session_id, party_user_id, current_work["id"], vid, payload)
                st.success("Saved to shared session (private to you).")
            except Exception as e:
                st.error(f"Could not save to session: {e}")
        else:
            st.session_state.notes[nk] = payload
            st.success("Saved locally (solo).")

    with st.expander("Reveal"):
        meta = yt_oembed(vid)
        if meta:
            st.markdown(f"**Title:** {meta.get('title', '—')}")
            st.markdown(f"**Channel:** {meta.get('author_name', '—')}")
        st.write("YouTube:", yt_url(vid))

    st.divider()

if party_mode:
    st.subheader("Share this session")
    st.caption("Send the URL in your browser (it contains ?session=...). Your friend logs in with a code and joins.")
