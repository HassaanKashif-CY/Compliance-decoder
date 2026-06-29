import streamlit as st
import fitz
import google.generativeai as genai
import json
import smtplib
import copy
import time
import base64
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from auth import login_ui

st.set_page_config(
    page_title="Sahl | Compliance Decoder",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── Auth ──────────────────────────────────────────────────────────────
if 'user' not in st.session_state:
    login_ui()
    st.stop()

# ── Logo (embedded base64 so no file path issues on Streamlit Cloud) ──
_LOGO_B64 = "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"
LOGO_IMG  = f'<img src="data:image/png;base64,{_LOGO_B64}" style="height:42px;">'
LOGO_SMALL = f'<img src="data:image/png;base64,{_LOGO_B64}" style="height:28px; vertical-align:middle;">'


# ── Theme ─────────────────────────────────────────────────────────────
def apply_theme():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
*{box-sizing:border-box;}
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
[data-testid="stSidebar"]{display:none!important;}
[data-testid="collapsedControl"]{display:none!important;}
#MainMenu{visibility:hidden;}footer{visibility:hidden;}header{visibility:hidden;}
.stApp{background:#f7f6ff;min-height:100vh;}
.main .block-container{padding:0!important;max-width:100%!important;}

/* Buttons */
.stButton>button{
  background:linear-gradient(135deg,#8a2be2 0%,#5b10b0 100%)!important;
  color:#fff!important;border:none!important;border-radius:12px!important;
  font-weight:600!important;font-size:0.97rem!important;padding:0.78rem 1.5rem!important;
  box-shadow:0 4px 18px rgba(138,43,226,0.28)!important;
  transition:all 0.18s ease!important;width:100%!important;letter-spacing:0.01em!important;
}
.stButton>button:hover{transform:translateY(-2px)!important;box-shadow:0 8px 28px rgba(138,43,226,0.38)!important;}

/* Inputs */
.stTextInput input{
  border:1.5px solid #e2d9f3!important;border-radius:11px!important;
  padding:0.72rem 1rem!important;font-size:0.95rem!important;
  color:#1a1035!important;background:#fff!important;
  transition:border-color 0.18s!important;
}
.stTextInput input:focus{border-color:#8a2be2!important;box-shadow:0 0 0 3px rgba(138,43,226,0.1)!important;}
.stTextInput label{font-weight:600!important;color:#3d3060!important;font-size:0.875rem!important;margin-bottom:4px!important;}

/* Radio */
.stRadio>div{gap:10px!important;}
.stRadio label{font-weight:500!important;color:#3d3060!important;font-size:0.92rem!important;}
[data-testid="stFileUploaderDropzone"]{background:#fff!important;border:2px dashed #c4a8f0!important;border-radius:16px!important;}
.streamlit-expanderHeader{background:#f7f6ff!important;border-radius:10px!important;font-weight:600!important;color:#4b0082!important;}

/* ── Top bar ── */
.topbar{background:#fff;border-bottom:1px solid #ede8f7;padding:14px 36px;display:flex;align-items:center;gap:10px;position:sticky;top:0;z-index:200;box-shadow:0 1px 8px rgba(90,0,160,0.05);}
.topbar-name{font-size:1.05rem;font-weight:800;color:#1a0033;letter-spacing:-0.01em;}
.topbar-badge{margin-left:auto;background:#f0e8ff;color:#6a1cb0;font-size:0.74rem;font-weight:700;padding:4px 12px;border-radius:20px;letter-spacing:0.04em;text-transform:uppercase;}

/* ── Onboarding ── */
.ob-page{min-height:calc(100vh - 58px);display:flex;align-items:center;justify-content:center;padding:40px 20px;background:linear-gradient(155deg,#f7f6ff 0%,#ede8f7 100%);}
.ob-card{background:#fff;border-radius:24px;padding:52px 52px 44px;width:100%;max-width:480px;box-shadow:0 24px 64px rgba(90,0,160,0.12);border:1px solid #ede8f7;}
.ob-logo{text-align:center;margin-bottom:26px;}
.ob-title{font-size:1.6rem;font-weight:800;color:#0d0020;margin:0 0 6px;text-align:center;letter-spacing:-0.025em;}
.ob-sub{font-size:0.9rem;color:#7c5cbf;text-align:center;margin-bottom:36px;font-weight:400;}
.ob-divider{border:none;border-top:1px solid #ede8f7;margin:22px 0;}
.ob-label{font-size:0.82rem;font-weight:700;color:#3d3060;margin-bottom:10px;letter-spacing:0.02em;text-transform:uppercase;}

/* ── Upload page ── */
.pg-wrap{max-width:700px;margin:0 auto;padding:36px 24px;}
.pg-heading{font-size:1.25rem;font-weight:800;color:#0d0020;margin:0 0 4px;letter-spacing:-0.02em;}
.pg-sub{font-size:0.875rem;color:#7c5cbf;margin:0 0 24px;}
.upload-card{background:#fff;border-radius:20px;padding:36px;border:1px solid #ede8f7;box-shadow:0 6px 28px rgba(90,0,160,0.06);}

/* ── Processing page ── */
.proc-card{background:#fff;border-radius:20px;padding:40px;border:1px solid #ede8f7;box-shadow:0 6px 28px rgba(90,0,160,0.06);}
.proc-hd{display:flex;align-items:center;gap:18px;padding-bottom:24px;border-bottom:1px solid #f0eafc;margin-bottom:28px;}
.proc-icon{width:52px;height:52px;background:linear-gradient(135deg,#f0e8ff,#ddd0f7);border-radius:14px;display:flex;align-items:center;justify-content:center;font-size:1.4rem;}
.proc-title{font-size:1.15rem;font-weight:800;color:#0d0020;margin:0 0 3px;}
.proc-subtitle{font-size:0.84rem;color:#7c5cbf;margin:0;}
.step-row{display:flex;align-items:center;gap:12px;padding:11px 16px;border-radius:10px;margin-bottom:8px;font-size:0.875rem;font-weight:500;}
.step-done{background:#f0fdf4;color:#15803d;}
.step-active{background:#f7f6ff;color:#4b0082;border:1.5px solid #e0d4f7;animation:pulse 1.5s infinite;}
.step-pend{background:#f9f9f9;color:#aaa;}
@keyframes pulse{0%,100%{opacity:1;}50%{opacity:0.65;}}
.proc-time{display:inline-flex;align-items:center;gap:6px;background:#f0e8ff;color:#6a1cb0;padding:6px 14px;border-radius:20px;font-size:0.82rem;font-weight:700;margin-top:20px;}
.proc-note{text-align:center;color:#aaa;font-size:0.8rem;margin-top:14px;}

/* ── Results ── */
.res-topstrip{display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:24px;flex-wrap:wrap;gap:12px;}
.res-left h2{font-size:1.15rem;font-weight:800;color:#0d0020;margin:0 0 4px;letter-spacing:-0.015em;}
.res-left p{font-size:0.84rem;color:#7c5cbf;margin:0;}
.fw-badge{background:#f0e8ff;color:#6a1cb0;padding:5px 14px;border-radius:20px;font-size:0.78rem;font-weight:700;white-space:nowrap;}
.btn-row{display:flex;gap:10px;align-items:center;}

.chapter-block{background:#fff;border-radius:16px;padding:24px 28px;margin-bottom:18px;border:1.5px solid #ede8f7;box-shadow:0 3px 12px rgba(90,0,160,0.04);}
.chapter-pill{display:inline-block;background:#f0e8ff;color:#6a1cb0;font-weight:700;font-size:0.7rem;padding:3px 11px;border-radius:20px;margin-bottom:8px;letter-spacing:0.06em;text-transform:uppercase;}
.chapter-title{color:#0d0020;font-weight:800;font-size:1.05rem;margin:0 0 14px;}
.art-block{border-left:3px solid #8a2be2;padding:13px 16px;margin-bottom:11px;border-radius:0 11px 11px 0;background:linear-gradient(90deg,#f9f7ff 0%,#fff 80%);}
.art-id{color:#8a2be2;font-weight:700;font-size:0.76rem;letter-spacing:0.06em;text-transform:uppercase;}
.art-title{color:#0d0020;font-weight:700;font-size:0.92rem;margin:3px 0 7px;}
.art-desc{color:#4b5563;font-size:0.84rem;line-height:1.65;margin-bottom:9px;}
.ctrl-block{background:#fff;border:1px solid #e2d9f3;border-radius:10px;padding:11px 15px;margin:5px 0;}
.ctrl-title{color:#6a1cb0;font-weight:700;font-size:0.845rem;margin-bottom:3px;}
.ctrl-desc{color:#4b5563;font-size:0.81rem;line-height:1.55;margin-bottom:7px;}
.act-pill{display:inline-block;background:#f0e8ff;color:#6a1cb0;font-size:0.73rem;padding:2px 9px;border-radius:20px;margin:2px 3px 2px 0;font-weight:500;}

/* Misc */
.quota-box{background:#fff7ed;border:1.5px solid #fed7aa;border-radius:14px;padding:20px 24px;color:#9a3412;font-weight:600;text-align:center;}
.success-card{background:linear-gradient(135deg,#f3e5f5,#ede7f6);border:1.5px solid #ce93d8;border-radius:20px;padding:52px 36px;text-align:center;max-width:540px;margin:48px auto;}
.success-card h3{color:#4b0082!important;font-size:1.5rem!important;margin:0 0 14px!important;}
.success-card p{color:#6a1cb0;font-size:0.97rem;line-height:2;margin:0;}
hr.div{border:none;border-top:1px solid #ede8f7;margin:20px 0;}
</style>
""", unsafe_allow_html=True)

apply_theme()

# ── Session defaults ───────────────────────────────────────────────────
DEFAULTS = {
    "stage": "onboarding",   # onboarding | upload | processing | results | submitted
    "company": "",
    "email": "",
    "lang": "English",
    "data": None,
    "edited": None,
    "pdf_bytes": None,
    "pdf_name": None,
    "elapsed": 0,
    "edit_mode": False,
    "submitted": False,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Topbar (shown after onboarding) ───────────────────────────────────
def render_topbar(badge_text="Compliance Decoder"):
    st.markdown(f"""
<div class="topbar">
  {LOGO_SMALL}&nbsp;<span class="topbar-name">Sahl</span>
  <span class="topbar-badge">{badge_text}</span>
</div>""", unsafe_allow_html=True)

# ── Extraction prompt ──────────────────────────────────────────────────
EXTRACTION_PROMPT = """
You are an expert GRC analyst. Extract ANY compliance framework document
into a strict JSON structure for the Sahl GRC platform.

RULES:
- Intelligently detect hierarchy: GDPR=Chapter/Article, NCNICC/ECC=Domain/Sub-domain/Control,
  ISO 27001=Clause/Control, PDPL=Chapter/Article, NCA=Domain/Sub-domain (these are just examples you should detect yourself according to the uploaded pdf).
- Preserve ALL Arabic text exactly. Do NOT translate.
- If a field is absent use empty string "".
- action_list: suggest 2-3 realistic policy documents/evidence items needed to comply.
- Return ONLY valid JSON. No markdown, no commentary, no extra keys.

SCHEMA:
{
  "framework_name": "detected framework name",
  "chapters": [
    {
      "chapter_id": "1",
      "chapter_title_en": "English chapter/domain title",
      "chapter_title_ar": "Arabic title or empty string",
      "articles": [
        {
          "article_id": "1.1",
          "article_title_en": "English article/sub-domain/clause title",
          "article_title_ar": "Arabic title or empty string",
          "description_en": "English policy requirement text",
          "description_ar": "Arabic policy requirement text or empty string",
          "controls": [
            {
              "control_title_en": "Short action-oriented control name in English",
              "control_title_ar": "Short control name in Arabic or empty string",
              "description_en": "What the organization must implement",
              "description_ar": "Arabic description or empty string",
              "action_list": ["Policy/Document name 1", "Policy/Document name 2"]
            }
          ]
        }
      ]
    }
  ]
}

DOCUMENT TEXT:
"""

# ═══════════════════════════════════════════════════════════════════
# STAGE 1 — ONBOARDING
# ═══════════════════════════════════════════════════════════════════
if st.session_state.stage == "onboarding":
    st.markdown(f"""
<div class="ob-page">
  <div class="ob-card">
    <div class="ob-logo">{LOGO_IMG}</div>
    <h1 class="ob-title">Sahl Compliance Decoder</h1>
    <p class="ob-sub">Enterprise GRC Automation Engine</p>
    <hr class="ob-divider" style="border:none;border-top:1px solid #ede8f7;margin:0 0 28px;">
""", unsafe_allow_html=True)

    company   = st.text_input("Company Name",    placeholder="", key="ob_company")
    usr_email = st.text_input("Business Email",  placeholder="", key="ob_email")

    st.markdown('<p class="ob-label" style="margin-top:18px;">Which language would you like to view the compliance breakdown in?</p>', unsafe_allow_html=True)
    lang_choice = st.radio("", ["English", "Arabic"], horizontal=True, key="ob_lang", label_visibility="collapsed")

    st.markdown('<div style="margin-top:28px;">', unsafe_allow_html=True)
    if st.button("Let's Start", key="ob_start"):
        if not company.strip():
            st.error("Please enter your company name.")
        elif not usr_email.strip() or "@" not in usr_email:
            st.error("Please enter a valid business email.")
        else:
            st.session_state.company = company.strip()
            st.session_state.email   = usr_email.strip()
            st.session_state.lang    = lang_choice
            st.session_state.stage   = "upload"
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div></div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════
# STAGE 2 — UPLOAD
# ═══════════════════════════════════════════════════════════════════
elif st.session_state.stage == "upload":
    render_topbar()
    st.markdown('<div class="pg-wrap">', unsafe_allow_html=True)
    st.markdown(f'<h2 class="pg-heading">Import New Regulation</h2><p class="pg-sub">Upload the official PDF of the regulatory framework you want to decode.</p>', unsafe_allow_html=True)

    st.markdown('<div class="upload-card">', unsafe_allow_html=True)
    uploaded = st.file_uploader("", type="pdf", label_visibility="collapsed")
    st.markdown(f'<p style="font-size:0.8rem;color:#aaa;text-align:center;margin-top:8px;">PDF files only &nbsp;·&nbsp; Max 50MB</p>', unsafe_allow_html=True)

    if uploaded:
        st.markdown(f'<p style="font-size:0.85rem;color:#15803d;font-weight:600;margin-top:4px;">&#10003; {uploaded.name} ready</p>', unsafe_allow_html=True)
        if st.button("Decode Compliance"):
            st.session_state.pdf_bytes = uploaded.read()
            st.session_state.pdf_name  = uploaded.name
            st.session_state.stage     = "processing"
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown(f'<p style="font-size:0.82rem;color:#7c5cbf;margin-top:16px;">Welcome, <b>{st.session_state.company}</b>. Your decoded compliance will be available to review before submission.</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════
# STAGE 3 — PROCESSING (live step updates + elapsed time)
# ═══════════════════════════════════════════════════════════════════
elif st.session_state.stage == "processing":
    render_topbar("Analyzing")

    _, col, _ = st.columns([1, 4, 1])
    with col:
        st.markdown('<div style="margin-top:32px;">', unsafe_allow_html=True)
        proc_placeholder = st.empty()

        def show_steps(steps, elapsed=None):
            rows = ""
            icons = {"done": "✓", "active": "⟳", "pend": "○"}
            for label, status in steps:
                rows += f'<div class="step-row step-{status}"><span>{icons.get(status,"○")}</span>{label}</div>'
            t_html = f'<div class="proc-time">&#9201; {elapsed}s elapsed</div>' if elapsed else ""
            proc_placeholder.markdown(f"""
<div class="proc-card">
  <div class="proc-hd">
    <div class="proc-icon">&#9889;</div>
    <div>
      <p class="proc-title">Analyzing Document</p>
      <p class="proc-subtitle">This may take a few minutes for complex regulatory frameworks</p>
    </div>
  </div>
  {rows}
  {t_html}
  <p class="proc-note">Please keep this window open. Closing it will interrupt the analysis.</p>
</div>""", unsafe_allow_html=True)

        STEPS = [
            "Extracting text from document",
            "Running AI analysis",
            "Building compliance structure",
            "Finalizing breakdown",
        ]

        start = time.time()
        try:
            # Step 1 active
            show_steps([(s, "active" if i == 0 else "pend") for i, s in enumerate(STEPS)])
            doc      = fitz.open(stream=st.session_state.pdf_bytes, filetype="pdf")
            raw_text = "\n".join([p.get_text() for p in doc])

            # Step 2 active
            show_steps([(s, "done" if i < 1 else "active" if i == 1 else "pend") for i, s in enumerate(STEPS)])
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            model    = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(
                EXTRACTION_PROMPT + raw_text[:100000],
                generation_config={"response_mime_type": "application/json"}
            )
            data = json.loads(response.text)

            # Step 3 active
            show_steps([(s, "done" if i < 2 else "active" if i == 2 else "pend") for i, s in enumerate(STEPS)],
                       elapsed=int(time.time() - start))
            time.sleep(0.5)

            # Step 4 active
            show_steps([(s, "done" if i < 3 else "active") for i, s in enumerate(STEPS)],
                       elapsed=int(time.time() - start))
            time.sleep(0.4)

            elapsed = int(time.time() - start)
            show_steps([(s, "done") for s in STEPS], elapsed=elapsed)
            time.sleep(0.6)

            st.session_state.data    = data
            st.session_state.edited  = copy.deepcopy(data)
            st.session_state.elapsed = elapsed
            st.session_state.stage   = "results"
            st.rerun()

        except Exception as e:
            err = str(e).lower()
            proc_placeholder.empty()
            if any(k in err for k in ["quota", "rate limit", "resource_exhausted", "429"]):
                st.markdown('<div class="quota-box">&#9203; Daily processing limit reached.<br>Please try again after 24 hours.</div>', unsafe_allow_html=True)
            else:
                st.error(f"Processing failed: {e}")
            if st.button("Go back"):
                st.session_state.stage = "upload"
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════
# STAGE 4 — RESULTS
# ═══════════════════════════════════════════════════════════════════
elif st.session_state.stage == "results" and not st.session_state.submitted:
    render_topbar()
    is_ar    = st.session_state.lang == "Arabic"
    data     = st.session_state.edited
    chapters = data.get("chapters", [])
    total_articles = sum(len(ch.get("articles", [])) for ch in chapters)

    st.markdown('<div class="pg-wrap" style="max-width:860px;">', unsafe_allow_html=True)

    # Results top strip
    c1, c2 = st.columns([3, 2])
    with c1:
        st.markdown(f"""
<div style="padding-top:8px;">
  <h2 style="font-size:1.15rem;font-weight:800;color:#0d0020;margin:0 0 4px;letter-spacing:-0.015em;">{data.get('framework_name','Compliance Framework')}</h2>
  <p style="font-size:0.84rem;color:#7c5cbf;margin:0;">{len(chapters)} chapters &nbsp;·&nbsp; {total_articles} articles &nbsp;·&nbsp; Decoded in {st.session_state.elapsed}s</p>
</div>""", unsafe_allow_html=True)
    with c2:
        bc1, bc2, bc3 = st.columns(3)
        with bc1:
            edit_lbl = "Preview" if st.session_state.edit_mode else "Edit"
            if st.button(edit_lbl):
                st.session_state.edit_mode = not st.session_state.edit_mode
                st.rerun()
        with bc2:
            if st.button("New Scan"):
                for k in ["data","edited","pdf_bytes","pdf_name","elapsed","submitted","edit_mode"]:
                    st.session_state.pop(k, None)
                st.session_state.stage = "upload"
                st.rerun()
        with bc3:
            submit_btn = st.button("Submit", type="primary")

    st.markdown('<hr class="div">', unsafe_allow_html=True)

    # ── Edit mode ───────────────────────────────────────────────────
    if st.session_state.edit_mode:
        st.info("Edit any field below, then click Submit when ready.")
        new_chapters = []
        for ci, ch in enumerate(chapters):
            st.markdown(f"#### Chapter {ch.get('chapter_id','')}")
            cc1, cc2 = st.columns(2)
            ch_en = cc1.text_input("Chapter Title (EN)", value=ch.get("chapter_title_en",""), key=f"ch_en_{ci}")
            ch_ar = cc2.text_input("Chapter Title (AR)", value=ch.get("chapter_title_ar",""), key=f"ch_ar_{ci}")
            new_articles = []
            for ai, art in enumerate(ch.get("articles", [])):
                with st.expander(f"Article {art.get('article_id','')} — {art.get('article_title_en','')[:55]}"):
                    a1, a2 = st.columns(2)
                    art_id  = a1.text_input("Article ID",     value=art.get("article_id",""),       key=f"a_id_{ci}_{ai}")
                    art_en  = a1.text_input("Title (EN)",      value=art.get("article_title_en",""), key=f"a_en_{ci}_{ai}")
                    art_ar  = a2.text_input("Title (AR)",      value=art.get("article_title_ar",""), key=f"a_ar_{ci}_{ai}")
                    desc_en = a1.text_area("Description (EN)", value=art.get("description_en",""),   key=f"d_en_{ci}_{ai}", height=90)
                    desc_ar = a2.text_area("Description (AR)", value=art.get("description_ar",""),   key=f"d_ar_{ci}_{ai}", height=90)
                    new_controls = []
                    for ki, ctrl in enumerate(art.get("controls", [])):
                        st.markdown(f"**Control {ki+1}**")
                        k1, k2 = st.columns(2)
                        ct_en = k1.text_input("Control (EN)",  value=ctrl.get("control_title_en",""), key=f"ct_en_{ci}_{ai}_{ki}")
                        ct_ar = k2.text_input("Control (AR)",  value=ctrl.get("control_title_ar",""), key=f"ct_ar_{ci}_{ai}_{ki}")
                        cd_en = k1.text_area("Desc (EN)",      value=ctrl.get("description_en",""),   key=f"cd_en_{ci}_{ai}_{ki}", height=75)
                        cd_ar = k2.text_area("Desc (AR)",      value=ctrl.get("description_ar",""),   key=f"cd_ar_{ci}_{ai}_{ki}", height=75)
                        araw  = ", ".join(ctrl.get("action_list",[]))
                        aedit = st.text_input("Action List (comma separated)", value=araw, key=f"al_{ci}_{ai}_{ki}")
                        new_controls.append({
                            "control_title_en": ct_en, "control_title_ar": ct_ar,
                            "description_en": cd_en,   "description_ar": cd_ar,
                            "action_list": [x.strip() for x in aedit.split(",") if x.strip()]
                        })
                    new_articles.append({
                        "article_id": art_id, "article_title_en": art_en, "article_title_ar": art_ar,
                        "description_en": desc_en, "description_ar": desc_ar, "controls": new_controls
                    })
            new_chapters.append({
                "chapter_id": ch.get("chapter_id",""), "chapter_title_en": ch_en,
                "chapter_title_ar": ch_ar, "articles": new_articles
            })
        st.session_state.edited = {**data, "chapters": new_chapters}

    # ── Preview mode ────────────────────────────────────────────────
    else:
        for ch in chapters:
            ch_title = ch.get("chapter_title_ar" if is_ar else "chapter_title_en", "")
            st.markdown(f"""
<div class="chapter-block">
  <span class="chapter-pill">Chapter {ch.get('chapter_id','')}</span>
  <div class="chapter-title">{ch_title}</div>""", unsafe_allow_html=True)
            for art in ch.get("articles", []):
                a_t = art.get("article_title_ar" if is_ar else "article_title_en", "")
                a_d = art.get("description_ar"   if is_ar else "description_en",   "")
                st.markdown(f"""
  <div class="art-block">
    <div class="art-id">Article {art.get('article_id','')}</div>
    <div class="art-title">{a_t}</div>
    <div class="art-desc">{a_d}</div>""", unsafe_allow_html=True)
                for ctrl in art.get("controls", []):
                    c_t = ctrl.get("control_title_ar" if is_ar else "control_title_en", "")
                    c_d = ctrl.get("description_ar"   if is_ar else "description_en",   "")
                    pills = "".join(f'<span class="act-pill">&#128206; {a}</span>' for a in ctrl.get("action_list",[]))
                    st.markdown(f"""
    <div class="ctrl-block">
      <div class="ctrl-title">&#128274; {c_t}</div>
      <div class="ctrl-desc">{c_d}</div>
      {"<div>" + pills + "</div>" if pills else ""}
    </div>""", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    # ── Submit ───────────────────────────────────────────────────────
    if submit_btn:
        final = st.session_state.edited
        with st.spinner("Sending to Sahl team..."):
            try:
                lines = [
                    f"Company  : {st.session_state.company}",
                    f"Email    : {st.session_state.email}",
                    f"File     : {st.session_state.get('pdf_name','N/A')}",
                    f"Framework: {final.get('framework_name','')}",
                    f"Language : {st.session_state.lang}",
                    "","="*60,"COMPLIANCE BREAKDOWN","="*60,
                ]
                for ch in final.get("chapters",[]):
                    lines += ["", f"CHAPTER {ch.get('chapter_id','')}: {ch.get('chapter_title_en','')}"]
                    if ch.get("chapter_title_ar"):
                        lines.append(f"  (AR): {ch['chapter_title_ar']}")
                    for art in ch.get("articles",[]):
                        lines += [
                            f"  Article {art.get('article_id','')}: {art.get('article_title_en','')}",
                            f"  Desc: {art.get('description_en','')}",
                        ]
                        for ctrl in art.get("controls",[]):
                            lines += [
                                f"    Control : {ctrl.get('control_title_en','')}",
                                f"    Desc    : {ctrl.get('description_en','')}",
                                f"    Actions : {', '.join(ctrl.get('action_list',[]))}","",
                            ]
                msg = MIMEMultipart()
                msg["From"]    = st.secrets["EMAIL_USER"]
                msg["To"]      = "product@getsahl.io"
                msg["Subject"] = f"Compliance Submission — {st.session_state.company} — {final.get('framework_name','')}"
                msg.attach(MIMEText("\n".join(lines), "plain", "utf-8"))
                if st.session_state.get("pdf_bytes"):
                    part = MIMEBase("application","octet-stream")
                    part.set_payload(st.session_state.pdf_bytes)
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", f"attachment; filename={st.session_state.get('pdf_name','compliance.pdf')}")
                    msg.attach(part)
                with smtplib.SMTP("smtp.gmail.com", 587) as srv:
                    srv.starttls()
                    srv.login(st.secrets["EMAIL_USER"], st.secrets["EMAIL_PASSWORD"])
                    srv.send_message(msg)
                st.session_state.submitted = True
                st.session_state.stage     = "submitted"
                st.rerun()
            except Exception as e:
                st.error(f"Failed to send — {e}")

    st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════
# STAGE 5 — SUCCESS
# ═══════════════════════════════════════════════════════════════════
elif st.session_state.stage == "submitted":
    render_topbar()
    st.markdown(f"""
<div style="display:flex;justify-content:center;padding:40px 20px;">
  <div class="success-card">
    <div style="font-size:2.5rem;margin-bottom:16px;">&#10003;</div>
    <h3>Submission Received</h3>
    <p>
      Thank you, <b>{st.session_state.company}</b>.<br>
      Your compliance framework has been sent to the Sahl team.<br>
      It will be added to the platform within <b>1&ndash;2 business days</b>.<br>
      We will reach out to <b>{st.session_state.email}</b> once it is live.
    </p>
  </div>
</div>""", unsafe_allow_html=True)

    _, cc, _ = st.columns([2,1,2])
    with cc:
        if st.button("Start New Submission"):
            for k in ["data","edited","pdf_bytes","pdf_name","elapsed","submitted","edit_mode"]:
                st.session_state.pop(k, None)
            st.session_state.stage = "upload"
            st.rerun()
