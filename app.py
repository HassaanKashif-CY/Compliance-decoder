import streamlit as st
import fitz
import google.generativeai as genai
import json
import smtplib
import copy
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

st.set_page_config(page_title="Sahl | GRC Auditor", page_icon="⚖️", layout="wide")


def apply_theme():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background: linear-gradient(180deg, #faf8ff 0%, #f5f2fc 100%); }

    [data-testid="stSidebar"] { background:#fff; border-right:1px solid #eee6fb; }
    [data-testid="stSidebar"] .stMarkdown h2 { color:#4b0082; font-weight:800; }
    [data-testid="stSidebar"] label { font-weight:600 !important; color:#3d3656 !important; font-size:0.85rem !important; }
    [data-testid="stSidebar"] input { border-radius:10px !important; border:1.5px solid #e4d9f7 !important; }

    h1 { color:#3a0066 !important; font-weight:800 !important; letter-spacing:-0.03em; }
    h2, h3 { color:#4b0082 !important; font-weight:700 !important; }

    .stButton > button, .stFormSubmitButton > button {
        background: linear-gradient(135deg,#8a2be2 0%,#6a1cb0 100%) !important;
        color:#fff !important; border:none !important; border-radius:10px !important;
        font-weight:600 !important; padding:0.55rem 1.2rem !important;
        box-shadow:0 4px 14px rgba(138,43,226,0.25) !important;
        transition:all 0.15s ease-in-out !important;
    }
    .stButton > button:hover { transform:translateY(-1px); box-shadow:0 6px 18px rgba(138,43,226,0.35) !important; }

    [data-testid="stFileUploaderDropzone"] {
        background:#fff !important; border:1.5px dashed #c9a8f0 !important; border-radius:14px !important;
    }

    .hero-banner {
        background:linear-gradient(135deg,#8a2be2 0%,#4b0082 100%);
        border-radius:20px; padding:34px 38px; margin-bottom:28px;
        box-shadow:0 8px 28px rgba(75,0,130,0.18);
    }
    .hero-banner h1 { color:#fff !important; margin:0 0 6px 0 !important; }
    .hero-banner p { color:#e6d6fc; margin:0; font-size:1.05rem; }

    /* Chapter block */
    .chapter-block {
        background:#fff; border-radius:18px; padding:24px 28px;
        margin-bottom:24px; border:1.5px solid #eee6fb;
        box-shadow:0 4px 16px rgba(138,43,226,0.06);
    }
    .chapter-label {
        display:inline-block; background:#f3e8ff; color:#6a1cb0;
        font-weight:700; font-size:0.78rem; padding:3px 12px;
        border-radius:20px; margin-bottom:10px; letter-spacing:0.04em;
        text-transform:uppercase;
    }
    .chapter-title { color:#3a0066; font-weight:800; font-size:1.15rem; margin:0 0 16px 0; }

    /* Article block */
    .article-block {
        border-left:4px solid #8a2be2; padding:14px 18px;
        margin-bottom:14px; border-radius:0 12px 12px 0;
        background:linear-gradient(135deg,#faf8ff 0%,#f5f2fc 100%);
    }
    .article-id { color:#8a2be2; font-weight:700; font-size:0.85rem; }
    .article-title { color:#4b0082; font-weight:700; font-size:1rem; margin:2px 0 8px 0; }
    .article-desc { color:#3d3656; font-size:0.9rem; line-height:1.6; margin-bottom:10px; }

    /* Control block */
    .control-block {
        background:#fff; border:1px solid #e4d9f7; border-radius:10px;
        padding:12px 16px; margin:8px 0;
    }
    .control-title { color:#6a1cb0; font-weight:700; font-size:0.92rem; margin-bottom:6px; }
    .control-desc { color:#3d3656; font-size:0.87rem; line-height:1.5; margin-bottom:8px; }
    .action-item {
        display:inline-block; background:#f3e8ff; color:#6a1cb0;
        font-size:0.8rem; padding:3px 10px; border-radius:20px;
        margin:2px 4px 2px 0; font-weight:500;
    }

    .quota-notice {
        background:#fff7ed; border:1.5px solid #fed7aa; border-radius:14px;
        padding:20px 24px; color:#9a3412; font-weight:600; text-align:center;
    }
    .success-banner {
        background:linear-gradient(135deg,#f3e5f5 0%,#ede7f6 100%);
        border:1.5px solid #ce93d8; border-radius:16px;
        padding:32px; text-align:center; margin:20px 0;
    }
    .success-banner h3 { color:#4b0082 !important; margin:0 0 10px 0 !important; }
    .success-banner p { color:#6a1cb0; font-size:1rem; line-height:1.8; }
    hr.divider { border:none; border-top:1.5px solid #eee6fb; margin:24px 0; }
    </style>
    """, unsafe_allow_html=True)


apply_theme()

# ── Session defaults ────────────────────────────────────────────────────
for k, v in [("initialized", False), ("edit_mode", False), ("submitted", False)]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── Sidebar ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Configuration")
    with st.form("onboarding"):
        company   = st.text_input("🏢 Company Name")
        usr_email = st.text_input("📧 Business Email")
        lang      = st.radio("UI Language", ["English", "العربية"], horizontal=True)
        ok        = st.form_submit_button("Initialize Workspace")
    if ok:
        for k in ["data", "edited_data", "pdf_bytes", "pdf_name", "submitted", "edit_mode"]:
            st.session_state.pop(k, None)
        st.session_state.update(initialized=True, company=company,
                                email=usr_email, lang=lang)
        st.rerun()

# ── Hero ────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-banner">
  <h1>⚖️ Sahl Compliance Decoder</h1>
  <p>Enterprise GRC Automation Engine</p>
</div>""", unsafe_allow_html=True)

if not st.session_state.initialized:
    st.warning("Please initialize your workspace in the sidebar to proceed.")
    st.stop()

# ═══════════════════════════════════════════════════════════════════════
# SMART PROMPT — framework-agnostic, maps to Sahl hierarchy
# ═══════════════════════════════════════════════════════════════════════
EXTRACTION_PROMPT = """
You are an expert GRC analyst. Your job is to extract ANY compliance framework document
into a strict JSON structure that Sahl GRC platform uses.

IMPORTANT RULES:
- Different frameworks use different naming: GDPR uses "Chapter/Article", NCNICC/ECC uses
  "Domain/Sub-domain/Control", ISO 27001 uses "Clause/Control", PDPL uses "Chapter/Article",
  NCA uses "Domain/Sub-domain". YOU must intelligently detect the hierarchy and map it.
- Preserve ALL Arabic text exactly as it appears. Do NOT translate.
- If a field does not exist in the source, use empty string "".
- For action_list: suggest 2-3 realistic policy documents or evidence items a company
  would need to comply with this control (e.g. "Access Control Policy", "Risk Register").
- Return ONLY valid JSON. No markdown, no explanation, no extra keys.

OUTPUT SCHEMA (use exactly these key names every time):
{
  "framework_name": "detected framework name",
  "chapters": [
    {
      "chapter_id": "1",
      "chapter_title_en": "English chapter/domain title",
      "chapter_title_ar": "Arabic chapter/domain title or empty string",
      "articles": [
        {
          "article_id": "1.1",
          "article_title_en": "English article/sub-domain/clause title",
          "article_title_ar": "Arabic article title or empty string",
          "description_en": "English policy requirement text",
          "description_ar": "Arabic policy requirement text or empty string",
          "controls": [
            {
              "control_title_en": "Short action-oriented control name in English",
              "control_title_ar": "Short control name in Arabic or empty string",
              "description_en": "What the organization must implement",
              "description_ar": "Arabic description or empty string",
              "action_list": [
                "Required Policy or Document name 1",
                "Required Policy or Document name 2"
              ]
            }
          ]
        }
      ]
    }
  ]
}

DOCUMENT TEXT:
"""


def run_extraction(raw_text: str) -> dict:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model    = genai.GenerativeModel("gemini-2.5-flash")
    prompt   = EXTRACTION_PROMPT + raw_text[:100000]
    response = model.generate_content(
        prompt, generation_config={"response_mime_type": "application/json"}
    )
    return json.loads(response.text)


# ── Upload ──────────────────────────────────────────────────────────────
if "data" not in st.session_state:
    uploaded = st.file_uploader("Upload Regulatory Framework (PDF)", type="pdf")
    if uploaded and st.button("🚀 Execute Audit"):
        with st.spinner("Decoding compliance framework..."):
            try:
                pdf_bytes = uploaded.read()
                doc       = fitz.open(stream=pdf_bytes, filetype="pdf")
                raw_text  = "\n".join([p.get_text() for p in doc])
                data      = run_extraction(raw_text)

                st.session_state.data      = data
                st.session_state.edited    = copy.deepcopy(data)
                st.session_state.pdf_bytes = pdf_bytes
                st.session_state.pdf_name  = uploaded.name
                st.success(f"✅ Audit complete for {st.session_state.company}!")
                st.rerun()
            except Exception as e:
                err = str(e).lower()
                if any(k in err for k in ["quota", "rate limit", "resource_exhausted", "429"]):
                    st.markdown('<div class="quota-notice">⏳ Daily processing limit reached.<br>Please try again after 24 hours.</div>',
                                unsafe_allow_html=True)
                else:
                    st.error(f"Processing failed: {e}")


# ═══════════════════════════════════════════════════════════════════════
# RESULTS
# ═══════════════════════════════════════════════════════════════════════
if "data" in st.session_state and not st.session_state.submitted:
    data   = st.session_state.edited
    is_ar  = st.session_state.lang == "العربية"
    chapters = data.get("chapters", [])

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([3, 1, 1])
    with c1:
        total_articles = sum(len(ch.get("articles", [])) for ch in chapters)
        st.markdown(f"### 📋 {data.get('framework_name','Compliance Framework')} — {len(chapters)} chapters · {total_articles} articles")
    with c2:
        toggle_label = "👁️ Preview" if st.session_state.edit_mode else "✏️ Edit"
        if st.button(toggle_label, use_container_width=True):
            # save edits before toggling if we're leaving edit mode
            st.session_state.edit_mode = not st.session_state.edit_mode
            st.rerun()
    with c3:
        submit_btn = st.button("📤 Submit to Sahl", use_container_width=True, type="primary")

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    # ── EDIT MODE ──────────────────────────────────────────────────────
    if st.session_state.edit_mode:
        st.info("✏️ Edit any field below. Click **Submit to Sahl** when ready.")

        new_chapters = []
        for ci, ch in enumerate(chapters):
            st.markdown(f"#### 📁 Chapter {ch.get('chapter_id','')}")
            cc1, cc2 = st.columns(2)
            ch_en = cc1.text_input("Chapter Title (EN)", value=ch.get("chapter_title_en",""), key=f"ch_en_{ci}")
            ch_ar = cc2.text_input("Chapter Title (AR)", value=ch.get("chapter_title_ar",""), key=f"ch_ar_{ci}")

            new_articles = []
            for ai, art in enumerate(ch.get("articles", [])):
                with st.expander(f"Article {art.get('article_id','')} — {art.get('article_title_en','')[:60]}"):
                    a1, a2 = st.columns(2)
                    art_id    = a1.text_input("Article ID",       value=art.get("article_id",""),       key=f"a_id_{ci}_{ai}")
                    art_en    = a1.text_input("Title (EN)",        value=art.get("article_title_en",""), key=f"a_en_{ci}_{ai}")
                    art_ar    = a2.text_input("Title (AR)",        value=art.get("article_title_ar",""), key=f"a_ar_{ci}_{ai}")
                    desc_en   = a1.text_area("Description (EN)",   value=art.get("description_en",""),   key=f"d_en_{ci}_{ai}", height=90)
                    desc_ar   = a2.text_area("Description (AR)",   value=art.get("description_ar",""),   key=f"d_ar_{ci}_{ai}", height=90)

                    new_controls = []
                    for ki, ctrl in enumerate(art.get("controls", [])):
                        st.markdown(f"**Control {ki+1}**")
                        k1, k2 = st.columns(2)
                        ct_en  = k1.text_input("Control Title (EN)",  value=ctrl.get("control_title_en",""), key=f"ct_en_{ci}_{ai}_{ki}")
                        ct_ar  = k2.text_input("Control Title (AR)",  value=ctrl.get("control_title_ar",""), key=f"ct_ar_{ci}_{ai}_{ki}")
                        cd_en  = k1.text_area("Control Desc (EN)",    value=ctrl.get("description_en",""),   key=f"cd_en_{ci}_{ai}_{ki}", height=80)
                        cd_ar  = k2.text_area("Control Desc (AR)",    value=ctrl.get("description_ar",""),   key=f"cd_ar_{ci}_{ai}_{ki}", height=80)
                        actions_raw = ", ".join(ctrl.get("action_list", []))
                        actions_edit = st.text_input("Action List (comma separated)", value=actions_raw, key=f"al_{ci}_{ai}_{ki}")
                        new_controls.append({
                            "control_title_en": ct_en, "control_title_ar": ct_ar,
                            "description_en": cd_en,   "description_ar": cd_ar,
                            "action_list": [x.strip() for x in actions_edit.split(",") if x.strip()]
                        })
                    new_articles.append({
                        "article_id": art_id, "article_title_en": art_en, "article_title_ar": art_ar,
                        "description_en": desc_en, "description_ar": desc_ar, "controls": new_controls
                    })
            new_chapters.append({
                "chapter_id": ch.get("chapter_id",""), "chapter_title_en": ch_en,
                "chapter_title_ar": ch_ar, "articles": new_articles
            })

        # always sync edits to session state
        st.session_state.edited = {**data, "chapters": new_chapters}

    # ── PREVIEW MODE ───────────────────────────────────────────────────
    else:
        for ch in chapters:
            ch_title = ch.get("chapter_title_ar" if is_ar else "chapter_title_en", "")
            st.markdown(f"""
            <div class="chapter-block">
              <span class="chapter-label">Chapter {ch.get('chapter_id','')}</span>
              <div class="chapter-title">{ch_title}</div>
            """, unsafe_allow_html=True)

            for art in ch.get("articles", []):
                a_title = art.get("article_title_ar" if is_ar else "article_title_en", "")
                a_desc  = art.get("description_ar"   if is_ar else "description_en",   "")
                st.markdown(f"""
                <div class="article-block">
                  <div class="article-id">Article {art.get('article_id','')}</div>
                  <div class="article-title">{a_title}</div>
                  <div class="article-desc">{a_desc}</div>
                """, unsafe_allow_html=True)

                for ctrl in art.get("controls", []):
                    c_title   = ctrl.get("control_title_ar" if is_ar else "control_title_en", "")
                    c_desc    = ctrl.get("description_ar"   if is_ar else "description_en",   "")
                    actions   = ctrl.get("action_list", [])
                    pills     = "".join(f'<span class="action-item">📎 {a}</span>' for a in actions)
                    st.markdown(f"""
                    <div class="control-block">
                      <div class="control-title">🔒 {c_title}</div>
                      <div class="control-desc">{c_desc}</div>
                      {('<div>' + pills + '</div>') if pills else ''}
                    </div>""", unsafe_allow_html=True)

                st.markdown("</div>", unsafe_allow_html=True)  # close article-block
            st.markdown("</div>", unsafe_allow_html=True)      # close chapter-block

    # ── SUBMIT HANDLER ─────────────────────────────────────────────────
    if submit_btn:
        # in edit mode: session_state.edited is already up-to-date (synced above)
        # in preview mode: session_state.edited = original or previously saved edits
        final = st.session_state.edited
        with st.spinner("Sending to Sahl team..."):
            try:
                # build summary text
                lines = [
                    f"Company : {st.session_state.company}",
                    f"Email   : {st.session_state.email}",
                    f"File    : {st.session_state.get('pdf_name','N/A')}",
                    f"Framework: {final.get('framework_name','')}",
                    "", "=" * 60, "COMPLIANCE BREAKDOWN", "=" * 60,
                ]
                for ch in final.get("chapters", []):
                    lines += ["", f"CHAPTER {ch['chapter_id']}: {ch['chapter_title_en']}"]
                    if ch.get("chapter_title_ar"):
                        lines.append(f"  (AR): {ch['chapter_title_ar']}")
                    for art in ch.get("articles", []):
                        lines += [
                            f"  Article {art['article_id']}: {art['article_title_en']}",
                            f"  Description: {art.get('description_en','')}",
                        ]
                        for ctrl in art.get("controls", []):
                            lines += [
                                f"    Control: {ctrl.get('control_title_en','')}",
                                f"    Desc   : {ctrl.get('description_en','')}",
                                f"    Actions: {', '.join(ctrl.get('action_list',[]))}",
                            ]
                        lines.append("")

                body = "\n".join(lines)

                sender   = st.secrets["EMAIL_USER"]
                password = st.secrets["EMAIL_PASSWORD"]

                msg = MIMEMultipart()
                msg["From"]    = sender
                msg["To"]      = "product@getsahl.io"
                msg["Subject"] = f"Compliance Submission — {st.session_state.company} — {final.get('framework_name','')}"
                msg.attach(MIMEText(body, "plain", "utf-8"))

                if st.session_state.get("pdf_bytes"):
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(st.session_state.pdf_bytes)
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition",
                                    f"attachment; filename={st.session_state.get('pdf_name','compliance.pdf')}")
                    msg.attach(part)

                with smtplib.SMTP("smtp.gmail.com", 587) as srv:
                    srv.starttls()
                    srv.login(sender, password)
                    srv.send_message(msg)

                st.session_state.submitted = True
                st.rerun()

            except Exception as e:
                st.error(f"Failed to send — {e}")

# ── Success screen ──────────────────────────────────────────────────────
if st.session_state.submitted:
    st.markdown(f"""
    <div class="success-banner">
      <h3>✅ Submission Received!</h3>
      <p>
        Thank you, <b>{st.session_state.company}</b>.<br><br>
        Your compliance framework has been sent to the Sahl team.<br>
        It will be added to the platform within <b>1–2 business days</b>.<br><br>
        We'll reach out to <b>{st.session_state.email}</b> once it's live.
      </p>
    </div>""", unsafe_allow_html=True)

    if st.button("🔄 Start New Submission"):
        for k in ["data", "edited", "pdf_bytes", "pdf_name", "submitted", "edit_mode"]:
            st.session_state.pop(k, None)
        st.rerun()