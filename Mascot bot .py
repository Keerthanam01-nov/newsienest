"""
mascot_bot.py - "Robo", the floating robot helper for NewsieNest.

Put this file next to app.py, then run:  python apply_patch.py app.py

What it gives you
- A round robot button (bottom-right on every page after login) that opens a chat panel.
- Chat styles: Auto / Cartoon / Real life / Game (re-uses Newsie's own answer engine, so
  Claude-first / Gemini-backup, kids filter, dictionary, translation and the cartoon player all work).
- Navigation by voice-like typing: "open Rate us", "show cricket news", "kids mode on",
  "change to Hindi", "bigger text", "news about ISRO". These commands work even when AI quota is used up.
- A 🎬 Guide page: an animated, narrated tour of the whole site, plus optional real video
  (set GUIDE_VIDEO_URL in Secrets to a YouTube or MP4 link and it shows above the tour).

It only reads from app.py (through the `g` globals dict). It never changes existing functions.
"""
import base64
import html as _html
import io
import json
import re
from urllib.parse import quote

import streamlit as st

BOT_NAME = "Robo"


# ----------------------------------------------------------------------------
# Robot avatar (SVG)
# ----------------------------------------------------------------------------
def robot_svg():
    return (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'>"
        "<defs><linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>"
        "<stop offset='0' stop-color='#8B6CFF'/><stop offset='1' stop-color='#FF5C8A'/></linearGradient></defs>"
        "<circle cx='50' cy='50' r='48' fill='url(#g)'/>"
        "<line x1='50' y1='15' x2='50' y2='25' stroke='#fff' stroke-width='4' stroke-linecap='round'/>"
        "<circle cx='50' cy='11' r='5' fill='#FFC93C'/>"
        "<rect x='12' y='44' width='7' height='16' rx='3' fill='#FFC93C'/>"
        "<rect x='81' y='44' width='7' height='16' rx='3' fill='#FFC93C'/>"
        "<rect x='20' y='26' width='60' height='50' rx='16' fill='#fff' stroke='#1c1650' stroke-width='4'/>"
        "<g class='eyes'><circle cx='38' cy='48' r='7' fill='#1c1650'/><circle cx='62' cy='48' r='7' fill='#1c1650'/>"
        "<circle cx='40' cy='46' r='2.4' fill='#fff'/><circle cx='64' cy='46' r='2.4' fill='#fff'/></g>"
        "<g class='mouth'><path d='M38 62 q12 9 24 0' stroke='#1c1650' stroke-width='4' fill='none' stroke-linecap='round'/></g>"
        "</svg>")


def _bot_uri():
    return "data:image/svg+xml," + quote(robot_svg(), safe="")


def _css():
    uri = _bot_uri()
    return (
        "<style>"
        ".st-key-mb_fab{position:fixed;bottom:18px;right:18px;z-index:999990;width:auto!important}"
        "html body .stApp .st-key-mb_fab.st-key-mb_fab button{width:68px;height:68px;min-height:68px;padding:0!important;"
        "border-radius:50%!important;border:3px solid #fff!important;font-size:0!important;"
        "background:#8B6CFF url(\"" + uri + "\") center/cover no-repeat!important;"
        "box-shadow:0 8px 24px rgba(0,0,0,.5);animation:mbfloat 3.2s ease-in-out infinite}"
        ".st-key-mb_fab button *{opacity:0!important;font-size:0!important}"
        "@keyframes mbfloat{50%{transform:translateY(-6px)}}"
        "@media (prefers-reduced-motion:reduce){.st-key-mb_fab button{animation:none!important}}"
        "div[data-testid='stPopoverBody']{width:min(440px,94vw)!important;max-width:94vw!important;"
        "max-height:82vh;overflow-y:auto;background:#12142A!important;border:1px solid #2E3358!important;border-radius:18px!important}"
        "div[data-testid='stPopoverBody'] .stButton>button,div[data-testid='stPopoverBody'] [data-testid='stBaseButton-secondary']{"
        "background:#171A30!important;color:#F2F3FA!important;border:1.5px solid #2E3358!important;border-radius:12px!important}"
        "div[data-testid='stPopoverBody'] .stButton>button *{color:#F2F3FA!important}"
        "div[data-testid='stPopoverBody'] button[data-testid='stBaseButton-primaryFormSubmit']{"
        "background:linear-gradient(135deg,#FF5C5C,#FF8A3D)!important;border:0!important}"
        "div[data-testid='stPopoverBody'] button[data-testid='stBaseButton-primaryFormSubmit'] *{color:#fff!important}"
        "@media (max-width:640px){.st-key-mb_fab{bottom:12px;right:12px}}"
        "</style>")


# ----------------------------------------------------------------------------
# Pending actions (applied at the very top of the next run, before widgets exist)
# ----------------------------------------------------------------------------
def apply_pending():
    """Called by app.py before the sidebar and menu widgets are drawn."""
    p = st.session_state.pop("_mb_pending", None)
    if not p:
        return
    try:
        for state_key, p_key in (("nav", "nav"), ("kids", "kids"), ("lang", "lang"),
                                 ("tsize", "tsize"), ("topic_pill", "topic")):
            if p_key in p:
                st.session_state[state_key] = p[p_key]
    except Exception:
        pass


def _queue(**kw):
    st.session_state["_mb_pending"] = kw


# ----------------------------------------------------------------------------
# Command understanding (no AI needed, so it works when quota is used up)
# ----------------------------------------------------------------------------
HELP = (f"Hi, I'm **{BOT_NAME}** 🤖. I can:\n"
        "- **Answer anything** as a 🎭 cartoon, 🌍 real-life example or 🎮 game (pick a style below)\n"
        "- **Take you around**: *open Rate us*, *go to My Space*, *play the guide video*\n"
        "- **Show news**: *show cricket news*, *news about ISRO*\n"
        "- **Change settings**: *kids mode on*, *change language to Hindi*, *bigger text*")

TOPIC_ALIAS = {"cricket": "cricket", "ipl": "cricket", "space": "space", "isro": "space", "rocket": "space",
               "movie": "movies", "movies": "movies", "film": "movies", "cinema": "movies",
               "science": "science", "ai": "ai", "tech": "ai", "technology": "ai", "football": "football",
               "soccer": "football", "exam": "exams", "exams": "exams", "weather": "weather", "rain": "weather"}
NEWS_WORDS = {"news", "stories", "headlines", "updates", "latest"}
NAV_VERB = r"\b(open|go|goto|take|bring|show|navigate|visit|switch|jump|head|launch|play|watch|see|view)\b"
PAGE_PATTERNS = [
    ("guide", r"\b(guide|tutorial|walkthrough|how[- ]to video|video|tour|demo)\b"),
    ("ask newsie", r"\b(ask newsie|ask page|chat page|chat with newsie|questions? page)\b"),
    ("my space", r"\b(my space|profile|saved stories|saved|bookmarks?|leaderboard|my xp|xp|streak|account)\b"),
    ("rate us", r"\b(rate us|rate|rating|feedback|review)\b"),
    ("privacy", r"\b(privacy|data safety)\b"),
    ("owner", r"\b(owner|admin)\b"),
    ("news", r"\b(news|headlines|stories|home|front page|main page)\b"),
]


def _find_page(pages, frag):
    for p in pages:
        if p.split(" ", 1)[-1].strip().lower() == frag:
            return p
    return None


def parse_command(text, pages, g):
    """Returns None (not a command), {"reply", "pending"?} or {"search": query}."""
    t = " ".join(text.lower().strip().split())
    words = set(re.findall(r"[a-z]+", t))
    langs, topics = g.get("LANGS", {}), g.get("TOPICS", {})

    if re.search(r"\bwhat can you do\b|\bhow can you help\b|^help\b|^commands?$", t):
        return {"reply": HELP}

    # "how do I use this website?" -> the guide
    if (re.search(r"how (?:do|can|should|to) (?:i |we |you )?use (?:this|the) (?:site|website|app)", t)
            or re.search(r"how does (?:this|the) (?:site|website|app) work", t)
            or re.search(r"\b(?:website|site|app)\b.*\b(?:tutorial|guide|walkthrough|demo|video)\b", t)
            or re.search(r"\b(?:tutorial|walkthrough|demo)\b.*\b(?:website|site|app)\b", t)):
        page = _find_page(pages, "guide")
        if page:
            return {"reply": "Great question! Opening the 🎬 Guide, press ▶ Play for the full tour.",
                    "pending": {"nav": page}}

    # Kids mode
    if re.search(r"\bkids? mode\b", t) and re.search(
            r"\b(turn|switch|put|enable|disable|activate|deactivate|start|stop|exit|set)\b|\b(on|off)\b", t):
        off = bool(re.search(r"\b(off|disable|deactivate|stop|exit|leave)\b", t))
        return {"reply": "🧸 Kids Mode is now **off**. You'll see the full news." if off
                else "🧸 Kids Mode is now **on**: safe stories and simple words.",
                "pending": {"kids": not off}}

    # Language
    if re.match(r"^(?:please )?(?:change|switch|set|translate|speak)\b", t) or "language" in words:
        for key in langs:
            nm = key.split(" ")[0].lower()
            if re.search(r"\b" + re.escape(nm) + r"\b", t):
                return {"reply": f"🌐 Done! Summaries and answers will now be in **{key}**.",
                        "pending": {"lang": key}}

    # Text size
    if re.search(r"\b(text|font|letters?|words)\b", t) and re.search(
            r"\b(big|bigger|large|larger|huge|small|smaller|normal|extra)\b", t):
        if re.search(r"\b(extra|huge)\b", t):
            size = "Extra large"
        elif re.search(r"\b(small|smaller|normal)\b", t):
            size = "Normal"
        else:
            size = "Large"
        return {"reply": f"🔠 Text size is now **{size}**.", "pending": {"tsize": size}}

    # News on a quick topic
    hit = next((TOPIC_ALIAS[w] for w in re.findall(r"[a-z]+", t) if w in TOPIC_ALIAS), None)
    if hit and (words & NEWS_WORDS):
        label = next((k for k in topics if k.split(" ", 1)[-1].lower().startswith(hit)), None)
        page = _find_page(pages, "news")
        if label and page:
            return {"reply": f"Showing **{label}** news 📰", "pending": {"nav": page, "topic": label}}

    # Search news inline
    m = re.match(r"^(?:search(?: for)?|find|latest news (?:on|about)|news (?:on|about)|"
                 r"show me news (?:on|about)|any news (?:on|about))\s+(.{2,60})$", t)
    if m:
        return {"search": m.group(1).strip()}

    # Page navigation
    if re.search(NAV_VERB, t) or t.startswith("where is"):
        for frag, pat in PAGE_PATTERNS:
            if re.search(pat, t):
                page = _find_page(pages, frag)
                if page:
                    return {"reply": f"Opening **{page}** 🚀", "pending": {"nav": page}}
    return None


# ----------------------------------------------------------------------------
# Answers
# ----------------------------------------------------------------------------
def _search_news(g, query):
    try:
        arts, _ = g["fetch_news"](query, "Top stories", 20, st.session_state.get("kids", False), "All trusted media")
    except Exception:
        arts = []
    if not arts or arts[0].get("source") == "Sample story":
        return f"🦉 I couldn't find live stories about **{query}** right now. Try the News page search."
    lines = []
    for a in arts[:5]:
        title = a["title"].replace("[", "(").replace("]", ")")
        ago = g["time_ago"](a.get("published")) if a.get("published") else ""
        lines.append(f"- [{title}]({a['url']}) · {a['source']} {('· ' + ago) if ago else ''}")
    return f"📰 Latest on **{query}**:\n\n" + "\n".join(lines)


def _ai(g, hist, text, style):
    """Re-use the app's own answer engine (kids filter, dictionary, cartoon, game, real life)."""
    orig = st.session_state.get("chat")
    st.session_state.chat = [{"role": m["role"], "content": m["content"]} for m in hist[-9:]]
    try:
        res = g["newsie_answer"](text, style)
    finally:
        if orig is None:
            st.session_state.pop("chat", None)
        else:
            st.session_state.chat = orig
    code = g["LANGS"][st.session_state.lang][0]
    if not res.get("panels") and code != "en":
        res["content"] = g["tr_safe"](res["content"])
        if res.get("answers"):
            res["answers"] = g["tr_safe"](res["answers"])
    return res


def _record(g, text, res):
    try:
        g["x"]("INSERT INTO chats(user_id,ts,question,answer) VALUES(?,?,?,?)",
               (g["uid"](), g["iso"](), text[:400], res["content"][:1500]))
        g["log"]("bot")
    except Exception:
        pass


def _handle(g, pages, text, style):
    hist = st.session_state.setdefault("mb_hist", [])
    hist.append({"role": "user", "content": text})
    try:
        cmd = parse_command(text, pages, g)
        if cmd and cmd.get("search"):
            res = {"content": _search_news(g, cmd["search"])}
        elif cmd:
            res = {"content": cmd["reply"]}
            if cmd.get("pending"):
                _queue(**cmd["pending"])
        else:
            with st.spinner(f"{BOT_NAME} is thinking..."):
                res = _ai(g, hist, text, style)
    except Exception as e:
        res = {"content": f"🤖 Oops, something went wrong ({type(e).__name__}). Please try again."}
    for old in hist:
        old.pop("panels", None)  # keep only the newest cartoon
    hist.append({"role": "assistant", **res})
    del hist[:-24]
    _record(g, text, res)
    st.rerun()


# ----------------------------------------------------------------------------
# Floating button + panel
# ----------------------------------------------------------------------------
def _panel(g, pages):
    hist = st.session_state.setdefault("mb_hist", [])
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:4px">'
        f'<img src="{_bot_uri()}" width="44" height="44" alt="">'
        f'<div><b style="font-size:1.1rem">{BOT_NAME}</b><br>'
        f'<small style="color:#AEB3D6">Ask me anything, or tell me where to go</small></div></div>',
        unsafe_allow_html=True)

    cols = st.columns(3)
    for i, p in enumerate(pages):
        if cols[i % 3].button(p, key=f"mb_nav_{i}", width="stretch"):
            st.session_state.mb_hist.append({"role": "assistant", "content": f"Opening **{p}** 🚀"})
            _queue(nav=p)
            st.rerun()

    box = st.container(height=320, border=False)
    with box:
        if not hist:
            st.markdown(HELP)
        for m in hist[-10:]:
            with st.chat_message(m["role"], avatar="🤖" if m["role"] == "assistant" else None):
                if "render_chat_msg" in g:
                    g["render_chat_msg"](m)
                else:
                    st.markdown(m["content"])

    chat_keys = g.get("CHAT_KEYS", {"✨ Auto": "auto", "🎭 Cartoon": "cartoon", "🌍 Real life": "real", "🎮 Game": "game"})
    pick = st.pills("Answer style", list(chat_keys), default=list(chat_keys)[0], key="mb_style",
                    label_visibility="collapsed")
    style = chat_keys.get(pick or list(chat_keys)[0], "auto")

    with st.form("mb_form", clear_on_submit=True):
        text = st.text_input("Message", placeholder="e.g. open Rate us · show cricket news · explain GDP",
                             max_chars=300, label_visibility="collapsed")
        sent = st.form_submit_button("Send ➤", type="primary", width="stretch")
    if sent and text.strip():
        _handle(g, pages, text.strip(), style)
    if hist and st.button("🧹 Clear chat", key="mb_clear"):
        st.session_state.mb_hist = []
        st.rerun()
    st.caption("I'm an AI and can make mistakes. Please don't share personal details.")


def render(g, pages):
    """Draws the floating robot. Called once at the end of every page by app.py."""
    with st.container(key="mb_fab"):
        st.markdown(_css(), unsafe_allow_html=True)
        with st.popover("Chat", help=f"Ask {BOT_NAME}: chat, cartoons, games, or go to any page"):
            _panel(g, pages)


# ----------------------------------------------------------------------------
# 🎬 Guide page: animated, narrated tour (+ optional real video)
# ----------------------------------------------------------------------------
def _steps(name):
    return [
        {"icon": "👋", "title": "Welcome",
         "text": f"Welcome to {name}! Log in or sign up to save stories and earn XP, or tap Explore to use every feature as a guest. It all works either way.",
         "chips": ["Log in", "Sign up", "Forgot password", "Explore"]},
        {"icon": "🎛️", "title": "Your settings",
         "text": "The left sidebar keeps your settings. Turn on Kids Mode for safe stories and simple words, choose one of fourteen languages, and make the text bigger if you like. On a phone, open the little arrow at the top left.",
         "chips": ["🧸 Kids Mode", "🌐 Translate", "🔠 Text size", "Log out"]},
        {"icon": "📰", "title": "Read the news",
         "text": "On the News page you see a live ticker and quick topic buttons like Cricket or Space. To search, type a topic, choose a category and a news source, set how many stories you want, then press Get news.",
         "chips": ["🔴 LIVE ticker", "⚡ Quick topics", "Search a topic", "🔎 Get news"]},
        {"icon": "🧾", "title": "Understand each story",
         "text": "Every card shows a short summary, a mood label and a credibility hint. These are quick hints, not facts, so use Cross-check or Source to confirm. Save keeps a story and Share sends it on WhatsApp.",
         "chips": ["😊 Sentiment", "Credibility hint", "🔍 Cross-check", "🔖 Save", "📲 Share"]},
        {"icon": "✨", "title": "Story Studio",
         "text": "Press Studio on any card. Pick a two minute briefing, a cartoon where Newsie and Kiki act out the news, a simple explanation, a quiz to earn XP, or a list of hard words with meanings.",
         "chips": ["📋 2-min briefing", "🎨 Cartoon", "🧒 Explain simply", "🧠 Quiz", "📚 Hard words"]},
        {"icon": "💬", "title": "Ask Newsie",
         "text": "Open Ask Newsie to ask any doubt. Choose Auto, Cartoon, Real life or Game to decide how the answer looks. Type just one word to get its dictionary meaning.",
         "chips": ["✨ Auto", "🎭 Cartoon", "🌍 Real life", "🎮 Game"]},
        {"icon": "🤖", "title": f"Meet {BOT_NAME}",
         "text": f"That's me! The round robot button at the bottom right of every page. Ask me anything, or tell me where to go. Try: open Rate us, show cricket news, kids mode on, or change language to Hindi.",
         "chips": ["open Rate us", "show cricket news", "kids mode on", "change language to Hindi"]},
        {"icon": "🧭", "title": "My Space",
         "text": "My Space shows your XP, streak, saved stories and the leaderboard. Finish the daily mission by opening three stories, watching a cartoon and finishing a quiz.",
         "chips": ["XP", "🔥 Streak", "🔖 Saved", "🏆 Leaderboard"]},
        {"icon": "⭐", "title": "Rate and stay safe",
         "text": "Use Rate us to send feedback. The Privacy page explains what we store, and you can delete your account any time from My Space. That's the tour. Have fun!",
         "chips": ["⭐ Rate us", "🔒 Privacy", "Delete my account"]},
    ]


@st.cache_data(ttl=86400, show_spinner=False, max_entries=20)
def _guide_audio(texts, code):
    from gtts import gTTS
    out = []
    for t in texts:
        try:
            buf = io.BytesIO()
            kw = {"tld": "co.in"} if code == "en" else {}
            gTTS(text=t, lang=code, **kw).write_to_fp(buf)
            out.append(base64.b64encode(buf.getvalue()).decode())
        except Exception:
            out.append("")
    return out


GUIDE_HTML = r"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{box-sizing:border-box}html,body{margin:0;font-family:system-ui,'Segoe UI',sans-serif;background:transparent;color:#1c1650}
.stage{border:4px solid #1c1650;border-radius:22px;box-shadow:6px 6px 0 #1c1650;background:linear-gradient(160deg,#EDE9FF,#FFE9F1);padding:12px;overflow:hidden}
.top{display:flex;justify-content:space-between;align-items:center;gap:8px;font-weight:800}
.badge{background:#FFC93C;border:2px solid #1c1650;border-radius:99px;padding:2px 12px;font-size:14px}
.main{display:flex;gap:12px;align-items:center;margin-top:10px;flex-wrap:wrap}
.bot{width:110px;flex:0 0 110px}.bot svg{width:100%;height:auto;display:block;overflow:visible}
.bot.talk{animation:bob .5s ease-in-out infinite}
.mouth{transform-box:fill-box;transform-origin:50% 0}.bot.talk .mouth{animation:chomp .25s infinite}
.eyes{animation:blink 4s infinite;transform-box:fill-box;transform-origin:center}
.screen{flex:1;min-width:220px;background:#fff;border:3px solid #1c1650;border-radius:14px;padding:12px;min-height:170px}
.icon{font-size:52px;text-align:center;line-height:1.1}.pop{animation:pop .45s ease-out}
.sh{font-weight:800;font-size:19px;margin:4px 0 6px;text-align:center}
.chips{display:flex;flex-wrap:wrap;gap:6px;justify-content:center}
.chips span{background:#EFEAFF;border:2px solid #1c1650;border-radius:99px;padding:3px 10px;font-size:13px;font-weight:700}
.chips span.hl{background:#FFC93C;animation:pulse 1.1s ease-in-out infinite}
.cap{background:#fff;border:3px solid #1c1650;border-radius:14px;padding:10px 14px;margin-top:10px;min-height:84px;font-weight:700;font-size:16px;line-height:1.45}
.bar{height:9px;background:#fff;border:2px solid #1c1650;border-radius:9px;margin-top:10px;overflow:hidden}.bar i{display:block;height:100%;width:0;background:#FF5C5C;transition:width .4s}
.ctl{display:flex;gap:8px;justify-content:center;flex-wrap:wrap;margin-top:10px}
button{font:800 15px system-ui;background:#FFC93C;border:3px solid #1c1650;border-radius:12px;padding:9px 16px;min-height:44px;cursor:pointer;box-shadow:0 3px 0 #1c1650;color:#1c1650}
button:active{transform:translateY(3px);box-shadow:none}button:focus-visible{outline:3px solid #7a3cff;outline-offset:2px}
.hint{font-size:12px;text-align:center;margin-top:8px;opacity:.8}
@keyframes bob{50%{transform:translateY(-6px)}}@keyframes chomp{50%{transform:scaleY(1.9)}}
@keyframes blink{0%,94%,100%{transform:scaleY(1)}97%{transform:scaleY(.08)}}
@keyframes pop{0%{transform:scale(.3) rotate(-12deg);opacity:0}70%{transform:scale(1.15)}100%{transform:none;opacity:1}}
@keyframes pulse{50%{transform:scale(1.08)}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
</style></head><body>
<div class="stage">
 <div class="top"><span class="badge">🎬 __NAME__ guide</span><span id="cnt">1 / 1</span></div>
 <div class="main">
  <div class="bot" id="bot">__BOT__</div>
  <div class="screen"><div class="icon" id="icon">👋</div><div class="sh" id="sh"></div><div class="chips" id="chips"></div></div>
 </div>
 <div class="cap" id="cap" aria-live="polite"></div>
 <div class="bar"><i id="bar"></i></div>
 <div class="ctl"><button id="prev">⏮ Back</button><button id="play">▶ Play the tour</button><button id="next">Next ⏭</button></div>
 <div class="hint">🔊 Turn your volume up and press Play. Use Back and Next to go at your own pace.</div>
</div>
<script>
(function(){
const S=__STEPS__,LANG="__LANG__",$=id=>document.getElementById(id);
let i=0,playing=false,tok=0,cyc=null,typer=null;
const synth=window.speechSynthesis,au=new Audio();
function voice(){const vs=synth?synth.getVoices():[],l=LANG.toLowerCase(),pl=l.split('-')[0];
 const pool=vs.filter(v=>v.lang.toLowerCase().replace('_','-').startsWith(pl));
 return pool.find(v=>/natural|google|online/i.test(v.name))||pool[0]||null;}
function talk(on){$('bot').classList.toggle('talk',on);}
function say(s,done){
 if(s.audio){au.pause();au.src='data:audio/mpeg;base64,'+s.audio;au.onended=done;au.onerror=done;const pr=au.play();if(pr&&pr.catch)pr.catch(done);return;}
 const wait=()=>setTimeout(done,Math.max(3000,s.text.length*70));
 if(!synth){wait();return;}
 const v=voice();if(!v&&!LANG.startsWith('en')){wait();return;}
 const u=new SpeechSynthesisUtterance(s.text);u.lang=LANG;if(v)u.voice=v;u.rate=.95;u.onend=done;u.onerror=done;window._u=u;synth.speak(u);}
function show(n,speak){
 i=n;const s=S[n],my=++tok;clearInterval(typer);clearInterval(cyc);if(synth)synth.cancel();au.pause();
 const ic=$('icon');ic.textContent=s.icon;ic.className='icon';void ic.offsetWidth;ic.className='icon pop';
 $('sh').textContent=s.title;
 const box=$('chips');box.textContent='';
 s.chips.forEach(c=>{const e=document.createElement('span');e.textContent=c;box.appendChild(e);});
 const cs=[...box.children];let h=0;
 if(cs.length){cs[0].classList.add('hl');cyc=setInterval(()=>{cs[h].classList.remove('hl');h=(h+1)%cs.length;cs[h].classList.add('hl');},1500);}
 $('bar').style.width=((n+1)/S.length*100)+'%';$('cnt').textContent=(n+1)+' / '+S.length;
 let k=0;$('cap').textContent='';
 typer=setInterval(()=>{$('cap').textContent=s.text.slice(0,++k);if(k>=s.text.length)clearInterval(typer);},speak?30:6);
 if(!speak){talk(false);return;}
 talk(true);let fin=false;
 const done=()=>{if(fin||my!==tok)return;fin=true;talk(false);
  if(playing&&n+1<S.length)setTimeout(()=>{if(my===tok)show(n+1,true);},500);
  else if(n+1>=S.length){playing=false;$('play').textContent='\u{1F501} Watch again';}};
 say(s,done);setTimeout(done,12000+s.text.length*110);
}
$('play').onclick=()=>{
 if(playing){playing=false;tok++;if(synth)synth.cancel();au.pause();talk(false);$('play').textContent='\u25B6 Play the tour';return;}
 playing=true;$('play').textContent='\u23F8 Pause';show(i>=S.length-1?0:i,true);};
$('next').onclick=()=>show(Math.min(i+1,S.length-1),playing);
$('prev').onclick=()=>show(Math.max(i-1,0),playing);
if(synth){synth.onvoiceschanged=()=>{};}
show(0,false);
})();
</script></body></html>"""


def _guide_html(steps, voice_lang, name):
    data = json.dumps(steps, ensure_ascii=False).replace("</", "<\\/")
    return (GUIDE_HTML.replace("__STEPS__", data).replace("__LANG__", _html.escape(voice_lang))
            .replace("__NAME__", _html.escape(name)).replace("__BOT__", robot_svg()))


def page_guide(g, pages):
    name = g.get("APP_NAME", "NewsieNest")
    st.markdown(f"### 🎬 How to use {_html.escape(name)}")
    st.caption("Watch the guided tour, or jump straight to any page below.")

    vid = g["cfg"]("GUIDE_VIDEO_URL") if "cfg" in g else ""
    if vid:
        try:
            st.video(vid)
        except Exception:
            st.link_button("▶ Watch the video", vid)

    langs = g.get("LANGS", {})
    code, voice = langs.get(st.session_state.get("lang", "English"), ("en", "en-IN"))
    steps = _steps(name)

    if code != "en":
        try:
            flat = tuple(s[k] for s in steps for k in ("title", "text"))
            tr = list(g["translate_many"](flat, code))
            for n, s in enumerate(steps):
                s["title"], s["text"] = tr[2 * n], tr[2 * n + 1]
        except Exception:
            st.caption("Translation isn't available right now, so the tour is in English.")
            code, voice = "en", "en-IN"

    if st.toggle("🔊 Clear voice (works on every device)", value=True, key="mb_guide_voice"):
        with st.spinner("Preparing the voice..."):
            audio = _guide_audio(tuple(s["text"] for s in steps), code)
        for s, a in zip(steps, audio):
            if a:
                s["audio"] = a

    if hasattr(st, "iframe"):
        st.iframe(_guide_html(steps, voice, name), height=620)
    else:
        import streamlit.components.v1 as components
        components.html(_guide_html(steps, voice, name), height=620, scrolling=True)

    st.markdown("#### 🚀 Try it yourself")
    cols = st.columns(3)
    for i, p in enumerate(pages):
        if p.split(" ", 1)[-1].strip().lower() == "guide":
            continue
        if cols[i % 3].button(p, key=f"mb_gd_{i}", width="stretch"):
            _queue(nav=p)
            st.rerun()
    st.caption(f"Tip: the round robot button at the bottom right is {BOT_NAME}. Ask {BOT_NAME} to take you anywhere.")
