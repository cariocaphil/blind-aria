"""
Authentication UI and logic for Blind Aria Trainer.
"""

import streamlit as st

from db import create_sb_client, supabase_available


def require_login_block(invited: bool = False) -> None:
    """Display login UI block (OTP via email)."""
    if invited:
        st.warning("🎟️ **You've been invited to a blind listening session.** Please log in to join.")
    else:
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
            st.session_state["active_session_id"] = None
            from utils import clear_session_param
            clear_session_param()
            st.rerun()

    sent_email = st.session_state.get("otp_email_sent")
    if sent_email:
        code = st.text_input("Code", key="otp_code", placeholder="123456")
        if st.button("Verify code", width="stretch"):
            if not code.strip():
                st.error("Enter the code.")
            else:
                try:
                    resp = sb.auth.verify_otp({"email": sent_email, "token": code.strip(), "type": "email"})
                    session = getattr(resp, "session", None) or (resp.get("session") if isinstance(resp, dict) else None)
                    user = getattr(resp, "user", None) or (resp.get("user") if isinstance(resp, dict) else None)

                    access_token = None
                    user_id = None

                    if session is not None:
                        access_token = getattr(session, "access_token", None)
                        if isinstance(session, dict):
                            access_token = access_token or session.get("access_token")

                    if user is not None:
                        user_id = getattr(user, "id", None)
                        if isinstance(user, dict):
                            user_id = user_id or user.get("id")

                    if not access_token or not user_id:
                        st.error("Login succeeded but access token/user_id missing.")
                        st.stop()

                    st.session_state["sb_auth"] = {
                        "user_id": user_id,
                        "email": sent_email,
                        "access_token": access_token,
                    }
                    st.success("Logged in.")
                    st.rerun()

                except Exception as e:
                    st.error(f"Verification failed: {e}")
