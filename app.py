import streamlit as st
import fitz
import google.generativeai as genai
import json
import smtplib
from email.message import EmailMessage
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

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
        color: #4b0082;
        font-weight: 800;
        font-size: 1.1rem;
        letter-spacing: -0.02em;
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
    [data-testid="stSidebar"] input:focus {
        border-color: #8a2be2 !important;
        box-shadow: 0 0 0 3px rgba(138,43,226,0.12) !important;
    }

    h1 {
        color: #3a0066 !important;
        font-weight: 800 !important;
        letter-spacing: -0.03em;
    }
    h2, h3 {
        color: #4b0082 !important;
        font-weight: 700 !important;
    }

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
    .stButton > button:hover,
    .stFormSubmitButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 18px rgba(138,43,226,0.35) !important;
    }

    [data-testid="stFileUploaderDropzone"] {
        background: #ffffff !important;
        border: 1.5px dashed #c9a8f0 !important;
        border-radius: 14px !important;
    }

    .saas-card {
        background: linear-gradient(135deg, #ffffff 0%, #fcf9ff 100%);
        padding: 22px 26px;
        border-radius: 16px;
        border-left: 5px solid #8a2be2;
        box-shadow: 0 4px 16px rgba(138,43,226,0.08);
        margin-bottom: 16px;
    }
    .saas-card h4 {
        color: #4b0082;
        margin: 0 0 10px 0;
        font-size: 1.05rem;
        font-weight: 700;
    }
    .saas-card p {
        color: #3d3656;
        margin: 6px 0;
        line-height: 1.5;
    }
    .saas-card code {
        background: #f3e8ff;
        color: #6a1cb0;
        padding: 2px 8px;
        border-radius: 6px;
        font-weight: 600;
    }

    .hero-banner {
        background: linear-gradient(135deg, #8a2be2 0%, #4b0082 100%);
        border-radius: 20px;
        padding: 34px 38px;
        margin-bottom: 28px;
        box-shadow: 0 8px 28px rgba(75,0,130,0.18);
    }
    .hero-banner h1 {
        color: #ffffff !important;
        margin: 0 0 6px 0 !important;
    }
    .hero-banner p {
        color: #e6d6fc;
        margin: 0;
        font-size: 1.05rem;
    }

    .quota-notice {
        background: #fff7ed;
        border: 1.5px solid #fed7aa;
        border-radius: 14px;
        padding: 20px 24px;
        color: #9a3412;
        font-weight: 600;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)


apply_saas_theme()

# ── Session state ──────────────────────────────────────────────────────
if "initialized" not in st.session_state:
    st.session_state.initialized = False

# ── Sidebar ────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Configuration")
    with st.form("onboarding"):
        company = st.text_input("🏢 Company Name")
        email = st.text_input("📧 Business Email")
        lang = st.radio("UI Language", ["English", "العربية"], horizontal=True)
        submitted = st.form_submit_button("Initialize Workspace")

    if submitted:
        st.session_state.initialized = True
        st.session_state.company = company
        st.session_state.email = email
        st.session_state.lang = lang
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
uploaded_file = st.file_uploader("Upload Regulatory Framework (PDF)", type="pdf")

if uploaded_file:
    if st.button("🚀 Execute Audit"):
        with st.spinner("Decoding and mapping controls..."):
            try:
                doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
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
                st.session_state.data = json.loads(response.text)
                st.success(f"Audit Complete for {st.session_state.company}!")

            except Exception as e:
                err_str = str(e).lower()
                is_quota = (
                    "quota" in err_str
                    or "rate limit" in err_str
                    or "resource_exhausted" in err_str
                    or "429" in err_str
                )
                if is_quota:
                    st.markdown("""
                    <div class="quota-notice">
                        ⏳ We've hit today's processing limit.<br>
                        Please try again after 24 hours.
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.error("Something went wrong while processing your document. Please try again.")

# ── Display results ────────────────────────────────────────────────────
if "data" in st.session_state:
    controls = st.session_state.data.get("controls", [])
    if not controls:
        st.warning("No controls were extracted. Please try uploading the document again.")
    else:
        for item in controls:
            title = item.get("title_en", "") if st.session_state.lang == "English" else item.get("title_ar", "")
            desc = item.get("description_en", "") if st.session_state.lang == "English" else item.get("description_ar", "")
            st.markdown(f"""
            <div class="saas-card">
                <h4>{item.get('id', '')} - {title}</h4>
                <p><b>Description:</b> {desc}</p>
                <p><b>Policy Suggestion:</b> <code>{item.get('policy_mapping', '')}</code></p>
            </div>
            """, unsafe_allow_html=True)


# ── Helper functions ───────────────────────────────────────────────────
def generate_pdf(data, company_name):
    filename = f"{company_name}_Report.pdf"
    c = canvas.Canvas(filename, pagesize=letter)
    c.drawString(100, 750, f"Compliance Audit: {company_name}")
    y = 700
    for item in data:
        c.drawString(50, y, f"Control: {item.get('title_en', '')}")
        y -= 30
    c.save()
    return filename


def send_email(user_email, pdf_path, company_name):
    msg = EmailMessage()
    msg["Subject"] = f"Sahl Compliance Report - {company_name}"
    msg["From"] = st.secrets["EMAIL_USER"]
    msg["To"] = user_email
    msg.set_content("Attached is your professional audit report.")
    with open(pdf_path, "rb") as f:
        msg.add_attachment(f.read(), maintype="application", subtype="pdf", filename=pdf_path)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(st.secrets["EMAIL_USER"], st.secrets["EMAIL_PASSWORD"])
        smtp.send_message(msg)