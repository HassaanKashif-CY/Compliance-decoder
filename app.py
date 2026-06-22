import streamlit as st
import fitz
import google.generativeai as genai
import json
import smtplib
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

st.set_page_config(
    page_title="Sahl | GRC Auditor",
    page_icon="⚖️",
    layout="wide"
)


def apply_saas_theme():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background: linear-gradient(180deg, #faf8ff 0%, #f5f2fc 100%); }

    [data-testid="stSidebar"] {
        background: #ffffff;
        border-right: 1px solid #eee6fb;
    }
    [data-testid="stSidebar"] .stMarkdown h2 {
        color: #4b0082; font-weight: 800;
        font-size: 1.1rem; letter-spacing: -0.02em;
    }
    [data-testid="stSidebar"] label {
        font-weight: 600 !important;
        color: #3d3656 !important;
        font-size: 0.85rem !important;
    }
    [data-testid="stSidebar"] input,
    [data-testid="stSidebar"] textarea {
        border-radius: 10px !important;
        border: 1.5px solid #e4d9f7 !important;
    }

    h1 { color: #3a0066 !important; font-weight: 800 !important; letter-spacing: -0.03em; }
    h2, h3 { color: #4b0082 !important; font-weight: 700 !important; }

    .stButton > button,
    .stFormSubmitButton > button {
        background: linear-gradient(135deg, #8a2be2 0%, #6a1cb0 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        padding: 0.55rem 1.2rem !important;
        box-shadow: 0 4px 14px rgba(138,43,226,0.25) !important;
        transition: all 0.15s ease-in-out !important;
    }
    .stButton > button:hover { transform: translateY(-1px); box-shadow: 0 6px 18px rgba(138,43,226,0.35) !important; }

    [data-testid="stFileUploaderDropzone"] {
        background: #ffffff !important;
        border: 1.5px dashed #c9a8f0 !important;
        border-radius: 14px !important;
    }

    .saas-card {
        background: linear-gradient(135deg, #ffffff 0%, #fcf9ff 100%);
        padding: 22px 26px; border-radius: 16px;
        border-left: 5px solid #8a2be2;
        box-shadow: 0 4px 16px rgba(138,43,226,0.08);
        margin-bottom: 16px;
    }
    .saas-card h4 { color: #4b0082; margin: 0 0 10px 0; font-size: 1.05rem; font-weight: 700; }
    .saas-card p { color: #3d3656; margin: 6px 0; line-height: 1.5; }
    .saas-card code { background: #f3e8ff; color: #6a1cb0; padding: 2px 8px; border-radius: 6px; font-weight: 600; }

    .hero-banner {
        background: linear-gradient(135deg, #8a2be2 0%, #4b0082 100%);
        border-radius: 20px; padding: 34px 38px; margin-bottom: 28px;
        box-shadow: 0 8px 28px rgba(75,0,130,0.18);
    }
    .hero-banner h1 { color: #ffffff !important; margin: 0 0 6px 0 !important; }
    .hero-banner p { color: #e6d6fc; margin: 0; font-size: 1.05rem; }

    .quota-notice {
        background: #fff7ed; border: 1.5px solid #fed7aa;
        border-radius: 14px; padding: 20px 24px;
        color: #9a3412; font-weight: 600; text-align: center;
    }

    .success-banner {
        background: linear-gradient(135deg, #f3e5f5 0%, #ede7f6 100%);
        border: 1.5px solid #ce93d8; border-radius: 16px;
        padding: 28px 32px; text-align: center; margin: 20px 0;
    }
    .success-banner h3 { color: #4b0082 !important; margin: 0 0 8px 0 !important; }
    .success-banner p { color: #6a1cb0; margin: 0; font-size: 1rem; }

    .edit-card {
        background: #ffffff; border-radius: 14px;
        border: 1.5px solid #e4d9f7;
        padding: 20px 24px; margin-bottom: 16px;
        box-shadow: 0 2px 10px rgba(138,43,226,0.06);
    }
    .edit-card-header {
        color: #4b0082; font-weight: 700;
        font-size: 1rem; margin-bottom: 12px;
        padding-bottom: 10px; border-bottom: 1px solid #eee6fb;
    }

    .divider {
        border: none; border-top: 1.5px solid #eee6fb;
        margin: 28px 0;
    }

    textarea { border-radius: 10px !important; border: 1.5px solid #e4d9f7 !important; }
    textarea:focus { border-color: #8a2be2 !important; box-shadow: 0 0 0 3px rgba(138,43,226,0.1) !important; }
    </style>
    """, unsafe_allow_html=True)


apply_saas_theme()

# ── Session state ──────────────────────────────────────────────────────
for key in ["initialized", "edit_mode", "submitted_to_sahl"]:
    if key not in st.session_state:
        st.session_state[key] = False

# ── Sidebar ────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Configuration")
    with st.form("onboarding"):
        company  = st.text_input("🏢 Company Name")
        email    = st.text_input("📧 Business Email")
        lang     = st.radio("UI Language", ["English", "العربية"], horizontal=True)
        submitted = st.form_submit_button("Initialize Workspace")

    if submitted:
        st.session_state.initialized     = True
        st.session_state.company         = company
        st.session_state.email           = email
        st.session_state.lang            = lang
        st.session_state.edit_mode       = False
        st.session_state.submitted_to_sahl = False
        if "data" in st.session_state:
            del st.session_state["data"]
        if "edited_data" in st.session_state:
            del st.session_state["edited_data"]
        if "pdf_bytes" in st.session_state:
            del st.session_state["pdf_bytes"]
        if "pdf_name" in st.session_state:
            del st.session_state["pdf_name"]
        st.rerun()

# ── Hero banner ────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-banner">
    <h1>⚖️ Sahl Compliance Decoder</h1>
    <p>Enterprise GRC Automation Engine</p>
</div>
""", unsafe_allow_html=True)

if not st.session_state.initialized:
    st.warning("Please initialize your workspace in the sidebar to proceed.")
    st.stop()

# ── Upload & process ───────────────────────────────────────────────────
if not st.session_state.get("data"):
    uploaded_file = st.file_uploader("Upload Regulatory Framework (PDF)", type="pdf")

    if uploaded_file:
        if st.button("🚀 Execute Audit"):
            with st.spinner("Decoding and mapping controls..."):
                try:
                    pdf_bytes = uploaded_file.read()
                    st.session_state.pdf_bytes = pdf_bytes
                    st.session_state.pdf_name  = uploaded_file.name

                    doc      = fitz.open(stream=pdf_bytes, filetype="pdf")
                    raw_text = "\n".join([page.get_text() for page in doc])

                    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                    model = genai.GenerativeModel("gemini-2.5-flash")

                    prompt = f"""
Act as a Senior GRC Auditor. Extract the compliance framework from the document below.
Return ONLY valid JSON — no markdown, no explanation, no extra keys.

Required JSON structure:
{{
  "controls": [
    {{
      "id": "1.1.1",
      "title_ar": "Arabic title here",
      "title_en": "English title here",
      "description_ar": "Arabic description here",
      "description_en": "English description here",
      "policy_mapping": "Suggested policy name"
    }}
  ]
}}

DOCUMENT TEXT:
{raw_text[:100000]}
"""
                    response = model.generate_content(
                        prompt,
                        generation_config={"response_mime_type": "application/json"}
                    )
                    st.session_state.data        = json.loads(response.text)
                    st.session_state.edited_data = json.loads(response.text)
                    st.success(f"Audit Complete for {st.session_state.company}!")
                    st.rerun()

                except Exception as e:
                    err_str  = str(e).lower()
                    is_quota = any(k in err_str for k in ["quota", "rate limit", "resource_exhausted", "429"])
                    if is_quota:
                        st.markdown("""
                        <div class="quota-notice">
                            ⏳ We've hit today's processing limit.<br>
                            Please try again after 24 hours.
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.error("Something went wrong while processing your document. Please try again.")

# ── Results section ────────────────────────────────────────────────────
if "data" in st.session_state and not st.session_state.submitted_to_sahl:
    controls = st.session_state.edited_data.get("controls", [])

    if not controls:
        st.warning("No controls were extracted. Please try uploading the document again.")
    else:
        st.markdown("<hr class='divider'>", unsafe_allow_html=True)

        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.markdown(f"### 📋 Extracted Controls ({len(controls)} total)")
        with col2:
            edit_label = "✏️ Edit Controls" if not st.session_state.edit_mode else "👁️ Preview Mode"
            if st.button(edit_label, use_container_width=True):
                st.session_state.edit_mode = not st.session_state.edit_mode
                st.rerun()
        with col3:
            submit_label = "📤 Submit to Sahl"
            submit_clicked = st.button(submit_label, use_container_width=True)

        st.markdown("<hr class='divider'>", unsafe_allow_html=True)

        # ── EDIT MODE ──────────────────────────────────────────────
        if st.session_state.edit_mode:
            st.info("✏️ Edit any field below, then click **Submit to Sahl** when ready.")
            updated_controls = []

            for i, item in enumerate(controls):
                st.markdown(f"<div class='edit-card-header'>Control {item.get('id', i+1)}</div>", unsafe_allow_html=True)

                col_a, col_b = st.columns(2)
                with col_a:
                    new_id        = st.text_input("ID",            value=item.get("id", ""),          key=f"id_{i}")
                    new_title_en  = st.text_input("Title (EN)",    value=item.get("title_en", ""),    key=f"ten_{i}")
                    new_title_ar  = st.text_input("Title (AR)",    value=item.get("title_ar", ""),    key=f"tar_{i}")
                with col_b:
                    new_policy    = st.text_input("Policy Mapping", value=item.get("policy_mapping", ""), key=f"pm_{i}")
                    new_desc_en   = st.text_area("Description (EN)", value=item.get("description_en", ""), key=f"den_{i}", height=100)
                    new_desc_ar   = st.text_area("Description (AR)", value=item.get("description_ar", ""), key=f"dar_{i}", height=100)

                updated_controls.append({
                    "id":             new_id,
                    "title_en":       new_title_en,
                    "title_ar":       new_title_ar,
                    "description_en": new_desc_en,
                    "description_ar": new_desc_ar,
                    "policy_mapping": new_policy,
                })
                st.markdown("<hr class='divider'>", unsafe_allow_html=True)

            # live-update edited_data as user types
            st.session_state.edited_data = {"controls": updated_controls}

        # ── PREVIEW MODE ───────────────────────────────────────────
        else:
            for item in controls:
                title = item.get("title_en", "") if st.session_state.lang == "English" else item.get("title_ar", "")
                desc  = item.get("description_en", "") if st.session_state.lang == "English" else item.get("description_ar", "")
                st.markdown(f"""
                <div class="saas-card">
                    <h4>{item.get('id', '')} — {title}</h4>
                    <p><b>Description:</b> {desc}</p>
                    <p><b>Policy Suggestion:</b> <code>{item.get('policy_mapping', '')}</code></p>
                </div>
                """, unsafe_allow_html=True)

        # ── SUBMIT TO SAHL ─────────────────────────────────────────
        if submit_clicked:
            with st.spinner("Sending to Sahl team..."):
                try:
                    final_controls = st.session_state.edited_data.get("controls", [])

                    # Build plain-text summary
                    summary_lines = [
                        f"Company: {st.session_state.company}",
                        f"Email:   {st.session_state.email}",
                        f"File:    {st.session_state.get('pdf_name', 'N/A')}",
                        "",
                        "=" * 60,
                        "COMPLIANCE BREAKDOWN",
                        "=" * 60,
                    ]
                    for ctrl in final_controls:
                        summary_lines += [
                            "",
                            f"ID:              {ctrl.get('id', '')}",
                            f"Title (EN):      {ctrl.get('title_en', '')}",
                            f"Title (AR):      {ctrl.get('title_ar', '')}",
                            f"Description EN:  {ctrl.get('description_en', '')}",
                            f"Description AR:  {ctrl.get('description_ar', '')}",
                            f"Policy Mapping:  {ctrl.get('policy_mapping', '')}",
                            "-" * 40,
                        ]
                    summary_text = "\n".join(summary_lines)

                    # ── Send email with PDF attachment ─────────────
                    sender   = st.secrets["EMAIL_USER"]
                    password = st.secrets["EMAIL_PASSWORD"]
                    receiver = "product@getsahl.io"

                    msg = MIMEMultipart()
                    msg["From"]    = sender
                    msg["To"]      = receiver
                    msg["Subject"] = f"Compliance Submission — {st.session_state.company}"

                    msg.attach(MIMEText(summary_text, "plain", "utf-8"))

                    # attach original PDF if available
                    if st.session_state.get("pdf_bytes"):
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(st.session_state.pdf_bytes)
                        encoders.encode_base64(part)
                        part.add_header(
                            "Content-Disposition",
                            f"attachment; filename={st.session_state.get('pdf_name', 'compliance.pdf')}"
                        )
                        msg.attach(part)

                    with smtplib.SMTP("smtp.gmail.com", 587) as server:
                        server.starttls()
                        server.login(sender, password)
                        server.send_message(msg)

                    st.session_state.submitted_to_sahl = True
                    st.rerun()

                except Exception as e:
                    st.error(f"Failed to send. Please try again. ({e})")

# ── Post-submit success screen ─────────────────────────────────────────
if st.session_state.submitted_to_sahl:
    st.markdown(f"""
    <div class="success-banner">
        <h3>✅ Submission Received!</h3>
        <p>
            Thank you, <b>{st.session_state.company}</b>.<br><br>
            Your compliance framework has been sent to the Sahl team.<br>
            It will be added to the platform within <b>1–2 business days</b>.<br><br>
            We'll reach out to <b>{st.session_state.email}</b> once it's live.
        </p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🔄 Start New Submission"):
        for key in ["data", "edited_data", "pdf_bytes", "pdf_name", "submitted_to_sahl", "edit_mode"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()