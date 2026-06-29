import streamlit as st
from supabase import create_client

supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

_LOGO_B64 = "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"

def login_ui():
    # ── Hide sidebar + Streamlit chrome ───────────────────────────
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
*{box-sizing:border-box;}
html,body,[class*="css"]{font-family:'Inter',sans-serif!important;}
[data-testid="stSidebar"]{display:none!important;}
[data-testid="collapsedControl"]{display:none!important;}
#MainMenu{visibility:hidden;}footer{visibility:hidden;}header{visibility:hidden;}
.stApp{background:linear-gradient(145deg,#0d0020 0%,#1a0040 40%,#2d006b 100%)!important;min-height:100vh;}
.main .block-container{padding:0!important;max-width:100%!important;}

/* Input fields */
.stTextInput input{
  background:#1e0845!important;
  border:1.5px solid #3d1a7a!important;
  border-radius:12px!important;
  color:#f0e8ff!important;
  padding:0.78rem 1.1rem!important;
  font-size:0.95rem!important;
  transition:all 0.18s!important;
}
.stTextInput input:focus{
  border-color:#8a2be2!important;
  box-shadow:0 0 0 3px rgba(138,43,226,0.2)!important;
  background:#200f4a!important;
}
.stTextInput input::placeholder{color:#6b4fa0!important;}
.stTextInput label{
  font-weight:600!important;
  color:#c4a8f0!important;
  font-size:0.82rem!important;
  letter-spacing:0.04em!important;
  text-transform:uppercase!important;
  margin-bottom:6px!important;
}

/* Login button */
.stButton>button{
  background:linear-gradient(135deg,#8a2be2 0%,#5b10b0 100%)!important;
  color:#fff!important;border:none!important;border-radius:12px!important;
  font-weight:700!important;font-size:0.97rem!important;
  padding:0.82rem 1.5rem!important;width:100%!important;
  box-shadow:0 6px 24px rgba(138,43,226,0.45)!important;
  letter-spacing:0.01em!important;transition:all 0.18s!important;
  margin-top:8px!important;
}
.stButton>button:hover{
  transform:translateY(-2px)!important;
  box-shadow:0 10px 32px rgba(138,43,226,0.55)!important;
}

/* Error override */
.stAlert{border-radius:12px!important;background:#2d0a0a!important;border:1px solid #7f1d1d!important;}

/* Card */
.login-page{
  min-height:100vh;display:flex;align-items:center;
  justify-content:center;padding:40px 20px;
}
.login-card{
  background:rgba(255,255,255,0.04);
  backdrop-filter:blur(20px);
  -webkit-backdrop-filter:blur(20px);
  border:1px solid rgba(255,255,255,0.08);
  border-radius:28px;
  padding:52px 52px 44px;
  width:100%;max-width:440px;
  box-shadow:0 32px 80px rgba(0,0,0,0.5);
}
.login-logo{text-align:center;margin-bottom:28px;}
.login-title{
  font-size:1.55rem;font-weight:800;color:#ffffff;
  text-align:center;margin:0 0 6px;letter-spacing:-0.025em;
}
.login-sub{
  font-size:0.88rem;color:#9b77d1;
  text-align:center;margin-bottom:36px;font-weight:400;
}
.login-divider{
  border:none;border-top:1px solid rgba(255,255,255,0.07);margin:26px 0;
}
.login-footer{
  text-align:center;font-size:0.78rem;
  color:#6b4fa0;margin-top:24px;letter-spacing:0.01em;
}
</style>
""", unsafe_allow_html=True)

    # ── Outer wrapper + card open ─────────────────────────────────
    st.markdown(f"""
<div class="login-page">
  <div class="login-card">
    <div class="login-logo">
      <img src="data:image/png;base64,{_LOGO_B64}"
           style="height:52px;filter:drop-shadow(0 0 18px rgba(138,43,226,0.5));">
    </div>
    <h1 class="login-title">Welcome to Sahl</h1>
    <p class="login-sub">Sign in to access the GRC Compliance Decoder</p>
    <hr class="login-divider">
""", unsafe_allow_html=True)

    # ── Form fields (Streamlit widgets inside the card) ───────────
    email    = st.text_input("Email Address",    placeholder="you@company.com", key="li_email")
    password = st.text_input("Password",         placeholder="••••••••••••",    key="li_pass", type="password")

    if st.button("Sign In"):
        if not email.strip() or not password.strip():
            st.error("Please enter your email and password.")
        else:
            try:
                res = supabase.auth.sign_in_with_password(
                    {"email": email.strip(), "password": password.strip()}
                )
                st.session_state.user = res.user
                st.rerun()
            except Exception:
                st.error("Invalid email or password. Please try again.")

    # ── Card close + footer ───────────────────────────────────────
    st.markdown("""
    <p class="login-footer">
      Sahl GRC &nbsp;·&nbsp; Enterprise Compliance Automation<br>
      <span style="color:#4a2f7a;">Secure &nbsp;·&nbsp; Encrypted &nbsp;·&nbsp; MENA-Ready</span>
    </p>
  </div>
</div>
""", unsafe_allow_html=True)
