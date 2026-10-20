"""Animations and mascots for NewsieNest. Safe to delete: remove the 3 lines the patcher added."""
import streamlit as st


def inject_extra_css(kids=False):
    css = """<style>
.stApp{background:linear-gradient(135deg,#1B1750,#0E1020 45%,#1a1040 70%,#0E1020)!important;background-size:300% 300%!important;animation:nvbg 24s ease infinite;overflow-x:hidden}
@keyframes nvbg{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}
.block-container{position:relative;z-index:1}
.nv-bg{position:fixed;inset:0;pointer-events:none;z-index:0;overflow:hidden}
.nv-bg span{position:absolute;bottom:-70px;opacity:.13;animation:nvfloat 22s linear infinite}
@keyframes nvfloat{to{transform:translateY(-120vh) rotate(360deg)}}
.nv-card{animation:nvup .45s ease both}
@keyframes nvup{from{opacity:0;transform:translateY(18px)}to{opacity:1;transform:none}}
.nv-card:hover h4{color:#FFD66B}
.trust>i{animation:nvgrow 1s ease-out both;transform-origin:left}
@keyframes nvgrow{from{transform:scaleX(0)}to{transform:scaleX(1)}}
.nv-feat>div{animation:nvpop .6s ease both;transition:transform .2s ease,border-color .2s ease}
.nv-feat>div:nth-child(2){animation-delay:.08s}.nv-feat>div:nth-child(3){animation-delay:.16s}
.nv-feat>div:nth-child(4){animation-delay:.24s}.nv-feat>div:nth-child(5){animation-delay:.32s}.nv-feat>div:nth-child(6){animation-delay:.4s}
.nv-feat>div:hover{transform:translateY(-6px) rotate(-2deg);border-color:#FF8A3D}
.nv-feat>div span{display:inline-block;animation:nvbob 3s ease-in-out infinite}
.nv-feat>div:nth-child(even) span{animation-delay:-1.5s}
@keyframes nvpop{from{opacity:0;transform:scale(.7)}to{opacity:1;transform:none}}
@keyframes nvbob{50%{transform:translateY(-6px) rotate(6deg)}}
.nv-mission{animation:nvglow 3s ease-in-out infinite}
@keyframes nvglow{50%{box-shadow:0 0 18px rgba(240,165,0,.45)}}
html body .stApp .stButton>button[data-testid="stBaseButton-primary"],
html body .stApp .stFormSubmitButton>button[data-testid="stBaseButton-primaryFormSubmit"]{
 background:linear-gradient(120deg,#FF5C5C,#FF8A3D,#FF5C8A,#FF8A3D)!important;background-size:250% 100%!important;
 animation:nvshine 6s ease infinite;box-shadow:0 6px 18px rgba(255,92,92,.35)}
@keyframes nvshine{50%{background-position:100% 0}}
html body .stApp .stButton>button:active,html body .stApp [data-testid^="stBaseLinkButton"]:active{transform:scale(.95)}
.nv-mascots{display:flex;align-items:center;gap:14px;background:linear-gradient(90deg,#2B2A8F,#5B3DF5 60%,#FF5C8A);
 border-radius:20px;padding:10px 16px;margin:6px 0 10px;color:#fff;box-shadow:0 8px 24px rgba(0,0,0,.3)}
.nv-mascots .mw{font-size:2.6rem;display:inline-block}
.nv-mascots .owl{animation:nvwave 2.4s ease-in-out infinite}
.nv-mascots .tiger{animation:nvjump 1.8s ease-in-out infinite}
.nv-mascots .mb{flex:1;font-weight:700;line-height:1.4}
@keyframes nvwave{50%{transform:rotate(12deg) translateY(-4px)}}
@keyframes nvjump{50%{transform:translateY(-12px)}}
[data-testid="stSegmentedControl"]{overflow-x:auto}
@media (max-width:640px){
 .nv-feat{grid-template-columns:repeat(2,1fr)}
 .nv-bg span{font-size:20px!important}
 .nv-mascots{flex-direction:column;text-align:center}
 html body .stApp .stButton>button,html body .stApp [data-testid^="stBaseLinkButton"]{min-height:48px}
}
@media (prefers-reduced-motion:reduce){.nv-bg{display:none}*{animation:none!important;transition:none!important}}
</style>"""
    if kids:
        css += """<style>
.stApp{background:linear-gradient(135deg,#2a1b6e,#5B3DF5 40%,#ff6b9a 100%)!important;background-size:300% 300%!important}
.nv-card{border-radius:26px;border-left-width:10px;border-width:2px}
.nv-card h4{font-size:1.2rem}.nv-sum{font-size:1.05rem}
html body .stApp .stButton>button,html body .stApp [data-testid^="stBaseLinkButton"]{border-radius:18px!important;font-size:1.05rem}
.nv-bg span{opacity:.22}
</style>"""
    st.markdown(css, unsafe_allow_html=True)


def fun_bg():
    em = ["📰", "🚀", "🌍", "🏏", "💡", "🔬", "🎬", "⭐", "🎈", "🦉", "🐯", "📚"]
    spans = "".join(
        f"<span style='left:{4 + i * 8}%;animation-delay:-{i * 2}s;animation-duration:{18 + (i % 4) * 4}s;"
        f"font-size:{22 + (i % 3) * 8}px'>{e}</span>" for i, e in enumerate(em))
    st.markdown(f'<div class="nv-bg" aria-hidden="true">{spans}</div>', unsafe_allow_html=True)


def mascot_strip():
    st.markdown('<div class="nv-mascots"><span class="mw owl">🦉</span><div class="mb">Hi! I\'m Newsie, and this is Kiki. '
                'Tap <b>✨ Studio</b> on any story and we\'ll act it out for you!</div>'
                '<span class="mw tiger">🐯</span></div>', unsafe_allow_html=True)
