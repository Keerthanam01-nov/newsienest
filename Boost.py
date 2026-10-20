"""boost.py - extras for NewsieNest (put next to app.py)."""
import re
import time
from urllib.parse import quote

import requests
import streamlit as st

_UA = {"User-Agent": "NewsieNest/1.0 (learning app; contact via site)"}


def typewriter(text):
    """ChatGPT-style streaming: yields the answer word by word."""
    for tok in re.findall(r"\S+\s*|\s+", text):
        yield tok
        time.sleep(0.012)


def wiki_answer(question):
    """Free, no-key fallback so Newsie still answers when the AI quota is used up."""
    try:
        s = re.sub(r"^(what is|what are|who is|who was|define|explain|tell me about|meaning of)\s+",
                   "", question.strip().lower().rstrip("?. !"))
        if len(s) < 2:
            return None
        r = requests.get("https://en.wikipedia.org/w/api.php", headers=_UA, timeout=6,
                         params={"action": "query", "list": "search", "srsearch": s,
                                 "srlimit": 1, "format": "json"})
        hits = r.json()["query"]["search"]
        if not hits:
            return None
        title = hits[0]["title"]
        j = requests.get("https://en.wikipedia.org/api/rest_v1/page/summary/"
                         + quote(title.replace(" ", "_")), headers=_UA, timeout=6).json()
        ext = j.get("extract", "")
        if len(ext) < 40:
            return None
        link = j.get("content_urls", {}).get("desktop", {}).get("page", "")
        return (f"📚 **{j.get('title', title)}** (from Wikipedia, while my AI brain rests)\n\n{ext[:700]}"
                + (f"\n\n[Read more]({link})" if link else ""))
    except Exception:
        return None


def forgot_tab(g):
    """Two steps on one screen: email -> code is emailed automatically -> code + new password."""
    S = st.session_state
    st.markdown("**Reset your password in 2 quick steps**")
    if S.get("fp_sent"):
        em = S.fp_sent
        if g["smtp_ready"]():
            st.success(f"✅ Step 1 done. We emailed a 6-digit code to **{em}** (valid 30 minutes, check Spam too).")
        else:
            st.warning("Automatic email is not set up yet. Email "
                       f"**{g['contact_email']()}** to get your code, then enter it below.")
        with st.form("fp_set"):
            code = st.text_input("Step 2. 6-digit code", max_chars=64)
            pw = st.text_input("New password (8+ characters, letters and numbers)", type="password")
            if st.form_submit_button("Set new password", type="primary", width="stretch"):
                ok, msg = g["finish_reset"](em, code, pw)
                if ok:
                    S.pop("fp_sent", None)
                    st.success(msg)
                else:
                    st.error(msg)
        a, b = st.columns(2)
        if a.button("↩ Use a different email", key="fp_back", width="stretch"):
            S.pop("fp_sent", None)
            st.rerun()
        if b.button("📧 Send the code again", key="fp_again", width="stretch"):
            S.pop("fp_last", None)
            S.fp_resend = em
            S.pop("fp_sent", None)
            st.rerun()
        return
    with st.form("fp_req"):
        em = st.text_input("Step 1. Your account email", value=S.pop("fp_resend", ""))
        if st.form_submit_button("📧 Email me a code", type="primary", width="stretch"):
            em = em.strip().lower()
            if not em:
                st.error("Please type your email first.")
            elif time.time() - S.get("fp_last", 0) < 60:
                st.warning("Please wait a minute before asking for another code.")
            else:
                S.fp_last = time.time()
                code = g["create_reset"](em)
                try:
                    if code and g["smtp_ready"]():
                        g["send_email"](em, f"{g['APP_NAME']} password reset code",
                                        f"Your {g['APP_NAME']} reset code is {code}.\n"
                                        "It works for 30 minutes. If you did not ask for it, ignore this email.")
                except Exception as e:
                    st.error("We couldn't send the email. Check the SMTP settings in Secrets.")
                    st.caption(f"{type(e).__name__}: {str(e)[:120]}")
                    return
                S.fp_sent = em
                st.rerun()
