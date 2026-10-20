"""
mascot_bot.py - floating robot chatbot + "How to use" guided tour for NewsieNest.

Drop this file next to app.py. app.py only needs a few one-line hooks (apply_patch.py adds them):
  mascot_bot.apply_pending()          -> applies page / kids-mode / language changes the bot asked for
  mascot_bot.render(globals(), pages) -> draws the floating robot button and chat
  mascot_bot.page_guide(globals(), pages) -> the "Guide" menu page (video + animated tour)

Nothing in the existing features is changed. Optional secret: HOWTO_VIDEO_URL (YouTube / mp4 link).
"""
import base64
import json
import re

import streamlit as st

ROBOT_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 220">'
    '<g stroke="#0f1a2e" stroke-width="6" stroke-linejoin="round" stroke-linecap="round">'
    '<path d="M52 50 L70 72 M148 50 L130 72" fill="none"/>'
    '<circle cx="40" cy="36" r="17" fill="#22E5E5"/><circle cx="160" cy="36" r="17" fill="#22E5E5"/>'
    '<rect x="14" y="80" width="26" height="52" rx="10" fill="#19B8C4"/>'
    '<rect x="160" y="80" width="26" height="52" rx="10" fill="#19B8C4"/>'
    '<ellipse cx="100" cy="96" rx="70" ry="64" fill="#22E5E5"/>'
    '<rect x="42" y="66" width="116" height="80" rx="26" fill="#fff"/>'
    '<rect x="74" y="152" width="52" height="30" rx="14" fill="#19B8C4"/>'
    '<ellipse cx="72" cy="198" rx="22" ry="13" fill="#22E5E5"/>'
    '<ellipse cx="128" cy="198" rx="22" ry="13" fill="#22E5E5"/></g>'
    '<ellipse cx="130" cy="50" rx="14" ry="6" fill="#fff" opacity=".6" transform="rotate(-20 130 50)"/>'
    '<g stroke="#0f1a2e" stroke-width="4"><circle cx="76" cy="104" r="20" fill="#22E5E5"/>'
    '<circle cx="124" cy="104" r="20" fill="#22E5E5"/></g>'
    '<circle cx="76" cy="104" r="12" fill="#0f1a2e"/><circle cx="124" cy="104" r="12" fill="#0f1a2e"/>'
    '<circle cx="71" cy="99" r="4" fill="#fff"/><circle cx="119" cy="99" r="4" fill="#fff"/>'
    '<path d="M82 130 Q100 138 118 130" fill="none" stroke="#0f1a2e" stroke-width="4" stroke-linecap="round"/>'
    "</svg>"
)
ROBOT_URI = "data:image/svg+xml;base64," + base64.b64encode(ROBOT_SVG.encode()).decode()

FAB_CSS = """<style>
div[data-testid="stPopover"]{position:fixed!important;right:16px;bottom:16px;z-index:9999;width:auto!important}
div[data-testid="stPopover"] button{width:70px!important;height:70px!important;min-height:70px!important;border-radius:50%!important;
 background:#0f1a2e url(__ROBOT__) center/80% no-repeat!important;border:3px solid #22E5E5!important;padding:0!important;
 color:transparent!important;font-size:0!important;box-shadow:0 8px 24px rgba(0,0,0,.5);animation:botpulse 2.6s ease-in-out infinite}
div[data-testid="stPopover"] button *{display:none!important}
div[data-testid="stPopoverBody"]{width:min(94vw,430px)!important;max-width:94vw!important}
@keyframes botpulse{0%,100%{box-shadow:0 8px 24px rgba(0,0,0,.5),0 0 0 0 rgba(34,229,229,.5)}50%{box-shadow:0 8px 24px rgba(0,0,0,.5),0 0 0 12px rgba(34,229,229,0)}}
@media (prefers-reduced-motion:reduce){div[data-testid="stPopover"] button{animation:none}}
</style>"""

# ----------------------------------------------------------------------------
# Pending actions (the bot asks, main() applies them BEFORE the widgets are drawn)
# ----------------------------------------------------------------------------
def apply_pending():
    ss = st.session_state
    p = ss.pop("bot_do", None)
    if not p:
        return
    if "nav" in p:
        ss["nav"] = p["nav"]
    if "kids" in p:
        ss["kids_set"] = p["kids"]
    if "lang" in p:
        ss["lang"] = p["lang"]
    if "topic" in p:
        ss["topic_pill"] = p["topic"]


# ----------------------------------------------------------------------------
# Understanding what the person wants
# ----------------------------------------------------------------------------
NAV_RULES = [
    (r"\b(guide|tutorial|walkthrough|how (do i|to|can i) use|video|tour)\b", "🎬 Guide", False),
    (r"\b(my space|profile|saved|leaderboard|xp|streak|account)\b", "🧭 My Space", True),
    (r"\b(ask newsie|chat page|doubts?)\b", "💬 Ask Newsie", True),
    (r"\b(rate|rating|feedback|review)\b", "⭐ Rate us", True),
    (r"\b(privacy|data safe)\b", "🔒 Privacy", True),
    (r"\b(owner|admin|dashboard)\b", "🛡️ Owner", True),
    (r"\b(news|headlines|stories|home)\b", "📰 News", True),
]
VERB = re.compile(r"\b(open|go to|goto|take me|show|navigate|switch|visit|where is|bring)\b")
GREET = re.compile(r"(hi+|hello+|hey+|namaste|good (morning|afternoon|evening))[!. ]*")


def detect(G, msg, pages):
    """Returns (action_dict, reply) when the message is a command, else (None, None)."""
    m = msg.lower()
    if re.search(r"kids? mode", m):
        off = re.search(r"\b(off|disable|exit|stop|normal)\b", m)
        return ({"kids": not off},
                "Kids Mode is OFF. You will see the full news." if off else
                "🧸 Kids Mode is ON: gentle stories and simple words.")
    if re.search(r"\b(language|translate|switch to|change to)\b", m):
        for name in G["LANGS"]:
            if name.split(" ")[0].lower() in m:
                return {"lang": name}, f"🌐 Done! Summaries will now be translated to {name.split(' ')[0]}."
    if re.search(r"\b(news|stories|headlines|updates)\b", m):
        for label, kw in G["TOPICS"].items():
            if any(w in m for w in kw.lower().split() if len(w) > 3):
                if "📰 News" in pages:
                    return {"nav": "📰 News", "topic": label}, f"Showing {label} stories on the News page 📰"
    for pat, page, needs_verb in NAV_RULES:
        if re.search(pat, m) and (not needs_verb or VERB.search(m)):
            if page not in pages:
                return {}, "That page is only for the site owner."
            return {"nav": page}, f"Opening {page} for you ✨"
    return None, None


# ----------------------------------------------------------------------------
# Answering any question
# ----------------------------------------------------------------------------
def answer(G, msg, style):
    ss = st.session_state
    kids = ss.kids
    if kids and G["KIDS_BLOCK"].search(msg):
        return {"content": "🤖 That's a topic for grown-ups, so let's explore something else! "
                           "Try space, animals, cricket or how things work."}
    if GREET.fullmatch(msg.strip().lower()):
        return {"content": "Hi! 👋 I'm Newsie Bot. Ask me anything, or say things like "
                           "“open My Space”, “show cricket news”, “turn on kids mode”."}
    if not G["ai_enabled"]():
        return {"content": G["keyword_answer"](msg)}
    if style != "auto":
        return G["newsie_answer"](msg, style)  # cartoon / real life / game use the existing engine
    d = re.match(r"^(?:define|meaning of)\s+([a-z][a-z\- ]{1,30})$", msg.strip().lower())
    if d:
        meaning = G["define"](d.group(1).strip())
        if meaning:
            return {"content": meaning}
    sysmsg = (G["GROUND"] + " You can answer ANY question: school subjects, current affairs, technology, coding, "
              "health basics, careers and daily life. Give the direct answer first, then a short real-life example "
              f"only if it helps. Plain words, at most 220 words. The reader is {G['audience'](kids)}. "
              "If asked about this website, say you can open pages for them: News, Ask Newsie, My Space, "
              "Rate us, Privacy and Guide.")
    msgs = [{"role": c["role"], "content": c["content"]} for c in ss.chat[-9:-1]]
    while msgs and msgs[0]["role"] != "user":
        msgs.pop(0)
    msgs.append({"role": "user", "content": msg})
    out = G["llm"](sysmsg, msgs, 800, search=True)
    return {"content": out or G["keyword_answer"](msg)}


def handle(G, msg, style, pages):
    ss = st.session_state
    ss.chat.append({"role": "user", "content": msg})
    act, reply = detect(G, msg, pages)
    if reply:
        ss.chat.append({"role": "assistant", "content": "🤖 " + reply})
        if act:
            ss.bot_do = act
            st.rerun()
        return
    with st.spinner("Newsie Bot is thinking..."):
        res = answer(G, msg, style)
    if not res.get("panels") and G["LANGS"][ss.lang][0] != "en":
        res["content"] = G["tr_safe"](res["content"])
        if res.get("answers"):
            res["answers"] = G["tr_safe"](res["answers"])
    for old in ss.chat:
        old.pop("panels", None)  # only the newest cartoon stays on screen
    ss.chat.append({"role": "assistant", **res})
    try:
        G["x"]("INSERT INTO chats(user_id,ts,question,answer) VALUES(?,?,?,?)",
               (G["uid"](), G["iso"](), msg[:400], res["content"][:1500]))
        G["log"]("chat")
    except Exception:
        pass


# ----------------------------------------------------------------------------
# The floating robot + chat window
# ----------------------------------------------------------------------------
def render(G, pages):
    ss = st.session_state
    ss.setdefault("chat", [])
    st.markdown(FAB_CSS.replace("__ROBOT__", ROBOT_URI), unsafe_allow_html=True)
    with st.popover("Newsie Bot", help="Chat with Newsie Bot"):
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:10px"><img src="{ROBOT_URI}" width="48" alt="">'
            '<div><b>Newsie Bot</b><br><small>Ask anything. I can also open pages for you.</small></div></div>',
            unsafe_allow_html=True)
        keys = G["CHAT_KEYS"]
        pick = st.pills("Answer style", list(keys), default="✨ Auto", key="bot_style",
                        label_visibility="collapsed")
        style = keys.get(pick or "✨ Auto", "auto")
        quick = [("📰 News", "📰 News"), ("💬 Ask", "💬 Ask Newsie"), ("🧭 Space", "🧭 My Space"), ("🎬 Guide", "🎬 Guide")]
        for c, (lab, pg) in zip(st.columns(4), quick):
            if pg in pages and c.button(lab, key="bn_" + pg, width="stretch"):
                ss.bot_do = {"nav": pg}
                st.rerun()
        hist = st.container(height=320)
        with st.form("bot_form", clear_on_submit=True, border=False):
            t = st.text_input("Message", placeholder="Ask anything, or say: open My Space",
                              label_visibility="collapsed", max_chars=400)
            sent = st.form_submit_button("Send ➤", type="primary", width="stretch")
        if sent and t.strip():
            handle(G, t.strip(), style, pages)
        with hist:
            if not ss.chat:
                st.markdown("🤖 Hi! Pick a style above, then ask me anything. Try: *why is the sky blue*, "
                            "*open My Space*, *show cricket news*, *how do I use this website*.")
            for m in ss.chat[-6:]:
                with st.chat_message(m["role"], avatar="🤖" if m["role"] == "assistant" else None):
                    G["render_chat_msg"](m)


# ----------------------------------------------------------------------------
# Guide page: optional real video + animated tour
# ----------------------------------------------------------------------------
TOUR = [
    ("Welcome!", "Log in, sign up, or tap Explore to enter as a guest. Every feature works for guests too.", -1),
    ("📰 News", "Pick a quick topic, search anything, choose a category, then press Get news. The red ticker shows live headlines.", 0),
    ("✨ Story Studio", "Press Studio on any story for a 2-minute briefing, a cartoon, a simple explanation, a quiz and hard words.", 0),
    ("🔖 Save and share", "Save keeps a story in My Space. Source opens the publisher, Cross-check compares coverage, Share sends it on WhatsApp.", 0),
    ("💬 Ask Newsie", "Ask any doubt. Choose Auto, Cartoon, Real life or Game and Newsie answers in that style.", 1),
    ("🧭 My Space", "See your XP, streak, saved stories and the leaderboard.", 2),
    ("⚙️ Sidebar", "On the left: Kids Mode, 14 languages, text size, log out and Check connections.", -1),
    ("🤖 Newsie Bot", "Tap the robot at the bottom-right. Ask anything, or say: open My Space, show cricket news, turn on kids mode.", -1),
    ("⭐ Rate us and 🔒 Privacy", "Rate us sends feedback. Privacy shows exactly what we store and why.", 3),
]
MENU = ["📰 News", "💬 Ask Newsie", "🧭 My Space", "⭐ Rate us", "🔒 Privacy", "🎬 Guide"]

TOUR_HTML = r"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{box-sizing:border-box}html,body{margin:0;font-family:system-ui,'Segoe UI',sans-serif;background:transparent;color:#F2F3FA}
.box{background:linear-gradient(160deg,#1B1750,#0E1020);border:1px solid #2E3358;border-radius:20px;padding:16px;min-height:430px;display:flex;flex-direction:column;gap:12px}
.menu{display:flex;gap:6px;flex-wrap:wrap;background:#12142A;padding:8px;border-radius:14px}
.menu span{padding:6px 12px;border-radius:10px;background:#171A30;border:1.5px solid #2E3358;font-size:13px;font-weight:700;transition:.3s}
.menu span.on{background:#FF5C5C;border-color:#FF5C5C;transform:scale(1.08);box-shadow:0 0 0 4px rgba(255,92,92,.25)}
.row{display:flex;gap:14px;align-items:center;flex:1}
.bot{width:120px;flex:none;animation:bob 3s ease-in-out infinite}
.bub{background:#fff;color:#1c1650;border:4px solid #1c1650;border-radius:18px;padding:14px 16px;flex:1}
.bub h3{margin:0 0 6px;font-size:20px}.bub p{margin:0;font-size:16px;line-height:1.45;font-weight:600}
.cnt{font-size:12px;color:#AEB3D6;text-align:center}
.bar{height:6px;background:#2E3358;border-radius:9px;overflow:hidden}.bar i{display:block;height:100%;width:0;background:#22E5E5}
.ctl{display:flex;gap:8px;flex-wrap:wrap;justify-content:center}
button{font:700 14px system-ui;background:#171A30;color:#F2F3FA;border:1.5px solid #2E3358;border-radius:12px;padding:10px 16px;min-height:44px;cursor:pointer}
button.p{background:linear-gradient(135deg,#FF5C5C,#FF8A3D);border:0;color:#fff}
@keyframes bob{50%{transform:translateY(-8px)}}
@media (max-width:520px){.row{flex-direction:column}.bot{width:90px}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
</style></head><body>
<div class="box">
 <div class="menu" id="menu"></div>
 <div class="row"><img class="bot" src="__ROBOT__" alt="Newsie Bot">
  <div class="bub" aria-live="polite"><h3 id="t"></h3><p id="d"></p></div></div>
 <div class="bar"><i id="b"></i></div><div class="cnt" id="c"></div>
 <div class="ctl"><button id="prev">⏮ Back</button><button class="p" id="play">▶ Play tour</button>
  <button id="next">Next ⏭</button><button id="vo">🔊 Voice: off</button></div>
</div>
<script>
(function(){
const S=__STEPS__,M=__MENU__,$=id=>document.getElementById(id);
let i=0,playing=false,timer=null,voice=false;
$('menu').innerHTML=M.map(m=>'<span>'+m+'</span>').join('');
const syn=window.speechSynthesis;
function speak(t){if(!voice||!syn)return;syn.cancel();const u=new SpeechSynthesisUtterance(t);u.lang='en-IN';u.rate=.95;syn.speak(u);}
function dur(){return Math.max(5500,S[i][1].length*80);}
function show(n){i=(n+S.length)%S.length;const s=S[i];
 $('t').textContent=s[0];$('d').textContent=s[1];$('c').textContent='Step '+(i+1)+' of '+S.length;
 [...$('menu').children].forEach((el,k)=>el.classList.toggle('on',k===s[2]));
 const b=$('b');b.style.transition='none';b.style.width='0';void b.offsetWidth;
 clearTimeout(timer);
 if(playing){b.style.transition='width '+dur()+'ms linear';b.style.width='100%';timer=setTimeout(()=>show(i+1),dur());}
 speak(s[0].replace(/[^\w\s]/g,'')+'. '+s[1]);}
$('play').onclick=()=>{playing=!playing;$('play').textContent=playing?'⏸ Pause':'▶ Play tour';show(i);if(!playing&&syn)syn.cancel();};
$('next').onclick=()=>show(i+1);$('prev').onclick=()=>show(i-1);
$('vo').onclick=()=>{voice=!voice;$('vo').textContent='🔊 Voice: '+(voice?'on':'off');if(voice)speak(S[i][1]);else if(syn)syn.cancel();};
show(0);
})();
</script></body></html>"""


def page_guide(G, pages):
    st.markdown("### 🎬 How to use " + G["APP_NAME"])
    url = G["cfg"]("HOWTO_VIDEO_URL")
    if url.startswith("http"):
        st.video(url)
        st.caption("Prefer a quick animated tour? Press Play below.")
    markup = (TOUR_HTML.replace("__STEPS__", json.dumps(TOUR, ensure_ascii=False).replace("</", "<\\/"))
              .replace("__MENU__", json.dumps(MENU, ensure_ascii=False))
              .replace("__ROBOT__", ROBOT_URI))
    G["embed_html"](markup, 470)
    st.markdown("#### Jump to a page")
    targets = [p for p in pages if p != "🎬 Guide"]
    for c, pg in zip(st.columns(len(targets)), targets):
        if c.button(pg, key="gj_" + pg, width="stretch"):
            st.session_state.bot_do = {"nav": pg}
            st.rerun()
    st.caption("Tip: tap the 🤖 robot at the bottom-right any time and say “open My Space” or “show cricket news”.")
